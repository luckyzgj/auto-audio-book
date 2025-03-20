import os
import json
import time
import re
from tqdm import tqdm
from dotenv import load_dotenv
import threading
from openai import OpenAI
import re
from tqdm import tqdm

load_dotenv(override=True)


prompt = """
    我发给你的是一章小说，请帮我仔细分析出来每句话都是谁说的，然后以json的形式给我
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


def get_book_json(book_id: str):
    """
    读取指定book_id的所有小说章节文件路径，并按照文件夹和文件名顺序排列，
    然后保存为JSON文件。

    Args:
        book_id (str): 小说ID，对应data目录下的子目录名
    """
    book_dir = os.path.join("data", book_id, "content")

    # 检查目录是否存在
    if not os.path.exists(book_dir):
        print(f"错误：目录 '{book_dir}' 不存在")
        return

    # 获取所有子目录
    subdirs = [
        d for d in os.listdir(book_dir) if os.path.isdir(os.path.join(book_dir, d))
    ]

    # 对子目录进行排序（可能包含数字，如"第1 - 50章"）
    def extract_number(s):
        # 从字符串中提取数字，用于排序
        match = re.search(r"(\d+)", s)
        return int(match.group(1)) if match else 0

    subdirs.sort(key=extract_number)

    all_chapters = []

    # 遍历每个子目录，收集所有章节文件
    for subdir in subdirs:
        subdir_path = os.path.join(book_dir, subdir)
        chapter_files = [f for f in os.listdir(subdir_path) if f.endswith(".txt")]

        # 对章节文件进行排序
        # 假设文件名格式类似 "0001_第1章 xxx.txt"
        def chapter_sort_key(filename):
            # 先尝试从文件名前缀提取序号
            prefix_match = re.match(r"(\d+)_", filename)
            if prefix_match:
                return int(prefix_match.group(1))

            # 如果没有前缀，尝试从"第X章"提取章节号
            chapter_match = re.search(r"第(\d+)章", filename)
            if chapter_match:
                return int(chapter_match.group(1))

            # 如果都没有，返回0
            return 0

        chapter_files.sort(key=chapter_sort_key)

        # 为每个章节文件构建相对路径
        for chapter_file in chapter_files:
            chapter_path = os.path.join(book_id, "content", subdir, chapter_file)
            all_chapters.append(chapter_path)

    # 保存章节路径列表到JSON文件
    output_file = f"{book_id}_chapters.json"
    # 判断是否没有这个文件
    if not os.path.exists(output_file):
        # 创建这个文件
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_chapters, f, ensure_ascii=False, indent=4)
    else:
        # 读取这个文件
        with open(output_file, "r", encoding="utf-8") as f:
            all_chapters = json.load(f)

    print(f"已成功读取 {len(all_chapters)} 个章节路径，并保存到 {output_file}")
    return all_chapters


def get_book_json_content(book_id: str):
    """
    读取指定book_id的所有小说章节内容，使用AI分析对话内容，
    并将结果保存为JSON文件。使用多线程并分配不同API密钥进行处理。

    Args:
        book_id (str): 小说ID，对应data目录下的子目录名
    """

    # 获取章节路径列表
    chapters = get_book_json(book_id)
    if not chapters:
        print(f"错误: 未找到书籍 {book_id} 的章节")
        return

    # 读取API密钥列表
    api_keys = []
    try:
        with open("api_keys.txt", "r") as f:
            api_keys = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"错误: 读取API密钥文件失败 - {str(e)}")
        return

    if not api_keys:
        print("错误: 未找到有效的API密钥")
        return

    # 确保输出目录存在
    output_dir = os.path.join("audio", book_id, "chapter")
    os.makedirs(output_dir, exist_ok=True)

    # 获取API基础URL
    api_base_url = os.getenv("GEMINI_API_URL")

    # 准备任务
    tasks = []
    for i, chapter_path in enumerate(chapters, 1):  # 从1开始计数
        output_path = os.path.join(output_dir, f"{i}.json")  # 使用简单的数字序号命名

        # 如果文件不存在，添加到任务列表
        if not os.path.exists(output_path):
            tasks.append((chapter_path, output_path))

    # 如果所有任务都已完成，直接返回
    if not tasks:
        return

    # 将任务平均分配给每个API密钥
    num_keys = len(api_keys)
    key_tasks = [[] for _ in range(num_keys)]

    for i, task in enumerate(tasks):
        key_index = i % num_keys
        key_tasks[key_index].append(task)

    # 共享计数和锁
    completed = 0
    lock = threading.Lock()

    # 创建进度条
    pbar = tqdm(total=len(tasks), desc=f"处理书籍 {book_id}")

    # 工作线程函数
    def worker(api_key, assigned_tasks, worker_id):
        nonlocal completed

        # 创建API客户端
        client = OpenAI(
            api_key=api_key,
            base_url=api_base_url,
        )

        for chapter_path, output_path in assigned_tasks:
            try:
                # 构建完整章节路径
                full_path = os.path.join("data", chapter_path)

                # 读取章节内容
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        chapter_content = f.read()
                except UnicodeDecodeError:
                    with open(full_path, "r", encoding="gbk") as f:
                        chapter_content = f.read()
                # 如果 output_path 文件 已经存在 则跳过
                if os.path.exists(output_path):
                    print(f"章节 {chapter_path} 已经存在，跳过")
                    pass
                else:
                    # 使用AI分析章节内容
                    result = generate_board_json_with_client(client, chapter_content)

                    # 保存结果
                    if result:
                        # 确保目录存在
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)

                        with open(output_path, "w", encoding="utf-8") as f:
                            json.dump(result, f, ensure_ascii=False, indent=4)

                # 更新进度
                with lock:
                    completed += 1
                    pbar.update(1)

            except Exception as e:
                print(f"处理章节 {chapter_path} 时出错: {str(e)}")

            # 添加短暂延迟，避免API速率限制
            time.sleep(1)

    # 使用原始的generate_board_json逻辑，但接受预创建的客户端
    def generate_board_json_with_client(
        client, chapter_content, max_retries=3, retry_delay=2, chapter_path=""
    ):
        # 将文本按行分割
        lines = chapter_content.split("\n")

        # 检查是否超过100行
        if len(lines) > 50:
            # 分割成每块100行
            chunks = [lines[i : i + 50] for i in range(0, len(lines), 50)]
            all_results = []

            print(f"文本过长，已分割为{len(chunks)}个块进行处理")

            # 处理每个块
            for i, chunk in enumerate(chunks):
                chunk_content = "\n".join(chunk)
                print(f"处理第{i+1}/{len(chunks)}块...")

                # 处理当前块
                chunk_result = process_single_chunk(
                    client, chunk_content, max_retries, retry_delay, chapter_path
                )

                # 将结果合并
                if chunk_result:
                    all_results.extend(chunk_result)

            print(f"所有块处理完成，共获取{len(all_results)}个对话记录")
            return all_results
        else:
            # 原始处理逻辑（文本行数不超过100行）
            return process_single_chunk(
                client, chapter_content, max_retries, retry_delay, chapter_path
            )

        # 提取原始处理逻辑到单独函数

    def process_single_chunk(
        client, content, max_retries=3, retry_delay=2, chapter_path=""
    ):
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model="gemini-2.0-flash",
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": content},
                    ],
                )
                content = response.choices[0].message.content
                content = re.sub(r"```json\n?|\n?```", "", content)

                try:
                    result = json.loads(content)
                    # 验证结果非空
                    if result and isinstance(result, list) and len(result) > 0:
                        return result
                    else:
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                        continue
                except json.JSONDecodeError:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                    continue

            except Exception as e:
                print(f"API请求错误: {str(e)}，第{attempt+1}次尝试")
                if chapter_path:  # 只在chapter_path有值时打印
                    print(chapter_path)
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                continue

        return []

    # 启动工作线程
    threads = []
    for i in range(num_keys):
        if key_tasks[i]:  # 只为有任务的密钥创建线程
            thread = threading.Thread(
                target=worker, args=(api_keys[i], key_tasks[i], i), daemon=True
            )
            threads.append(thread)
            thread.start()

    # 等待所有线程完成
    for thread in threads:
        thread.join()

    # 关闭进度条
    pbar.close()


def check_json_conversion_status(book_id: str):
    """
    检查指定book_id的小说章节是否都已转换为JSON文件。

    Args:
        book_id (str): 小说ID，对应data目录下的子目录名

    Returns:
        tuple: (总章节数, 已转换章节数, 缺失章节列表)
    """
    # 获取章节路径列表
    chapters = get_book_json(book_id)
    if not chapters:
        print(f"错误: 未找到书籍 {book_id} 的章节")
        return 0, 0, []

    # 定义输出目录
    output_dir = os.path.join("audio", book_id, "chapter")

    # 检查每个章节对应的JSON文件
    converted_chapters = 0
    missing_chapters = []

    for i, chapter_path in enumerate(chapters, 1):  # 从1开始计数
        output_path = os.path.join(output_dir, f"{i}.json")  # 使用简单的数字序号命名

        if os.path.exists(output_path):
            converted_chapters += 1
        else:
            missing_chapters.append((i, chapter_path))

    # 输出统计信息
    total_chapters = len(chapters)
    percentage = (
        (converted_chapters / total_chapters) * 100 if total_chapters > 0 else 0
    )

    print(f"书籍 {book_id} 转换状态:")
    print(f"总章节数: {total_chapters}")
    print(f"已转换章节数: {converted_chapters} ({percentage:.2f}%)")
    print(f"未转换章节数: {total_chapters - converted_chapters}")

    if missing_chapters:
        print("\n缺失的章节:")
        for chapter_num, chapter_path in missing_chapters:
            print(f"  章节 {chapter_num}: {chapter_path}")

    return total_chapters, converted_chapters, missing_chapters


if __name__ == "__main__":
    # 可以在这里指定book_id
    book_id = "115690"
    get_book_json_content(book_id)
    # check_json_conversion_status(book_id)
