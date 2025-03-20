import json
import requests
import os
import time
from bs4 import BeautifulSoup
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
import threading


def load_json(json_file):
    """加载JSON文件"""
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"错误: 加载JSON文件出错: {e}")
        return []


def fetch_html(url, timeout=10, retry=3):
    """获取URL的HTML内容，带有重试机制"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }

    for i in range(retry):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            if i == retry - 1:  # 最后一次重试
                raise e
            time.sleep(1)  # 重试前等待1秒


def parse_html(html):
    """解析HTML内容，提取<div class="content">下的所有<p>标签的文本"""
    soup = BeautifulSoup(html, "html.parser")
    content_div = soup.find("div", class_="content")

    if not content_div:
        return []

    paragraphs = content_div.find_all("p")
    return [p.get_text().strip() for p in paragraphs if p.get_text().strip()]


def save_content(content, save_path):
    """保存内容到文件"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content))
        return True
    except Exception as e:
        print(f"错误: 保存文件出错: {save_path}, {e}")
        return False


def get_file_path(chapter, save_dir, index):
    """根据章节信息获取保存文件的路径"""
    title = chapter["chapter_title"]
    group = chapter.get("group", "")

    # 创建合法的文件名
    safe_title = "".join(c if c.isalnum() or c in "- " else "_" for c in title)
    filename = f"{index:04d}_{safe_title}.txt"  # 添加序号前缀，保证排序

    # 如果有分组，创建子目录
    if group:
        safe_group = "".join(c if c.isalnum() or c in "- " else "_" for c in group)
        group_dir = os.path.join(save_dir, safe_group)
        return os.path.join(group_dir, filename)
    else:
        return os.path.join(save_dir, filename)


def process_chapter(chapter, save_dir, index):
    """处理单个章节"""
    url = chapter["chapter_url"]
    title = chapter["chapter_title"]

    # 获取文件保存路径
    save_path = get_file_path(chapter, save_dir, index)

    # 检查文件是否已存在，如果存在则跳过
    if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
        return True

    try:
        html = fetch_html(url)
        content = parse_html(html)
        if content:
            if save_content(content, save_path):
                return True
            else:
                return False
        else:
            print(f"错误: 未提取到内容: {url}")
            return False
    except Exception as e:
        print(f"错误: 处理章节出错: {title}, {url}, {e}")
        return False
    finally:
        # 每次请求后等待0.2秒
        time.sleep(0.2)


def download_novel(json_file, save_dir, max_workers=10):
    """
    下载小说内容的主函数

    参数:
        json_file: JSON文件路径
        save_dir: 保存内容的目录
        max_workers: 最大线程数
    """
    # 确保保存目录存在
    os.makedirs(save_dir, exist_ok=True)

    # 加载JSON数据
    chapters = load_json(json_file)
    if not chapters:
        print(f"错误: 未加载到章节数据或章节为空: {json_file}")
        return

    # 创建进度条
    pbar = tqdm(total=len(chapters), desc="下载进度")

    # 线程安全的计数器
    success_count = 0
    fail_count = 0
    skip_count = 0  # 添加跳过计数
    lock = threading.Lock()

    # 处理章节和更新进度的函数
    def process_and_update(chapter, index):
        nonlocal success_count, fail_count, skip_count

        # 检查文件是否已存在
        save_path = get_file_path(chapter, save_dir, index)
        already_exists = os.path.exists(save_path) and os.path.getsize(save_path) > 0

        if already_exists:
            with lock:
                skip_count += 1
                pbar.update(1)
            return True

        result = process_chapter(chapter, save_dir, index)
        with lock:
            if result:
                success_count += 1
            else:
                fail_count += 1
            pbar.update(1)
        return result

    # 使用线程池处理
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务，并保持原始顺序的索引
        futures = [
            executor.submit(process_and_update, chapter, i)
            for i, chapter in enumerate(chapters)
        ]

        # 等待所有任务完成
        for future in futures:
            try:
                future.result()
            except Exception as e:
                print(f"错误: 任务执行出错: {e}")
                with lock:
                    fail_count += 1

    pbar.close()

    # 只在有错误时打印汇总信息
    if fail_count > 0:
        print(
            f"下载完成，成功: {success_count}, 失败: {fail_count}, 跳过: {skip_count}"
        )
    elif skip_count > 0:
        print(f"下载完成，所有文件已下载: {success_count}, 跳过已有文件: {skip_count}")


# 如果直接运行脚本，支持命令行参数
if __name__ == "__main__":
    json_path = os.path.join(os.getcwd(), "data/xszj.json")
    save_path = os.path.join(os.getcwd(), "data/115690/")
    # 调用下载函数
    download_novel(json_path, save_path, max_workers=5)
