import requests
from bs4 import BeautifulSoup
import json
import os
import argparse
from urllib.parse import urljoin


def read_json_file(file_path):
    """读取JSON文件"""
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"读取文件出错: {e}")
        return []


def fetch_html_content(url):
    """获取URL的HTML内容"""
    try:
        response = requests.get(url)
        response.encoding = "utf-8"  # 确保中文编码正确

        if response.status_code != 200:
            print(f"错误: 无法获取页面，状态码: {response.status_code}, URL: {url}")
            return None

        return response.text
    except Exception as e:
        print(f"获取页面内容出错: {e}, URL: {url}")
        return None


def extract_chapters(html_content, base_url):
    """提取小说章节信息"""
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, "html.parser")

    # 查找指定的ul元素
    ul_element = soup.find("ul", class_="read")

    if not ul_element:
        print("错误: 未找到指定的ul元素")
        return []

    # 提取所有li元素
    li_elements = ul_element.find_all("li")

    chapters = []

    for li in li_elements:
        a_tag = li.find("a")
        if a_tag:
            href = a_tag.get("href")
            title = a_tag.text.strip()

            # 处理相对URL
            if href and not href.startswith(("http://", "https://")):
                href = urljoin(base_url, href)

            chapters.append({"chapter_url": href, "chapter_title": title})

    return chapters


def is_chapter_exists(chapter, existing_chapters):
    """检查章节是否已存在"""
    for existing_chapter in existing_chapters:
        # 通过URL和标题双重判断是否为同一章节
        if existing_chapter.get("chapter_url") == chapter.get(
            "chapter_url"
        ) and existing_chapter.get("chapter_title") == chapter.get("chapter_title"):
            return True
    return False


def save_to_json(data, filename):
    """保存为JSON文件"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f"数据已保存到 {filename}")
        return True
    except Exception as e:
        print(f"保存文件出错: {e}")
        return False


def main(input_file, output_file):
    """主函数，接收输入和输出文件路径作为参数"""
    # 读取options.json
    options = read_json_file(input_file)

    if not options:
        print(f"错误: {input_file}为空或无法读取")
        return

    # 首先读取已有的章节数据（如果存在）
    existing_chapters = read_json_file(output_file)
    print(f"已读取现有章节数据，共 {len(existing_chapters)} 章")

    new_chapters_count = 0

    # 处理每个URL
    for option in options:
        url = option.get("list_url")
        text = option.get("text")

        if not url:
            continue

        print(f"正在处理: {text} - {url}")

        html_content = fetch_html_content(url)
        chapters = extract_chapters(html_content, url)

        # 添加章节分组信息，并检查是否已存在
        for chapter in chapters:
            chapter["group"] = text

            # 检查章节是否已存在
            if not is_chapter_exists(chapter, existing_chapters):
                existing_chapters.append(chapter)
                new_chapters_count += 1
            else:
                print(f"跳过已存在章节: {chapter['chapter_title']}")

    # 保存所有章节信息
    if new_chapters_count > 0:
        save_to_json(existing_chapters, output_file)
        print(
            f"已添加 {new_chapters_count} 个新章节，现共有 {len(existing_chapters)} 个章节"
        )
    else:
        print("没有发现新章节")


if __name__ == "__main__":

    options = os.path.join(os.getcwd(), "data/options.json")
    save_path = os.path.join(os.getcwd(), "data/xszj.json")
    # 调用主函数，传入参数
    main(options, save_path)
