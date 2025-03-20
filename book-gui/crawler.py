"""
爬虫核心模块，处理网络请求和数据解析
"""

import time
import threading
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm


class NovelCrawler:
    """小说爬虫核心类，处理网络请求和数据解析"""

    def __init__(self):
        """初始化爬虫类"""
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

    def fetch_options_from_url(self, url, callback=None):
        """从URL获取选项列表"""
        try:
            response = self.session.get(url)
            response.encoding = "utf-8"

            if response.status_code != 200:
                if callback:
                    callback(f"错误: 无法获取页面，状态码: {response.status_code}")
                return None

            soup = BeautifulSoup(response.text, "html.parser")
            select_element = soup.find(
                "select", attrs={"onchange": "location.href=this.value"}
            )

            if not select_element:
                if callback:
                    callback("错误: 未找到指定的select元素")
                return None

            options = select_element.find_all("option")
            result = []

            for option in options:
                value = option.get("value")
                text = option.text.strip()

                if value:
                    if not value.startswith(("http://", "https://")):
                        value = urljoin(url, value)

                    result.append({"list_url": value, "text": text})

                    if callback:
                        callback(f"已找到选项: {text}")

            return result

        except Exception as e:
            if callback:
                callback(f"获取选项出错: {str(e)}")
            return None

    def fetch_chapters(self, option, existing_chapters=None, callback=None):
        """从选项URL获取章节列表"""
        if existing_chapters is None:
            existing_chapters = []

        url = option.get("list_url")
        text = option.get("text")

        if not url:
            if callback:
                callback(f"错误: URL为空")
            return []

        if callback:
            callback(f"正在处理: {text} - {url}")

        try:
            response = self.session.get(url)
            response.encoding = "utf-8"

            if response.status_code != 200:
                if callback:
                    callback(f"错误: 无法获取页面，状态码: {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            ul_element = soup.find("ul", class_="read")

            if not ul_element:
                if callback:
                    callback("错误: 未找到指定的ul元素")
                return []

            li_elements = ul_element.find_all("li")
            new_chapters = []

            for li in li_elements:
                a_tag = li.find("a")
                if a_tag:
                    href = a_tag.get("href")
                    title = a_tag.text.strip()

                    if href and not href.startswith(("http://", "https://")):
                        href = urljoin(url, href)

                    chapter = {
                        "chapter_url": href,
                        "chapter_title": title,
                        "group": text,
                    }

                    # 检查章节是否已存在
                    if not self.is_chapter_exists(chapter, existing_chapters):
                        new_chapters.append(chapter)
                        if callback:
                            callback(f"新章节: {title}")
                    else:
                        if callback:
                            callback(f"跳过已存在章节: {title}")

            return new_chapters

        except Exception as e:
            if callback:
                callback(f"获取章节出错: {str(e)}")
            return []

    @staticmethod
    def is_chapter_exists(chapter, existing_chapters):
        """检查章节是否已存在"""
        for existing_chapter in existing_chapters:
            if existing_chapter.get("chapter_url") == chapter.get(
                "chapter_url"
            ) and existing_chapter.get("chapter_title") == chapter.get("chapter_title"):
                return True
        return False

    def fetch_chapter_content(self, chapter_url, timeout=10, retry=3):
        """获取章节内容"""
        for i in range(retry):
            try:
                response = self.session.get(chapter_url, timeout=timeout)
                response.encoding = "utf-8"
                response.raise_for_status()

                # 解析HTML内容
                soup = BeautifulSoup(response.text, "html.parser")
                content_div = soup.find("div", class_="content")

                if not content_div:
                    return None, "未找到内容区域"

                paragraphs = content_div.find_all("p")
                content = [
                    p.get_text().strip() for p in paragraphs if p.get_text().strip()
                ]

                # 计算总字数
                word_count = sum(len(p) for p in content)

                return content, word_count
            except Exception as e:
                if i == retry - 1:  # 最后一次重试
                    return None, f"获取内容失败: {str(e)}"
                time.sleep(1)  # 重试前等待1秒

    def download_chapters_content(self, chapters, callback=None, max_workers=5):
        """下载章节内容并统计字数"""
        if not chapters:
            if callback:
                callback("没有章节需要下载")
            return []

        updated_chapters = []
        total = len(chapters)
        completed = 0

        # 线程安全的计数器
        success_count = 0
        fail_count = 0
        lock = threading.Lock()

        def process_chapter(chapter):
            nonlocal success_count, fail_count, completed

            try:
                # 检查是否已有字数统计
                if "word_count" in chapter and chapter["word_count"] > 0:
                    with lock:
                        completed += 1
                        if callback:
                            callback(
                                f"跳过已有字数统计: {chapter['chapter_title']} ({completed}/{total})"
                            )
                    return chapter

                # 获取章节内容
                content, word_count = self.fetch_chapter_content(chapter["chapter_url"])

                with lock:
                    completed += 1

                    if content is not None:
                        # 更新章节信息
                        chapter_copy = chapter.copy()
                        chapter_copy["word_count"] = word_count
                        chapter_copy["content"] = content  # 确保内容被存储
                        updated_chapters.append(chapter_copy)
                        success_count += 1

                        if callback:
                            callback(
                                f"已获取: {chapter['chapter_title']}，字数: {word_count} ({completed}/{total})"
                            )
                    else:
                        fail_count += 1
                        if callback:
                            callback(
                                f"获取失败: {chapter['chapter_title']} ({completed}/{total})"
                            )

                # 每次请求后等待一小段时间，避免请求过快
                time.sleep(0.2)

                return chapter

            except Exception as e:
                with lock:
                    completed += 1
                    fail_count += 1
                    if callback:
                        callback(
                            f"处理出错: {chapter.get('chapter_title', '')}, {str(e)} ({completed}/{total})"
                        )
                return chapter

        # 使用线程池并发下载
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            futures = [
                executor.submit(process_chapter, chapter) for chapter in chapters
            ]

            # 等待所有任务完成
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    if callback:
                        callback(f"任务执行出错: {str(e)}")

        if callback:
            callback(f"内容获取完成，成功: {success_count}, 失败: {fail_count}")

        return updated_chapters

    def extract_novel_info(self, url, callback=None):
        """从小说页面提取小说基本信息"""
        try:
            response = self.session.get(url)
            response.encoding = "utf-8"

            if response.status_code != 200:
                if callback:
                    callback(f"错误: 无法获取页面，状态码: {response.status_code}")
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            # 尝试提取小说标题
            title_element = soup.find("h1")
            novel_title = title_element.text.strip() if title_element else ""

            # 尝试提取小说作者
            author_element = soup.find("div", class_="info")
            author = ""
            if author_element:
                author_span = author_element.find(
                    "span", string=lambda text: "作者" in text if text else False
                )
                if author_span:
                    author = (
                        author_span.next_sibling.strip()
                        if author_span.next_sibling
                        else ""
                    )

            # 尝试提取小说简介
            intro_element = soup.find("div", class_="intro")
            description = intro_element.get_text().strip() if intro_element else ""

            # 构建小说信息字典
            novel_info = {
                "name": novel_title,
                "author": author,
                "description": description,
                "source_url": url,
            }

            if callback:
                callback(f"已提取小说信息: {novel_title}")

            return novel_info

        except Exception as e:
            if callback:
                callback(f"提取小说信息出错: {str(e)}")
            return None
