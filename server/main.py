import streamlit as st
from book_manager import BookManager
from config_page import show_config_page
from audiobook_creator import show_audiobook_creation_page

# 初始化图书管理器
book_manager = BookManager()


# 添加书籍对话框
def show_add_book_dialog():
    with st.form(key="add_book_form"):
        st.subheader("添加新书")
        book_name = st.text_input("小说名")
        chapters_url = st.text_input("小说章节列表URL")
        book_id = st.text_input("小说ID")

        col1, col2 = st.columns(2)
        with col1:
            submit_button = st.form_submit_button(label="确定")
        with col2:
            cancel_button = st.form_submit_button(label="取消")

        if cancel_button:
            st.session_state.show_add_dialog = False
            st.rerun()

        if submit_button:
            if not book_name or not chapters_url or not book_id:
                st.error("请填写所有字段")
                return

            with st.spinner("正在获取和处理章节信息..."):
                success, message = book_manager.add_new_book(
                    book_name, chapters_url, book_id
                )

            if success:
                st.success(message)
                st.session_state.show_add_dialog = False
                st.rerun()
            else:
                st.error(message)


# 格式化字数显示
def format_word_count(count):
    if count >= 10000:
        return f"{count/10000:.2f}万字"
    else:
        return f"{count}字"


# 显示书籍章节列表
def show_book_chapters(book_id):
    chapters = book_manager.get_book_chapters(book_id)

    if not chapters:
        return

    # 获取书籍总字数
    total_words, downloaded_chapters = book_manager.get_book_total_words(book_id)

    # 检查是否所有章节都已下载
    all_downloaded = book_manager.are_all_chapters_downloaded(book_id)

    # 显示统计信息
    st.subheader("书籍统计")
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])  # 修改为4列
    with col1:
        st.metric("总章节数", len(chapters))
    with col2:
        st.metric("已下载章节", downloaded_chapters)
    with col3:
        st.metric("总字数", format_word_count(total_words))
    with col4:
        # 添加有声书制作按钮
        if st.button("开始制作有声书", key="start_audiobook"):
            st.session_state.current_page = "audiobook_creation"
            st.session_state.audiobook_book_id = book_id
            st.rerun()

    # 添加下载控制区域
    st.subheader("章节内容下载")

    if all_downloaded:
        st.success("✅ 所有章节都已下载至本地")
    else:
        download_col1, download_col2 = st.columns([1, 2])

        with download_col1:
            max_workers = st.slider("下载线程数", 1, 10, 5)

        with download_col2:
            if st.button("一键下载所有章节", key="download_all"):
                with st.spinner("正在下载章节内容..."):
                    success, message, result = book_manager.download_book_content(
                        book_id, max_workers
                    )

                if success:
                    st.success(message)
                    # 刷新页面显示下载状态
                    st.rerun()
                else:
                    st.error(message)

        # 提供下载状态信息
        st.info("下载过程可能需要几分钟时间，请耐心等待。下载完成后页面会自动刷新。")

    # 按分组显示章节
    groups = {}
    for chapter in chapters:
        group = chapter.get("group", "未分组")
        if group not in groups:
            groups[group] = []
        groups[group].append(chapter)

    # 遍历分组显示
    for group, group_chapters in sorted(groups.items()):
        # 计算当前分组的总字数
        group_word_count = sum(
            book_manager.get_chapter_word_count(book_id, chapter)
            for chapter in group_chapters
        )
        group_downloaded = sum(
            1
            for chapter in group_chapters
            if book_manager.is_chapter_downloaded(book_id, chapter)
        )

        with st.expander(
            f"{group} ({group_downloaded}/{len(group_chapters)}章 - {format_word_count(group_word_count)})",
            expanded=True,
        ):
            for i, chapter in enumerate(group_chapters, 1):
                # 检查章节是否已下载
                is_downloaded = book_manager.is_chapter_downloaded(book_id, chapter)

                if is_downloaded:
                    # 获取字数
                    word_count = book_manager.get_chapter_word_count(book_id, chapter)
                    download_status = f"✅ {format_word_count(word_count)}"
                else:
                    download_status = "❌ 未下载"

                # 显示章节信息
                st.write(f"{i}. {chapter['chapter_title']} - {download_status}")


# 主应用
def main():
    st.title("小说章节管理系统")

    # 初始化会话状态
    if "show_add_dialog" not in st.session_state:
        st.session_state.show_add_dialog = False

    if "selected_book" not in st.session_state:
        st.session_state.selected_book = None

    if "current_page" not in st.session_state:
        st.session_state.current_page = "books"  # 默认显示书籍页面

    if "audiobook_book_id" not in st.session_state:
        st.session_state.audiobook_book_id = None

    if "audiobook_tab" not in st.session_state:
        st.session_state.audiobook_tab = "character_info"

    # 侧边栏 - 菜单
    st.sidebar.title("菜单")

    # 根据当前页面调整菜单显示
    if st.session_state.current_page != "audiobook_creation":
        # 使用单选按钮替代普通按钮，更明显
        menu_selection = st.sidebar.radio(
            "选择功能", ["📚 书籍管理", "⚙️ 全局配置"], key="menu_radio"
        )

        # 根据选择切换页面
        if menu_selection == "📚 书籍管理" and st.session_state.current_page != "books":
            st.session_state.current_page = "books"
            st.session_state.selected_book = None
            st.session_state.show_add_dialog = False
            st.rerun()

        if menu_selection == "⚙️ 全局配置" and st.session_state.current_page != "config":
            st.session_state.current_page = "config"
            st.session_state.selected_book = None
            st.session_state.show_add_dialog = False
            st.rerun()
    else:
        # 有声书制作页面的侧边栏
        st.sidebar.button("返回书籍列表", on_click=lambda: back_to_books())

        # 有声书制作页面的标签页
        audiobook_tab = st.sidebar.radio(
            "有声书制作功能",
            ["书籍角色信息提取与配置", "小说内容"],
            key="audiobook_sidebar_tab",
        )

        # 设置当前活动的标签页
        st.session_state.audiobook_tab = audiobook_tab.replace(
            "书籍角色信息提取与配置", "character_info"
        ).replace("小说内容", "novel_content")

    st.sidebar.divider()

    # 如果在书籍管理页面，显示书籍列表
    if st.session_state.current_page == "books":
        # 添加图书按钮
        if st.sidebar.button(
            "➕ 添加图书", type="primary"
        ):  # 使用primary类型使按钮更明显
            st.session_state.show_add_dialog = True
            st.session_state.selected_book = None
            st.rerun()

        # 显示书籍列表
        st.sidebar.subheader("本地书库")
        books = book_manager.get_books_list()

        if not books:
            st.sidebar.info("本地书库为空，请添加书籍")

        for book in books:
            chapters_count = book.get("chapters_count", 0)
            if st.sidebar.button(
                f"📚 {book['name']} ({chapters_count}章)", key=f"book_{book['id']}"
            ):
                st.session_state.selected_book = book["id"]
                st.session_state.show_add_dialog = False
                st.rerun()

    # 主内容区域
    if st.session_state.current_page == "config":
        # 显示配置页面
        show_config_page()
    elif st.session_state.current_page == "audiobook_creation":
        # 显示有声书制作页面
        show_audiobook_creation_page(st.session_state.audiobook_book_id)
    elif st.session_state.show_add_dialog:
        # 显示添加书籍对话框
        show_add_book_dialog()
    elif st.session_state.selected_book:
        # 显示选中的书籍
        books = book_manager.get_books_list()
        selected_book_info = next(
            (book for book in books if book["id"] == st.session_state.selected_book),
            None,
        )
        if selected_book_info:
            st.header(f"《{selected_book_info['name']}》的章节列表")
            show_book_chapters(st.session_state.selected_book)
        else:
            st.warning("未找到选中的书籍信息")
    else:
        # 显示欢迎信息
        st.info("👈 请从侧边栏选择一本书，或者点击'添加图书'按钮添加新书")

        # 显示书籍统计信息
        books = book_manager.get_books_list()
        if books:
            st.subheader("书库统计")

            # 计算总章节数和总字数
            total_chapters = 0
            total_downloaded = 0
            total_words = 0

            for book in books:
                book_id = book.get("id")
                chapters_count = book.get("chapters_count", 0)
                total_chapters += chapters_count

                if book_id:
                    words, downloaded = book_manager.get_book_total_words(book_id)
                    total_words += words
                    total_downloaded += downloaded

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("书籍总数", len(books))
            with col2:
                st.metric("章节总数", f"{total_downloaded}/{total_chapters}")
            with col3:
                st.metric("总字数", format_word_count(total_words))


# 返回书籍列表的辅助函数
def back_to_books():
    st.session_state.current_page = "books"
    st.session_state.audiobook_book_id = None
    st.session_state.audiobook_tab = "novel_content"


if __name__ == "__main__":
    main()
