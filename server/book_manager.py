import os
import json
import streamlit as st
from chapter_parser import fetch_chapter_pages_from_url, fetch_all_detailed_chapters
from chapter_downloader import ChapterDownloader


class BookManager:
    def __init__(self):
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)

    def get_books_list(self):
        """获取本地书库中的所有书籍"""
        books = []

        if not os.path.exists(self.data_dir):
            return books

        for book_id in os.listdir(self.data_dir):
            book_path = os.path.join(self.data_dir, book_id)
            if os.path.isdir(book_path) and book_id != "config":  # 排除配置目录
                info_file = os.path.join(book_path, "info.json")
                if os.path.exists(info_file):
                    try:
                        with open(info_file, "r", encoding="utf-8") as f:
                            book_info = json.load(f)
                            books.append(book_info)
                    except Exception as e:
                        st.error(f"读取书籍信息出错: {str(e)}")
                else:
                    # 如果没有info.json，尝试从chapters.json获取信息
                    chapters_file = os.path.join(book_path, "chapters.json")
                    if os.path.exists(chapters_file):
                        try:
                            with open(chapters_file, "r", encoding="utf-8") as f:
                                chapters = json.load(f)
                                books.append(
                                    {
                                        "id": book_id,
                                        "name": book_id,  # 使用ID作为书名
                                        "chapters_count": len(chapters),
                                    }
                                )
                        except Exception as e:
                            st.error(f"读取章节信息出错: {str(e)}")

        return books

    def get_book_chapters(self, book_id):
        """获取指定书籍的章节列表"""
        chapters_file = os.path.join(self.data_dir, book_id, "chapters.json")
        if os.path.exists(chapters_file):
            try:
                with open(chapters_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                st.error(f"读取章节列表出错: {str(e)}")
                return []
        else:
            st.warning("未找到章节列表文件")
            return []

    def add_new_book(self, book_name, chapters_url, book_id):
        """添加新书籍"""
        if not book_name or not chapters_url or not book_id:
            return False, "请填写所有字段"

        # 获取章节分页列表
        chapter_pages = fetch_chapter_pages_from_url(chapters_url)

        if isinstance(chapter_pages, str):  # 如果是错误信息
            return False, chapter_pages

        # 获取详细章节列表
        detailed_chapters = fetch_all_detailed_chapters(chapter_pages)

        # 保存数据
        return self.save_book_data(chapter_pages, detailed_chapters, book_id, book_name)

    def save_book_data(self, chapter_pages, detailed_chapters, book_id, book_name):
        """保存书籍数据"""
        try:
            # 确保目录存在
            dir_path = os.path.join(self.data_dir, book_id)
            os.makedirs(dir_path, exist_ok=True)

            # 保存分页选项信息
            options_file = os.path.join(dir_path, "options.json")
            with open(options_file, "w", encoding="utf-8") as f:
                json.dump(chapter_pages, f, ensure_ascii=False, indent=4)

            # 保存详细章节信息
            chapters_file = os.path.join(dir_path, "chapters.json")
            with open(chapters_file, "w", encoding="utf-8") as f:
                json.dump(detailed_chapters, f, ensure_ascii=False, indent=4)

            # 保存书籍信息
            info_file = os.path.join(dir_path, "info.json")
            info_data = {
                "id": book_id,
                "name": book_name,
                "pages_count": len(chapter_pages),
                "chapters_count": len(detailed_chapters),
            }

            with open(info_file, "w", encoding="utf-8") as f:
                json.dump(info_data, f, ensure_ascii=False, indent=4)

            return (
                True,
                f"书籍《{book_name}》已成功添加，共 {len(detailed_chapters)} 章",
            )
        except Exception as e:
            return False, f"保存书籍数据时出错: {str(e)}"

    def download_book_content(self, book_id, max_workers=5):
        """下载书籍所有章节内容"""
        chapters = self.get_book_chapters(book_id)
        if not chapters:
            return False, "未找到章节信息"

        downloader = ChapterDownloader(book_id, max_workers)
        result = downloader.download_all_chapters(chapters)

        status_message = f"下载完成！总章节：{result['total']}，"
        status_message += (
            f"成功：{result['success']}，跳过：{result['skip']}，失败：{result['fail']}"
        )

        return True, status_message, result

    def is_chapter_downloaded(self, book_id, chapter):
        """检查章节是否已下载"""
        downloader = ChapterDownloader(book_id)
        return downloader.is_chapter_downloaded(chapter)

    def are_all_chapters_downloaded(self, book_id):
        """检查是否所有章节都已下载"""
        chapters = self.get_book_chapters(book_id)
        if not chapters:
            return False

        downloader = ChapterDownloader(book_id)
        return downloader.are_all_chapters_downloaded(chapters)

    def get_chapter_word_count(self, book_id, chapter):
        """获取章节的字数"""
        downloader = ChapterDownloader(book_id)
        return downloader.get_chapter_word_count(chapter)

    def get_book_total_words(self, book_id):
        """获取书籍总字数"""
        chapters = self.get_book_chapters(book_id)
        if not chapters:
            return 0, 0

        downloader = ChapterDownloader(book_id)
        return downloader.get_total_word_count(chapters)
