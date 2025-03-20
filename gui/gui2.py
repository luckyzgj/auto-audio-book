import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, simpledialog
import requests
import json
import threading
import datetime
import os
import time
import configparser
import pyperclip
import re
import sys


class XimalayaManager:
    def __init__(self, root):
        self.root = root
        self.root.title("喜马拉雅作品管理工具")
        self.root.geometry("1800x1000")

        self.tracks = []  # 存储所有获取到的作品信息

        # 配置文件
        self.config_file = "config.ini"
        self.config = configparser.ConfigParser()
        self.album_id = "123456"  # 默认专辑ID
        self.cookie_file = "cookie.txt"  # 保存cookie的文件

        self.load_config()
        self.setup_ui()
        self.load_cookie()

    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                self.config.read(self.config_file, encoding="utf-8")
                if "Settings" in self.config:
                    if "album_id" in self.config["Settings"]:
                        self.album_id = self.config["Settings"]["album_id"]
                    if "cookie_file" in self.config["Settings"]:
                        self.cookie_file = self.config["Settings"]["cookie_file"]
        except Exception as e:
            print(f"加载配置文件失败: {str(e)}")

    def save_config(self):
        """保存配置文件"""
        try:
            if "Settings" not in self.config:
                self.config["Settings"] = {}

            self.config["Settings"]["album_id"] = self.album_id
            self.config["Settings"]["cookie_file"] = self.cookie_file

            with open(self.config_file, "w", encoding="utf-8") as f:
                self.config.write(f)
        except Exception as e:
            print(f"保存配置文件失败: {str(e)}")

    def setup_ui(self):
        """设置用户界面"""
        # 设置样式
        style = ttk.Style()
        style.configure("TButton", padding=5)
        style.configure("TLabel", padding=2)

        # 创建菜单
        menu_bar = tk.Menu(self.root)

        # 文件菜单
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="保存Cookie", command=self.save_cookie)
        file_menu.add_command(label="加载Cookie", command=self.load_cookie)
        file_menu.add_separator()
        file_menu.add_command(label="导出作品列表", command=self.export_track_list)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        menu_bar.add_cascade(label="文件", menu=file_menu)

        # 操作菜单
        action_menu = tk.Menu(menu_bar, tearoff=0)
        action_menu.add_command(label="获取作品列表", command=self.get_tracks)
        action_menu.add_command(
            label="批量删除作品", command=lambda: self.show_delete_dialog()
        )
        menu_bar.add_cascade(label="操作", menu=action_menu)

        # 设置菜单
        settings_menu = tk.Menu(menu_bar, tearoff=0)
        settings_menu.add_command(label="设置专辑ID", command=self.set_album_id)
        menu_bar.add_cascade(label="设置", menu=settings_menu)

        # 帮助菜单
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)
        menu_bar.add_cascade(label="帮助", menu=help_menu)

        self.root.config(menu=menu_bar)

        # 创建主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 创建顶部工具栏
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.pack(fill="x", pady=(0, 10))

        # 专辑ID显示和设置
        ttk.Label(toolbar_frame, text="专辑ID:").pack(side="left", padx=(0, 5))
        self.album_id_label = ttk.Label(toolbar_frame, text=self.album_id)
        self.album_id_label.pack(side="left", padx=(0, 10))

        set_album_btn = ttk.Button(
            toolbar_frame, text="设置专辑ID", command=self.set_album_id
        )
        set_album_btn.pack(side="left", padx=5)

        get_tracks_btn = ttk.Button(
            toolbar_frame, text="获取作品列表", command=self.get_tracks
        )
        get_tracks_btn.pack(side="left", padx=5)

        # 右侧统计信息
        self.stats_label = ttk.Label(toolbar_frame, text="总作品数: 0")
        self.stats_label.pack(side="right", padx=5)

        # 创建标签框架
        cookie_frame = ttk.LabelFrame(main_frame, text="Cookie设置")
        cookie_frame.pack(fill="x", pady=(0, 10))

        # Cookie输入框
        self.cookie_entry = scrolledtext.ScrolledText(cookie_frame, height=3, width=80)
        self.cookie_entry.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        # Cookie操作按钮
        cookie_btn_frame = ttk.Frame(cookie_frame)
        cookie_btn_frame.pack(side="right", fill="y", padx=5, pady=5)

        save_cookie_btn = ttk.Button(
            cookie_btn_frame, text="保存Cookie", command=self.save_cookie
        )
        save_cookie_btn.pack(pady=2)

        load_cookie_btn = ttk.Button(
            cookie_btn_frame, text="加载Cookie", command=self.load_cookie
        )
        load_cookie_btn.pack(pady=2)

        # 创建作品列表与删除操作的PanedWindow
        paned = ttk.PanedWindow(main_frame, orient="vertical")
        paned.pack(fill="both", expand=True, pady=(0, 10))

        # 作品列表框架
        list_frame = ttk.LabelFrame(paned, text="作品列表")

        # 作品列表上方的搜索框
        search_frame = ttk.Frame(list_frame)
        search_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(search_frame, text="搜索:").pack(side="left", padx=(0, 5))
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.pack(side="left", padx=(0, 5))
        self.search_entry.bind("<KeyRelease>", self.search_tracks)

        # 清除搜索
        clear_search_btn = ttk.Button(
            search_frame, text="清除", command=self.clear_search
        )
        clear_search_btn.pack(side="left", padx=5)

        # 作品列表
        columns = ("序号", "作品ID", "标题", "创建时间", "时长(秒)", "播放次数")
        self.track_tree = ttk.Treeview(list_frame, columns=columns, show="headings")

        # 定义每列的标题和宽度
        self.track_tree.heading(
            "序号", text="序号", command=lambda: self.sort_treeview("序号", False)
        )
        self.track_tree.column("序号", width=50)

        self.track_tree.heading(
            "作品ID", text="作品ID", command=lambda: self.sort_treeview("作品ID", False)
        )
        self.track_tree.column("作品ID", width=80)

        self.track_tree.heading(
            "标题", text="标题", command=lambda: self.sort_treeview("标题", False)
        )
        self.track_tree.column("标题", width=300)

        self.track_tree.heading(
            "创建时间",
            text="创建时间",
            command=lambda: self.sort_treeview("创建时间", False),
        )
        self.track_tree.column("创建时间", width=150)

        self.track_tree.heading(
            "时长(秒)",
            text="时长(秒)",
            command=lambda: self.sort_treeview("时长(秒)", False),
        )
        self.track_tree.column("时长(秒)", width=80)

        self.track_tree.heading(
            "播放次数",
            text="播放次数",
            command=lambda: self.sort_treeview("播放次数", False),
        )
        self.track_tree.column("播放次数", width=80)

        # 右键菜单
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="复制作品ID", command=self.copy_track_id)
        self.context_menu.add_command(label="复制标题", command=self.copy_title)
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="删除选中作品", command=self.delete_selected_track
        )

        self.track_tree.bind("<Button-3>", self.show_context_menu)

        # 添加水平和垂直滚动条
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.track_tree.pack(side="left", fill="both", expand=True)

        v_scrollbar = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.track_tree.yview
        )
        v_scrollbar.pack(side="right", fill="y")
        self.track_tree.configure(yscrollcommand=v_scrollbar.set)

        self.track_tree.pack(in_=tree_frame, side="top", fill="both", expand=True)

        h_scrollbar = ttk.Scrollbar(
            tree_frame, orient="horizontal", command=self.track_tree.xview
        )
        h_scrollbar.pack(side="bottom", fill="x")
        self.track_tree.configure(xscrollcommand=h_scrollbar.set)

        # 添加到PanedWindow
        paned.add(list_frame, weight=3)

        # 删除操作框架
        delete_frame = ttk.LabelFrame(paned, text="批量删除操作")

        # 删除操作的选项卡
        delete_notebook = ttk.Notebook(delete_frame)
        delete_notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # 按序号删除选项卡
        seq_tab = ttk.Frame(delete_notebook)
        delete_notebook.add(seq_tab, text="按序号删除")

        ttk.Label(seq_tab, text="删除序号范围 (例如: 1-5):").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        self.seq_range_entry = ttk.Entry(seq_tab, width=30)
        self.seq_range_entry.grid(row=0, column=1, padx=5, pady=5)

        delete_by_seq_btn = ttk.Button(
            seq_tab, text="执行删除", command=lambda: self.delete_tracks("seq")
        )
        delete_by_seq_btn.grid(row=0, column=2, padx=5, pady=5)

        # 按名称删除选项卡
        name_tab = ttk.Frame(delete_notebook)
        delete_notebook.add(name_tab, text="按名称删除")

        ttk.Label(name_tab, text="开始名称:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        self.start_name_entry = ttk.Entry(name_tab, width=30)
        self.start_name_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(name_tab, text="结束名称:").grid(
            row=1, column=0, padx=5, pady=5, sticky="w"
        )
        self.end_name_entry = ttk.Entry(name_tab, width=30)
        self.end_name_entry.grid(row=1, column=1, padx=5, pady=5)

        delete_by_name_btn = ttk.Button(
            name_tab, text="执行删除", command=lambda: self.delete_tracks("name")
        )
        delete_by_name_btn.grid(row=0, column=2, rowspan=2, padx=5, pady=5, sticky="ns")

        # 添加到PanedWindow
        paned.add(delete_frame, weight=1)

        # 状态框
        status_frame = ttk.LabelFrame(main_frame, text="操作日志")
        status_frame.pack(fill="x", pady=(0, 5))

        # 添加日志和清除按钮
        log_frame = ttk.Frame(status_frame)
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.status_text = scrolledtext.ScrolledText(log_frame, height=8)
        self.status_text.pack(side="left", fill="both", expand=True)

        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.pack(side="right", fill="y")

        clear_log_btn = ttk.Button(
            log_btn_frame, text="清除日志", command=self.clear_log
        )
        clear_log_btn.pack(pady=2)

        export_log_btn = ttk.Button(
            log_btn_frame, text="导出日志", command=self.export_log
        )
        export_log_btn.pack(pady=2)

        # 状态栏
        self.status_bar = ttk.Label(self.root, text="就绪", relief="sunken", anchor="w")
        self.status_bar.pack(side="bottom", fill="x")

        # 初始状态日志
        self.log("程序已启动")
        self.log(f"当前专辑ID: {self.album_id}")

    def log(self, message):
        """添加日志信息到状态文本框"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.status_text.insert(tk.END, log_message)
        self.status_text.see(tk.END)

        # 更新状态栏
        self.status_bar.config(text=message)

    def clear_log(self):
        """清除日志"""
        self.status_text.delete(1.0, tk.END)
        self.log("日志已清除")

    def export_log(self):
        """导出日志到文件"""
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
                title="导出日志",
            )
            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.status_text.get(1.0, tk.END))
                self.log(f"日志已导出到: {file_path}")
        except Exception as e:
            self.log(f"导出日志失败: {str(e)}")
            messagebox.showerror("错误", f"导出日志失败: {str(e)}")

    def save_cookie(self):
        """保存Cookie到文件"""
        try:
            cookie = self.cookie_entry.get(1.0, tk.END).strip()
            if not cookie:
                messagebox.showwarning("警告", "Cookie内容为空!")
                return

            with open(self.cookie_file, "w", encoding="utf-8") as f:
                f.write(cookie)

            self.log(f"Cookie已保存到文件: {self.cookie_file}")
        except Exception as e:
            self.log(f"保存Cookie失败: {str(e)}")
            messagebox.showerror("错误", f"保存Cookie失败: {str(e)}")

    def load_cookie(self):
        """从文件加载Cookie"""
        try:
            if os.path.exists(self.cookie_file):
                with open(self.cookie_file, "r", encoding="utf-8") as f:
                    cookie = f.read()

                self.cookie_entry.delete(1.0, tk.END)
                self.cookie_entry.insert(tk.END, cookie)

                self.log(f"已从文件加载Cookie: {self.cookie_file}")
            else:
                self.log(f"Cookie文件不存在: {self.cookie_file}")
        except Exception as e:
            self.log(f"加载Cookie失败: {str(e)}")
            messagebox.showerror("错误", f"加载Cookie失败: {str(e)}")

    def set_album_id(self):
        """设置专辑ID"""
        try:
            new_album_id = simpledialog.askstring(
                "设置专辑ID", "请输入专辑ID:", initialvalue=self.album_id
            )
            if new_album_id and new_album_id.strip():
                self.album_id = new_album_id.strip()
                self.album_id_label.config(text=self.album_id)

                # 更新配置
                self.save_config()

                self.log(f"专辑ID已更新为: {self.album_id}")
        except Exception as e:
            self.log(f"设置专辑ID失败: {str(e)}")

    def get_tracks(self):
        """获取作品列表"""
        try:
            # 清空现有列表
            for item in self.track_tree.get_children():
                self.track_tree.delete(item)

            # 清空缓存的作品列表
            self.tracks = []

            # 获取Cookie
            cookie = self.cookie_entry.get(1.0, tk.END).strip()
            if not cookie:
                messagebox.showwarning("警告", "请先填入Cookie!")
                self.log("获取作品列表失败: Cookie为空")
                return

            # 启动线程获取作品列表
            self.log(f"开始获取专辑 {self.album_id} 的作品列表...")

            # 禁用获取按钮，避免重复点击
            self.root.config(cursor="wait")
            self.status_bar.config(text="正在获取作品列表...")

            thread = threading.Thread(target=self._get_tracks_thread, args=(cookie,))
            thread.daemon = True
            thread.start()
        except Exception as e:
            self.log(f"获取作品列表失败: {str(e)}")
            messagebox.showerror("错误", f"获取作品列表失败: {str(e)}")
            self.root.config(cursor="")

    def _get_tracks_thread(self, cookie):
        """在线程中获取作品列表"""
        try:
            total_pages = 1
            current_page = 1
            all_tracks = []

            while current_page <= total_pages:
                url = f"https://www.ximalaya.com/reform-upload/manage/album/tracks?albumId={self.album_id}&page={current_page}&pageSize=40&order=ASC&state=1"

                headers = {
                    "Cookie": cookie,
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                }

                response = requests.get(url, headers=headers)
                data = response.json()
                if data.get("ret") == 0 and data.get("msg") == "成功":
                    # 获取作品列表成功
                    page_data = data.get("data", {})
                    tracks = page_data.get("infos", [])

                    # 更新总页数
                    if current_page == 1:
                        total_size = page_data.get("totalSize", 0)
                        page_size = page_data.get("pageSize", 40)
                        total_pages = (total_size + page_size - 1) // page_size

                        self.log(f"共找到 {total_size} 个作品，共 {total_pages} 页")

                    all_tracks.extend(tracks)

                    self.log(
                        f"已获取第 {current_page}/{total_pages} 页作品，{len(tracks)} 个"
                    )

                    current_page += 1

                    # 防止请求过快
                    time.sleep(0.5)
                else:
                    error_msg = data.get("msg", "未知错误")
                    self.log(f"获取作品列表失败: {error_msg}")
                    self.log(f"获取作品列表失败: {response.text}")
                    messagebox.showerror("错误", f"获取作品列表失败: {error_msg}")
                    break

            # 在主线程中更新UI
            self.root.after(0, lambda: self._update_track_list(all_tracks))
        except Exception as e:
            self.log(f"获取作品列表失败: {str(e)}")
            messagebox.showerror("错误", f"获取作品列表失败: {str(e)}")
            self.root.config(cursor="")

    def _update_track_list(self, tracks):
        """更新作品列表UI"""
        try:
            # 保存作品列表
            self.tracks = tracks

            # 更新TreeView
            for i, track in enumerate(tracks, 1):
                track_id = track.get("trackId", "")
                title = track.get("title", "")

                # 转换时间戳
                create_time_ms = track.get("createAt", 0)
                if create_time_ms:
                    create_time = datetime.datetime.fromtimestamp(create_time_ms / 1000)
                    create_time_str = create_time.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    create_time_str = ""

                duration = track.get("duration", 0)
                play_count = track.get("trackStatInfo", {}).get("playCount", 0)

                # 添加到TreeView
                self.track_tree.insert(
                    "",
                    "end",
                    values=(i, track_id, title, create_time_str, duration, play_count),
                )

            # 更新统计信息
            self.stats_label.config(text=f"总作品数: {len(tracks)}")

            self.log(f"成功获取 {len(tracks)} 个作品的详细信息")
            self.status_bar.config(text="作品列表获取完成")
        except Exception as e:
            self.log(f"更新作品列表失败: {str(e)}")
        finally:
            self.root.config(cursor="")

    def search_tracks(self, event=None):
        """搜索作品"""
        try:
            search_text = self.search_entry.get().strip().lower()

            # 清空当前列表
            for item in self.track_tree.get_children():
                self.track_tree.delete(item)

            if not search_text:
                # 如果搜索内容为空，显示所有作品
                self._update_track_list(self.tracks)
                return

            # 搜索匹配的作品
            filtered_tracks = []
            for track in self.tracks:
                track_id = str(track.get("trackId", ""))
                title = track.get("title", "").lower()

                if search_text in track_id or search_text in title:
                    filtered_tracks.append(track)

            # 更新列表
            for i, track in enumerate(filtered_tracks, 1):
                track_id = track.get("trackId", "")
                title = track.get("title", "")

                # 转换时间戳
                create_time_ms = track.get("createAt", 0)
                if create_time_ms:
                    create_time = datetime.datetime.fromtimestamp(create_time_ms / 1000)
                    create_time_str = create_time.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    create_time_str = ""

                duration = track.get("duration", 0)
                play_count = track.get("trackStatInfo", {}).get("playCount", 0)

                # 添加到TreeView
                self.track_tree.insert(
                    "",
                    "end",
                    values=(i, track_id, title, create_time_str, duration, play_count),
                )

            self.log(f"搜索结果: 找到 {len(filtered_tracks)} 个匹配作品")
        except Exception as e:
            self.log(f"搜索失败: {str(e)}")

    def clear_search(self):
        """清除搜索内容并显示所有作品"""
        self.search_entry.delete(0, tk.END)

        # 清空当前列表
        for item in self.track_tree.get_children():
            self.track_tree.delete(item)

        # 重新显示所有作品
        self._update_track_list(self.tracks)

        self.log("已清除搜索，显示所有作品")

    def sort_treeview(self, column, reverse):
        """按列排序TreeView"""
        try:
            # 获取所有行的数据
            items = [
                (self.track_tree.set(k, column), k)
                for k in self.track_tree.get_children("")
            ]

            # 根据列类型排序
            if column in ["序号", "作品ID", "时长(秒)", "播放次数"]:
                # 数字排序
                items.sort(
                    key=lambda x: int(x[0]) if x[0].isdigit() else 0, reverse=reverse
                )
            else:
                # 字符串排序
                items.sort(reverse=reverse)

            # 重新排列行
            for index, (val, k) in enumerate(items):
                self.track_tree.move(k, "", index)

            # 切换排序方向
            self.track_tree.heading(
                column, command=lambda: self.sort_treeview(column, not reverse)
            )

            self.log(f"已按列 '{column}' {'降序' if reverse else '升序'} 排序")
        except Exception as e:
            self.log(f"排序失败: {str(e)}")

    def show_context_menu(self, event):
        """显示右键菜单"""
        try:
            # 选择鼠标所在行
            item = self.track_tree.identify_row(event.y)
            if item:
                self.track_tree.selection_set(item)
                self.context_menu.post(event.x_root, event.y_root)
        except Exception as e:
            self.log(f"显示右键菜单失败: {str(e)}")

    def copy_track_id(self):
        """复制选中作品的ID"""
        try:
            selected_items = self.track_tree.selection()
            if not selected_items:
                messagebox.showinfo("提示", "请先选择一个作品")
                return

            # 获取选中行的第二列（作品ID）
            track_id = self.track_tree.item(selected_items[0], "values")[1]

            # 复制到剪贴板
            pyperclip.copy(str(track_id))

            self.log(f"已复制作品ID: {track_id}")
        except Exception as e:
            self.log(f"复制作品ID失败: {str(e)}")

    def copy_title(self):
        """复制选中作品的标题"""
        try:
            selected_items = self.track_tree.selection()
            if not selected_items:
                messagebox.showinfo("提示", "请先选择一个作品")
                return

            # 获取选中行的第三列（标题）
            title = self.track_tree.item(selected_items[0], "values")[2]

            # 复制到剪贴板
            pyperclip.copy(title)

            self.log(f"已复制作品标题: {title}")
        except Exception as e:
            self.log(f"复制作品标题失败: {str(e)}")

    def delete_selected_track(self):
        """删除选中的作品"""
        try:
            selected_items = self.track_tree.selection()
            if not selected_items:
                messagebox.showinfo("提示", "请先选择一个作品")
                return

            # 获取选中行的第二列（作品ID）
            track_id = self.track_tree.item(selected_items[0], "values")[1]
            title = self.track_tree.item(selected_items[0], "values")[2]

            # 确认删除
            if not messagebox.askyesno(
                "确认删除", f"确定要删除作品《{title}》(ID: {track_id})吗？"
            ):
                return

            # 获取Cookie
            cookie = self.cookie_entry.get(1.0, tk.END).strip()
            if not cookie:
                messagebox.showwarning("警告", "请先填入Cookie!")
                return

            # 启动线程删除作品
            self.log(f"开始删除作品《{title}》(ID: {track_id})...")

            thread = threading.Thread(
                target=self._delete_track_thread, args=(cookie, track_id, title)
            )
            thread.daemon = True
            thread.start()
        except Exception as e:
            self.log(f"删除作品失败: {str(e)}")

    def show_delete_dialog(self):
        """显示批量删除对话框"""
        # 该功能已通过UI实现，无需额外操作
        pass

    def delete_tracks(self, delete_type):
        """批量删除作品"""
        try:
            # 获取Cookie
            cookie = self.cookie_entry.get(1.0, tk.END).strip()
            if not cookie:
                messagebox.showwarning("警告", "请先填入Cookie!")
                return

            tracks_to_delete = []

            if delete_type == "seq":
                # 按序号删除
                seq_range = self.seq_range_entry.get().strip()
                if not seq_range:
                    messagebox.showwarning("警告", "请输入序号范围！")
                    return

                # 解析序号范围
                try:
                    if "-" in seq_range:
                        start, end = seq_range.split("-")
                        start = int(start.strip())
                        end = int(end.strip())

                        if start < 1 or end > len(self.tracks) or start > end:
                            messagebox.showwarning(
                                "警告", f"序号范围无效！有效范围为1-{len(self.tracks)}"
                            )
                            return

                        # 获取对应序号的作品
                        for i in range(start - 1, end):
                            if i < len(self.tracks):
                                tracks_to_delete.append(self.tracks[i])
                    else:
                        # 单个序号
                        seq = int(seq_range)
                        if seq < 1 or seq > len(self.tracks):
                            messagebox.showwarning(
                                "警告", f"序号无效！有效范围为1-{len(self.tracks)}"
                            )
                            return

                        tracks_to_delete.append(self.tracks[seq - 1])
                except ValueError:
                    messagebox.showwarning(
                        "警告", "序号格式无效！请使用数字或数字范围（如1-5）"
                    )
                    return

            elif delete_type == "name":
                # 按名称删除
                start_name = self.start_name_entry.get().strip()
                end_name = self.end_name_entry.get().strip()

                if not start_name or not end_name:
                    messagebox.showwarning("警告", "请输入开始和结束名称！")
                    return

                # 查找名称对应的索引
                start_index = -1
                end_index = -1

                for i, track in enumerate(self.tracks):
                    title = track.get("title", "")

                    if start_name in title and start_index == -1:
                        start_index = i

                    if end_name in title:
                        end_index = i

                if start_index == -1 or end_index == -1:
                    messagebox.showwarning("警告", "未找到指定的开始或结束名称！")
                    return

                if start_index > end_index:
                    # 交换位置，确保起始小于结束
                    start_index, end_index = end_index, start_index

                # 获取对应名称范围的作品
                for i in range(start_index, end_index + 1):
                    tracks_to_delete.append(self.tracks[i])

            # 确认删除
            if not tracks_to_delete:
                messagebox.showinfo("提示", "没有找到符合条件的作品！")
                return

            confirm = messagebox.askyesno(
                "确认删除", f"即将删除 {len(tracks_to_delete)} 个作品，是否继续？"
            )
            if not confirm:
                return

            # 启动线程批量删除
            thread = threading.Thread(
                target=self._batch_delete_thread, args=(cookie, tracks_to_delete)
            )
            thread.daemon = True
            thread.start()

        except Exception as e:
            self.log(f"批量删除失败: {str(e)}")
            messagebox.showerror("错误", f"批量删除失败: {str(e)}")

    def _delete_track_thread(self, cookie, track_id, title):
        """在线程中删除作品"""
        try:
            print(f"请求之前{1}")
            url = "https://www.ximalaya.com/reform-upload/manage/album/track/delete"

            print(f"请求之前{2}")
            payload = json.dumps({"trackId": int(track_id)})
            print(f"请求之前{3}")
            headers = {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Host": "www.ximalaya.com",
                "Pragma": "no-cache",
                "Referer": "https://www.ximalaya.com/reform-upload/page/sound/manage/123456",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                "sec-ch-ua": ' "Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
                "sec-ch-ua-platform": "Windows",
                "Content-Type": "application/json",
                "Cookie": cookie,
            }

            self.log(f"请求之前{headers}")
            response = requests.post(url, headers=headers, data=payload)
            self.log(f"请求之后: {payload}")
            # 添加响应内容检查和调试信息
            if response.status_code != 200:
                self.log(f"HTTP错误: 状态码 {response.status_code}")
                self.log(f"响应内容: {response.text}")
                messagebox.showerror("错误", f"HTTP错误: 状态码 {response.status_code}")
                return

            # 尝试解析JSON前先检查响应内容
            response_text = response.text
            if not response_text.strip():
                self.log("错误: 服务器返回了空响应")
                messagebox.showerror("错误", "服务器返回了空响应")
                return

            # 打印原始响应以便调试
            self.log(f"原始响应: {response_text}")

            try:
                data = response.json()
            except json.JSONDecodeError as json_err:
                self.log(f"JSON解析错误: {str(json_err)}")
                self.log(f"响应内容: {response_text}")
                messagebox.showerror("错误", f"无法解析服务器响应: {str(json_err)}")
                return
            if (
                response.status_code == 200
                and data.get("ret") == 0
                and data.get("msg") == "成功"
            ):
                # 删除成功
                self.log(f"成功删除作品《{title}》(ID: {track_id})")

                # 从列表中移除
                self.root.after(0, lambda: self._remove_track_from_list(track_id))
            else:
                error_msg = data.get("msg", "未知错误")
                self.log(f"删除作品《{title}》(ID: {track_id})失败: {error_msg}")
                self.log(f"{response.text}")
                messagebox.showerror("错误", f"删除作品失败: {error_msg}")
        except Exception as e:
            self.log(f"删除作品《{title}》(ID: {track_id})失败: {str(e)}")
            messagebox.showerror("错误", f"删除作品失败: {str(e)}")

    def _batch_delete_thread(self, cookie, tracks):
        """在线程中批量删除作品"""
        try:
            self.log(f"开始批量删除 {len(tracks)} 个作品...")
            self.status_bar.config(text=f"正在批量删除作品...")

            # 禁用按钮
            self.root.config(cursor="wait")

            success_count = 0
            fail_count = 0

            url = "https://www.ximalaya.com/reform-upload/manage/album/track/delete"

            headers = {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Host": "www.ximalaya.com",
                "Pragma": "no-cache",
                "Referer": "https://www.ximalaya.com/reform-upload/page/sound/manage/123456",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
                "sec-ch-ua-platform": "Windows",
                "Content-Type": "application/json",
                "Cookie": cookie,
            }

            total = len(tracks)
            deleted_track_ids = []

            for i, track in enumerate(tracks, 1):
                track_id = track.get("trackId", "")
                title = track.get("title", "")

                if not track_id:
                    continue

                payload = json.dumps({"trackId": int(track_id)})

                # 更新状态栏
                self.root.after(
                    0,
                    lambda msg=f"正在删除 ({i}/{total}): {title}": self.status_bar.config(
                        text=msg
                    ),
                )

                try:
                    response = requests.post(url, headers=headers, data=payload)
                    data = response.json()

                    if data.get("ret") == 0 and data.get("msg") == "成功":
                        # 删除成功
                        success_count += 1
                        deleted_track_ids.append(track_id)
                        self.log(
                            f"[{i}/{total}] 成功删除作品《{title}》(ID: {track_id})"
                        )
                    else:
                        error_msg = data.get("msg", "未知错误")
                        fail_count += 1
                        self.log(
                            f"[{i}/{total}] 删除作品《{title}》(ID: {track_id})失败: {error_msg}"
                        )
                except Exception as e:
                    fail_count += 1
                    self.log(
                        f"[{i}/{total}] 删除作品《{title}》(ID: {track_id})失败: {str(e)}"
                    )

                # 删除间隔，避免请求过快
                time.sleep(0.5)

            # 批量删除完成后，更新列表
            self.root.after(
                0, lambda ids=deleted_track_ids: self._remove_tracks_from_list(ids)
            )

            self.log(f"批量删除完成: 成功 {success_count} 个，失败 {fail_count} 个")
            self.root.after(
                0,
                lambda: self.status_bar.config(
                    text=f"批量删除完成: 成功 {success_count} 个，失败 {fail_count} 个"
                ),
            )

            # 恢复光标
            self.root.after(0, lambda: self.root.config(cursor=""))

            # 显示结果
            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "批量删除结果",
                    f"批量删除完成: 成功 {success_count} 个，失败 {fail_count} 个",
                ),
            )
        except Exception as e:
            self.log(f"批量删除过程中发生错误: {str(e)}")
            messagebox.showerror("错误", f"批量删除过程中发生错误: {str(e)}")
            self.root.config(cursor="")

    def _remove_track_from_list(self, track_id):
        """从列表中移除已删除的作品"""
        try:
            # 从TreeView中移除
            for item in self.track_tree.get_children():
                if self.track_tree.item(item, "values")[1] == str(track_id):
                    self.track_tree.delete(item)
                    break

            # 从缓存中移除
            self.tracks = [
                track
                for track in self.tracks
                if str(track.get("trackId", "")) != str(track_id)
            ]

            # 更新统计信息
            self.stats_label.config(text=f"总作品数: {len(self.tracks)}")
        except Exception as e:
            self.log(f"从列表中移除作品失败: {str(e)}")

    def _remove_tracks_from_list(self, track_ids):
        """从列表中批量移除已删除的作品"""
        try:
            # 从TreeView中移除
            for item in self.track_tree.get_children():
                if self.track_tree.item(item, "values")[1] in map(str, track_ids):
                    self.track_tree.delete(item)

            # 从缓存中移除
            self.tracks = [
                track
                for track in self.tracks
                if str(track.get("trackId", "")) not in map(str, track_ids)
            ]

            # 更新统计信息
            self.stats_label.config(text=f"总作品数: {len(self.tracks)}")
        except Exception as e:
            self.log(f"从列表中批量移除作品失败: {str(e)}")

    def export_track_list(self):
        """导出作品列表到文件"""
        try:
            if not self.tracks:
                messagebox.showinfo("提示", "当前没有作品列表，请先获取作品列表！")
                return

            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")],
                title="导出作品列表",
            )

            if not file_path:
                return

            with open(file_path, "w", encoding="utf-8-sig") as f:
                # 写入表头
                f.write("序号,作品ID,标题,创建时间,时长(秒),播放次数\n")

                # 写入数据
                for i, track in enumerate(self.tracks, 1):
                    track_id = track.get("trackId", "")
                    title = track.get("title", "").replace(",", "，")  # 避免CSV格式问题

                    # 转换时间戳
                    create_time_ms = track.get("createAt", 0)
                    if create_time_ms:
                        create_time = datetime.datetime.fromtimestamp(
                            create_time_ms / 1000
                        )
                        create_time_str = create_time.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        create_time_str = ""

                    duration = track.get("duration", 0)
                    play_count = track.get("trackStatInfo", {}).get("playCount", 0)

                    f.write(
                        f"{i},{track_id},{title},{create_time_str},{duration},{play_count}\n"
                    )

            self.log(f"作品列表已导出到: {file_path}")
            messagebox.showinfo("导出成功", f"作品列表已导出到: {file_path}")
        except Exception as e:
            self.log(f"导出作品列表失败: {str(e)}")
            messagebox.showerror("错误", f"导出作品列表失败: {str(e)}")

    def show_help(self):
        """显示使用帮助"""
        help_text = """使用说明：

1. 设置专辑ID：
   - 点击主界面上的「设置专辑ID」按钮或使用菜单「设置」→「设置专辑ID」
   - 输入喜马拉雅专辑的ID（可从专辑URL中获取）

2. 设置Cookie：
   - 在Cookie输入框中粘贴从喜马拉雅网站获取的Cookie
   - 点击「保存Cookie」按钮保存到文件，方便下次使用

3. 获取作品列表：
   - 点击「获取作品列表」按钮
   - 软件会自动获取该专辑下的所有作品

4. 作品管理：
   - 可以按照各列进行排序
   - 可以搜索作品
   - 右键点击作品可复制ID或标题，或单独删除

5. 批量删除：
   - 按序号删除：输入序号范围（如1-5）
   - 按名称删除：输入开始名称和结束名称

6. 日志和导出：
   - 可导出操作日志
   - 可导出作品列表为CSV文件

注意事项：
1. 删除操作不可恢复，请谨慎操作！
2. Cookie的有效期可能有限，若操作失败请更新Cookie
3. 建议在操作前导出作品列表，以便备份
"""
        messagebox.showinfo("使用帮助", help_text)

    def show_about(self):
        """显示关于信息"""
        about_text = """喜马拉雅作品管理工具

版本：1.0.0
时间：2025年3月

功能：
- 获取专辑作品列表
- 支持批量删除作品
- 按序号或名称范围删除
- 导出作品列表和日志

本工具仅供学习和个人使用，请勿用于非法用途。
"""
        messagebox.showinfo("关于", about_text)


def resource_path(relative_path):
    """获取资源绝对路径"""
    try:
        # PyInstaller创建临时文件夹，将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def main():
    # 设置样式
    try:
        root = tk.Tk()
        root.title("喜马拉雅作品管理工具")

        # 设置图标
        try:
            icon_path = resource_path("icon.ico")
            if os.path.exists(icon_path):
                root.iconbitmap(icon_path)
        except:
            pass

        # 设置DPI感知
        try:
            from ctypes import windll

            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass

        # 创建应用程序
        app = XimalayaManager(root)

        # 运行主循环
        root.mainloop()
    except Exception as e:
        print(f"程序启动失败: {str(e)}")
        messagebox.showerror("错误", f"程序启动失败: {str(e)}")


if __name__ == "__main__":
    main()
