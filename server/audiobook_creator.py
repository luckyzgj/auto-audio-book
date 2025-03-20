import os
import json
import time
import streamlit as st
import random
import requests
import threading
from config_manager import ConfigManager
from chapter_downloader import ChapterDownloader
from openai import OpenAI


# 初始化会话状态
if "extraction_task_running" not in st.session_state:
    st.session_state.extraction_task_running = False
if "extraction_thread" not in st.session_state:
    st.session_state.extraction_thread = None


def show_audiobook_creation_page(book_id):
    """显示有声书制作页面"""
    if not book_id:
        st.error("未选择书籍")
        return

    # 显示书籍信息
    book_info = get_book_info(book_id)
    st.header(f"《{book_info.get('name', book_id)}》有声书制作")

    # 根据当前选择的标签页显示不同内容
    if st.session_state.audiobook_tab == "novel_content":
        show_novel_content_tab(book_id)
    else:
        show_character_info_tab(book_id)


def get_book_info(book_id):
    """获取书籍信息"""
    info_file = os.path.join("data", book_id, "info.json")
    if os.path.exists(info_file):
        with open(info_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"id": book_id, "name": book_id}


def get_chapters(book_id):
    """获取书籍章节列表"""
    chapters_file = os.path.join("data", book_id, "chapters.json")
    if os.path.exists(chapters_file):
        with open(chapters_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def get_chapter_dialogue(book_id, chapter_index, chapter_title):
    """获取章节对话数据"""
    # 构建文件名
    safe_title = "".join(c if c.isalnum() or c in "- " else "_" for c in chapter_title)
    dialogue_file = os.path.join("audio", book_id, "chapter", f"{safe_title}.json")

    if os.path.exists(dialogue_file):
        try:
            with open(dialogue_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def get_chapter_word_count(book_id, chapter):
    """获取章节字数"""
    downloader = ChapterDownloader(book_id)
    return downloader.get_chapter_word_count(chapter)


def format_word_count(count):
    """格式化字数显示"""
    if count >= 10000:
        return f"{count/10000:.2f}万字"
    else:
        return f"{count}字"


def show_novel_content_tab(book_id):
    """显示小说内容标签页"""
    st.subheader("章节列表")

    # 获取所有章节
    chapters = get_chapters(book_id)

    if not chapters:
        st.warning("未找到章节信息")
        return

    # 遍历所有章节
    for i, chapter in enumerate(chapters):
        # 获取章节字数
        word_count = get_chapter_word_count(book_id, chapter)

        # 显示章节信息
        col1, col2 = st.columns([4, 1])

        with col1:
            st.write(
                f"**{i+1}. {chapter['chapter_title']}** ({format_word_count(word_count)})"
            )

        with col2:
            # 添加显示对话信息按钮
            if st.button("显示对话信息", key=f"dialogue_{i}"):
                # 获取对话数据
                dialogue_data = get_chapter_dialogue(
                    book_id, i, chapter["chapter_title"]
                )

                if dialogue_data:
                    # 显示对话数据
                    st.json(dialogue_data)
                else:
                    st.warning("还未提取对话数据")


def show_character_info_tab(book_id):
    """显示书籍角色信息提取与配置标签页"""
    st.subheader("角色信息提取与配置")

    # 检查状态文件
    status_file = os.path.join("data", book_id, "users", "extraction_status.json")
    task_status = "idle"  # 默认状态为空闲
    task = {
        "status": "idle",
        "progress": 0,
        "completed": 0,
        "total": 0,
        "succeeded": 0,
        "failed": 0,
        "errors": [],
        "result": None,
    }

    # 只有当状态文件存在时才读取状态
    if os.path.exists(status_file):
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                task = json.load(f)
                task_status = task.get("status", "idle")
        except Exception as e:
            st.error(f"读取状态文件出错: {str(e)}")

    # 角色信息目录路径和检查
    users_dir = os.path.join("data", book_id, "users")
    has_character_data = os.path.exists(users_dir) and any(
        f.endswith(".json") and f != "extraction_status.json"
        for f in os.listdir(users_dir)
        if os.path.isfile(os.path.join(users_dir, f))
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        # 只有当任务不在运行且没有活跃线程时，才启用按钮
        button_disabled = task_status == "running" or (
            st.session_state.extraction_thread is not None
            and st.session_state.extraction_thread.is_alive()
        )

        if st.button("一键提取全文角色信息", disabled=button_disabled):
            # 设置初始状态文件
            initial_status = {
                "status": "running",
                "progress": 0,
                "completed": 0,
                "total": len(get_chapters(book_id)),
                "succeeded": 0,
                "failed": 0,
                "errors": [],
                "result": None,
            }
            try:
                os.makedirs(os.path.dirname(status_file), exist_ok=True)
                with open(status_file, "w", encoding="utf-8") as f:
                    json.dump(initial_status, f, ensure_ascii=False, indent=2)
                    # 确保数据写入磁盘
                    f.flush()
                    os.fsync(f.fileno())

                # 创建并启动提取任务线程
                extraction_thread = threading.Thread(
                    target=process_chapters_in_thread,
                    args=(book_id,),
                    daemon=True,  # 设置为守护线程，这样当主程序退出时，线程也会退出
                )
                extraction_thread.start()

                # 保存线程引用到会话状态
                st.session_state.extraction_thread = extraction_thread

                # 立即刷新页面，确保按钮被禁用
                st.rerun()
            except Exception as e:
                st.error(f"创建状态文件失败: {str(e)}")
                return

    # 根据任务状态显示不同内容
    if task_status == "running":
        st.info("正在提取角色信息，请勿关闭页面...")

        # 显示进度
        progress_bar = st.progress(task.get("progress", 0))
        st.write(
            f"已处理: {task.get('completed', 0)}/{task.get('total', 0)} 章节 ({int(task.get('progress', 0)*100)}%)"
        )
        st.write(f"成功: {task.get('succeeded', 0)}, 失败: {task.get('failed', 0)}")

        # 添加自动刷新功能
        auto_refresh = st.checkbox("启用自动刷新", value=True)
        if auto_refresh:
            refresh_interval = st.slider("刷新间隔(秒)", 1, 30, 5)
            st.write(f"页面将每 {refresh_interval} 秒自动刷新一次")

            # 使用更高效的自动刷新方法
            refresh_html = f"""
            <script>
                // 使用更优雅的方式刷新
                var timer = setTimeout(function() {{
                    window.location.reload();
                }}, {refresh_interval * 1000});
                
                // 如果用户与页面交互，重置定时器
                document.addEventListener('click', function() {{
                    clearTimeout(timer);
                    timer = setTimeout(function() {{
                        window.location.reload();
                    }}, {refresh_interval * 1000});
                }});
            </script>
            """
            st.components.v1.html(refresh_html, height=0)

        # 添加手动刷新按钮
        if st.button("手动刷新状态"):
            st.rerun()

    elif task_status == "completed":
        st.success(task.get("result", "角色信息提取完成"))

        # 检查线程状态并清理
        if (
            st.session_state.extraction_thread is not None
            and not st.session_state.extraction_thread.is_alive()
        ):
            st.session_state.extraction_thread = None

        if st.button("清除状态"):
            try:
                os.remove(status_file)
                st.rerun()
            except Exception as e:
                st.error(f"删除状态文件失败: {str(e)}")

    # 显示错误信息（如果有）
    if task.get("errors") and len(task.get("errors", [])) > 0:
        with st.expander("查看错误详情", expanded=False):
            for error in task.get("errors", []):
                st.error(error)

    # 如果存在角色数据，显示角色列表
    if has_character_data:
        # 获取角色统计信息
        characters = compile_character_statistics(book_id)
        if characters:
            st.markdown("---")
            st.subheader(f"已识别出 {len(characters)} 个角色")
            show_character_list(book_id, characters)


def process_chapters_in_thread(book_id):
    """在独立线程中处理章节提取任务"""
    try:
        # 准备目录
        audio_dir = os.path.join("audio", book_id)
        chapter_dir = os.path.join(audio_dir, "chapter")
        os.makedirs(chapter_dir, exist_ok=True)

        users_dir = os.path.join("data", book_id, "users")
        os.makedirs(users_dir, exist_ok=True)

        # 获取配置和章节
        config_manager = ConfigManager()
        api_keys = config_manager.get_silica_api_keys()
        chapters = get_chapters(book_id)

        if not api_keys or not chapters:
            # 更新状态文件，标记为失败
            status_file = os.path.join(users_dir, "extraction_status.json")
            error_status = {
                "status": "completed",
                "progress": 0,
                "completed": 0,
                "total": len(chapters) if chapters else 0,
                "succeeded": 0,
                "failed": 0,
                "errors": ["未配置硅基流动API密钥或获取章节失败"],
                "result": "提取失败：未配置API密钥或章节获取失败",
            }
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(error_status, f, ensure_ascii=False, indent=2)
            return

        # 调用原始的处理函数
        process_chapters_sequential(
            book_id, chapters, api_keys, config_manager.get_silica_api_url()
        )
    except Exception as e:
        # 捕获线程中的任何异常，更新状态文件
        status_file = os.path.join("data", book_id, "users", "extraction_status.json")
        if os.path.exists(os.path.dirname(status_file)):
            error_status = {
                "status": "completed",
                "progress": 0,
                "completed": 0,
                "total": 0,
                "succeeded": 0,
                "failed": 0,
                "errors": [f"处理过程中发生错误: {str(e)}"],
                "result": "提取失败：处理过程中发生错误",
            }
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(error_status, f, ensure_ascii=False, indent=2)


def start_extraction_task(book_id):
    """启动提取角色信息的任务 - 单线程版本"""
    # 准备目录
    audio_dir = os.path.join("audio", book_id)
    chapter_dir = os.path.join(audio_dir, "chapter")
    os.makedirs(chapter_dir, exist_ok=True)

    users_dir = os.path.join("data", book_id, "users")
    os.makedirs(users_dir, exist_ok=True)

    # 获取配置和章节
    config_manager = ConfigManager()
    # 使用硅基流动API密钥，而不是Gemini API密钥
    api_keys = config_manager.get_silica_api_keys()
    chapters = get_chapters(book_id)

    if not api_keys or not chapters:
        st.error("未配置硅基流动API密钥或获取章节失败")
        return False

    # 使用单线程处理所有章节
    process_chapters_sequential(
        book_id, chapters, api_keys, config_manager.get_silica_api_url()
    )

    return True


# 修改原始函数只处理提取逻辑，不涉及UI
def process_chapters_sequential(book_id, chapters, api_keys, api_url):
    """以单线程方式顺序处理所有章节"""
    # 准备目录
    audio_dir = os.path.join("audio", book_id)
    chapter_dir = os.path.join(audio_dir, "chapter")
    os.makedirs(chapter_dir, exist_ok=True)

    users_dir = os.path.join("data", book_id, "users")
    os.makedirs(users_dir, exist_ok=True)

    # 创建状态文件
    status_file = os.path.join(users_dir, "extraction_status.json")

    # 检查哪些章节需要处理
    pending_chapters = []
    for i, chapter in enumerate(chapters):
        user_file = os.path.join(users_dir, f"{i+1}.json")
        if not os.path.exists(user_file) or os.path.getsize(user_file) == 0:
            pending_chapters.append((i, chapter))

    # 统计信息
    total = len(chapters)
    completed = total - len(pending_chapters)
    succeeded = completed
    failed = 0

    # 如果所有章节都已处理，直接完成
    if not pending_chapters:
        compile_character_info(book_id)
        status = {
            "status": "completed",
            "progress": 1.0,
            "completed": total,
            "total": total,
            "succeeded": total,
            "failed": 0,
            "result": "所有章节已处理完成",
        }
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
            # 确保数据写入磁盘
            f.flush()
            os.fsync(f.fileno())
        return

    # 写入初始状态
    status = {
        "status": "running",
        "progress": completed / total,
        "completed": completed,
        "total": total,
        "succeeded": succeeded,
        "failed": failed,
        "errors": [],
    }
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
        # 确保数据写入磁盘
        f.flush()
        os.fsync(f.fileno())

    # 使用第一个可用的API密钥
    if not api_keys:
        status["status"] = "completed"
        status["result"] = "未配置API密钥，无法处理"
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
            # 确保数据写入磁盘
            f.flush()
            os.fsync(f.fileno())
        return

    api_key = api_keys[0]  # 使用第一个API密钥

    # 循环处理每个章节
    for chapter_index, chapter in pending_chapters:
        try:
            # 处理章节
            success, message = extract_chapter_dialogue(
                api_key, api_url, book_id, chapter, chapter_index
            )

            # 更新统计信息
            completed += 1
            if success:
                succeeded += 1
            else:
                failed += 1
                status["errors"].append(message)

            # 更新状态文件
            status.update(
                {
                    "progress": completed / total,
                    "completed": completed,
                    "succeeded": succeeded,
                    "failed": failed,
                }
            )
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
                # 确保数据写入磁盘
                f.flush()
                os.fsync(f.fileno())

            # 强制延迟，避免API频率限制
            time.sleep(2)

        except Exception as e:
            # 处理异常
            completed += 1
            failed += 1
            error_msg = f"章节 {chapter_index+1}: 处理出错 - {str(e)}"
            status["errors"].append(error_msg)

            # 更新状态文件
            status.update(
                {
                    "progress": completed / total,
                    "completed": completed,
                    "succeeded": succeeded,
                    "failed": failed,
                }
            )
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
                # 确保数据写入磁盘
                f.flush()
                os.fsync(f.fileno())

            # 即使出错也要延迟，避免频率限制
            time.sleep(2)

    # 处理完成后汇总角色信息
    compile_character_info(book_id)

    # 写入最终状态
    final_status = {
        "status": "completed",
        "progress": 1.0,
        "completed": completed,
        "total": total,
        "succeeded": succeeded,
        "failed": failed,
        "result": f"角色信息提取完成，成功处理 {succeeded} 章，失败 {failed} 章",
    }
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(final_status, f, ensure_ascii=False, indent=2)
        # 确保数据写入磁盘
        f.flush()
        os.fsync(f.fileno())


def extract_chapter_dialogue(
    api_key, api_url, book_id, chapter, chapter_index, max_retries=3
):
    """提取单个章节的对话信息，带有重试机制"""
    # 获取章节内容
    downloader = ChapterDownloader(book_id)
    file_path = downloader.get_chapter_file_path(chapter)
    chapter_title = chapter.get("chapter_title", "未知章节")

    # 检查目标文件是否已存在
    users_dir = os.path.join("data", book_id, "users")
    user_file = os.path.join(users_dir, f"{chapter_index+1}.json")

    if os.path.exists(user_file) and os.path.getsize(user_file) > 0:
        return True, f"章节 {chapter_index+1} 已存在，跳过处理"

    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return False, f"章节 {chapter_index+1} ({chapter_title}) 文件不存在或为空"

    # 读取章节内容
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            chapter_content = f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, "r", encoding="gbk") as f:
                chapter_content = f.read()
        except Exception as e:
            return (
                False,
                f"读取章节 {chapter_index+1} ({chapter_title}) 内容出错: {str(e)}",
            )

    # 限制章节内容长度
    if len(chapter_content) > 50000:
        chapter_content = chapter_content[:50000] + "...(内容已截断)"

    # 构建提示词
    prompt = """
        我发给你的是一章小说，请帮我仔细分析出来每句话都是谁说的，然后以json的形式给我
        并且按照这个规则，给话语中添加一些标记使语言更加真实
        对于自然语言指令，在自然语言描述前添加一个特殊的结束标记""。这些描述涵盖了情感、说话速度、角色扮演和方言等方面。对于详细的指令，在文本标记之间插入音高爆发，使用像""和""这样的标记。此外，我们还对短语应用音高特征标记；例如：
        你能用快乐的情绪说吗？ 今天真的很开心，春节就要到了！我是如此的开心，春节就要到了！ 。
        请以json的形式给我
        type为角色的名字 sex为角色性别 text为 角色这句话，性别有 男 女 中，如果不知道是什么性别就选中性
        旁白固定式中性
        Use this JSON schema:
        Recipe ={
            type:"xxx",
            sex:"",
            text:"xxxxxxx"
        }
        Return: list[Recipe]
    """

    # 获取配置管理器
    config_manager = ConfigManager()

    # 重试循环
    for attempt in range(max_retries):
        try:
            # 从配置获取API密钥和URL
            gemini_api_key = config_manager.get_gemini_api_keys()[0]
            base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"

            client = OpenAI(api_key=gemini_api_key, base_url=f"{base_url}")

            # 发送请求
            response = client.chat.completions.create(
                model="gemini-2.0-flash-lite",
                messages=[
                    {"role": "user", "content": prompt},
                    {"role": "user", "content": chapter_content},
                ],
                temperature=0.2,
                top_p=0.8,
                n=1,
            )

            # 解析响应
            if response.choices and len(response.choices) > 0:
                text = response.choices[0].message.content

                # 提取JSON部分
                import re

                json_text = re.sub(r"```json\n?|\n?```", "", text)

                try:
                    dialogue_data = json.loads(json_text)

                    # 验证对话数据
                    if not isinstance(dialogue_data, list) or len(dialogue_data) == 0:
                        return (
                            False,
                            f"章节 {chapter_index+1}: 提取的数据不是有效的对话列表",
                        )

                    # 保存对话数据到两个位置，并检查保存结果
                    audio_save_result = save_chapter_dialogue_file(
                        book_id, chapter, dialogue_data
                    )
                    user_save_result = save_chapter_user_info(
                        book_id, chapter_index + 1, dialogue_data
                    )

                    if not audio_save_result or not user_save_result:
                        return (
                            False,
                            f"章节 {chapter_index+1}: 保存对话数据失败",
                        )

                    # 最后确认文件确实存在
                    if not os.path.exists(user_file) or os.path.getsize(user_file) == 0:
                        return (
                            False,
                            f"章节 {chapter_index+1}: 文件保存后验证失败",
                        )
                    return True, f"章节 {chapter_index+1}: 成功提取对话信息"
                except json.JSONDecodeError:
                    return False, f"章节 {chapter_index+1}: JSON解析失败"
                except Exception as e:
                    print(f"章节 {chapter_index+1}: 保存数据时出错: {str(e)}")
                    return (
                        False,
                        f"章节 {chapter_index+1}: 保存数据时出错: {str(e)}",
                    )

            else:
                return False, f"章节 {chapter_index+1}: API响应格式不正确"

        except Exception as e:
            if "429" in str(e):
                if attempt == max_retries - 1:
                    print(f"章节 {chapter_index+1}: API请求频率超限，请稍后再试")
                    return False, f"章节 {chapter_index+1}: API请求频率超限，请稍后再试"
            elif attempt == max_retries - 1:
                print(f"章节 {chapter_index+1} ({chapter_title}) 处理异常: {str(e)}")
                return (
                    False,
                    f"章节 {chapter_index+1} ({chapter_title}) 处理异常: {str(e)}",
                )

            # 指数退避等待
            wait_time = (2**attempt) * 2 + random.uniform(0, 1)
            if "429" in str(e):  # 对频率限制增加更长的等待时间
                wait_time = wait_time * 2
            time.sleep(wait_time)

    return False, f"章节 {chapter_index+1} ({chapter_title}) 达到最大重试次数"


def save_chapter_dialogue_file(book_id, chapter, dialogue_data):
    """保存章节对话数据到audio目录"""
    # 构建文件名
    chapter_title = chapter.get("chapter_title", "未知章节")
    safe_title = "".join(c if c.isalnum() or c in "- " else "_" for c in chapter_title)
    dialogue_file = os.path.join("audio", book_id, "chapter", f"{safe_title}.json")

    # 确保目录存在
    os.makedirs(os.path.dirname(dialogue_file), exist_ok=True)

    # 保存对话数据
    try:
        with open(dialogue_file, "w", encoding="utf-8") as f:
            json.dump(dialogue_data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"保存对话数据出错: {str(e)}")
        return False


def save_chapter_user_info(book_id, chapter_number, dialogue_data):
    """保存章节角色信息到users目录"""
    # 确保目录存在
    users_dir = os.path.join("data", book_id, "users")
    os.makedirs(users_dir, exist_ok=True)

    # 构建文件名
    user_file = os.path.join(users_dir, f"{chapter_number}.json")

    # 保存对话数据
    try:
        with open(user_file, "w", encoding="utf-8") as f:
            json.dump(dialogue_data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"保存角色信息出错: {str(e)}")
        return False


def compile_character_statistics(book_id):
    """从所有章节文件中汇总角色统计信息"""
    # 角色统计信息
    characters_info = {}

    # 章节文件目录路径
    users_dir = os.path.join("data", book_id, "users")

    # 确保目录存在
    if not os.path.exists(users_dir):
        return []

    # 遍历所有JSON文件
    for filename in os.listdir(users_dir):
        if not filename.endswith(".json") or filename == "extraction_status.json":
            continue

        file_path = os.path.join(users_dir, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                dialogues = json.load(f)

            # 处理每个对话
            for dialogue in dialogues:
                if not isinstance(dialogue, dict):
                    continue

                character = dialogue.get("type", "")
                gender = dialogue.get("sex", "")

                if character:
                    if character not in characters_info:
                        characters_info[character] = {
                            "name": character,
                            "gender": gender,
                            "lines_count": 0,
                        }

                    characters_info[character]["lines_count"] += 1

        except Exception as e:
            print(f"处理文件 {filename} 时出错: {str(e)}")

    # 转换为列表
    characters_list = list(characters_info.values())

    # 按台词数量降序排序
    characters_list.sort(key=lambda x: x["lines_count"], reverse=True)

    return characters_list


def compile_character_info(book_id):
    """汇总所有角色信息并保存到用户信息文件"""
    # 获取汇总的角色统计信息
    characters_list = compile_character_statistics(book_id)

    # 保存结果
    output_dir = os.path.join("data", book_id)
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "user_info.json")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(characters_list, f, ensure_ascii=False, indent=2)


def show_character_list(book_id, characters):
    """显示角色列表并允许设置语音"""
    # 初始化session state用于跟踪选中的角色
    if "selected_character" not in st.session_state:
        st.session_state.selected_character = None
        st.session_state.is_misc_characters = False
        st.session_state.misc_characters_list = None

    # 分为主要角色和杂毛角色
    main_characters = characters[:15] if len(characters) > 15 else characters
    misc_characters = characters[15:] if len(characters) > 15 else []

    # 显示主要角色
    st.subheader(f"主要角色 ({len(main_characters)}个)")

    # 使用自定义CSS使卡片更美观
    st.markdown(
        """
    <style>
    .character-card {
        border: 1px solid #eeeeee;
        border-radius: 5px;
        padding: 10px;
        margin: 5px;
        background-color: #f9f9f9;
    }
    .character-name {
        font-weight: bold;
        font-size: 1.1em;
    }
    .character-info {
        margin: 5px 0;
        color: #555555;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # 每行显示3个角色
    cols_per_row = 3

    # 计算需要多少行
    rows = (len(main_characters) + cols_per_row - 1) // cols_per_row

    # 显示主要角色卡片
    for row in range(rows):
        cols = st.columns(cols_per_row)

        for col_idx in range(cols_per_row):
            char_idx = row * cols_per_row + col_idx

            if char_idx < len(main_characters):
                char = main_characters[char_idx]
                name = char.get("name", "未知")
                gender = char.get("gender", "中")
                if gender == "中":
                    gender = "未知"
                lines_count = char.get("lines_count", 0)

                with cols[col_idx]:
                    # 创建卡片容器
                    with st.container():
                        # 角色信息
                        st.markdown(f"**{name}**")
                        st.markdown(f"性别: {gender} | 台词: {lines_count}句")

                        # 设置按钮
                        if st.button("设置语音", key=f"set_voice_{char_idx}"):
                            st.session_state.selected_character = char
                            st.session_state.is_misc_characters = False
                            st.session_state.misc_characters_list = None
                            st.rerun()

    # 显示杂毛角色部分
    if misc_characters:
        st.markdown("---")
        st.subheader(f"杂毛角色 ({len(misc_characters)}个)")

        total_misc_lines = sum(c.get("lines_count", 0) for c in misc_characters)
        st.info(f"杂毛角色总共有{total_misc_lines}句台词")

        # 为所有杂毛角色统一设置语音按钮
        if st.button("为所有杂毛角色设置统一语音模型", type="primary"):
            st.session_state.selected_character = {
                "name": "杂毛角色",
                "gender": "中",
            }
            st.session_state.is_misc_characters = True
            st.session_state.misc_characters_list = misc_characters
            st.rerun()

        # 显示详细杂毛角色列表（可折叠）
        with st.expander("查看所有杂毛角色详情", expanded=False):
            # 以小卡片网格形式显示杂毛角色
            misc_rows = (len(misc_characters) + cols_per_row - 1) // cols_per_row

            for row in range(misc_rows):
                misc_cols = st.columns(cols_per_row)

                for col_idx in range(cols_per_row):
                    char_idx = row * cols_per_row + col_idx

                    if char_idx < len(misc_characters):
                        char = misc_characters[char_idx]
                        name = char.get("name", "未知")
                        gender = char.get("gender", "中")
                        if gender == "中":
                            gender = "未知"
                        lines_count = char.get("lines_count", 0)

                        with misc_cols[col_idx]:
                            st.markdown(f"**{name}**")
                            st.markdown(f"性别: {gender} | 台词: {lines_count}句")

                            # 为单个杂毛角色设置语音的按钮
                            if st.button("设置语音", key=f"set_misc_voice_{char_idx}"):
                                st.session_state.selected_character = char
                                st.session_state.is_misc_characters = False
                                st.session_state.misc_characters_list = None
                                st.rerun()

    # 如果有选中的角色，显示语音模型选择器
    if st.session_state.selected_character:
        st.markdown("---")

        # 创建模态对话框效果
        with st.container():
            col1, col2 = st.columns([5, 1])

            with col1:
                if st.session_state.is_misc_characters:
                    st.subheader(f"为所有杂毛角色选择语音模型")
                else:
                    st.subheader(
                        f"为角色 '{st.session_state.selected_character.get('name', '未知')}' 选择语音模型"
                    )

            with col2:
                if st.button("✖ 关闭", key="close_voice_selector"):
                    st.session_state.selected_character = None
                    st.session_state.is_misc_characters = False
                    st.session_state.misc_characters_list = None
                    st.rerun()

            # 显示语音选择器
            display_voice_model_selector(
                book_id,
                st.session_state.selected_character,
                st.session_state.is_misc_characters,
                st.session_state.misc_characters_list,
            )


def display_voice_model_selector(
    book_id, character, is_misc=False, misc_characters=None
):
    """显示语音模型选择器（使用优化布局）"""
    # 获取配置管理器
    config_manager = ConfigManager()

    # 创建两个标签页
    tab1, tab2 = st.tabs(["Edge TTS语音", "硅基流动语音"])

    with tab1:
        # 按照性别筛选Edge TTS语音
        gender = character.get("gender", "中")

        # 手动定义Edge TTS语音模型
        edge_voices = [
            {"id": "zh-CN-XiaoxiaoNeural", "name": "普通话-小晓", "gender": "女"},
            {"id": "zh-CN-XiaoyiNeural", "name": "普通话-小艺", "gender": "女"},
            {"id": "zh-CN-YunjianNeural", "name": "普通话-云健", "gender": "男"},
            {"id": "zh-CN-YunxiNeural", "name": "普通话-云希", "gender": "男"},
            {"id": "zh-CN-YunxiaNeural", "name": "普通话-云霞", "gender": "女"},
            {"id": "zh-CN-YunyangNeural", "name": "普通话-云扬", "gender": "男"},
            {
                "id": "zh-CN-liaoning-XiaobeiNeural",
                "name": "辽宁话-小北",
                "gender": "女",
            },
            {"id": "zh-HK-HiuGaaiNeural", "name": "粤语-欢歌", "gender": "女"},
            {"id": "zh-HK-HiuMaanNeural", "name": "粤语-华文", "gender": "女"},
            {"id": "zh-HK-WanLungNeural", "name": "粤语-文勇", "gender": "男"},
            {"id": "zh-TW-HsiaoChenNeural", "name": "台湾话-晓晨", "gender": "男"},
            {"id": "zh-TW-HsiaoYuNeural", "name": "台湾话-晓语", "gender": "女"},
            {"id": "zh-TW-YunJheNeural", "name": "台湾话-韵杰", "gender": "男"},
        ]

        # 筛选性别匹配的语音模型
        if gender == "男":
            filtered_voices = [v for v in edge_voices if v["gender"] == "男"]
        elif gender == "女":
            filtered_voices = [v for v in edge_voices if v["gender"] == "女"]
        else:
            filtered_voices = edge_voices

        # 每行3个语音模型
        voice_cols_per_row = 3
        voice_rows = (
            len(filtered_voices) + voice_cols_per_row - 1
        ) // voice_cols_per_row

        for row in range(voice_rows):
            voice_cols = st.columns(voice_cols_per_row)

            for col_idx in range(voice_cols_per_row):
                voice_idx = row * voice_cols_per_row + col_idx

                if voice_idx < len(filtered_voices):
                    voice = filtered_voices[voice_idx]

                    with voice_cols[col_idx]:
                        with st.container():
                            st.markdown(f"**{voice['name']}**")

                            # 获取样本路径
                            sample_dir = os.path.join("data", "samples")
                            os.makedirs(sample_dir, exist_ok=True)
                            voice_name = (
                                voice["id"].split("-")[-1].replace("Neural", "")
                            )
                            sample_path = os.path.join(
                                sample_dir, f"edge_{voice_name}.mp3"
                            )

                            # 按钮显示在两列
                            btn_cols = st.columns(2)

                            with btn_cols[0]:
                                if (
                                    os.path.exists(sample_path)
                                    and os.path.getsize(sample_path) > 0
                                ):
                                    if st.button(
                                        "▶ 播放", key=f"play_edge_{voice_idx}"
                                    ):
                                        st.audio(sample_path)
                                else:
                                    if st.button(
                                        "获取示例", key=f"get_edge_{voice_idx}"
                                    ):
                                        with st.spinner("正在生成示例..."):
                                            success, result = (
                                                config_manager.generate_edge_tts_sample(
                                                    voice["id"],
                                                    f"你好，我是{voice['name']}的语音模型",
                                                )
                                            )
                                        if success:
                                            st.success("示例生成成功")
                                            st.audio(result)
                                            st.rerun()
                                        else:
                                            st.error("生成失败")

                            with btn_cols[1]:
                                if st.button(
                                    "✓ 选择",
                                    key=f"select_edge_{voice_idx}",
                                    type="primary",
                                ):
                                    if is_misc and misc_characters:
                                        # 为所有杂毛角色设置相同的语音
                                        success_count = 0
                                        for misc_char in misc_characters:
                                            if save_character_voice(
                                                book_id,
                                                misc_char["name"],
                                                {
                                                    "engine": "edge_tts",
                                                    "voice_id": voice["id"],
                                                    "voice_name": voice["name"],
                                                },
                                            ):
                                                success_count += 1

                                        if success_count > 0:
                                            st.success(
                                                f"已为{success_count}个杂毛角色设置语音: {voice['name']}"
                                            )
                                            # 设置完成后清除选择状态
                                            st.session_state.selected_character = None
                                            st.session_state.is_misc_characters = False
                                            st.session_state.misc_characters_list = None
                                            st.rerun()
                                        else:
                                            st.error("设置语音失败")
                                    else:
                                        # 为单个角色设置语音
                                        if save_character_voice(
                                            book_id,
                                            character["name"],
                                            {
                                                "engine": "edge_tts",
                                                "voice_id": voice["id"],
                                                "voice_name": voice["name"],
                                            },
                                        ):
                                            st.success(
                                                f"已为角色 {character['name']} 设置语音: {voice['name']}"
                                            )
                                            # 设置完成后清除选择状态
                                            st.session_state.selected_character = None
                                            st.rerun()
                                        else:
                                            st.error("设置语音失败")

    with tab2:
        # 检查是否有API密钥配置
        silica_keys = config_manager.get_silica_api_keys()
        if not silica_keys:
            st.warning("您尚未配置硅基流动API密钥，请先在'全局配置'页面中添加API密钥")
        else:
            # 硅基流动语音模型
            silica_voices = [
                {
                    "id": "FunAudioLLM/CosyVoice2-0.5B:alex",
                    "name": "Alex",
                    "gender": "男",
                },
                {
                    "id": "FunAudioLLM/CosyVoice2-0.5B:anna",
                    "name": "Anna",
                    "gender": "女",
                },
                {
                    "id": "FunAudioLLM/CosyVoice2-0.5B:bella",
                    "name": "Bella",
                    "gender": "女",
                },
                {
                    "id": "FunAudioLLM/CosyVoice2-0.5B:benjamin",
                    "name": "Benjamin",
                    "gender": "男",
                },
                {
                    "id": "FunAudioLLM/CosyVoice2-0.5B:charles",
                    "name": "Charles",
                    "gender": "男",
                },
                {
                    "id": "FunAudioLLM/CosyVoice2-0.5B:claire",
                    "name": "Claire",
                    "gender": "女",
                },
                {
                    "id": "FunAudioLLM/CosyVoice2-0.5B:david",
                    "name": "David",
                    "gender": "男",
                },
                {
                    "id": "FunAudioLLM/CosyVoice2-0.5B:diana",
                    "name": "Diana",
                    "gender": "女",
                },
            ]

            # 筛选性别匹配的语音模型
            if gender == "男":
                filtered_voices = [v for v in silica_voices if v["gender"] == "男"]
            elif gender == "女":
                filtered_voices = [v for v in silica_voices if v["gender"] == "女"]
            else:
                filtered_voices = silica_voices

            # 显示语音模型
            voice_cols_per_row = 3
            voice_rows = (
                len(filtered_voices) + voice_cols_per_row - 1
            ) // voice_cols_per_row

            for row in range(voice_rows):
                voice_cols = st.columns(voice_cols_per_row)

                for col_idx in range(voice_cols_per_row):
                    voice_idx = row * voice_cols_per_row + col_idx

                    if voice_idx < len(filtered_voices):
                        voice = filtered_voices[voice_idx]

                        with voice_cols[col_idx]:
                            with st.container():
                                st.markdown(f"**{voice['name']}**")

                                # 获取样本路径
                                sample_dir = os.path.join("data", "samples")
                                os.makedirs(sample_dir, exist_ok=True)
                                voice_name = voice["id"].split(":")[-1]
                                sample_path = os.path.join(
                                    sample_dir, f"silica_{voice_name}.mp3"
                                )

                                # 按钮显示在两列
                                btn_cols = st.columns(2)

                                with btn_cols[0]:
                                    if (
                                        os.path.exists(sample_path)
                                        and os.path.getsize(sample_path) > 0
                                    ):
                                        if st.button(
                                            "▶ 播放", key=f"play_silica_{voice_idx}"
                                        ):
                                            st.audio(sample_path)
                                    else:
                                        if st.button(
                                            "获取示例", key=f"get_silica_{voice_idx}"
                                        ):
                                            with st.spinner("正在生成示例..."):
                                                success, result = (
                                                    config_manager.generate_silica_voice_sample(
                                                        voice["id"],
                                                        f"你好，我是{voice['name']}的语音模型",
                                                    )
                                                )
                                            if success:
                                                st.success("示例生成成功")
                                                st.audio(result)
                                                st.rerun()
                                            else:
                                                st.error("生成失败")

                                with btn_cols[1]:
                                    if st.button(
                                        "✓ 选择",
                                        key=f"select_silica_{voice_idx}",
                                        type="primary",
                                    ):
                                        if is_misc and misc_characters:
                                            # 为所有杂毛角色设置相同的语音
                                            success_count = 0
                                            for misc_char in misc_characters:
                                                if save_character_voice(
                                                    book_id,
                                                    misc_char["name"],
                                                    {
                                                        "engine": "silica_voice",
                                                        "voice_id": voice["id"],
                                                        "voice_name": voice["name"],
                                                    },
                                                ):
                                                    success_count += 1

                                            if success_count > 0:
                                                st.success(
                                                    f"已为{success_count}个杂毛角色设置语音: {voice['name']}"
                                                )
                                                # 设置完成后清除选择状态
                                                st.session_state.selected_character = (
                                                    None
                                                )
                                                st.session_state.is_misc_characters = (
                                                    False
                                                )
                                                st.session_state.misc_characters_list = (
                                                    None
                                                )
                                                st.rerun()
                                            else:
                                                st.error("设置语音失败")
                                        else:
                                            # 为单个角色设置语音
                                            if save_character_voice(
                                                book_id,
                                                character["name"],
                                                {
                                                    "engine": "silica_voice",
                                                    "voice_id": voice["id"],
                                                    "voice_name": voice["name"],
                                                },
                                            ):
                                                st.success(
                                                    f"已为角色 {character['name']} 设置语音: {voice['name']}"
                                                )
                                                # 设置完成后清除选择状态
                                                st.session_state.selected_character = (
                                                    None
                                                )
                                                st.rerun()
                                            else:
                                                st.error("设置语音失败")


def save_character_voice(book_id, character_name, voice_config):
    """保存角色语音设置"""
    # 语音配置文件路径
    voices_file = os.path.join("data", book_id, "character_voices.json")

    # 加载现有配置
    voices_config = {}
    if os.path.exists(voices_file):
        try:
            with open(voices_file, "r", encoding="utf-8") as f:
                voices_config = json.load(f)
        except Exception:
            voices_config = {}

    # 更新配置
    voices_config[character_name] = voice_config

    # 保存配置
    try:
        with open(voices_file, "w", encoding="utf-8") as f:
            json.dump(voices_config, f, ensure_ascii=False, indent=4)

        # 同时保存一份角色与模型的映射关系，更人性化的格式
        mapping_file = os.path.join("data", book_id, "voice_mapping.json")
        mapping = {}

        for char_name, config in voices_config.items():
            mapping[char_name] = {
                "引擎": (
                    "Edge TTS" if config.get("engine") == "edge_tts" else "硅基流动"
                ),
                "语音名称": config.get("voice_name", "未知"),
                "语音ID": config.get("voice_id", ""),
            }

        with open(mapping_file, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=4)

        return True
    except Exception as e:
        print(f"保存角色语音配置出错: {str(e)}")
        return False
