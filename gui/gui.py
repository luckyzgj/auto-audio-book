import os
import re
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import time


class AudioFileSorter:
    def __init__(self, root):
        self.root = root
        self.root.title("音频文件排序工具")
        self.root.geometry("1600x1200")

        # 设置变量
        self.processing = False
        self.cancel_flag = False
        self.group_size = tk.IntVar(value=50)  # 默认每组50个文件
        self.preview_mode = tk.BooleanVar(value=True)  # 默认启用预览模式
        self.folder_prefix = tk.StringVar(value="Group_")  # 文件夹前缀

        # 中文数字映射
        self.chinese_to_arabic = {
            "零": 0,
            "一": 1,
            "二": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "七": 7,
            "八": 8,
            "九": 9,
            "十": 10,
            "百": 100,
            "千": 1000,
            "万": 10000,
            "亿": 100000000,
        }

        # 文件信息列表
        self.file_info = []

        # 创建界面元素
        self.create_widgets()

    def create_widgets(self):
        # 创建菜单栏
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)

        # 创建"文件"菜单
        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="选择目录", command=self.browse_directory)
        file_menu.add_command(label="刷新", command=self.refresh_files)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)

        # 创建"设置"菜单
        settings_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="设置", menu=settings_menu)
        settings_menu.add_command(label="分组设置", command=self.show_settings)
        settings_menu.add_checkbutton(label="启用预览", variable=self.preview_mode)

        # 创建"帮助"菜单
        help_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)
        help_menu.add_command(label="使用说明", command=self.show_help)

        # 创建主框架
        main_frame = tk.PanedWindow(self.root, orient=tk.VERTICAL)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 上部框架 - 设置部分
        settings_frame = tk.LabelFrame(main_frame, text="设置")
        main_frame.add(settings_frame)

        # 目录选择部分
        dir_frame = tk.Frame(settings_frame)
        dir_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(dir_frame, text="目录:").pack(side=tk.LEFT, padx=5)
        self.dir_entry = tk.Entry(dir_frame, width=50)
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        browse_btn = tk.Button(dir_frame, text="浏览", command=self.browse_directory)
        browse_btn.pack(side=tk.LEFT, padx=5)

        refresh_btn = tk.Button(dir_frame, text="刷新", command=self.refresh_files)
        refresh_btn.pack(side=tk.LEFT, padx=5)

        # 分组设置部分
        group_frame = tk.Frame(settings_frame)
        group_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(group_frame, text="每组文件数:").pack(side=tk.LEFT, padx=5)
        group_size_entry = tk.Entry(group_frame, textvariable=self.group_size, width=5)
        group_size_entry.pack(side=tk.LEFT, padx=5)

        tk.Label(group_frame, text="文件夹前缀:").pack(side=tk.LEFT, padx=5)
        folder_prefix_entry = tk.Entry(
            group_frame, textvariable=self.folder_prefix, width=10
        )
        folder_prefix_entry.pack(side=tk.LEFT, padx=5)

        tk.Checkbutton(group_frame, text="启用预览", variable=self.preview_mode).pack(
            side=tk.LEFT, padx=20
        )

        # 操作按钮 - 确保这部分正确显示
        btn_frame = tk.Frame(settings_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        # 修改按钮样式和大小，确保它们更醒目
        self.scan_btn = tk.Button(
            btn_frame,
            text="扫描文件",
            command=self.scan_files,
            width=15,
            height=2,
            bg="#e1e1e1",
            font=("黑体", 10, "bold"),
        )
        self.scan_btn.pack(side=tk.LEFT, padx=10, pady=5)

        self.start_btn = tk.Button(
            btn_frame,
            text="开始分组",
            command=self.start_processing,
            width=15,
            height=2,
            bg="#a0d8ef",
            font=("黑体", 10, "bold"),
        )
        self.start_btn.pack(side=tk.LEFT, padx=10, pady=5)

        self.cancel_btn = tk.Button(
            btn_frame,
            text="取消",
            command=self.cancel_processing,
            width=15,
            height=2,
            bg="#ffb3a7",
            font=("黑体", 10, "bold"),
            state=tk.DISABLED,
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=10, pady=5)

        # 中部框架 - 文件预览
        preview_frame = tk.LabelFrame(main_frame, text="文件预览")
        main_frame.add(preview_frame)

        preview_inner = tk.Frame(preview_frame)
        preview_inner.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 创建Treeview组件
        columns = ("文件名", "章节号", "分组")
        self.file_tree = ttk.Treeview(preview_inner, columns=columns, show="headings")

        # 设置列标题
        for col in columns:
            self.file_tree.heading(col, text=col)
            self.file_tree.column(col, width=100)

        # 设置列宽
        self.file_tree.column("文件名", width=300)

        # 添加滚动条
        ysb = ttk.Scrollbar(
            preview_inner, orient=tk.VERTICAL, command=self.file_tree.yview
        )
        xsb = ttk.Scrollbar(
            preview_inner, orient=tk.HORIZONTAL, command=self.file_tree.xview
        )
        self.file_tree.configure(yscroll=ysb.set, xscroll=xsb.set)

        # 放置Treeview和滚动条
        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        xsb.pack(side=tk.BOTTOM, fill=tk.X)

        # 下部框架 - 日志和进度
        bottom_frame = tk.Frame(main_frame)
        main_frame.add(bottom_frame)

        # 进度条
        progress_frame = tk.LabelFrame(bottom_frame, text="处理进度")
        progress_frame.pack(fill=tk.X, padx=5, pady=5)

        self.progress = ttk.Progressbar(progress_frame, length=680, mode="determinate")
        self.progress.pack(fill=tk.X, padx=5, pady=5)

        self.status_label = tk.Label(progress_frame, text="就绪")
        self.status_label.pack(anchor=tk.W, padx=5)

        # 日志显示区域
        log_frame = tk.LabelFrame(bottom_frame, text="处理日志")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        log_inner = tk.Frame(log_frame)
        log_inner.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.log_text = tk.Text(log_inner, height=8, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        log_sb = tk.Scrollbar(log_inner)
        log_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_sb.set)
        log_sb.config(command=self.log_text.yview)

        # 状态栏
        self.status_bar = tk.Label(
            self.root, text="准备就绪", bd=1, relief=tk.SUNKEN, anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # 设置窗格比例
        main_frame.paneconfigure(
            settings_frame, height=150
        )  # 增加设置区高度，确保按钮可见
        main_frame.paneconfigure(preview_frame, height=300)

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)
            self.status_bar.config(text=f"已选择目录: {directory}")
            self.refresh_files()

    def refresh_files(self):
        directory = self.dir_entry.get()
        if directory and os.path.exists(directory):
            self.scan_files()

    def show_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("分组设置")
        settings_window.geometry("400x250")
        settings_window.grab_set()  # 模态窗口

        # 基本设置
        basic_frame = tk.LabelFrame(settings_window, text="基本设置")
        basic_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(basic_frame, text="每组文件数量:").grid(
            row=0, column=0, padx=5, pady=5, sticky=tk.W
        )
        tk.Entry(basic_frame, textvariable=self.group_size, width=10).grid(
            row=0, column=1, padx=5, pady=5
        )

        tk.Label(basic_frame, text="文件夹前缀:").grid(
            row=1, column=0, padx=5, pady=5, sticky=tk.W
        )
        tk.Entry(basic_frame, textvariable=self.folder_prefix, width=20).grid(
            row=1, column=1, padx=5, pady=5
        )

        # 预览设置
        preview_frame = tk.LabelFrame(settings_window, text="预览设置")
        preview_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Checkbutton(
            preview_frame, text="启用预览模式", variable=self.preview_mode
        ).pack(anchor=tk.W, padx=5, pady=5)

        # 按钮
        button_frame = tk.Frame(settings_window)
        button_frame.pack(pady=20)

        tk.Button(
            button_frame,
            text="确定",
            command=lambda: settings_window.destroy(),
            width=10,
        ).pack(side=tk.LEFT, padx=10)

        tk.Button(
            button_frame,
            text="取消",
            command=lambda: settings_window.destroy(),
            width=10,
        ).pack(side=tk.LEFT, padx=10)

    def show_about(self):
        messagebox.showinfo(
            "关于",
            "音频文件排序工具\n\n"
            "功能：按章节顺序整理MP3文件并分组\n"
            "作者：AI助手\n"
            "版本：1.0",
        )

    def show_help(self):
        help_text = """使用说明：

1. 选择包含MP3文件的目录
2. 点击"扫描文件"按钮扫描文件
3. 在预览中查看文件分组情况
4. 调整分组设置（如有必要）
5. 点击"开始分组"执行文件移动

文件名格式：
程序将识别"第xxx章"格式的文件名，提取章节号进行排序。
支持阿拉伯数字和中文数字（如"第一章"、"第1章"）。
"""
        help_window = tk.Toplevel(self.root)
        help_window.title("使用说明")
        help_window.geometry("500x400")

        text = tk.Text(help_window, wrap=tk.WORD, padx=10, pady=10)
        text.pack(fill=tk.BOTH, expand=True)
        text.insert(tk.END, help_text)
        text.config(state=tk.DISABLED)

        tk.Button(help_window, text="关闭", command=help_window.destroy, width=10).pack(
            pady=10
        )

    def log(self, message):
        self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def update_status(self, message):
        self.status_label.config(text=message)
        self.status_bar.config(text=message)
        self.root.update_idletasks()

    def chinese_to_int(self, chinese_str):
        """将中文数字转换为阿拉伯数字"""
        if not chinese_str:
            return None

        result = 0
        tmp = 0

        for char in chinese_str:
            if char in self.chinese_to_arabic:
                num = self.chinese_to_arabic[char]
                if num >= 10:  # 是单位
                    if tmp == 0:
                        tmp = 1
                    result += tmp * num
                    tmp = 0
                else:  # 是数字
                    tmp = tmp * 10 + num
            else:
                return None  # 包含非中文数字字符

        result += tmp
        return result

    def extract_chapter_number(self, filename):
        """从文件名中提取章节号"""
        # 尝试匹配阿拉伯数字章节号
        match = re.search(r"第(\d+)章", filename)
        if match:
            return int(match.group(1))

        # 尝试匹配其他格式的阿拉伯数字
        match = re.search(r"[第\s]*(\d+)[章節\s]", filename)
        if match:
            return int(match.group(1))

        # 尝试匹配中文数字章节号
        match = re.search(r"第([零一二三四五六七八九十百千万亿]+)章", filename)
        if match:
            chinese_num = match.group(1)
            try:
                return self.chinese_to_int(chinese_num)
            except:
                pass

        # 尝试从文件名开头提取数字
        match = re.search(r"^(\d+)", filename)
        if match:
            return int(match.group(1))

        return float("inf")  # 无法提取章节号

    def scan_files(self):
        """扫描目录中的MP3文件并解析章节号"""
        directory = self.dir_entry.get()
        if not directory:
            messagebox.showerror("错误", "请选择一个目录")
            return

        if not os.path.exists(directory):
            messagebox.showerror("错误", "所选目录不存在")
            return

        # 更新状态
        self.update_status("正在扫描文件...")
        self.log(f"扫描目录: {directory}")

        # 清空文件树
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)

        # 获取所有mp3文件
        try:
            mp3_files = [f for f in os.listdir(directory) if f.lower().endswith(".mp3")]
            if not mp3_files:
                self.log("目录中没有找到MP3文件")
                messagebox.showinfo("信息", "目录中没有找到MP3文件")
                self.update_status("就绪")
                return

            self.log(f"找到 {len(mp3_files)} 个MP3文件")

            # 解析文件名，提取章节数
            self.file_info = []
            for filename in mp3_files:
                chapter_num = self.extract_chapter_number(filename)
                self.file_info.append((filename, chapter_num))

                # 检查是否可以识别章节号
                if chapter_num == float("inf"):
                    self.log(f"警告: 无法从文件 '{filename}' 中提取章节号")

            # 按章节数排序
            self.file_info.sort(key=lambda x: x[1])

            # 按指定数量一组分组
            group_size = self.group_size.get()
            groups = [
                self.file_info[i : i + group_size]
                for i in range(0, len(self.file_info), group_size)
            ]

            # 填充预览树
            for i, group in enumerate(groups):
                group_name = f"{self.folder_prefix.get()}{i+1}"
                for filename, chapter_num in group:
                    chapter_display = (
                        str(chapter_num) if chapter_num != float("inf") else "未知"
                    )
                    self.file_tree.insert(
                        "", tk.END, values=(filename, chapter_display, group_name)
                    )

            self.log(f"文件将被分为 {len(groups)} 组")
            self.update_status(
                f"扫描完成，找到 {len(mp3_files)} 个文件，将分为 {len(groups)} 组"
            )

        except Exception as e:
            self.log(f"扫描文件时发生错误: {str(e)}")
            messagebox.showerror("错误", f"扫描文件时发生错误: {str(e)}")
            self.update_status("就绪")

    def start_processing(self):
        # 获取所选目录
        directory = self.dir_entry.get()
        if not directory:
            messagebox.showerror("错误", "请选择一个目录")
            return

        if not os.path.exists(directory):
            messagebox.showerror("错误", "所选目录不存在")
            return

        # 检查是否已经扫描文件
        if not self.file_info:
            if messagebox.askyesno("确认", "尚未扫描文件或没有找到文件，是否先扫描？"):
                self.scan_files()
                if not self.file_info:
                    return
            else:
                return

        try:
            group_size = self.group_size.get()
            if group_size <= 0:
                messagebox.showerror("错误", "每组文件数量必须大于0")
                return
        except:
            messagebox.showerror("错误", "每组文件数量必须是一个有效的整数")
            return

        # 如果启用预览模式，询问用户是否继续
        if self.preview_mode.get():
            if not messagebox.askyesno("确认", "确定要按照预览中的分组移动文件吗？"):
                return

        # 更新界面状态
        self.processing = True
        self.cancel_flag = False
        self.start_btn.config(state=tk.DISABLED)
        self.scan_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)

        # 重置进度条
        self.progress["value"] = 0

        # 在新线程中处理，避免GUI卡死
        threading.Thread(
            target=self.process_directory, args=(directory, group_size), daemon=True
        ).start()

    def cancel_processing(self):
        if messagebox.askyesno("确认", "确定要取消处理吗？"):
            self.cancel_flag = True
            self.log("用户请求取消处理...")
            self.update_status("正在取消...")

    def process_directory(self, directory, group_size):
        try:
            self.update_status(f"正在处理目录: {directory}")
            self.log(f"开始处理目录: {directory}")
            self.log(f"每组文件数量: {group_size}")

            # 按指定数量一组分组
            groups = [
                self.file_info[i : i + group_size]
                for i in range(0, len(self.file_info), group_size)
            ]

            # 设置进度条
            self.progress["maximum"] = len(self.file_info)
            self.progress["value"] = 0

            # 创建文件夹并移动文件
            processed_count = 0
            for i, group in enumerate(groups):
                if self.cancel_flag:
                    self.log("处理已取消")
                    self.processing_completed()
                    return

                group_dir = os.path.join(directory, f"{self.folder_prefix.get()}{i+1}")

                # 创建组文件夹
                if not os.path.exists(group_dir):
                    os.makedirs(group_dir)
                    self.log(f"创建文件夹: {group_dir}")

                # 移动文件
                for filename, chapter_num in group:
                    if self.cancel_flag:
                        self.log("处理已取消")
                        self.processing_completed()
                        return

                    src_path = os.path.join(directory, filename)
                    dst_path = os.path.join(group_dir, filename)

                    # 检查源文件是否存在
                    if not os.path.exists(src_path):
                        self.log(f"警告: 文件 '{filename}' 不存在，跳过")
                        continue

                    try:
                        self.update_status(f"正在移动: {filename}")
                        shutil.move(src_path, dst_path)
                        self.log(
                            f"移动文件: {filename} -> {os.path.basename(group_dir)}"
                        )
                    except Exception as e:
                        self.log(f"错误: 移动文件 '{filename}' 失败: {str(e)}")

                    # 更新进度条
                    processed_count += 1
                    self.progress["value"] = processed_count

                    # 更新处理百分比
                    percentage = int(processed_count / len(self.file_info) * 100)
                    self.update_status(
                        f"已处理: {processed_count}/{len(self.file_info)} ({percentage}%)"
                    )

                    # 小延迟，让GUI有时间更新
                    time.sleep(0.01)

            self.log("处理完成!")
            messagebox.showinfo(
                "完成",
                f"处理完成！\n\n共处理 {processed_count} 个文件，分为 {len(groups)} 组。",
            )

            # 处理完成后清空文件信息列表
            self.file_info = []

            # 清空文件树
            for item in self.file_tree.get_children():
                self.file_tree.delete(item)

        except Exception as e:
            self.log(f"发生错误: {str(e)}")
            messagebox.showerror("错误", f"处理过程中发生错误: {str(e)}")

        finally:
            self.processing_completed()

    def processing_completed(self):
        # 恢复界面状态
        self.processing = False
        self.start_btn.config(state=tk.NORMAL)
        self.scan_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        self.update_status("就绪")


if __name__ == "__main__":
    root = tk.Tk()
    app = AudioFileSorter(root)
    root.mainloop()
