import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import streamlit as st
from chapter_parser import fetch_html_content, parse_chapter_content


class ChapterDownloader:
    def __init__(self, book_id, max_workers=5):
        self.book_id = book_id
        self.max_workers = max_workers
        self.base_dir = os.path.join("data", book_id)
        self.content_dir = os.path.join(self.base_dir, "content")
        self.lock = threading.Lock()
        self.total_chapters = 0
        self.success_count = 0
        self.fail_count = 0
        self.skip_count = 0
        self.chapter_statuses = {}
        os.makedirs(self.content_dir, exist_ok=True)

    def get_chapter_file_path(self, chapter):
        """根据章节信息生成保存文件的路径"""
        title = chapter["chapter_title"]
        group = chapter.get("group", "")

        # 创建合法的文件名
        safe_title = "".join(c if c.isalnum() or c in "- " else "_" for c in title)
        filename = f"{safe_title}.txt"

        # 如果有分组，创建子目录
        if group:
            safe_group = "".join(c if c.isalnum() or c in "- " else "_" for c in group)
            group_dir = os.path.join(self.content_dir, safe_group)
            return os.path.join(group_dir, filename)
        else:
            return os.path.join(self.content_dir, filename)

    def is_chapter_downloaded(self, chapter):
        """检查章节内容是否已下载"""
        file_path = self.get_chapter_file_path(chapter)
        return os.path.exists(file_path) and os.path.getsize(file_path) > 0

    def get_chapter_word_count(self, chapter):
        """获取章节的字数"""
        file_path = self.get_chapter_file_path(chapter)
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            return 0

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                # 统计中文字符数（移除空格、换行符等）
                text = (
                    content.replace(" ", "")
                    .replace("\n", "")
                    .replace("\r", "")
                    .replace("\t", "")
                )
                return len(text)
        except Exception as e:
            print(f"读取章节内容出错: {str(e)}")
            return 0

    def are_all_chapters_downloaded(self, chapters):
        """检查是否所有章节都已下载"""
        for chapter in chapters:
            if not self.is_chapter_downloaded(chapter):
                return False
        return True

    def download_chapter(self, index, chapter):
        """下载单个章节内容"""
        url = chapter.get("chapter_url")
        title = chapter.get("chapter_title")
        file_path = self.get_chapter_file_path(chapter)

        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # 检查文件是否已存在
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            with self.lock:
                self.skip_count += 1
                self.chapter_statuses[index] = "已存在"
            return True

        try:
            html_content = fetch_html_content(url, timeout=15)
            if not html_content:
                with self.lock:
                    self.fail_count += 1
                    self.chapter_statuses[index] = "获取内容失败"
                return False

            content_paragraphs = parse_chapter_content(html_content)
            if not content_paragraphs:
                with self.lock:
                    self.fail_count += 1
                    self.chapter_statuses[index] = "解析内容失败"
                return False

            # 保存内容
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(content_paragraphs))

            with self.lock:
                self.success_count += 1
                self.chapter_statuses[index] = "下载成功"
            return True

        except Exception as e:
            with self.lock:
                self.fail_count += 1
                self.chapter_statuses[index] = f"错误: {str(e)[:50]}..."
            return False

    def download_all_chapters(self, chapters):
        """下载所有章节内容"""
        self.total_chapters = len(chapters)
        self.success_count = 0
        self.fail_count = 0
        self.skip_count = 0
        self.chapter_statuses = {i: "等待中" for i in range(len(chapters))}

        # 使用线程池处理下载
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for i, chapter in enumerate(chapters):
                # 直接提交任务，不在子线程中使用streamlit组件
                future = executor.submit(self.download_chapter, i, chapter)
                futures.append(future)
                # 短暂等待避免同时提交太多任务
                time.sleep(0.1)

            # 创建一个进度条 - 在主线程中创建
            progress_bar = st.progress(0.0)
            status_text = st.empty()

            # 监控进度并更新UI
            completed = 0
            while completed < len(futures):
                completed = sum(1 for f in futures if f.done())
                progress = completed / len(futures)

                # 在主线程中更新UI
                progress_bar.progress(progress)
                current_status = f"进度: {completed}/{len(futures)} "
                current_status += f"(成功: {self.success_count}, 跳过: {self.skip_count}, 失败: {self.fail_count})"
                status_text.text(current_status)

                # 避免过于频繁更新UI
                time.sleep(0.5)

            # 等待所有任务完成
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f"任务执行出错: {e}")

        final_status = {
            "total": self.total_chapters,
            "success": self.success_count,
            "skip": self.skip_count,
            "fail": self.fail_count,
            "chapter_statuses": self.chapter_statuses,
        }

        return final_status

    def get_total_word_count(self, chapters):
        """获取所有已下载章节的总字数"""
        total_count = 0
        downloaded_count = 0

        for chapter in chapters:
            word_count = self.get_chapter_word_count(chapter)
            if word_count > 0:
                total_count += word_count
                downloaded_count += 1

        return total_count, downloaded_count
