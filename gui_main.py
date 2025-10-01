#!/usr/bin/env python3
"""
文件名称: gui_main.py
内容摘要: 串口文件传输工具 - 图形界面版本
当前版本: v1.0.0
作者: AI Assistant
创建日期: 2025-10-01
"""

import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import threading
import queue
import time

# 添加src路径到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from serial_file_transfer.core.serial_manager import SerialManager
from serial_file_transfer.config.settings import SerialConfig, TransferConfig
from serial_file_transfer.transfer.sender import FileSender
from serial_file_transfer.transfer.receiver import FileReceiver
from serial_file_transfer.utils.logger import setup_logger
import logging


class SerialTransferGUI:
    """串口文件传输工具 GUI 主界面"""

    def __init__(self, root):
        """初始化 GUI"""
        self.root = root
        self.root.title("串口文件传输工具 v1.4.0")
        self.root.geometry("1100x800")
        self.root.resizable(True, True)
        self.root.minsize(900, 700)

        # 设置主题色 - 更现代的配色
        self.bg_color = "#ffffff"
        self.secondary_bg = "#f5f7fa"
        self.primary_color = "#3b82f6"  # 更鲜艳的蓝色
        self.primary_hover = "#2563eb"
        self.success_color = "#10b981"
        self.warning_color = "#f59e0b"
        self.error_color = "#ef4444"
        self.text_color = "#1f2937"
        self.text_secondary = "#6b7280"
        
        # 配置根窗口背景
        self.root.configure(bg=self.bg_color)

        # 配置样式
        self.setup_styles()

        # 初始化变量
        self.mode_var = tk.StringVar(value="send")
        self.baudrate_var = tk.StringVar(value="2")  # 默认460800（选项2）
        self.port_var = tk.StringVar()
        self.file_path_var = tk.StringVar()
        self.recv_dir_var = tk.StringVar(value="received_files")
        
        # 波特率按钮引用（用于样式切换）
        self.baudrate_buttons = {}

        # 传输状态
        self.is_transferring = False
        self.transfer_thread = None
        self.log_queue = queue.Queue()

        # 设置日志
        self.setup_logger()

        # 创建界面
        self.create_widgets()

        # 刷新串口列表
        self.refresh_ports()

        # 启动日志更新
        self.update_logs()

    def setup_styles(self):
        """配置样式"""
        style = ttk.Style()
        style.theme_use("clam")

        # 配置标签框样式 - 更大的字体和边距
        style.configure(
            "TLabelframe",
            background=self.bg_color,
            borderwidth=0,
            relief="flat"
        )
        style.configure(
            "TLabelframe.Label",
            font=("微软雅黑", 12, "bold"),
            foreground=self.text_color,
            background=self.bg_color
        )

        # 配置标签样式
        style.configure(
            "TLabel",
            font=("微软雅黑", 11),
            background=self.bg_color,
            foreground=self.text_color
        )

        # 配置单选按钮样式
        style.configure(
            "TRadiobutton",
            font=("微软雅黑", 11),
            background=self.bg_color,
            foreground=self.text_color
        )

        # 配置按钮样式 - 更大的按钮
        style.configure(
            "Primary.TButton",
            font=("微软雅黑", 12, "bold"),
            padding=(20, 12),
            borderwidth=0,
            relief="flat"
        )
        style.configure(
            "Success.TButton",
            font=("微软雅黑", 12, "bold"),
            padding=(20, 12),
            borderwidth=0,
            relief="flat"
        )
        style.configure(
            "TButton",
            font=("微软雅黑", 11),
            padding=(15, 10),
            borderwidth=0,
            relief="flat"
        )

        # 配置下拉框样式
        style.configure(
            "TCombobox",
            font=("微软雅黑", 11),
            padding=10,
            fieldbackground="white",
            background="white",
            foreground=self.text_color,
            arrowcolor=self.primary_color,
            borderwidth=1,
            relief="solid"
        )
        
        # 配置下拉框下拉列表样式
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", "white")],
            selectbackground=[("readonly", self.primary_color)],
            selectforeground=[("readonly", "white")]
        )

        # 配置输入框样式
        style.configure(
            "TEntry",
            font=("微软雅黑", 11),
            padding=10,
            fieldbackground="white",
            borderwidth=1,
            relief="solid"
        )

    def setup_logger(self):
        """设置日志记录器"""
        # 创建自定义日志处理器，将日志发送到队列
        class QueueHandler(logging.Handler):
            def __init__(self, log_queue):
                super().__init__()
                self.log_queue = log_queue

            def emit(self, record):
                self.log_queue.put(self.format(record))

        # 配置根日志记录器
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)

        # 清除现有处理器
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # 添加队列处理器
        queue_handler = QueueHandler(self.log_queue)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
        )
        queue_handler.setFormatter(formatter)
        self.logger.addHandler(queue_handler)

    def create_widgets(self):
        """创建界面组件"""
        # 主容器 - 增加内边距
        main_container = tk.Frame(self.root, bg=self.bg_color)
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_container.grid_configure(padx=20, pady=20)

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(2, weight=1)

        # 1. 标题区域
        self.create_header(main_container)

        # 2. 模式选择区域（大按钮）
        self.create_mode_selector(main_container)

        # 3. 内容区域（根据模式显示不同内容）
        self.content_frame = tk.Frame(main_container, bg=self.bg_color)
        self.content_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(15, 0))
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(1, weight=1)

        # 创建发送和接收的界面（但只显示一个）
        self.create_send_interface()
        self.create_receive_interface()

        # 默认显示发送界面
        self.switch_mode("send")

    def create_header(self, parent):
        """创建标题区域"""
        header_frame = tk.Frame(parent, bg=self.bg_color)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 25))

        title_label = tk.Label(
            header_frame,
            text="🚀 串口文件传输工具",
            font=("微软雅黑", 26, "bold"),
            fg=self.primary_color,
            bg=self.bg_color
        )
        title_label.pack(side=tk.LEFT)
    
    def create_mode_selector(self, parent):
        """创建模式选择区域（大按钮）"""
        mode_frame = tk.Frame(parent, bg=self.bg_color)
        mode_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        mode_frame.columnconfigure(0, weight=1)
        mode_frame.columnconfigure(1, weight=1)
        
        # 发送模式按钮
        self.send_mode_btn = tk.Button(
            mode_frame,
            text="📤 发送文件/文件夹",
            font=("微软雅黑", 14, "bold"),
            bg=self.primary_color,
            fg="white",
            activebackground=self.primary_hover,
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=lambda: self.switch_mode("send"),
            height=2
        )
        self.send_mode_btn.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # 接收模式按钮
        self.receive_mode_btn = tk.Button(
            mode_frame,
            text="📥 接收文件",
            font=("微软雅黑", 14, "bold"),
            bg=self.secondary_bg,
            fg=self.text_color,
            activebackground=self.secondary_bg,
            activeforeground=self.text_color,
            relief="flat",
            cursor="hand2",
            command=lambda: self.switch_mode("receive"),
            height=2
        )
        self.receive_mode_btn.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
    
    def switch_mode(self, mode):
        """切换模式"""
        self.mode_var.set(mode)
        
        # 更新按钮样式
        if mode == "send":
            self.send_mode_btn.config(
                bg=self.primary_color,
                fg="white"
            )
            self.receive_mode_btn.config(
                bg=self.secondary_bg,
                fg=self.text_color
            )
            # 显示发送界面，隐藏接收界面
            self.send_frame.grid()
            self.receive_frame.grid_remove()
        else:
            self.send_mode_btn.config(
                bg=self.secondary_bg,
                fg=self.text_color
            )
            self.receive_mode_btn.config(
                bg=self.primary_color,
                fg="white"
            )
            # 显示接收界面，隐藏发送界面
            self.receive_frame.grid()
            self.send_frame.grid_remove()

    def create_send_interface(self):
        """创建发送界面"""
        self.send_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        self.send_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.send_frame.columnconfigure(0, weight=1)
        self.send_frame.rowconfigure(2, weight=1)
        
        # 配置区域
        config_card = tk.Frame(self.send_frame, bg=self.secondary_bg, relief="solid", bd=1)
        config_card.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        config_card.grid_configure(padx=2, pady=2)
        
        config_inner = tk.Frame(config_card, bg=self.secondary_bg)
        config_inner.pack(fill="both", expand=True, padx=15, pady=15)
        config_inner.columnconfigure(1, weight=1)
        
        # 波特率 - 使用按钮组样式
        tk.Label(
            config_inner, text="波特率:", font=("微软雅黑", 12, "bold"),
            bg=self.secondary_bg, fg=self.text_color
        ).grid(row=0, column=0, sticky=tk.W, pady=12, padx=(0, 20))
        
        baud_frame = tk.Frame(config_inner, bg=self.secondary_bg)
        baud_frame.grid(row=0, column=1, sticky=tk.W, pady=12)
        
        # 波特率选项配置
        baud_options = [
            ("1", "115200", "⭐⭐⭐⭐⭐"),
            ("2", "460800", "⭐⭐⭐⭐⭐"),
            ("3", "921600", "⭐⭐⭐"),
            ("4", "1728000", "⭐⭐")
        ]
        
        for idx, (value, rate, stars) in enumerate(baud_options):
            btn = tk.Button(
                baud_frame,
                text=f"{rate}\n{stars}",
                font=("微软雅黑", 10),
                bg="white",
                fg=self.text_color,
                activebackground=self.primary_color,
                activeforeground="white",
                relief="solid",
                bd=1,
                cursor="hand2",
                width=10,
                height=2,
                command=lambda v=value: self.select_baudrate(v)
            )
            btn.pack(side=tk.LEFT, padx=(0, 8))
            self.baudrate_buttons[f"send_{value}"] = btn
        
        # 设置默认选中样式
        self.update_baudrate_buttons("send")
        
        # 串口
        tk.Label(
            config_inner, text="串口:", font=("微软雅黑", 12, "bold"),
            bg=self.secondary_bg, fg=self.text_color
        ).grid(row=1, column=0, sticky=tk.W, pady=12, padx=(0, 20))
        
        port_frame = tk.Frame(config_inner, bg=self.secondary_bg)
        port_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=12)
        port_frame.columnconfigure(0, weight=1)
        
        self.send_port_combo = ttk.Combobox(
            port_frame, textvariable=self.port_var, state="readonly",
            font=("微软雅黑", 11), width=50, height=10
        )
        self.send_port_combo.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # 配置下拉列表的样式
        self.root.option_add("*TCombobox*Listbox.font", ("微软雅黑", 11))
        self.root.option_add("*TCombobox*Listbox.background", "white")
        self.root.option_add("*TCombobox*Listbox.foreground", self.text_color)
        self.root.option_add("*TCombobox*Listbox.selectBackground", self.primary_color)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "white")
        
        refresh_btn = tk.Button(
            port_frame, text="🔄 刷新", command=self.refresh_ports,
            font=("微软雅黑", 11), bg="white", fg=self.text_color,
            relief="solid", bd=1, cursor="hand2", padx=20, pady=8
        )
        refresh_btn.grid(row=0, column=1)
        
        # 文件选择
        file_card = tk.Frame(self.send_frame, bg=self.secondary_bg, relief="solid", bd=1)
        file_card.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        file_card.grid_configure(padx=2, pady=2)
        
        file_inner = tk.Frame(file_card, bg=self.secondary_bg)
        file_inner.pack(fill="both", expand=True, padx=15, pady=15)
        file_inner.columnconfigure(1, weight=1)
        
        tk.Label(
            file_inner, text="选择发送内容:", font=("微软雅黑", 12, "bold"),
            bg=self.secondary_bg, fg=self.text_color
        ).grid(row=0, column=0, sticky=tk.W, pady=12)
        
        path_frame = tk.Frame(file_inner, bg=self.secondary_bg)
        path_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=12)
        path_frame.columnconfigure(0, weight=1)
        
        path_entry = tk.Entry(
            path_frame, textvariable=self.file_path_var,
            font=("微软雅黑", 11), relief="solid", bd=1
        )
        path_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10), ipady=8)
        
        btn_frame = tk.Frame(path_frame, bg=self.secondary_bg)
        btn_frame.grid(row=0, column=1)
        
        file_btn = tk.Button(
            btn_frame, text="📄 选择文件", command=self.select_file,
            font=("微软雅黑", 11), bg="white", fg=self.text_color,
            relief="solid", bd=1, cursor="hand2", padx=15, pady=8
        )
        file_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        folder_btn = tk.Button(
            btn_frame, text="📁 选择文件夹", command=self.select_folder,
            font=("微软雅黑", 11), bg="white", fg=self.text_color,
            relief="solid", bd=1, cursor="hand2", padx=15, pady=8
        )
        folder_btn.pack(side=tk.LEFT)
        
        # 日志和控制按钮
        self.create_log_and_controls(self.send_frame)
    
    def create_receive_interface(self):
        """创建接收界面"""
        self.receive_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        self.receive_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.receive_frame.columnconfigure(0, weight=1)
        self.receive_frame.rowconfigure(2, weight=1)
        
        # 配置区域
        config_card = tk.Frame(self.receive_frame, bg=self.secondary_bg, relief="solid", bd=1)
        config_card.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        config_card.grid_configure(padx=2, pady=2)
        
        config_inner = tk.Frame(config_card, bg=self.secondary_bg)
        config_inner.pack(fill="both", expand=True, padx=15, pady=15)
        config_inner.columnconfigure(1, weight=1)
        
        # 波特率 - 使用按钮组样式
        tk.Label(
            config_inner, text="波特率:", font=("微软雅黑", 12, "bold"),
            bg=self.secondary_bg, fg=self.text_color
        ).grid(row=0, column=0, sticky=tk.W, pady=12, padx=(0, 20))
        
        baud_frame = tk.Frame(config_inner, bg=self.secondary_bg)
        baud_frame.grid(row=0, column=1, sticky=tk.W, pady=12)
        
        # 波特率选项配置
        baud_options = [
            ("1", "115200", "⭐⭐⭐⭐⭐"),
            ("2", "460800", "⭐⭐⭐⭐⭐"),
            ("3", "921600", "⭐⭐⭐"),
            ("4", "1728000", "⭐⭐")
        ]
        
        for idx, (value, rate, stars) in enumerate(baud_options):
            btn = tk.Button(
                baud_frame,
                text=f"{rate}\n{stars}",
                font=("微软雅黑", 10),
                bg="white",
                fg=self.text_color,
                activebackground=self.primary_color,
                activeforeground="white",
                relief="solid",
                bd=1,
                cursor="hand2",
                width=10,
                height=2,
                command=lambda v=value: self.select_baudrate(v)
            )
            btn.pack(side=tk.LEFT, padx=(0, 8))
            self.baudrate_buttons[f"recv_{value}"] = btn
        
        # 设置默认选中样式
        self.update_baudrate_buttons("recv")
        
        # 串口
        tk.Label(
            config_inner, text="串口:", font=("微软雅黑", 12, "bold"),
            bg=self.secondary_bg, fg=self.text_color
        ).grid(row=1, column=0, sticky=tk.W, pady=12, padx=(0, 20))
        
        port_frame = tk.Frame(config_inner, bg=self.secondary_bg)
        port_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=12)
        port_frame.columnconfigure(0, weight=1)
        
        self.recv_port_combo = ttk.Combobox(
            port_frame, textvariable=self.port_var, state="readonly",
            font=("微软雅黑", 11), width=50, height=10
        )
        self.recv_port_combo.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        refresh_btn = tk.Button(
            port_frame, text="🔄 刷新", command=self.refresh_ports,
            font=("微软雅黑", 11), bg="white", fg=self.text_color,
            relief="solid", bd=1, cursor="hand2", padx=20, pady=8
        )
        refresh_btn.grid(row=0, column=1)
        
        # 接收目录选择
        dir_card = tk.Frame(self.receive_frame, bg=self.secondary_bg, relief="solid", bd=1)
        dir_card.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        dir_card.grid_configure(padx=2, pady=2)
        
        dir_inner = tk.Frame(dir_card, bg=self.secondary_bg)
        dir_inner.pack(fill="both", expand=True, padx=15, pady=15)
        dir_inner.columnconfigure(1, weight=1)
        
        tk.Label(
            dir_inner, text="保存目录:", font=("微软雅黑", 12, "bold"),
            bg=self.secondary_bg, fg=self.text_color
        ).grid(row=0, column=0, sticky=tk.W, pady=12)
        
        dir_frame = tk.Frame(dir_inner, bg=self.secondary_bg)
        dir_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=12)
        dir_frame.columnconfigure(0, weight=1)
        
        dir_entry = tk.Entry(
            dir_frame, textvariable=self.recv_dir_var,
            font=("微软雅黑", 11), relief="solid", bd=1
        )
        dir_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10), ipady=8)
        
        dir_btn = tk.Button(
            dir_frame, text="📂 选择目录", command=self.select_recv_dir,
            font=("微软雅黑", 11), bg="white", fg=self.text_color,
            relief="solid", bd=1, cursor="hand2", padx=20, pady=8
        )
        dir_btn.grid(row=0, column=1)
        
        # 日志和控制按钮
        self.create_log_and_controls(self.receive_frame)

    def create_log_and_controls(self, parent):
        """创建日志和控制按钮区域"""
        # 日志区域
        log_card = tk.Frame(parent, bg=self.secondary_bg, relief="solid", bd=1)
        log_card.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 15))
        log_card.grid_configure(padx=2, pady=2)
        
        log_inner = tk.Frame(log_card, bg=self.secondary_bg)
        log_inner.pack(fill="both", expand=True, padx=15, pady=15)
        log_inner.rowconfigure(1, weight=1)
        log_inner.columnconfigure(0, weight=1)
        
        tk.Label(
            log_inner, text="📋 传输日志", font=("微软雅黑", 12, "bold"),
            bg=self.secondary_bg, fg=self.text_color
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # 创建带滚动条的文本框
        self.log_text = scrolledtext.ScrolledText(
            log_inner,
            wrap=tk.WORD,
            width=80,
            height=12,
            font=("Consolas", 10),
            bg="#1e1e1e",
            fg="#d4d4d4",
            relief="flat"
        )
        self.log_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置日志文本标签
        self.log_text.tag_config("INFO", foreground="#4EC9B0")
        self.log_text.tag_config("WARNING", foreground="#CE9178")
        self.log_text.tag_config("ERROR", foreground="#F48771")
        self.log_text.tag_config("DEBUG", foreground="#9CDCFE")
        
        # 控制按钮区域
        control_frame = tk.Frame(parent, bg=self.bg_color)
        control_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        control_frame.columnconfigure(0, weight=1)
        
        # 进度条和状态
        progress_frame = tk.Frame(control_frame, bg=self.bg_color)
        progress_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 12))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
            length=400,
        )
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 15))
        
        self.status_label = tk.Label(
            progress_frame, text="就绪", font=("微软雅黑", 12),
            fg=self.text_secondary, bg=self.bg_color
        )
        self.status_label.grid(row=0, column=1)
        
        # 按钮区域
        button_frame = tk.Frame(control_frame, bg=self.bg_color)
        button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        button_frame.columnconfigure(0, weight=1)
        
        # 开始按钮
        self.start_button = tk.Button(
            button_frame,
            text="▶️  开始传输",
            command=self.start_transfer,
            font=("微软雅黑", 13, "bold"),
            bg=self.success_color,
            fg="white",
            activebackground="#059669",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            padx=40,
            pady=12
        )
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 停止按钮
        self.stop_button = tk.Button(
            button_frame,
            text="⏹️ 停止",
            command=self.stop_transfer,
            font=("微软雅黑", 12),
            bg=self.error_color,
            fg="white",
            activebackground="#dc2626",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            state="disabled",
            padx=30,
            pady=12
        )
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 清空日志按钮
        clear_button = tk.Button(
            button_frame,
            text="🗑️ 清空日志",
            command=self.clear_log,
            font=("微软雅黑", 11),
            bg="white",
            fg=self.text_color,
            activebackground=self.secondary_bg,
            activeforeground=self.text_color,
            relief="solid",
            bd=1,
            cursor="hand2",
            padx=25,
            pady=12
        )
        clear_button.pack(side=tk.LEFT)

    def refresh_ports(self):
        """刷新可用串口列表"""
        ports = SerialManager.list_available_ports()
        port_list = [f"{p['device']} - {p['description']}" for p in ports]

        if not port_list:
            port_list = ["未检测到串口"]

        # 更新发送端和接收端的下拉框
        self.send_port_combo["values"] = port_list
        self.recv_port_combo["values"] = port_list
        
        if port_list:
            self.send_port_combo.current(0)
            self.recv_port_combo.current(0)

        self.log_info(f"检测到 {len(ports)} 个串口")

    def select_file(self):
        """选择文件"""
        filename = filedialog.askopenfilename(title="选择要发送的文件")
        if filename:
            self.file_path_var.set(filename)
            self.log_info(f"已选择文件: {filename}")

    def select_folder(self):
        """选择文件夹"""
        folder = filedialog.askdirectory(title="选择要发送的文件夹")
        if folder:
            self.file_path_var.set(folder)
            self.log_info(f"已选择文件夹: {folder}")

    def select_recv_dir(self):
        """选择接收目录"""
        folder = filedialog.askdirectory(title="选择接收文件保存目录")
        if folder:
            self.recv_dir_var.set(folder)
            self.log_info(f"接收目录: {folder}")

    def select_baudrate(self, value):
        """选择波特率"""
        self.baudrate_var.set(value)
        # 更新当前模式的按钮样式
        mode = "send" if self.mode_var.get() == "send" else "recv"
        self.update_baudrate_buttons(mode)
    
    def update_baudrate_buttons(self, mode):
        """更新波特率按钮样式"""
        selected_value = self.baudrate_var.get()
        
        for key, btn in self.baudrate_buttons.items():
            if key.startswith(mode):
                value = key.split("_")[1]
                if value == selected_value:
                    # 选中样式
                    btn.config(
                        bg=self.primary_color,
                        fg="white",
                        relief="solid",
                        bd=2
                    )
                else:
                    # 未选中样式
                    btn.config(
                        bg="white",
                        fg=self.text_color,
                        relief="solid",
                        bd=1
                    )
    
    def get_baudrate(self):
        """获取选中的波特率"""
        baudrate_map = {
            "1": 115200,
            "2": 460800,
            "3": 921600,
            "4": 1728000
        }
        return baudrate_map.get(self.baudrate_var.get(), 460800)

    def get_block_size(self):
        """根据波特率获取推荐块长"""
        baudrate = self.get_baudrate()
        if baudrate == 115200:
            return 512
        elif baudrate == 460800:
            return 2048
        elif baudrate == 921600:
            return 512
        else:  # 1728000
            return 8192

    def get_selected_port(self):
        """获取选中的串口"""
        port_text = self.port_var.get()
        if not port_text or "未检测到串口" in port_text:
            return None
        # 提取串口号（COM3 - xxx => COM3）
        return port_text.split(" - ")[0].strip()

    def start_transfer(self):
        """开始传输"""
        # 验证输入
        if self.is_transferring:
            messagebox.showwarning("警告", "传输正在进行中，请等待完成或停止当前传输")
            return

        port = self.get_selected_port()
        if not port:
            messagebox.showerror("错误", "请选择串口")
            return

        mode = self.mode_var.get()

        if mode == "send":
            file_path = self.file_path_var.get()
            if not file_path:
                messagebox.showerror("错误", "请选择要发送的文件或文件夹")
                return
            if not Path(file_path).exists():
                messagebox.showerror("错误", f"文件或文件夹不存在: {file_path}")
                return
        else:
            recv_dir = self.recv_dir_var.get()
            if not recv_dir:
                messagebox.showerror("错误", "请选择接收文件保存目录")
                return

        # 更新UI状态
        self.is_transferring = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.progress_var.set(0)
        self.update_status("传输中...", self.primary_color)

        # 在新线程中执行传输
        self.transfer_thread = threading.Thread(target=self.transfer_worker, daemon=True)
        self.transfer_thread.start()

    def transfer_worker(self):
        """传输工作线程"""
        try:
            port = self.get_selected_port()
            baudrate = self.get_baudrate()
            block_size = self.get_block_size()
            mode = self.mode_var.get()

            self.log_info(f"开始传输 - 模式: {mode}, 串口: {port}, 波特率: {baudrate}")

            # 配置串口
            serial_config = SerialConfig(
                port=port, baudrate=baudrate, timeout=1.0
            )

            # 配置传输参数
            transfer_config = TransferConfig(
                max_data_length=block_size,
                request_timeout=2,
                retry_count=5,
                show_progress=False,
            )

            serial_manager = SerialManager(serial_config)

            if mode == "send":
                # 发送文件
                file_path = self.file_path_var.get()
                sender = FileSender(serial_manager, transfer_config)

                serial_manager.open()
                self.log_info(f"串口已打开: {port}")

                if Path(file_path).is_file():
                    # 单文件传输
                    self.log_info(f"开始发送文件: {file_path}")
                    success = sender.send_file(file_path)
                else:
                    # 文件夹传输
                    self.log_info(f"开始发送文件夹: {file_path}")
                    success = sender.send_folder(file_path)

                serial_manager.close()

                if success:
                    self.log_info("✅ 传输完成")
                    self.update_status("传输成功", self.success_color)
                    self.progress_var.set(100)
                    messagebox.showinfo("成功", "文件传输完成！")
                else:
                    self.log_error("❌ 传输失败")
                    self.update_status("传输失败", self.error_color)
                    messagebox.showerror("失败", "文件传输失败，请查看日志")

            else:
                # 接收文件
                recv_dir = Path(self.recv_dir_var.get())
                recv_dir.mkdir(parents=True, exist_ok=True)

                receiver = FileReceiver(serial_manager, transfer_config)

                serial_manager.open()
                self.log_info(f"串口已打开: {port}")
                self.log_info(f"等待接收文件到: {recv_dir}")

                # 这里需要实现接收逻辑
                # 暂时模拟接收
                self.log_info("接收端就绪，等待发送端连接...")
                success = receiver.start_transfer()

                serial_manager.close()

                if success:
                    self.log_info("✅ 接收完成")
                    self.update_status("接收成功", self.success_color)
                    self.progress_var.set(100)
                    messagebox.showinfo("成功", f"文件已保存到: {recv_dir}")
                else:
                    self.log_error("❌ 接收失败")
                    self.update_status("接收失败", self.error_color)
                    messagebox.showerror("失败", "文件接收失败，请查看日志")

        except Exception as e:
            self.log_error(f"传输异常: {e}")
            self.update_status("传输异常", self.error_color)
            messagebox.showerror("错误", f"传输过程发生异常:\n{e}")

        finally:
            self.is_transferring = False
            self.root.after(0, self.reset_ui)

    def stop_transfer(self):
        """停止传输"""
        if self.is_transferring:
            self.log_warning("用户请求停止传输...")
            self.is_transferring = False
            # 这里需要添加中断传输的逻辑

    def reset_ui(self):
        """重置UI状态"""
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        if not self.is_transferring:
            self.update_status("就绪", "#666666")

    def update_status(self, text, color):
        """更新状态标签"""
        self.root.after(0, lambda: self.status_label.config(text=text, fg=color))

    def log_info(self, message):
        """记录信息日志"""
        self.logger.info(message)

    def log_warning(self, message):
        """记录警告日志"""
        self.logger.warning(message)

    def log_error(self, message):
        """记录错误日志"""
        self.logger.error(message)

    def update_logs(self):
        """更新日志显示"""
        try:
            while True:
                log_entry = self.log_queue.get_nowait()
                # 提取日志级别
                if "[INFO]" in log_entry:
                    tag = "INFO"
                elif "[WARNING]" in log_entry:
                    tag = "WARNING"
                elif "[ERROR]" in log_entry:
                    tag = "ERROR"
                elif "[DEBUG]" in log_entry:
                    tag = "DEBUG"
                else:
                    tag = None

                self.log_text.insert(tk.END, log_entry + "\n", tag)
                self.log_text.see(tk.END)
        except queue.Empty:
            pass

        # 每100ms更新一次
        self.root.after(100, self.update_logs)

    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        self.log_info("日志已清空")


def main():
    """主函数"""
    root = tk.Tk()
    app = SerialTransferGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

