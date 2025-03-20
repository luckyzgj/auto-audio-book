import os
import requests
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time
from pydub import AudioSegment
import shutil
import random
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)



def setup_logging(book_id):
    """
    配置中文日志系统

    参数:
    book_id: 书籍ID，用于创建专用日志目录

    返回:
    配置好的日志记录器
    """
    # 创建日志目录
    log_dir = f"logs/{book_id}"
    os.makedirs(log_dir, exist_ok=True)

    # 生成带时间戳的日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"audio_generation_{timestamp}.log")

    # 创建日志记录器
    logger = logging.getLogger("audio_generation")
    logger.setLevel(logging.INFO)

    # 清除之前的处理器，防止重复日志
    logger.handlers.clear()

    # 控制台处理器（彩色输出）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)

    # 日志格式
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # 添加处理器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger





def validate_audio_content(audio_content):
    """
    验证音频内容是否合规

    参数:
    audio_content: 从API获取的音频内容

    返回:
    布尔值，表示音频是否有效
    """
    # 检查参数有效性
    if audio_content is None:
        return False

    # 检查音频内容长度 (最小文件大小阈值，单位：字节)
    min_audio_size = 1024  # 1KB
    if len(audio_content) < min_audio_size:
        return False

    # 尝试检查音频文件头部标识
    try:
        # MP3文件头部标识检查
        if not (
            audio_content.startswith(b"ID3") or audio_content.startswith(b"\xff\xf3")
        ):
            return False
    except Exception:
        return False

    return True


def create_audio_from_api(text: str, module: str, max_retries: int = 3):
    """
    通过API生成音频，支持多次重试

    参数:
    text: 待转换的文本内容
    module: 使用的语音模型
    max_retries: 最大重试次数，默认为3

    返回:
    成功时返回音频内容，失败时返回None
    """
    url = "https://api.siliconflow.cn/v1/audio/speech"

    payload = {
        "model": "FunAudioLLM/CosyVoice2-0.5B",
        "input": text,
        "voice": module,
        "response_format": "mp3",
        "sample_rate": 44100,
        "stream": True,
        "speed": 1,
        "gain": 0,
    }

    headers = {
        "Authorization": f"Bearer {os.getenv('COSYVOICE_API_KEY')}",
        "Content-Type": "application/json",
    }

    for attempt in range(max_retries):
        try:
            # 随机延迟 0.1 - 1秒发起请求
            time.sleep(random.uniform(0.1, 0.3))
            response = requests.post(url, json=payload, headers=headers, timeout=None)

            # 检查响应状态码
            if response.status_code == 200:
                audio_content = response.content
                return audio_content
            # 非200状态码的重试间隔
            time.sleep(2**attempt)  # 指数退避策略

        except requests.RequestException as e:
            # 捕获网络相关异常
            time.sleep(2**attempt)  # 指数退避策略
            logger.error(f"音频生成失败：{e}", exc_info=True)
        except Exception as e:
            # 捕获其他未预料的异常
            time.sleep(2**attempt)  # 指数退避策略
            logger.error(f"音频生成失败：{e}", exc_info=True)
    return None


# 处理单个文本片段并生成音频
def process_text_segment(args):
    index, content, user_voices, chapter_index, book_id = args

    # 创建保存临时音频的文件夹
    temp_dir = f"audio/{book_id}/audio_temp/{chapter_index}"
    os.makedirs(temp_dir, exist_ok=True)

    # 生成音频文件路径
    audio_path = f"{temp_dir}/{index}.mp3"
    # 合成后的音频文件路径
    output_path = f"audio/{book_id}/audio/{index}.mp3"
    # 如果文件已存在，直接返回路径（避免重复生成）
    if os.path.exists(audio_path):
        return index, audio_path

    # 获取文本内容
    text = content.get("text", "").strip()

    # 如果文本为空，返回None
    if not text:
        return index, None

    # 获取角色类型
    role_type = content.get("type", "旁白")

    # 查找对应的语音模型，如果没有则使用旁白
    voice_model = user_voices.get(
        role_type, user_voices.get("旁白", "FunAudioLLM/CosyVoice2-0.5B:david")
    )

    # 调用API生成音频
    audio_content = create_audio_from_api(text, voice_model)
    if not audio_content:
        return index, None
    # 保存音频文件
    with open(audio_path, "wb") as f:
        f.write(audio_content)

    # 返回索引和音频文件路径（用于后续合并）
    return index, audio_path


def get_audio_duration(file_path):
    """
    获取音频文件的总时长（毫秒）

    参数:
    file_path: 音频文件路径

    返回:
    音频总时长（毫秒），如果无法读取则返回0
    """
    try:
        audio = AudioSegment.from_mp3(file_path)
        return len(audio)  # 返回音频长度（毫秒）
    except Exception as e:
        print(f"获取音频时长失败: {file_path}, 错误: {e}")
        return 0


def merge_chapter_audio(audio_files, output_path):
    """
    合并章节音频片段，并进行长度校验

    参数:
    audio_files: 音频文件列表，每个元素为 (索引, 文件路径)
    output_path: 合并后音频的输出路径

    返回:
    合并后的音频文件路径，如果不需要合并则返回现有文件路径
    """
    # 过滤掉None值的音频文件
    audio_files = [file for file in audio_files if file[1] is not None]
    audio_files.sort(key=lambda x: x[0])

    # 如果没有有效音频文件，返回None
    if not audio_files:
        return None

    # 检查本地是否已存在合成音频
    if os.path.exists(output_path):
        # 计算分段音频总时长
        total_segment_duration = sum(
            get_audio_duration(file_path) for _, file_path in audio_files
        )

        # 获取已存在音频的时长
        existing_audio_duration = get_audio_duration(output_path)

        # 允许的时长误差范围（毫秒）
        DURATION_TOLERANCE = 5000  # 5秒

        # 判断是否需要重新合成
        if abs(total_segment_duration - existing_audio_duration) <= DURATION_TOLERANCE:
            print(f"现有音频长度符合，跳过重新合成: {output_path}")
            return output_path

    # 开始合并音频
    try:
        # 第一个音频作为基础
        combined = AudioSegment.from_mp3(audio_files[0][1])

        # 添加其余音频
        for _, file_path in audio_files[1:]:
            audio = AudioSegment.from_mp3(file_path)
            combined += audio

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 导出合并后的音频
        combined.export(output_path, format="mp3")

        print(f"音频合并完成: {output_path}")
        return output_path

    except Exception as e:
        print(f"音频合并失败: {e}")
        return None


# 处理单个章节
def process_chapter(chapter_meta, user_voices, book_id, chapter_index, max_workers=100):
    """
    处理单个章节

    chapter_meta: 章节元数据
    user_voices: 角色语音对照表
    book_id: 书籍ID
    chapter_index: 章节索引
    max_workers: 最大线程数
    """
    chapter_title = chapter_meta.get("chapter_title", f"第{chapter_index+1}章")
    chapter_file = os.path.join(os.getcwd(), "audio", book_id, "chapter", f"{chapter_index+1}.json")

    # 如果章节文件路径不存在，返回
    if not chapter_file or not os.path.exists(chapter_file):
        print(f"章节文件不存在: {chapter_file}")
        return None

    # 读取章节详细内容
    with open(chapter_file, "r", encoding="utf-8") as f:
        try:
            chapter_content = json.load(f)
        except json.JSONDecodeError:
            print(f"章节文件格式错误: {chapter_file}")
            return None

    # 确保章节内容是列表
    if not isinstance(chapter_content, list) or not chapter_content:
        print(f"章节内容为空或格式错误: {chapter_file}")
        return None

    print(f"\n开始处理章节：{chapter_title}")

    # 准备处理任务
    tasks = []
    for i, content in enumerate(chapter_content):
        # 添加任务，直接传递用户语音对照表
        tasks.append((i, content, user_voices, chapter_index, book_id))

    # 创建临时目录
    temp_dir = f"audio/{book_id}/audio_temp/{chapter_index}"
    os.makedirs(temp_dir, exist_ok=True)

    # 多线程处理音频生成
    audio_files = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 创建进度条
        futures = {executor.submit(process_text_segment, task): task for task in tasks}

        # 使用tqdm显示进度
        with tqdm(total=len(tasks), desc=f"章节 {chapter_title} 音频生成进度") as pbar:
            for future in as_completed(futures):
                try:
                    index, audio_path = future.result()
                    if audio_path:  # 只添加成功生成的音频
                        audio_files.append((index, audio_path))
                    pbar.update(1)
                except Exception as e:
                    print(f"处理音频时出错: {e}")
                    pbar.update(1)

    # 合并章节音频
    if audio_files:
        output_dir = f"audio/{book_id}/audio"
        os.makedirs(output_dir, exist_ok=True)

        # 使用章节标题作为文件名，但去除不合法的字符
        safe_title = "".join(
            c for c in chapter_title if c.isalnum() or c in " _-"
        ).strip()
        if not safe_title:
            safe_title = f"chapter_{chapter_index}"

        output_path = f"{output_dir}/{safe_title}.mp3"
        if os.path.exists(output_path):
            return output_path
        print(f"正在合并章节 {chapter_title} 的音频...")
        merge_chapter_audio(audio_files, output_path)
        print(f"章节 {chapter_title} 音频已生成: {output_path}")

        # 清理临时文件
        print(f"清理临时文件...")
        shutil.rmtree(temp_dir, ignore_errors=True)

        return output_path

    return None


# 读取章节信息与角色语音对照表生成章节音频
def create_audio(book_id: str, max_workers=100):
    """
    book_id: 书籍id
    max_workers: 最大线程数
    """
    # 确保必要的目录存在
    os.makedirs(f"audio/{book_id}", exist_ok=True)
    os.makedirs(f"audio/{book_id}/audio", exist_ok=True)
    os.makedirs(f"audio/{book_id}/audio_temp", exist_ok=True)

    # 读取章节元数据
    with open(f"audio/{book_id}/xszj.json", "r", encoding="utf-8") as f:
        chapters_meta = json.load(f)

    # 如果不是列表，将其包装成列表
    if not isinstance(chapters_meta, list):
        chapters_meta = [chapters_meta]

    # 读取角色语音对照表
    with open(f"audio/{book_id}/user.json", "r", encoding="utf-8") as f:
        user_voices = json.load(f)

    # 逐章节处理
    total_chapters = len(chapters_meta)
    print(f"总共 {total_chapters} 个章节需要处理")

    # 总进度条
    with tqdm(total=total_chapters, desc="总体进度") as pbar:
        for i, chapter_meta in enumerate(chapters_meta):
            # 处理单个章节（等待完成后再处理下一个）
            chapter_output = process_chapter(
                chapter_meta, user_voices, book_id, i, max_workers
            )

            # 更新总进度条
            pbar.update(1)

    print(f"\n所有章节音频生成完毕！音频文件保存在 audio/{book_id}/audio 目录下")


if __name__ == "__main__":
    book_id = "115690"
    # 使用示例
    # 在主程序或模块开头初始化
    logger = setup_logging(book_id=book_id)
    create_audio(book_id, max_workers=20)  # 设置并发线程数为5，可以根据需要调整
