"""
工具函数模块，提供各种通用辅助功能
"""

import os
import re
import json
import time
import base64
import hashlib
from datetime import datetime
from pathlib import Path
import threading
from typing import List, Dict, Any, Tuple, Optional, Union


def ensure_dir(directory: str) -> bool:
    """确保目录存在，如果不存在则创建"""
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        print(f"创建目录失败: {str(e)}")
        return False


def get_current_time_str(format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """获取当前时间的格式化字符串"""
    return datetime.now().strftime(format_str)


def log_format(message: str) -> str:
    """格式化日志消息"""
    return f"[{get_current_time_str()}] {message}"


def safe_filename(filename: str) -> str:
    """将字符串转换为安全的文件名"""
    # 移除不合法的文件名字符
    safe_name = re.sub(r'[\\/:*?"<>|]', "_", filename)
    # 限制长度
    if len(safe_name) > 200:
        safe_name = safe_name[:197] + "..."
    return safe_name


def count_text_words(text: str) -> int:
    """统计文本中的字数（中文环境）"""
    if not text:
        return 0
    # 移除空白字符
    text = re.sub(r"\s", "", text)
    # 返回长度
    return len(text)


def split_text_into_chunks(text: str, chunk_size: int = 1000) -> List[str]:
    """将文本分割成固定大小的块"""
    if not text:
        return []

    # 按行分割
    lines = text.split("\n")

    chunks = []
    current_chunk = []
    current_size = 0

    for line in lines:
        line_size = len(line)
        if current_size + line_size <= chunk_size:
            current_chunk.append(line)
            current_size += line_size
        else:
            # 如果当前行会导致超出块大小，先保存当前块
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = [line]
                current_size = line_size
            else:
                # 如果单行就超过块大小，则将该行单独作为一个块
                chunks.append(line)
                current_chunk = []
                current_size = 0

    # 添加最后一个块
    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


def read_text_file(file_path: str, encoding: str = "utf-8") -> Optional[str]:
    """读取文本文件"""
    try:
        with open(file_path, "r", encoding=encoding) as f:
            return f.read()
    except UnicodeDecodeError:
        # 尝试其他编码
        try:
            with open(file_path, "r", encoding="gbk") as f:
                return f.read()
        except Exception as e:
            print(f"读取文件失败: {str(e)}")
            return None
    except Exception as e:
        print(f"读取文件失败: {str(e)}")
        return None


def write_text_file(file_path: str, content: str, encoding: str = "utf-8") -> bool:
    """写入文本文件"""
    try:
        # 确保目录存在
        directory = os.path.dirname(file_path)
        if directory:
            ensure_dir(directory)

        with open(file_path, "w", encoding=encoding) as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"写入文件失败: {str(e)}")
        return False


def load_json_file(file_path: str, default: Any = None) -> Any:
    """加载JSON文件"""
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return default
    except json.JSONDecodeError:
        print(f"JSON解析错误: {file_path}")
        return default
    except Exception as e:
        print(f"加载JSON文件失败: {str(e)}")
        return default


def save_json_file(file_path: str, data: Any, indent: int = 4) -> bool:
    """保存数据为JSON文件"""
    try:
        # 确保目录存在
        directory = os.path.dirname(file_path)
        if directory:
            ensure_dir(directory)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        return True
    except Exception as e:
        print(f"保存JSON文件失败: {str(e)}")
        return False


def encrypt_api_key(api_key: str, salt: str = "NovelApiKey") -> str:
    """简单加密API密钥（注意：这不是安全的加密方法，仅用于基本混淆）"""
    if not api_key:
        return ""

    try:
        # 生成盐值哈希
        salt_hash = hashlib.sha256(salt.encode()).digest()
        # 与API密钥组合并编码
        combined = salt_hash + api_key.encode()
        # Base64编码
        return base64.b64encode(combined).decode()
    except Exception as e:
        print(f"加密API密钥失败: {str(e)}")
        return ""


def decrypt_api_key(encrypted_key: str, salt: str = "NovelApiKey") -> str:
    """解密API密钥"""
    if not encrypted_key:
        return ""

    try:
        # Base64解码
        decoded = base64.b64decode(encrypted_key)
        # 移除盐值哈希（32字节）
        api_key_bytes = decoded[32:]
        # 解码为字符串
        return api_key_bytes.decode()
    except Exception as e:
        print(f"解密API密钥失败: {str(e)}")
        return ""


def batch_process(
    items: List[Any], process_func, max_workers: int = 5, callback: callable = None
) -> List[Any]:
    """
    使用多线程批量处理项目

    Args:
        items: 要处理的项目列表
        process_func: 处理单个项目的函数
        max_workers: 最大线程数
        callback: 进度回调函数，接收三个参数：已完成数量，总数量，当前项目

    Returns:
        处理结果列表
    """
    if not items:
        return []

    results = []
    lock = threading.Lock()
    completed = 0
    total = len(items)

    def worker(item):
        nonlocal completed

        try:
            # 处理项目
            result = process_func(item)

            # 更新进度并存储结果
            with lock:
                results.append(result)
                completed += 1
                if callback:
                    callback(completed, total, item)

        except Exception as e:
            with lock:
                completed += 1
                print(f"处理项目出错: {str(e)}")
                if callback:
                    callback(completed, total, item, error=str(e))

    # 创建并启动线程
    threads = []
    for item in items:
        thread = threading.Thread(target=worker, args=(item,))
        threads.append(thread)
        thread.start()

        # 控制并发线程数
        if len(threads) >= max_workers:
            for t in threads:
                t.join()
            threads = []

    # 等待剩余线程完成
    for thread in threads:
        thread.join()

    return results


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def get_file_info(file_path: str) -> Dict[str, Any]:
    """获取文件信息"""
    try:
        file_stat = os.stat(file_path)
        return {
            "path": file_path,
            "filename": os.path.basename(file_path),
            "size": file_stat.st_size,
            "size_formatted": format_file_size(file_stat.st_size),
            "modified_time": datetime.fromtimestamp(file_stat.st_mtime),
            "created_time": datetime.fromtimestamp(file_stat.st_ctime),
            "exists": True,
        }
    except FileNotFoundError:
        return {
            "path": file_path,
            "filename": os.path.basename(file_path),
            "exists": False,
        }
    except Exception as e:
        print(f"获取文件信息失败: {str(e)}")
        return {
            "path": file_path,
            "filename": os.path.basename(file_path),
            "error": str(e),
            "exists": False,
        }


def find_files(directory: str, pattern: str = "*.*") -> List[str]:
    """查找匹配模式的文件"""
    try:
        matches = []
        for root, _, files in os.walk(directory):
            for filename in files:
                if re.match(pattern, filename):
                    matches.append(os.path.join(root, filename))
        return matches
    except Exception as e:
        print(f"查找文件失败: {str(e)}")
        return []


def export_book_to_json(
    book_id: str,
    novel_data: Dict[str, Any],
    chapters_data: List[Dict[str, Any]],
    export_dir: str,
) -> Tuple[bool, str]:
    """
    导出小说和章节数据为JSON格式

    Args:
        book_id: 小说ID
        novel_data: 小说数据
        chapters_data: 章节数据列表
        export_dir: 导出目录

    Returns:
        (是否成功, 消息)
    """
    try:
        # 创建小说目录
        book_dir = os.path.join(export_dir, str(book_id))
        ensure_dir(book_dir)

        # 创建内容目录
        content_dir = os.path.join(book_dir, "content")
        ensure_dir(content_dir)

        # 按卷分组章节
        volumes = {}
        for chapter in chapters_data:
            volume = chapter.get("volume", "默认分组")
            if volume not in volumes:
                volumes[volume] = []
            volumes[volume].append(chapter)

        # 创建卷目录并导出章节内容
        chapter_paths = []
        chapter_index = 1

        for volume_name, volume_chapters in volumes.items():
            # 创建卷目录
            safe_volume_name = safe_filename(volume_name)
            volume_dir = os.path.join(content_dir, safe_volume_name)
            ensure_dir(volume_dir)

            # 导出章节内容
            for i, chapter in enumerate(volume_chapters, 1):
                # 构建章节文件名
                chapter_title = chapter.get("title", f"第{i}章")
                safe_title = safe_filename(chapter_title)
                filename = f"{i:04d}_{safe_title}.txt"
                filepath = os.path.join(volume_dir, filename)

                # 写入章节内容
                content = chapter.get("content", [])
                content_text = "\n".join(content) if content else ""

                write_text_file(filepath, content_text)

                # 保存相对路径
                rel_path = os.path.join(
                    str(book_id), "content", safe_volume_name, filename
                )
                chapter_paths.append(rel_path)

                chapter_index += 1

        # 保存章节路径列表到JSON文件
        output_file = os.path.join(export_dir, f"{book_id}_chapters.json")
        save_json_file(output_file, chapter_paths)

        # 保存小说信息
        novel_info_file = os.path.join(book_dir, "novel_info.json")
        save_json_file(novel_info_file, novel_data)

        return True, f"已成功导出 {len(chapter_paths)} 个章节到 {book_dir}"

    except Exception as e:
        return False, f"导出小说失败: {str(e)}"


def convert_chapter_to_dialogue_format(chapter_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    将章节数据转换为对话分析所需格式

    Args:
        chapter_data: 章节数据

    Returns:
        转换后的数据
    """
    # 构建转换后的章节数据
    return {
        "chapter_title": chapter_data.get("title", ""),
        "chapter_url": chapter_data.get("url", ""),
        "group": chapter_data.get("volume", ""),
        "word_count": chapter_data.get("word_count", 0),
        "content": chapter_data.get("content", []),
    }
