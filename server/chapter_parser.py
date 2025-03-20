import requests
from bs4 import BeautifulSoup
import streamlit as st
from urllib.parse import urljoin
import time


# 获取HTML内容
def fetch_html_content(url, timeout=10, retry=3):
    """获取URL的HTML内容，带有重试机制"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }

    for i in range(retry):
        try:
            time.sleep(0.1)
            response = requests.get(url, headers=headers, timeout=timeout)
            response.encoding = "utf-8"  # 确保中文编码正确
            response.raise_for_status()
            return response.text
        except Exception as e:
            if i == retry - 1:  # 最后一次重试
                st.error(f"获取页面失败: {url}, 错误: {e}")
                return None
            continue
    return None


# 获取章节分页列表
def fetch_chapter_pages_from_url(url):
    try:
        html_content = fetch_html_content(url)
        if not html_content:
            return f"错误: 无法获取页面内容"

        # 解析HTML
        soup = BeautifulSoup(html_content, "html.parser")

        # 查找指定的select元素
        select_element = soup.find(
            "select", attrs={"onchange": "location.href=this.value"}
        )

        if not select_element:
            return "错误: 未找到指定的select元素"

        # 提取所有option元素
        options = select_element.find_all("option")

        # 创建结果列表
        result = []

        for option in options:
            value = option.get("value")
            text = option.text.strip()

            if value:
                # 处理相对URL
                if not value.startswith(("http://", "https://")):
                    value = urljoin(url, value)

                result.append({"list_url": value, "text": text})  # 使用list_url作为键名

        return result
    except Exception as e:
        return f"获取章节列表时出错: {str(e)}"


# 从HTML内容中提取章节信息
def extract_detailed_chapters(html_content, base_url):
    """提取小说章节信息"""
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, "html.parser")

    # 查找指定的ul元素
    ul_element = soup.find("ul", class_="read")

    if not ul_element:
        return []  # 错误: 未找到指定的ul元素

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


# 获取所有分页中的详细章节信息
def fetch_all_detailed_chapters(chapter_pages):
    """从所有分页URL获取详细章节列表"""
    all_chapters = []
    progress_bar = st.progress(0)
    total_pages = len(chapter_pages)

    for i, page in enumerate(chapter_pages):
        url = page.get("list_url")
        text = page.get("text")

        if not url:
            continue

        # 更新进度条
        progress_bar.progress((i + 1) / total_pages)
        st.write(f"正在处理: {text} - {url}")

        html_content = fetch_html_content(url)
        if not html_content:
            continue

        chapters = extract_detailed_chapters(html_content, url)

        # 添加章节分组信息
        for chapter in chapters:
            chapter["group"] = text
            # 检查章节是否已存在
            if not any(
                ch.get("chapter_url") == chapter["chapter_url"] for ch in all_chapters
            ):
                all_chapters.append(chapter)

    return all_chapters


# 解析章节内容
def parse_chapter_content(html_content):
    """解析章节内容，返回段落文本列表"""
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    content_div = soup.find("div", class_="content")

    if not content_div:
        return []

    paragraphs = content_div.find_all("p")
    return [p.get_text().strip() for p in paragraphs if p.get_text().strip()]
