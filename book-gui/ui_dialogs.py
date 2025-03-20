"""
界面对话框模块，提供各种交互界面组件
"""

import os
import re
import json
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from bson import ObjectId
from openai import OpenAI

# 导入自定义配置
from config import DEFAULT_AI_NAME, DEFAULT_API_BASE_URL, DEFAULT_AI_MODEL


class DatabaseConfigDialog(tk.Toplevel):
    """数据库配置对话框"""

    def __init__(self, parent, db_manager, config=None):
        super().__init__(parent)
        self.parent = parent
        self.db_manager = db_manager
        self.result = None

        self.title("MongoDB数据库配置")
        self.geometry("500x250")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # 默认配置
        self.config = {
            "host": "localhost",
            "port": "27017",
            "username": "",
            "password": "",
            "auth_db": "admin",
            "db_name": "novels",
        }

        # 如果有传入配置，则使用传入配置
        if config:
            self.config.update(config)

        self.create_widgets()
        self.center_window()

    def create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 连接类型选择
        conn_frame = ttk.LabelFrame(main_frame, text="连接类型")
        conn_frame.pack(fill=tk.X, pady=5)

        self.conn_type = tk.StringVar(value="local")
        ttk.Radiobutton(
            conn_frame,
            text="本地连接",
            variable=self.conn_type,
            value="local",
            command=self.toggle_connection_type,
        ).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(
            conn_frame,
            text="远程连接",
            variable=self.conn_type,
            value="remote",
            command=self.toggle_connection_type,
        ).pack(side=tk.LEFT, padx=10)

        # 创建输入框架
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # 主机和端口
        host_frame = ttk.Frame(input_frame)
        host_frame.pack(fill=tk.X, pady=2)

        ttk.Label(host_frame, text="主机:", width=10).pack(side=tk.LEFT)
        self.host_var = tk.StringVar(value=self.config["host"])
        self.host_entry = ttk.Entry(host_frame, textvariable=self.host_var)
        self.host_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        ttk.Label(host_frame, text="端口:").pack(side=tk.LEFT, padx=(10, 0))
        self.port_var = tk.StringVar(value=self.config["port"])
        self.port_entry = ttk.Entry(host_frame, textvariable=self.port_var, width=8)
        self.port_entry.pack(side=tk.LEFT, padx=5)

        # 用户名和密码
        user_frame = ttk.Frame(input_frame)
        user_frame.pack(fill=tk.X, pady=2)

        ttk.Label(user_frame, text="用户名:", width=10).pack(side=tk.LEFT)
        self.username_var = tk.StringVar(value=self.config["username"])
        self.username_entry = ttk.Entry(user_frame, textvariable=self.username_var)
        self.username_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        pass_frame = ttk.Frame(input_frame)
        pass_frame.pack(fill=tk.X, pady=2)

        ttk.Label(pass_frame, text="密码:", width=10).pack(side=tk.LEFT)
        self.password_var = tk.StringVar(value=self.config["password"])
        self.password_entry = ttk.Entry(
            pass_frame, textvariable=self.password_var, show="*"
        )
        self.password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 验证数据库
        auth_frame = ttk.Frame(input_frame)
        auth_frame.pack(fill=tk.X, pady=2)

        ttk.Label(auth_frame, text="验证库:", width=10).pack(side=tk.LEFT)
        self.auth_db_var = tk.StringVar(value=self.config["auth_db"])
        self.auth_db_entry = ttk.Entry(auth_frame, textvariable=self.auth_db_var)
        self.auth_db_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 数据库名称
        db_frame = ttk.Frame(input_frame)
        db_frame.pack(fill=tk.X, pady=2)

        ttk.Label(db_frame, text="数据库名:", width=10).pack(side=tk.LEFT)
        self.db_name_var = tk.StringVar(value=self.config["db_name"])
        self.db_name_entry = ttk.Entry(db_frame, textvariable=self.db_name_var)
        self.db_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="测试连接", command=self.test_connection).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frame, text="取消", command=self.cancel).pack(
            side=tk.RIGHT, padx=5
        )
        ttk.Button(btn_frame, text="保存", command=self.save).pack(
            side=tk.RIGHT, padx=5
        )

        # 初始调整界面
        self.toggle_connection_type()

    def toggle_connection_type(self):
        """切换连接类型"""
        conn_type = self.conn_type.get()

        if conn_type == "local":
            # 本地连接，禁用用户名和密码
            self.host_var.set("localhost")
            self.username_var.set("")
            self.password_var.set("")
            self.username_entry.configure(state="disabled")
            self.password_entry.configure(state="disabled")
            self.auth_db_entry.configure(state="disabled")
        else:
            # 远程连接，启用所有字段
            self.username_entry.configure(state="normal")
            self.password_entry.configure(state="normal")
            self.auth_db_entry.configure(state="normal")

    def build_connection_string(self):
        """构建MongoDB连接字符串"""
        host = self.host_var.get()
        port = self.port_var.get()
        username = self.username_var.get()
        password = self.password_var.get()
        auth_db = self.auth_db_var.get()

        if self.conn_type.get() == "local" or not username:
            # 本地连接或无用户名
            return f"mongodb://{host}:{port}/"
        else:
            # 远程连接，带认证信息
            return f"mongodb://{username}:{password}@{host}:{port}/{auth_db}"

    def test_connection(self):
        """测试数据库连接"""
        connection_string = self.build_connection_string()
        db_name = self.db_name_var.get()

        # 临时创建一个MongoDB管理器来测试连接
        success, message = self.db_manager.connect(connection_string, db_name)

        if success:
            messagebox.showinfo("连接测试", f"连接成功!\n数据库: {db_name}")
        else:
            messagebox.showerror("连接测试", f"连接失败!\n{message}")

    def save(self):
        """保存配置并尝试连接"""
        connection_string = self.build_connection_string()
        db_name = self.db_name_var.get()

        # 保存当前配置
        self.result = {
            "connection_string": connection_string,
            "db_name": db_name,
            "config": {
                "host": self.host_var.get(),
                "port": self.port_var.get(),
                "username": self.username_var.get(),
                "password": self.password_var.get(),
                "auth_db": self.auth_db_var.get(),
                "db_name": db_name,
            },
        }

        # 保存连接配置
        self.db_manager.save_connection_config(self.result)

        # 尝试连接
        success, message = self.db_manager.connect(connection_string, db_name)

        if success:
            self.destroy()
        else:
            messagebox.showerror("连接错误", message)

    def cancel(self):
        """取消操作"""
        self.result = None
        self.destroy()

    def center_window(self):
        """将窗口居中显示"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.parent.winfo_width() - width) // 2 + self.parent.winfo_x()
        y = (self.parent.winfo_height() - height) // 2 + self.parent.winfo_y()
        self.geometry(f"{width}x{height}+{x}+{y}")


class NovelInfoDialog(tk.Toplevel):
    """小说信息编辑对话框"""

    def __init__(self, parent, novel=None):
        super().__init__(parent)
        self.parent = parent
        self.novel = novel
        self.result = None

        self.title("小说信息")
        self.geometry("400x300")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.create_widgets()
        self.center_window()

    def create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 表单区域
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # 小说名称
        name_frame = ttk.Frame(form_frame)
        name_frame.pack(fill=tk.X, pady=5)

        ttk.Label(name_frame, text="小说名称:", width=10).pack(side=tk.LEFT)
        self.name_var = tk.StringVar(value=self.novel.name if self.novel else "")
        name_entry = ttk.Entry(name_frame, textvariable=self.name_var)
        name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 作者
        author_frame = ttk.Frame(form_frame)
        author_frame.pack(fill=tk.X, pady=5)

        ttk.Label(author_frame, text="作者:", width=10).pack(side=tk.LEFT)
        self.author_var = tk.StringVar(value=self.novel.author if self.novel else "")
        author_entry = ttk.Entry(author_frame, textvariable=self.author_var)
        author_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 来源URL
        url_frame = ttk.Frame(form_frame)
        url_frame.pack(fill=tk.X, pady=5)

        ttk.Label(url_frame, text="来源URL:", width=10).pack(side=tk.LEFT)
        self.url_var = tk.StringVar(value=self.novel.source_url if self.novel else "")
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var)
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 描述
        desc_frame = ttk.LabelFrame(form_frame, text="描述")
        desc_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.desc_text = tk.Text(desc_frame, height=5, wrap=tk.WORD)
        self.desc_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        if self.novel and self.novel.description:
            self.desc_text.insert(tk.END, self.novel.description)

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="取消", command=self.cancel).pack(
            side=tk.RIGHT, padx=5
        )
        ttk.Button(btn_frame, text="保存", command=self.save).pack(
            side=tk.RIGHT, padx=5
        )

    def save(self):
        """保存小说信息"""
        # 获取表单数据
        name = self.name_var.get().strip()

        if not name:
            messagebox.showwarning("警告", "小说名称不能为空")
            return

        # 更新小说对象属性
        if not self.novel:
            from models import Novel

            self.novel = Novel()

        self.novel.name = name
        self.novel.author = self.author_var.get().strip()
        self.novel.source_url = self.url_var.get().strip()
        self.novel.description = self.desc_text.get("1.0", tk.END).strip()

        self.result = self.novel
        self.destroy()

    def cancel(self):
        """取消操作"""
        self.result = None
        self.destroy()

    def center_window(self):
        """将窗口居中显示"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.parent.winfo_width() - width) // 2 + self.parent.winfo_x()
        y = (self.parent.winfo_height() - height) // 2 + self.parent.winfo_y()
        self.geometry(f"{width}x{height}+{x}+{y}")


class DownloadProgressDialog(tk.Toplevel):
    """下载进度对话框"""

    def __init__(self, parent, total_items, title="下载进度"):
        super().__init__(parent)
        self.parent = parent
        self.total = total_items

        self.title(title)
        self.geometry("500x200")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.create_widgets()
        self.center_window()

        # 日志消息列表
        self.messages = []

        # 关闭窗口时的回调函数
        self.on_close = None

    def create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 进度条
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=10)

        self.progress_label = ttk.Label(
            progress_frame, text=f"正在处理 (0/{self.total})"
        )
        self.progress_label.pack(fill=tk.X, side=tk.TOP, pady=5)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(
            progress_frame,
            orient=tk.HORIZONTAL,
            length=100,
            mode="determinate",
            variable=self.progress_var,
        )
        self.progress.pack(fill=tk.X, side=tk.BOTTOM)

        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="处理日志")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL)
        self.log_text = tk.Text(log_frame, height=8, yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        log_scroll.config(command=self.log_text.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        self.cancel_button = ttk.Button(btn_frame, text="取消", command=self.cancel)
        self.cancel_button.pack(side=tk.RIGHT, padx=5)

        # 绑定关闭窗口事件
        self.protocol("WM_DELETE_WINDOW", self.cancel)

    def update_progress(self, completed):
        """更新进度条"""
        progress = (completed / self.total) * 100
        self.progress_var.set(progress)
        self.progress_label.config(text=f"正在处理 ({completed}/{self.total})")

    def add_message(self, message):
        """添加日志消息"""
        self.messages.append(message)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)

        # 从消息中提取完成进度
        match = re.search(r"\((\d+)/\d+\)", message)
        if match:
            completed = int(match.group(1))
            self.update_progress(completed)

    def set_finished(self):
        """设置为完成状态"""
        self.progress_var.set(100)
        self.progress_label.config(text="处理完成")
        self.cancel_button.config(text="关闭")

    def cancel(self):
        """取消操作"""
        if self.on_close:
            self.on_close()
        self.destroy()

    def center_window(self):
        """将窗口居中显示"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.parent.winfo_width() - width) // 2 + self.parent.winfo_x()
        y = (self.parent.winfo_height() - height) // 2 + self.parent.winfo_y()
        self.geometry(f"{width}x{height}+{x}+{y}")


class APIKeyConfigDialog(tk.Toplevel):
    """API密钥配置对话框"""

    def __init__(self, parent, db_manager=None, ai_name=DEFAULT_AI_NAME):
        super().__init__(parent)
        self.parent = parent
        self.db_manager = db_manager
        self.ai_name = ai_name
        self.result = None

        self.title(f"{self.ai_name} API配置")
        self.geometry("500x260")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # 尝试从数据库获取默认API密钥
        self.default_api_key = None
        if self.db_manager and self.db_manager.is_connected():
            key_info = self.db_manager.get_default_api_key(self.ai_name)
            if key_info:
                self.default_api_key = key_info.get("api_key")

        self.create_widgets()
        self.center_window()

    def create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # API密钥输入
        api_frame = ttk.Frame(main_frame)
        api_frame.pack(fill=tk.X, pady=5)

        ttk.Label(api_frame, text="API密钥:").pack(side=tk.LEFT)
        self.api_key_var = tk.StringVar(value=self.default_api_key or "")
        self.api_key_entry = ttk.Entry(
            api_frame, textvariable=self.api_key_var, width=40, show="*"
        )
        self.api_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # API基础URL
        base_url_frame = ttk.Frame(main_frame)
        base_url_frame.pack(fill=tk.X, pady=5)

        ttk.Label(base_url_frame, text="API基础URL:").pack(side=tk.LEFT)
        self.base_url_var = tk.StringVar(value=DEFAULT_API_BASE_URL)
        self.base_url_entry = ttk.Entry(
            base_url_frame, textvariable=self.base_url_var, width=40
        )
        self.base_url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 模型选择
        model_frame = ttk.Frame(main_frame)
        model_frame.pack(fill=tk.X, pady=5)

        ttk.Label(model_frame, text="模型:").pack(side=tk.LEFT)
        self.model_var = tk.StringVar(value=DEFAULT_AI_MODEL)
        self.model_combobox = ttk.Combobox(
            model_frame, textvariable=self.model_var, width=30
        )
        self.model_combobox["values"] = [
            "gemini-2.0-flash",
            "gemini-2.0-pro",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]
        self.model_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 设为默认
        default_frame = ttk.Frame(main_frame)
        default_frame.pack(fill=tk.X, pady=5)

        self.default_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(default_frame, text="设为默认", variable=self.default_var).pack(
            side=tk.LEFT
        )

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="测试API", command=self.test_api).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frame, text="取消", command=self.cancel).pack(
            side=tk.RIGHT, padx=5
        )
        ttk.Button(btn_frame, text="保存", command=self.save).pack(
            side=tk.RIGHT, padx=5
        )

    def test_api(self):
        """测试API连接"""
        api_key = self.api_key_var.get().strip()
        base_url = self.base_url_var.get().strip()
        model = self.model_var.get().strip()

        if not api_key:
            messagebox.showwarning("警告", "请输入API密钥")
            return

        try:
            # 创建临时客户端进行测试
            client = OpenAI(api_key=api_key, base_url=base_url)
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "你好，这是一个测试。"}],
            )

            if response.choices and len(response.choices) > 0:
                messagebox.showinfo("测试成功", "API连接测试成功!")
            else:
                messagebox.showerror("测试失败", "API返回无效响应")

        except Exception as e:
            error_message = str(e)
            if "403" in error_message and "Permission denied" in error_message and "CONSUMER SUSPENDED" in error_message:
                messagebox.showerror("测试失败", "API 密钥已被停用，请检查你的账户状态或更换 API 密钥。")
            else:
                messagebox.showerror("测试失败", f"API连接测试失败: {error_message}")

    def save(self):
        """保存API配置"""
        api_key = self.api_key_var.get().strip()
        base_url = self.base_url_var.get().strip()
        model = self.model_var.get().strip()
        is_default = self.default_var.get()

        if not api_key:
            messagebox.showwarning("警告", "请输入API密钥")
            return

        # 保存到数据库
        if self.db_manager and self.db_manager.is_connected():
            success, message = self.db_manager.save_api_key(
                api_key, self.ai_name, is_default
            )
            if not success:
                messagebox.showerror("保存失败", message)
                return

        # 保存到环境变量或配置文件
        os.environ[f"{self.ai_name.upper()}_API_KEY"] = api_key
        os.environ[f"{self.ai_name.upper()}_API_BASE_URL"] = base_url
        os.environ[f"{self.ai_name.upper()}_MODEL"] = model

        self.result = {
            "api_key": api_key,
            "base_url": base_url,
            "model": model,
            "is_default": is_default,
        }

        self.destroy()

    def cancel(self):
        """取消操作"""
        self.result = None
        self.destroy()

    def center_window(self):
        """将窗口居中显示"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.parent.winfo_width() - width) // 2 + self.parent.winfo_x()
        y = (self.parent.winfo_height() - height) // 2 + self.parent.winfo_y()
        self.geometry(f"{width}x{height}+{x}+{y}")


class MultiAPIKeysDialog(tk.Toplevel):
    """多API密钥管理对话框"""

    def __init__(self, parent, db_manager=None, ai_name=DEFAULT_AI_NAME):
        super().__init__(parent)
        self.parent = parent
        self.db_manager = db_manager
        self.ai_name = ai_name
        self.result = None

        self.title(f"{self.ai_name} API密钥管理")
        self.geometry("700x400")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        # 加载现有密钥
        self.api_keys = []
        self.load_api_keys()

        self.create_widgets()
        self.center_window()

    def load_api_keys(self):
        """加载API密钥"""
        if self.db_manager and self.db_manager.is_connected():
            try:
                # 从数据库加载
                keys = self.db_manager.get_api_keys(self.ai_name)
                if keys:
                    self.api_keys = keys
                    return
            except Exception as e:
                print(f"从数据库加载API密钥失败: {str(e)}")

        # 如果数据库加载失败，尝试从文件加载
        try:
            keys_file = "api_keys.txt"
            if os.path.exists(keys_file):
                with open(keys_file, "r") as f:
                    file_keys = [line.strip() for line in f if line.strip()]
                    for key in file_keys:
                        self.api_keys.append(
                            {
                                "_id": ObjectId(),
                                "api_key": key,
                                "ai_name": self.ai_name,
                                "is_default": False,
                            }
                        )

                    # 设置第一个为默认
                    if self.api_keys:
                        self.api_keys[0]["is_default"] = True
        except Exception as e:
            print(f"从文件加载API密钥失败: {str(e)}")

    def save_api_keys_to_file(self):
        """保存API密钥到文件（备份）"""
        try:
            with open("api_keys.txt", "w") as f:
                for key in self.api_keys:
                    f.write(f"{key.get('api_key', '')}\n")
            return True
        except Exception as e:
            print(f"保存API密钥到文件失败: {str(e)}")
            return False

    def create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 密钥列表
        list_frame = ttk.LabelFrame(main_frame, text="API密钥列表")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # 创建树状视图
        columns = ("api_key", "is_default")
        self.keys_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        self.keys_tree.heading("api_key", text="API密钥")
        self.keys_tree.heading("is_default", text="默认")
        self.keys_tree.column("api_key", width=400)
        self.keys_tree.column("is_default", width=50)

        # 显示密钥（隐藏部分）
        for key in self.api_keys:
            full_key = key.get("api_key", "")
            display_key = (
                full_key[:4] + "*" * (len(full_key) - 8) + full_key[-4:]
                if len(full_key) > 8
                else full_key
            )
            is_default = "✓" if key.get("is_default", False) else ""
            self.keys_tree.insert(
                "", "end", values=(display_key, is_default), tags=(str(key.get("_id")),)
            )

        # 添加滚动条
        keys_scroll = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.keys_tree.yview
        )
        self.keys_tree.configure(yscrollcommand=keys_scroll.set)

        self.keys_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        keys_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 5), pady=5)

        # 输入区域
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=5)

        ttk.Label(input_frame, text="API密钥:").pack(side=tk.LEFT)
        self.key_var = tk.StringVar()
        self.key_entry = ttk.Entry(
            input_frame, textvariable=self.key_var, width=50, show="*"
        )
        self.key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.default_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(input_frame, text="设为默认", variable=self.default_var).pack(
            side=tk.LEFT, padx=5
        )

        # 操作按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="添加", command=self.add_key).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frame, text="删除选中", command=self.delete_key).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frame, text="设为默认", command=self.set_default_key).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frame, text="测试选中", command=self.test_key).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Button(btn_frame, text="取消", command=self.cancel).pack(
            side=tk.RIGHT, padx=5
        )
        ttk.Button(btn_frame, text="保存", command=self.save).pack(
            side=tk.RIGHT, padx=5
        )

    def add_key(self):
        """添加新密钥"""
        key = self.key_var.get().strip()
        if not key:
            messagebox.showwarning("警告", "请输入API密钥")
            return

        # 检查是否已存在相同密钥
        for existing_key in self.api_keys:
            if existing_key.get("api_key") == key:
                messagebox.showinfo("提示", "该密钥已存在")
                return

        # 创建新密钥记录
        is_default = self.default_var.get()
        new_key = {
            "_id": ObjectId(),
            "api_key": key,
            "ai_name": self.ai_name,
            "is_default": is_default,
        }

        # 如果设为默认，取消其他默认
        if is_default:
            for existing_key in self.api_keys:
                existing_key["is_default"] = False

        self.api_keys.append(new_key)

        # 更新显示
        display_key = key[:4] + "*" * (len(key) - 8) + key[-4:] if len(key) > 8 else key
        is_default_mark = "✓" if is_default else ""
        self.keys_tree.insert(
            "",
            "end",
            values=(display_key, is_default_mark),
            tags=(str(new_key["_id"]),),
        )

        self.key_var.set("")
        self.default_var.set(False)

    def delete_key(self):
        """删除选中密钥"""
        selected = self.keys_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要删除的密钥")
            return

        item = selected[0]
        item_id = self.keys_tree.item(item, "tags")[0]

        # 查找并删除密钥
        for i, key in enumerate(self.api_keys):
            if str(key.get("_id")) == item_id:
                was_default = key.get("is_default", False)
                del self.api_keys[i]
                self.keys_tree.delete(item)

                # 如果删除的是默认密钥，设置第一个为默认
                if was_default and self.api_keys:
                    self.api_keys[0]["is_default"] = True
                    # 更新树状视图
                    self.refresh_keys_tree()
                break

    def set_default_key(self):
        """设置选中密钥为默认"""
        selected = self.keys_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要设为默认的密钥")
            return

        item = selected[0]
        item_id = self.keys_tree.item(item, "tags")[0]

        # 更新默认状态
        for key in self.api_keys:
            key["is_default"] = str(key.get("_id")) == item_id

        # 刷新显示
        self.refresh_keys_tree()

    def refresh_keys_tree(self):
        """刷新密钥列表显示"""
        # 清空树状视图
        self.keys_tree.delete(*self.keys_tree.get_children())

        # 重新添加所有密钥
        for key in self.api_keys:
            full_key = key.get("api_key", "")
            display_key = (
                full_key[:4] + "*" * (len(full_key) - 8) + full_key[-4:]
                if len(full_key) > 8
                else full_key
            )
            is_default = "✓" if key.get("is_default", False) else ""
            self.keys_tree.insert(
                "", "end", values=(display_key, is_default), tags=(str(key.get("_id")),)
            )

    def test_key(self):
        """测试选中密钥"""
        selected = self.keys_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要测试的密钥")
            return

        item = selected[0]
        item_id = self.keys_tree.item(item, "tags")[0]

        # 查找选中的密钥
        api_key = None
        for key in self.api_keys:
            if str(key.get("_id")) == item_id:
                api_key = key.get("api_key")
                break

        if not api_key:
            return

        try:
            # 创建临时客户端进行测试
            client = OpenAI(api_key=api_key, base_url=DEFAULT_API_BASE_URL)
            response = client.chat.completions.create(
                model=DEFAULT_AI_MODEL,
                messages=[{"role": "user", "content": "你好，这是一个测试。"}],
            )

            if response.choices and len(response.choices) > 0:
                messagebox.showinfo("测试成功", "API密钥有效!")
            else:
                messagebox.showerror("测试失败", "API返回无效响应")

        except Exception as e:
            messagebox.showerror("测试失败", f"API密钥无效: {str(e)}")

    def save(self):
        """保存所有密钥"""
        if not self.api_keys:
            messagebox.showwarning("警告", "没有要保存的API密钥")
            return

        # 确保有默认密钥
        has_default = False
        for key in self.api_keys:
            if key.get("is_default", False):
                has_default = True
                break

        if not has_default and self.api_keys:
            self.api_keys[0]["is_default"] = True

        # 保存到数据库
        if self.db_manager and self.db_manager.is_connected():
            try:
                # 先删除所有现有的API密钥
                self.db_manager.db.api_keys.delete_many({"ai_name": self.ai_name})

                # 插入新的API密钥
                for key in self.api_keys:
                    self.db_manager.save_api_key(
                        key.get("api_key", ""),
                        self.ai_name,
                        key.get("is_default", False),
                    )
            except Exception as e:
                messagebox.showerror("保存失败", f"保存API密钥到数据库失败: {str(e)}")
                return

        # 同时保存到文件（作为备份）
        self.save_api_keys_to_file()

        # 返回结果
        self.result = self.api_keys
        messagebox.showinfo("成功", f"已保存 {len(self.api_keys)} 个API密钥")
        self.destroy()

    def cancel(self):
        """取消操作"""
        self.result = None
        self.destroy()

    def center_window(self):
        """将窗口居中显示"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.parent.winfo_width() - width) // 2 + self.parent.winfo_x()
        y = (self.parent.winfo_height() - height) // 2 + self.parent.winfo_y()
        self.geometry(f"{width}x{height}+{x}+{y}")


class DialogueViewDialog(tk.Toplevel):
    """对话内容查看对话框"""

    def __init__(self, parent, chapter_title, dialogues):
        super().__init__(parent)
        self.parent = parent
        self.chapter_title = chapter_title
        self.dialogues = dialogues

        self.title(f"对话分析 - {chapter_title}")
        self.geometry("1600x1200")
        self.resizable(True, True)
        self.transient(parent)

        self.create_widgets()
        self.center_window()

    def create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            title_frame, text=f"章节: {self.chapter_title}", font=("", 12, "bold")
        ).pack(side=tk.LEFT)
        ttk.Label(title_frame, text=f"共 {len(self.dialogues)} 条对话").pack(
            side=tk.RIGHT
        )

        # 对话列表
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # 创建表格
        columns = ("character", "gender", "text")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        self.tree.heading("character", text="角色")
        self.tree.heading("gender", text="性别")
        self.tree.heading("text", text="对话内容")
        self.tree.column("character", width=100)
        self.tree.column("gender", width=50)
        self.tree.column("text", width=600)

        # 添加滚动条
        scroll_y = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scroll_y.set)

        # 布局
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        # 填充数据
        for dialogue in self.dialogues:
            character = dialogue.get("type", "")
            gender = dialogue.get("sex", "")
            text = dialogue.get("text", "")

            self.tree.insert("", tk.END, values=(character, gender, text))

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="导出", command=self.export_dialogues).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frame, text="关闭", command=self.destroy).pack(
            side=tk.RIGHT, padx=5
        )

    def export_dialogues(self):
        """导出对话内容为JSON文件"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json")],
            title="导出对话分析",
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(self.dialogues, f, ensure_ascii=False, indent=4)
                messagebox.showinfo("导出成功", f"对话分析结果已导出到\n{file_path}")
            except Exception as e:
                messagebox.showerror("导出失败", f"导出对话分析结果失败: {str(e)}")

    def center_window(self):
        """将窗口居中显示"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.parent.winfo_width() - width) // 2 + self.parent.winfo_x()
        y = (self.parent.winfo_height() - height) // 2 + self.parent.winfo_y()
        self.geometry(f"{width}x{height}+{x}+{y}")
