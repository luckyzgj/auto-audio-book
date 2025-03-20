"""
小说章节爬虫与对话分析工具主界面
整合了爬虫、数据库、对话分析等功能，提供统一的图形界面
"""

import os
import re
import json
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(override=True)

# 导入自定义模块
from config import (
    APP_NAME,
    UI_DEFAULT_WIDTH,
    UI_DEFAULT_HEIGHT,
    UI_MIN_WIDTH,
    UI_MIN_HEIGHT,
)
from models import Novel, Chapter, APIKey
from db_manager import MongoDBManager
from crawler import NovelCrawler
from dialogue_analyzer import DialogueAnalyzer
from ui_dialogs import (
    DatabaseConfigDialog,
    NovelInfoDialog,
    DownloadProgressDialog,
    APIKeyConfigDialog,
    MultiAPIKeysDialog,
    DialogueViewDialog,
)
import utils


class NovelCrawlerGUI(tk.Tk):
    """小说爬虫GUI应用"""

    def __init__(self):
        """初始化GUI应用"""
        super().__init__()

        self.title(APP_NAME)
        self.geometry(f"{UI_DEFAULT_WIDTH}x{UI_DEFAULT_HEIGHT}")
        self.minsize(UI_MIN_WIDTH, UI_MIN_HEIGHT)

        # 初始化核心组件
        self.crawler = NovelCrawler()
        self.db_manager = MongoDBManager()
        self.dialogue_analyzer = DialogueAnalyzer(self.db_manager)

        # 当前加载的小说相关数据
        self.current_novel = None
        self.current_novel_id = None
        self.options = []
        self.chapters = []

        # 下载任务标志
        self.download_task = None
        self.analyze_task = None

        # 创建界面
        self.create_widgets()

        # 绑定事件
        self.bind_events()

        # 尝试连接到默认数据库
        self.connect_to_database()

        # 加载小说列表
        self.load_novel_list()

    def create_widgets(self):
        """创建GUI组件"""
        # 创建菜单栏
        menubar = tk.Menu(self)

        # 数据库菜单
        db_menu = tk.Menu(menubar, tearoff=0)
        db_menu.add_command(label="配置数据库", command=self.configure_database)
        db_menu.add_command(label="重新连接", command=self.reconnect_database)
        db_menu.add_command(label="断开连接", command=self.disconnect_database)
        db_menu.add_separator()
        db_menu.add_command(label="退出", command=self.quit)
        menubar.add_cascade(label="数据库", menu=db_menu)

        # 小说菜单
        novel_menu = tk.Menu(menubar, tearoff=0)
        novel_menu.add_command(label="新建小说", command=self.create_novel)
        novel_menu.add_command(label="编辑小说信息", command=self.edit_novel)
        novel_menu.add_command(label="删除小说", command=self.delete_novel)
        novel_menu.add_separator()
        novel_menu.add_command(label="导出到JSON", command=self.export_book_to_json)
        menubar.add_cascade(label="小说", menu=novel_menu)

        # 章节菜单
        chapter_menu = tk.Menu(menubar, tearoff=0)
        chapter_menu.add_command(
            label="获取章节内容", command=self.download_chapters_content
        )
        chapter_menu.add_command(
            label="分析章节对话", command=self.analyze_chapters_dialogue
        )
        menubar.add_cascade(label="章节", menu=chapter_menu)

        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="GeminiAI 设置", command=self.configure_api)
        tools_menu.add_command(label="多API密钥管理", command=self.manage_api_keys)
        menubar.add_cascade(label="工具", menu=tools_menu)

        # 设置菜单栏
        self.config(menu=menubar)

        # 创建主框架
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 顶部区域 - 小说选择和URL输入
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=5)

        # 小说选择
        novel_frame = ttk.LabelFrame(top_frame, text="小说选择")
        novel_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.novel_var = tk.StringVar()
        self.novel_combobox = ttk.Combobox(novel_frame, textvariable=self.novel_var)
        self.novel_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)

        refresh_btn = ttk.Button(novel_frame, text="刷新", command=self.load_novel_list)
        refresh_btn.pack(side=tk.RIGHT, padx=5, pady=5)

        load_btn = ttk.Button(
            novel_frame, text="加载", command=self.load_selected_novel
        )
        load_btn.pack(side=tk.RIGHT, padx=5, pady=5)

        # URL输入
        url_frame = ttk.LabelFrame(top_frame, text="网址输入")
        url_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))

        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var)
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)

        fetch_btn = ttk.Button(url_frame, text="获取选项", command=self.fetch_options)
        fetch_btn.pack(side=tk.RIGHT, padx=5, pady=5)

        # 分割线
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # 内容区域
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # 左右分割的面板
        self.paned = ttk.PanedWindow(content_frame, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # 左侧选项列表
        left_frame = ttk.LabelFrame(self.paned, text="选项列表")
        self.paned.add(left_frame, weight=1)

        # 选项列表及滚动条
        options_frame = ttk.Frame(left_frame)
        options_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.options_tree = ttk.Treeview(
            options_frame, columns=("text", "url"), show="headings"
        )
        self.options_tree.heading("text", text="选项名称")
        self.options_tree.heading("url", text="链接")
        self.options_tree.column("text", width=150)
        self.options_tree.column("url", width=300)
        self.options_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        options_scroll = ttk.Scrollbar(
            options_frame, orient=tk.VERTICAL, command=self.options_tree.yview
        )
        options_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.options_tree.configure(yscrollcommand=options_scroll.set)

        # 选项操作按钮
        options_btn_frame = ttk.Frame(left_frame)
        options_btn_frame.pack(fill=tk.X, padx=5, pady=5)

        fetch_chapters_btn = ttk.Button(
            options_btn_frame, text="抓取选中章节", command=self.fetch_selected_chapters
        )
        fetch_chapters_btn.pack(side=tk.LEFT, padx=5)

        fetch_all_btn = ttk.Button(
            options_btn_frame, text="抓取全部章节", command=self.fetch_all_chapters
        )
        fetch_all_btn.pack(side=tk.LEFT, padx=5)

        save_options_btn = ttk.Button(
            options_btn_frame, text="保存选项", command=self.save_options
        )
        save_options_btn.pack(side=tk.RIGHT, padx=5)

        # 右侧章节列表
        right_frame = ttk.LabelFrame(self.paned, text="章节列表")
        self.paned.add(right_frame, weight=2)

        # 章节列表及滚动条
        chapters_frame = ttk.Frame(right_frame)
        chapters_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 修改章节列表，添加字数列和对话分析状态列
        self.chapters_tree = ttk.Treeview(
            chapters_frame,
            columns=("title", "group", "word_count", "dialogue_status", "url"),
            show="headings",
        )
        self.chapters_tree.heading("title", text="章节标题")
        self.chapters_tree.heading("group", text="分组")
        self.chapters_tree.heading("word_count", text="字数")
        self.chapters_tree.heading("dialogue_status", text="对话分析")
        self.chapters_tree.heading("url", text="链接")
        self.chapters_tree.column("title", width=200)
        self.chapters_tree.column("group", width=100)
        self.chapters_tree.column("word_count", width=80)
        self.chapters_tree.column("dialogue_status", width=80)
        self.chapters_tree.column("url", width=300)
        self.chapters_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        chapters_scroll = ttk.Scrollbar(
            chapters_frame, orient=tk.VERTICAL, command=self.chapters_tree.yview
        )
        chapters_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.chapters_tree.configure(yscrollcommand=chapters_scroll.set)

        # 章节操作按钮
        chapters_btn_frame = ttk.Frame(right_frame)
        chapters_btn_frame.pack(fill=tk.X, padx=5, pady=5)

        # 添加获取章节内容按钮
        get_content_btn = ttk.Button(
            chapters_btn_frame, text="获取内容", command=self.download_chapters_content
        )
        get_content_btn.pack(side=tk.LEFT, padx=5)

        # 添加分析对话按钮
        analyze_btn = ttk.Button(
            chapters_btn_frame, text="分析对话", command=self.analyze_chapters_dialogue
        )
        analyze_btn.pack(side=tk.LEFT, padx=5)

        save_chapters_btn = ttk.Button(
            chapters_btn_frame, text="保存章节", command=self.save_chapters
        )
        save_chapters_btn.pack(side=tk.RIGHT, padx=5)

        # 状态栏
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=5)

        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(
            status_frame,
            orient=tk.HORIZONTAL,
            length=100,
            mode="determinate",
            variable=self.progress_var,
        )
        self.progress.pack(fill=tk.X, padx=5, pady=5)

        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_label = ttk.Label(
            status_frame, textvariable=self.status_var, anchor=tk.W
        )
        status_label.pack(fill=tk.X, padx=5)

        # 数据库状态
        self.db_status_var = tk.StringVar(value="未连接")
        db_status_label = ttk.Label(
            status_frame, textvariable=self.db_status_var, anchor=tk.E
        )
        db_status_label.pack(fill=tk.X, padx=5)

        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="操作日志")
        log_frame.pack(fill=tk.X, pady=5)

        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL)
        self.log_text = tk.Text(log_frame, height=5, yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        log_scroll.config(command=self.log_text.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)

    def bind_events(self):
        """绑定事件处理"""
        # 双击选项跳转到对应URL
        self.options_tree.bind("<Double-1>", self.open_option_url)

        # 双击章节跳转到对应URL
        self.chapters_tree.bind("<Double-1>", self.open_chapter_url)

        # 章节右键菜单
        self.chapters_tree.bind("<Button-3>", self.show_chapter_context_menu)

        # 小说选择改变时更新界面
        self.novel_combobox.bind(
            "<<ComboboxSelected>>", lambda e: self.load_selected_novel()
        )

    def show_chapter_context_menu(self, event):
        """显示章节右键菜单"""
        # 确保选中了章节
        item = self.chapters_tree.identify_row(event.y)
        if not item:
            return

        # 选中点击的行
        self.chapters_tree.selection_set(item)

        # 创建菜单
        context_menu = tk.Menu(self, tearoff=0)
        context_menu.add_command(
            label="获取内容", command=self.download_chapters_content
        )
        context_menu.add_command(
            label="分析对话", command=self.analyze_chapters_dialogue
        )
        context_menu.add_command(
            label="查看对话分析", command=self.view_chapter_dialogue
        )
        context_menu.add_separator()
        context_menu.add_command(
            label="打开链接", command=lambda: self.open_chapter_url(None)
        )

        # 显示菜单
        context_menu.tk_popup(event.x_root, event.y_root)

    def log(self, message):
        """添加日志消息"""
        formatted_message = utils.log_format(message)
        self.log_text.insert(tk.END, f"{formatted_message}\n")
        self.log_text.see(tk.END)
        self.status_var.set(message)
        self.update_idletasks()

    def open_option_url(self, event):
        """打开选项URL（双击事件）"""
        selected = self.options_tree.selection()
        if not selected:
            return

        item = selected[0]
        url = self.options_tree.item(item, "values")[1]
        if messagebox.askyesno("打开URL", f"是否在浏览器中打开该URL?\n{url}"):
            import webbrowser

            webbrowser.open(url)

    def open_chapter_url(self, event):
        """打开章节URL（双击事件）"""
        selected = self.chapters_tree.selection()
        if not selected:
            return

        item = selected[0]
        url = self.chapters_tree.item(item, "values")[
            4
        ]  # 索引变为4，因为添加了对话分析状态列
        if messagebox.askyesno("打开URL", f"是否在浏览器中打开该URL?\n{url}"):
            import webbrowser

            webbrowser.open(url)

    def update_options_tree(self):
        """更新选项列表显示"""
        self.options_tree.delete(*self.options_tree.get_children())
        for option in self.options:
            self.options_tree.insert(
                "", "end", values=(option.get("text"), option.get("list_url"))
            )

    def update_chapters_tree(self):
        """更新章节列表显示"""
        self.chapters_tree.delete(*self.chapters_tree.get_children())

        # 获取所有已有对话分析的章节URL集合
        analyzed_chapters = set()
        if self.db_manager.is_connected() and self.current_novel_id:
            try:
                # 查询有对话分析结果的章节
                chapters_with_dialogues = list(
                    self.db_manager.db.chapters.find(
                        {
                            "novel_id": self.current_novel_id,
                            "dialogues": {"$exists": True, "$ne": []},
                        }
                    )
                )

                # 将URL加入集合
                for chapter in chapters_with_dialogues:
                    analyzed_chapters.add(chapter.get("url", ""))
            except Exception as e:
                self.log(f"获取对话分析状态出错: {str(e)}")

        for chapter in self.chapters:
            # 处理字数显示
            word_count = chapter.get("word_count", 0)
            if isinstance(word_count, int) and word_count > 0:
                word_count_str = f"{word_count}"
            else:
                word_count_str = "-"  # 未获取字数

            # 对话分析状态
            has_analysis = chapter.get("chapter_url", "") in analyzed_chapters
            status = "✓" if has_analysis else ""

            # 更新为包含字数和对话分析状态的数据结构
            self.chapters_tree.insert(
                "",
                "end",
                values=(
                    chapter.get("chapter_title"),
                    chapter.get("group"),
                    word_count_str,
                    status,  # 添加对话分析状态
                    chapter.get("chapter_url"),
                ),
            )

    def update_db_status(self):
        """更新数据库状态显示"""
        if self.db_manager.is_connected():
            self.db_status_var.set(f"已连接: {self.db_manager.db.name}")
        else:
            self.db_status_var.set("未连接")

    def connect_to_database(self):
        """连接到数据库"""
        # 尝试连接到默认的本地MongoDB
        try:
            success, message = self.db_manager.connect(
                "mongodb://localhost:27017/", "novels"
            )

            if success:
                self.log("已连接到默认数据库")
                self.update_db_status()

                # 保存连接配置
                self.db_manager.save_connection_config(
                    {
                        "connection_string": "mongodb://localhost:27017/",
                        "db_name": "novels",
                        "config": {
                            "host": "localhost",
                            "port": "27017",
                            "username": "",
                            "password": "",
                            "auth_db": "admin",
                            "db_name": "novels",
                        },
                    }
                )
            else:
                self.log(f"连接默认数据库失败: {message}")
        except Exception as e:
            self.log(f"连接数据库出错: {str(e)}")

    def configure_database(self):
        """配置数据库连接"""
        # 创建配置对话框
        config = None
        if self.db_manager.last_config:
            config = self.db_manager.last_config.get("config")

        dialog = DatabaseConfigDialog(self, self.db_manager, config)
        self.wait_window(dialog)

        # 如果有返回结果，则更新状态
        if dialog.result:
            self.update_db_status()
            self.load_novel_list()

    def reconnect_database(self):
        """重新连接数据库"""
        if not self.db_manager.last_config:
            messagebox.showwarning("警告", "没有保存的连接配置，请先配置数据库")
            self.configure_database()
            return

        try:
            success, message = self.db_manager.reconnect()

            if success:
                self.log("已重新连接到数据库")
                self.update_db_status()
                self.load_novel_list()
            else:
                self.log(f"重新连接数据库失败: {message}")
                messagebox.showerror("连接错误", message)
        except Exception as e:
            self.log(f"重新连接数据库出错: {str(e)}")

    def disconnect_database(self):
        """断开数据库连接"""
        if self.db_manager.is_connected():
            self.db_manager.disconnect()
            self.update_db_status()
            self.log("已断开数据库连接")

    def load_novel_list(self):
        """加载小说列表"""
        if not self.db_manager.is_connected():
            messagebox.showwarning("警告", "未连接到数据库")
            return

        try:
            novels = self.db_manager.get_novels()

            # 更新下拉框
            self.novel_combobox["values"] = [
                f"{novel['name']} ({novel['_id']})" for novel in novels
            ]

            if novels:
                self.log(f"已加载 {len(novels)} 本小说")
            else:
                self.log("数据库中没有小说")

        except Exception as e:
            self.log(f"加载小说列表失败: {str(e)}")

    def load_selected_novel(self):
        """加载选中的小说"""
        if not self.db_manager.is_connected():
            messagebox.showwarning("警告", "未连接到数据库")
            return

        selection = self.novel_var.get()
        if not selection:
            return

        # 从选择中提取小说ID
        match = re.search(r"\((.*?)\)$", selection)
        if not match:
            return

        novel_id = match.group(1)

        try:
            # 加载小说信息
            novel_data = self.db_manager.get_novel(novel_id)
            if not novel_data:
                self.log(f"未找到小说: {novel_id}")
                return

            # 加载章节信息
            chapters_data = self.db_manager.get_chapters(novel_id)

            # 转换为爬虫格式
            chapters = []
            for chapter in chapters_data:
                chapters.append(
                    {
                        "chapter_title": chapter.get("title", ""),
                        "chapter_url": chapter.get("url", ""),
                        "group": chapter.get("volume", ""),
                        "word_count": chapter.get("word_count", 0),
                        "content": chapter.get("content", []),  # Add this line
                    }
                )

            # 更新当前数据
            self.current_novel = Novel.from_dict(novel_data)
            self.current_novel_id = novel_data["_id"]
            self.options = novel_data.get("volumes", [])
            self.chapters = chapters

            # 更新界面
            self.update_options_tree()
            self.update_chapters_tree()

            self.log(f"已加载小说: {novel_data['name']}, {len(chapters)} 章节")

        except Exception as e:
            self.log(f"加载小说失败: {str(e)}")
            import traceback

            traceback.print_exc()

    def create_novel(self):
        """创建新小说"""
        dialog = NovelInfoDialog(self)
        self.wait_window(dialog)

        if dialog.result:
            self.current_novel = dialog.result
            self.current_novel_id = None
            self.options = []
            self.chapters = []

            # 更新界面
            self.update_options_tree()
            self.update_chapters_tree()

            self.log(f"已创建新小说: {self.current_novel.name}")

            # 更新URL
            if self.current_novel.source_url:
                self.url_var.set(self.current_novel.source_url)

    def edit_novel(self):
        """编辑当前小说信息"""
        if not self.current_novel:
            messagebox.showwarning("警告", "请先选择或创建小说")
            return

        dialog = NovelInfoDialog(self, self.current_novel)
        self.wait_window(dialog)

        if dialog.result:
            self.current_novel = dialog.result
            self.log(f"已更新小说信息: {self.current_novel.name}")

            # 更新URL
            if self.current_novel.source_url:
                self.url_var.set(self.current_novel.source_url)

    def delete_novel(self):
        """删除当前小说"""
        if not self.db_manager.is_connected():
            messagebox.showwarning("警告", "未连接到数据库")
            return

        if not self.current_novel_id:
            messagebox.showwarning("警告", "请先选择已保存的小说")
            return

        if not messagebox.askyesno(
            "确认删除", f"确定要删除小说 '{self.current_novel.name}' 及其所有章节吗？"
        ):
            return

        try:
            success, message = self.db_manager.delete_novel(self.current_novel_id)

            if success:
                self.log(message)
                self.current_novel = None
                self.current_novel_id = None
                self.options = []
                self.chapters = []

                # 更新界面
                self.update_options_tree()
                self.update_chapters_tree()
                self.load_novel_list()
            else:
                self.log(f"删除小说失败: {message}")

        except Exception as e:
            self.log(f"删除小说出错: {str(e)}")

    def fetch_options(self):
        """获取选项列表"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("警告", "请输入有效的URL")
            return

        # 尝试从URL提取小说信息
        self.log(f"正在从 {url} 提取小说信息...")
        novel_info = self.crawler.extract_novel_info(url, callback=self.log)

        if novel_info:
            # 使用提取的信息创建小说对象
            novel = Novel(
                name=novel_info.get("name", ""),
                author=novel_info.get("author", ""),
                description=novel_info.get("description", ""),
                source_url=url,
            )

            # 显示小说信息编辑对话框，让用户确认或修改
            dialog = NovelInfoDialog(self, novel)
            self.wait_window(dialog)

            if dialog.result:
                self.current_novel = dialog.result
                self.current_novel_id = None
                self.options = []
                self.chapters = []
            else:
                return
        else:
            # 如果提取失败，让用户手动输入
            dialog = NovelInfoDialog(self, Novel(source_url=url))
            self.wait_window(dialog)

            if dialog.result:
                self.current_novel = dialog.result
                self.current_novel_id = None
                self.options = []
                self.chapters = []
            else:
                return

        self.log(f"开始获取选项: {url}")
        self.progress_var.set(0)

        # 在后台线程执行爬取操作
        def background_task():
            options = self.crawler.fetch_options_from_url(url, callback=self.log)

            # 在主线程更新界面
            self.after(0, lambda: self.handle_options_result(options))

        threading.Thread(target=background_task).start()

    def handle_options_result(self, options):
        """处理获取到的选项结果"""
        if options is None:
            self.log("获取选项失败")
            messagebox.showerror("错误", "获取选项失败，请检查URL或网络连接")
            return

        if not options:
            self.log("未找到选项")
            messagebox.showinfo("提示", "未找到任何选项")
            return

        self.options = options
        self.update_options_tree()
        self.progress_var.set(100)
        self.log(f"成功获取 {len(options)} 个选项")

    def fetch_selected_chapters(self):
        """获取选中选项的章节"""
        selected_items = self.options_tree.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先选择要抓取的选项")
            return

        selected_options = []
        for item in selected_items:
            idx = self.options_tree.index(item)
            if 0 <= idx < len(self.options):
                selected_options.append(self.options[idx])

        self.fetch_chapters_batch(selected_options)

    def fetch_all_chapters(self):
        """获取所有选项的章节"""
        if not self.options:
            messagebox.showwarning("警告", "请先获取选项列表")
            return

        self.fetch_chapters_batch(self.options)

    def fetch_chapters_batch(self, options_list):
        """批量获取章节信息"""
        if not options_list:
            return

        self.log(f"开始获取章节，共 {len(options_list)} 个选项")
        self.progress_var.set(0)

        # 在后台线程执行爬取操作
        def background_task():
            new_chapters = []
            total = len(options_list)

            for i, option in enumerate(options_list):
                # 更新进度
                progress = (i / total) * 100
                self.after(0, lambda p=progress: self.progress_var.set(p))
                self.after(
                    0,
                    lambda msg=f"正在处理: {option.get('text')} ({i+1}/{total})": self.log(
                        msg
                    ),
                )

                # 抓取章节
                chapters = self.crawler.fetch_chapters(
                    option, self.chapters, callback=self.log
                )
                new_chapters.extend(chapters)

            # 在主线程更新界面
            self.after(0, lambda: self.handle_chapters_result(new_chapters))

        threading.Thread(target=background_task).start()

    def handle_chapters_result(self, new_chapters):
        """处理获取到的章节结果"""
        if new_chapters:
            self.chapters.extend(new_chapters)
            self.update_chapters_tree()
            self.log(
                f"成功获取 {len(new_chapters)} 个新章节，总共 {len(self.chapters)} 个章节"
            )
        else:
            self.log("未找到新章节")

        self.progress_var.set(100)

    def download_chapters_content(self):
        """下载章节内容"""
        if not self.chapters:
            messagebox.showwarning("警告", "没有章节可下载")
            return

        # 询问是下载所有章节还是选中章节
        selected_items = self.chapters_tree.selection()

        if selected_items:
            if messagebox.askyesno("确认", "是否只下载选中的章节？\n否 - 下载所有章节"):
                # 下载选中章节
                chapters_to_download = []
                for item in selected_items:
                    idx = self.chapters_tree.index(item)
                    if 0 <= idx < len(self.chapters):
                        chapters_to_download.append(self.chapters[idx])
            else:
                # 下载所有章节
                chapters_to_download = self.chapters
        else:
            # 下载所有章节
            chapters_to_download = self.chapters

        # 创建下载进度对话框
        progress_dialog = DownloadProgressDialog(self, len(chapters_to_download))

        # 在后台线程执行下载
        def download_task():
            try:
                # 下载章节内容
                updated_chapters = self.crawler.download_chapters_content(
                    chapters_to_download,
                    callback=lambda msg: self.after(
                        0, lambda: progress_dialog.add_message(msg)
                    ),
                    max_workers=5,
                )

                # 更新章节数据
                if updated_chapters:
                    # 更新字数信息
                    for updated in updated_chapters:
                        # 查找原章节并更新
                        for chapter in self.chapters:
                            if (
                                chapter["chapter_url"] == updated["chapter_url"]
                                and chapter["chapter_title"] == updated["chapter_title"]
                            ):
                                chapter["word_count"] = updated["word_count"]
                                chapter["content"] = updated["content"]
                                break

                    # 通知主线程更新UI
                    self.after(0, self.update_chapters_tree)
                    self.after(
                        0,
                        lambda: self.log(
                            f"已更新 {len(updated_chapters)} 个章节的内容信息"
                        ),
                    )

                    # 自动保存到数据库
                    self.after(100, self.save_chapters)

                # 设置为完成状态
                self.after(0, progress_dialog.set_finished)

            except Exception as e:
                self.after(0, lambda: self.log(f"下载内容出错: {str(e)}"))
                self.after(0, progress_dialog.set_finished)

        # 设置取消回调
        progress_dialog.on_close = lambda: (
            self.log("下载已取消")
            if self.download_task and self.download_task.is_alive()
            else None
        )

        # 启动下载线程
        self.download_task = threading.Thread(target=download_task)
        self.download_task.daemon = True
        self.download_task.start()

    def analyze_chapters_dialogue(self):
        """分析章节对话，支持多API密钥并行处理"""
        if not self.chapters:
            messagebox.showwarning("警告", "没有章节可分析")
            return

        # 加载API密钥
        self.dialogue_analyzer.load_api_keys_from_db()

        if not self.dialogue_analyzer.has_valid_api_keys():
            messagebox.showwarning("警告", "未找到有效的API密钥，请先配置")
            self.configure_api()
            return

        # 询问是分析所有章节还是选中章节
        selected_items = self.chapters_tree.selection()
        print(self.current_novel.name)
        if selected_items:
            if messagebox.askyesno("确认", "是否只分析选中的章节？"):
                # 分析选中章节
                chapters_to_analyze = []
                for item in selected_items:
                    idx = self.chapters_tree.index(item)
                    if 0 <= idx < len(self.chapters):
                        chapters_to_analyze.append(self.chapters[idx])
            else:
                if messagebox.askyesno("确认", "是否分析所有章节？"):
                    # 分析所有章节
                    chapters_to_analyze = self.chapters
                else:
                    # 关闭对话框什么也不做
                    return
        else:
            # 分析所有章节
            chapters_to_analyze = self.chapters

        # 过滤掉没有内容的章节
        chapters_to_analyze = [
            ch
            for ch in chapters_to_analyze
            if ch.get("content") and len(ch.get("content")) > 0
        ]

        if not chapters_to_analyze:
            messagebox.showwarning("警告", "选中的章节没有内容，请先获取章节内容")
            return

        # 创建进度对话框
        progress_dialog = DownloadProgressDialog(
            self, len(chapters_to_analyze), "分析对话进度"
        )

        # 在后台线程执行分析
        def analyze_task():
            try:
                # 分析章节对话
                results = self.dialogue_analyzer.batch_analyze_chapters(
                    chapters_to_analyze,
                    callback=lambda msg: self.after(
                        0, lambda: progress_dialog.add_message(msg)
                    ),
                    max_workers=3,
                )
                self.after(0, lambda: self.log(f"对话分析完成，获取到 {len(results) if results else 0} 个结果"))

                # 更新到数据库
                if results and messagebox.askyesno("确认", "是否保存分析结果？"):
                    try:
                        # 将分析结果映射到数据库章节ID
                        chapter_dialogue_map = {}

                        # 获取所有需要分析的章节URL
                        chapter_urls = {
                            chapter["chapter_url"] for chapter in chapters_to_analyze
                        }

                        # 一次性查询所有章节信息
                        if self.db_manager.is_connected() and self.current_novel_id:
                            db_chapters = list(
                                self.db_manager.db.chapters.find(
                                    {
                                        "novel_id": self.current_novel_id,
                                        "url": {"$in": list(chapter_urls)},
                                    }
                                )
                            )

                            # 创建URL到ID的映射
                            url_to_id = {
                                ch["url"]: ch["_id"]
                                for ch in db_chapters
                                if "url" in ch
                            }

                            # 根据映射创建要保存的数据
                            for chapter_url, dialogue_result in results.items():
                                if chapter_url in url_to_id:
                                    chapter_dialogue_map[url_to_id[chapter_url]] = (
                                        dialogue_result
                                    )

                        # 批量保存到数据库
                        if chapter_dialogue_map:
                            success, message = self.db_manager.save_batch_dialogues(
                                chapter_dialogue_map
                            )
                            self.after(0, lambda: self.log(message))

                    except Exception as e:
                        self.after(0, lambda: self.log(f"保存分析结果失败: {str(e)}"))

                # 处理完成后更新进度对话框
                self.after(0, lambda: progress_dialog.set_finished())
                self.after(
                    0, lambda: self.log(f"对话分析完成，成功分析 {len(results)} 个章节")
                )

                # 刷新章节列表，显示对话分析状态
                self.after(0, self.update_chapters_tree)

            except Exception as e:
                self.after(0, lambda: self.log(f"对话分析出错: {str(e)}"))
                self.after(0, progress_dialog.set_finished)

        # 设置取消回调
        progress_dialog.on_close = lambda: self.log("分析已取消")

        # 启动分析线程
        self.analyze_task = threading.Thread(target=analyze_task)
        self.analyze_task.daemon = True
        self.analyze_task.start()

    def view_chapter_dialogue(self):
        """查看章节对话分析结果"""
        if not self.db_manager.is_connected():
            messagebox.showwarning("警告", "未连接到数据库")
            return

        selected = self.chapters_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要查看的章节")
            return

        item = selected[0]
        idx = self.chapters_tree.index(item)

        if 0 <= idx < len(self.chapters):
            chapter = self.chapters[idx]
            chapter_url = chapter.get("chapter_url", "")
            chapter_title = chapter.get("chapter_title", "")

            # 查询数据库获取对话分析结果
            try:
                chapter_doc = self.db_manager.db.chapters.find_one(
                    {"novel_id": self.current_novel_id, "url": chapter_url}
                )

                if not chapter_doc or not chapter_doc.get("dialogues"):
                    messagebox.showinfo("提示", "该章节没有对话分析结果")
                    return

                # 显示对话分析结果
                dialogues = chapter_doc.get("dialogues", [])
                dialog = DialogueViewDialog(self, chapter_title, dialogues)

            except Exception as e:
                self.log(f"获取对话分析结果失败: {str(e)}")
                messagebox.showerror("错误", f"获取对话分析结果失败: {str(e)}")

    def save_options(self):
        """保存选项到数据库"""
        if not self.db_manager.is_connected():
            messagebox.showwarning("警告", "未连接到数据库")
            return

        if not self.current_novel:
            messagebox.showwarning("警告", "请先选择或创建小说")
            return

        if not self.options:
            messagebox.showinfo("提示", "没有选项可保存")
            return

        # 更新小说中的选项
        self.current_novel.volumes = self.options

        # 保存到数据库
        try:
            success, novel_id, message = self.db_manager.save_novel(
                self.current_novel.to_dict()
            )

            if success:
                self.current_novel_id = novel_id
                self.log(message)
                messagebox.showinfo("成功", f"已保存 {len(self.options)} 个选项")

                # 刷新小说列表
                self.load_novel_list()
            else:
                self.log(f"保存选项失败: {message}")
                messagebox.showerror("错误", message)

        except Exception as e:
            self.log(f"保存选项出错: {str(e)}")
            messagebox.showerror("错误", f"保存选项时出错: {str(e)}")

    def save_chapters(self):
        """保存章节到数据库"""
        if not self.db_manager.is_connected():
            messagebox.showwarning("警告", "未连接到数据库")
            return

        if not self.current_novel_id:
            # 如果小说未保存，先保存小说
            if not self.current_novel:
                messagebox.showwarning("警告", "请先选择或创建小说")
                return

            try:
                success, novel_id, message = self.db_manager.save_novel(
                    self.current_novel.to_dict()
                )

                if success:
                    self.current_novel_id = novel_id
                    self.log(message)
                else:
                    self.log(f"保存小说失败: {message}")
                    messagebox.showerror("错误", message)
                    return

            except Exception as e:
                self.log(f"保存小说出错: {str(e)}")
                messagebox.showerror("错误", f"保存小说时出错: {str(e)}")
                return

        if not self.chapters:
            messagebox.showinfo("提示", "没有章节可保存")
            return

        # 保存章节到数据库
        try:
            success, message = self.db_manager.save_chapters(
                self.current_novel_id, self.chapters
            )

            if success:
                self.log(message)
                messagebox.showinfo("成功", message)
            else:
                self.log(f"保存章节失败: {message}")
                messagebox.showerror("错误", message)

        except Exception as e:
            self.log(f"保存章节出错: {str(e)}")
            messagebox.showerror("错误", f"保存章节时出错: {str(e)}")

    def export_book_to_json(self):
        """导出小说章节到JSON文件"""
        if not self.db_manager.is_connected():
            messagebox.showwarning("警告", "未连接到数据库")
            return

        if not self.current_novel_id:
            messagebox.showwarning("警告", "请先选择小说")
            return

        # 获取小说信息
        novel = self.db_manager.get_novel(self.current_novel_id)
        if not novel:
            messagebox.showerror("错误", "获取小说信息失败")
            return

        # 获取所有章节
        chapters = self.db_manager.get_chapters(self.current_novel_id)
        if not chapters:
            messagebox.showinfo("提示", "该小说没有章节")
            return

        # 选择导出目录
        export_dir = filedialog.askdirectory(title="选择导出目录")
        if not export_dir:
            return

        # 使用工具函数导出
        success, message = utils.export_book_to_json(
            str(novel["_id"]), novel, chapters, export_dir
        )

        if success:
            self.log(message)
            messagebox.showinfo("导出成功", message)
        else:
            self.log(message)
            messagebox.showerror("导出失败", message)

    def configure_api(self):
        """配置 GeminiAI API"""
        if not self.db_manager.is_connected():
            if messagebox.askyesno(
                "数据库未连接", "API密钥需要保存到数据库中，是否先连接数据库？"
            ):
                self.configure_database()
            else:
                return

            if not self.db_manager.is_connected():
                return

        dialog = APIKeyConfigDialog(self, self.db_manager)
        self.wait_window(dialog)

        if dialog.result:
            self.log(f"API 配置已更新，使用模型: {dialog.result['model']}")

            # 重新加载对话分析器的API密钥
            self.dialogue_analyzer.load_api_keys_from_db()

    def manage_api_keys(self):
        """管理多个API密钥"""
        if not self.db_manager.is_connected():
            if messagebox.askyesno(
                "数据库未连接", "API密钥需要保存到数据库中，是否先连接数据库？"
            ):
                self.configure_database()
            else:
                return

            if not self.db_manager.is_connected():
                return

        dialog = MultiAPIKeysDialog(self, self.db_manager)
        self.wait_window(dialog)

        if dialog.result:
            self.log(f"API密钥已更新，共 {len(dialog.result)} 个")

            # 重新加载对话分析器的API密钥
            self.dialogue_analyzer.load_api_keys_from_db()


def main():
    # 确保必要的库已安装
    try:
        import pymongo
    except ImportError:
        print("请先安装pymongo：pip install pymongo")
        return

    try:
        import tqdm
    except ImportError:
        print("请先安装tqdm：pip install tqdm")
        return

    try:
        import openai
    except ImportError:
        print("请先安装openai：pip install openai")
        return

    try:
        import dotenv
    except ImportError:
        print("请先安装python-dotenv：pip install python-dotenv")
        return

    app = NovelCrawlerGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
