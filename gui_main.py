#!/usr/bin/env python3
"""
文件名称: gui_main.py
内容摘要: 串口文件传输工具 - 图形界面版本（三层架构）
当前版本: v1.4.0
作者: AI Assistant
创建日期: 2025-10-01
更新日期: 2025-10-01
说明: 采用模式选择 → 功能界面的三层架构，解决界面组件混合问题
"""

import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import threading
import queue
import time
from typing import Optional, Dict, Any

# 添加src路径到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from serial_file_transfer.core.serial_manager import SerialManager
from serial_file_transfer.config.settings import SerialConfig, TransferConfig
from serial_file_transfer.transfer.sender import FileSender
from serial_file_transfer.transfer.receiver import FileReceiver
import logging


class SerialTransferGUI:
    """串口文件传输工具 GUI 主应用类"""

    def __init__(self, root: tk.Tk) -> None:
        """初始化 GUI 主应用
        
        Args:
            root: Tkinter根窗口对象
        """
        self.root = root
        self.root.title("串口文件传输工具 v1.4.0")
        self.root.geometry("1100x800")
        self.root.resizable(True, True)
        self.root.minsize(900, 700)

        # 设置主题色 - 现代化配色方案
        self.bg_color = "#ffffff"
        self.secondary_bg = "#f5f7fa"
        self.primary_color = "#3b82f6"
        self.primary_hover = "#2563eb"
        self.success_color = "#10b981"
        self.warning_color = "#f59e0b"
        self.error_color = "#ef4444"
        self.text_color = "#1f2937"
        self.text_secondary = "#6b7280"
        
        # 配置根窗口背景
        self.root.configure(bg=self.bg_color)

        # 配置全局样式
        self.setup_styles()

        # 用户配置记忆（跨界面保持）
        self.saved_baudrate = "2"  # 默认460800
        self.saved_port = None
        self.saved_file_path = ""
        self.saved_recv_dir = "received_files"
        
        # 当前视图的UI组件引用（每次切换视图时重新创建）
        self.current_view_widgets: Dict[str, Any] = {}
        
        # 传输状态
        self.is_transferring = False
        self.transfer_thread: Optional[threading.Thread] = None
        
        # 日志系统（全局共享，但每个视图有独立的显示组件）
        self.log_queue: queue.Queue = queue.Queue()
        self.setup_logger()
        
        # 日志更新定时器ID
        self.log_update_timer: Optional[str] = None

        # 显示模式选择界面
        self.show_mode_selection()

    def setup_styles(self) -> None:
        """配置全局TTK样式"""
        style = ttk.Style()
        style.theme_use("clam")

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
        
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", "white")],
            selectbackground=[("readonly", self.primary_color)],
            selectforeground=[("readonly", "white")]
        )
        
        # 配置下拉列表样式
        self.root.option_add("*TCombobox*Listbox.font", ("微软雅黑", 11))
        self.root.option_add("*TCombobox*Listbox.background", "white")
        self.root.option_add("*TCombobox*Listbox.foreground", self.text_color)
        self.root.option_add("*TCombobox*Listbox.selectBackground", self.primary_color)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "white")

    def setup_logger(self) -> None:
        """设置日志记录器"""
        class QueueHandler(logging.Handler):
            """自定义日志处理器，将日志发送到队列"""
            def __init__(self, log_queue: queue.Queue):
                super().__init__()
                self.log_queue = log_queue

            def emit(self, record: logging.LogRecord) -> None:
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

    # ==================== 视图切换核心方法 ====================
    
    def clear_current_view(self) -> None:
        """清空当前视图的所有组件"""
        # 停止日志更新定时器
        if self.log_update_timer:
            self.root.after_cancel(self.log_update_timer)
            self.log_update_timer = None
        
        # 销毁所有子组件
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 清空组件引用
        self.current_view_widgets.clear()
    
    def show_mode_selection(self) -> None:
        """显示模式选择界面"""
        # 如果正在传输，禁止返回
        if self.is_transferring:
            messagebox.showwarning("警告", "传输正在进行中，请等待完成或停止当前传输")
            return
            
        self.clear_current_view()
        
        # 主容器
        main_container = tk.Frame(self.root, bg=self.bg_color)
        main_container.place(relx=0.5, rely=0.5, anchor="center")
        
        # 大标题
        title_label = tk.Label(
            main_container,
            text="🚀 串口文件传输工具",
            font=("微软雅黑", 32, "bold"),
            fg=self.primary_color,
            bg=self.bg_color
        )
        title_label.pack(pady=(0, 20))
        
        # 副标题
        subtitle_label = tk.Label(
            main_container,
            text="请选择您要执行的操作模式",
            font=("微软雅黑", 14),
            fg=self.text_secondary,
            bg=self.bg_color
        )
        subtitle_label.pack(pady=(0, 50))
        
        # 按钮容器
        button_container = tk.Frame(main_container, bg=self.bg_color)
        button_container.pack()
        
        # 发送模式按钮
        send_btn = tk.Button(
            button_container,
            text="📤\n\n发送文件/文件夹\n\n适用于发送端设备",
            font=("微软雅黑", 16, "bold"),
            bg=self.primary_color,
            fg="white",
            activebackground=self.primary_hover,
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=self.show_send_view,
            width=20,
            height=8,
            bd=0
        )
        send_btn.pack(side=tk.LEFT, padx=20)
        
        # 鼠标悬停效果
        def on_enter(e):
            send_btn.config(bg=self.primary_hover)
        def on_leave(e):
            send_btn.config(bg=self.primary_color)
        send_btn.bind("<Enter>", on_enter)
        send_btn.bind("<Leave>", on_leave)
        
        # 接收模式按钮
        receive_btn = tk.Button(
            button_container,
            text="📥\n\n接收文件\n\n适用于接收端设备",
            font=("微软雅黑", 16, "bold"),
            bg=self.success_color,
            fg="white",
            activebackground="#059669",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=self.show_receive_view,
            width=20,
            height=8,
            bd=0
        )
        receive_btn.pack(side=tk.LEFT, padx=20)
        
        # 鼠标悬停效果
        def on_enter_recv(e):
            receive_btn.config(bg="#059669")
        def on_leave_recv(e):
            receive_btn.config(bg=self.success_color)
        receive_btn.bind("<Enter>", on_enter_recv)
        receive_btn.bind("<Leave>", on_leave_recv)
        
        # 版本信息
        version_label = tk.Label(
            main_container,
            text="v1.4.0",
            font=("微软雅黑", 10),
            fg=self.text_secondary,
            bg=self.bg_color
        )
        version_label.pack(pady=(50, 0))

    # ==================== 发送视图 ====================
    
    def show_send_view(self) -> None:
        """显示发送界面"""
        self.clear_current_view()
        
        # 主容器
        main_container = tk.Frame(self.root, bg=self.bg_color)
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_container.grid_configure(padx=20, pady=20)
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(3, weight=1)
        
        # 返回按钮和标题区域
        header_frame = tk.Frame(main_container, bg=self.bg_color)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        back_btn = tk.Button(
            header_frame,
            text="← 返回",
            font=("微软雅黑", 11),
            bg=self.secondary_bg,
            fg=self.text_color,
            activebackground=self.text_secondary,
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=self.show_mode_selection,
            padx=20,
            pady=8
        )
        back_btn.pack(side=tk.LEFT)
        
        title_label = tk.Label(
            header_frame,
            text="📤 发送文件",
            font=("微软雅黑", 20, "bold"),
            fg=self.primary_color,
            bg=self.bg_color
        )
        title_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # 配置区域
        self._create_send_config_section(main_container)
        
        # 文件选择区域
        self._create_send_file_section(main_container)
        
        # 日志和控制区域
        self._create_log_and_controls(main_container, "send")
        
        # 刷新串口列表
        self.refresh_ports_for_view("send")
        
        # 启动日志更新
        self.start_log_updates()
    
    def _create_send_config_section(self, parent: tk.Frame) -> None:
        """创建发送界面的配置区域"""
        config_card = tk.Frame(parent, bg=self.secondary_bg, relief="solid", bd=1)
        config_card.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        config_card.grid_configure(padx=2, pady=2)
        
        config_inner = tk.Frame(config_card, bg=self.secondary_bg)
        config_inner.pack(fill="both", expand=True, padx=15, pady=15)
        config_inner.columnconfigure(1, weight=1)
        
        # 波特率
        tk.Label(
            config_inner, text="波特率:", font=("微软雅黑", 12, "bold"),
            bg=self.secondary_bg, fg=self.text_color
        ).grid(row=0, column=0, sticky=tk.W, pady=12, padx=(0, 20))
        
        baud_frame = tk.Frame(config_inner, bg=self.secondary_bg)
        baud_frame.grid(row=0, column=1, sticky=tk.W, pady=12)
        
        # 波特率选项
        baud_options = [
            ("1", "115200", "⭐⭐⭐⭐⭐"),
            ("2", "460800", "⭐⭐⭐⭐⭐"),
            ("3", "921600", "⭐⭐⭐"),
            ("4", "1728000", "⭐⭐")
        ]
        
        # 波特率按钮字典
        baud_buttons = {}
        
        def select_baud(value: str) -> None:
            self.saved_baudrate = value
            for v, btn in baud_buttons.items():
                if v == value:
                    btn.config(bg=self.primary_color, fg="white", bd=2)
                else:
                    btn.config(bg="white", fg=self.text_color, bd=1)
        
        for value, rate, stars in baud_options:
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
                command=lambda v=value: select_baud(v)
            )
            btn.pack(side=tk.LEFT, padx=(0, 8))
            baud_buttons[value] = btn
        
        # 设置默认选中
        select_baud(self.saved_baudrate)
        
        # 串口
        tk.Label(
            config_inner, text="串口:", font=("微软雅黑", 12, "bold"),
            bg=self.secondary_bg, fg=self.text_color
        ).grid(row=1, column=0, sticky=tk.W, pady=12, padx=(0, 20))
        
        port_frame = tk.Frame(config_inner, bg=self.secondary_bg)
        port_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=12)
        port_frame.columnconfigure(0, weight=1)
        
        port_var = tk.StringVar(value=self.saved_port or "")
        port_combo = ttk.Combobox(
            port_frame, textvariable=port_var, state="readonly",
            font=("微软雅黑", 11), width=50, height=10
        )
        port_combo.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        self.current_view_widgets["port_var"] = port_var
        self.current_view_widgets["port_combo"] = port_combo
        
        refresh_btn = tk.Button(
            port_frame, text="🔄 刷新", command=lambda: self.refresh_ports_for_view("send"),
            font=("微软雅黑", 11), bg="white", fg=self.text_color,
            relief="solid", bd=1, cursor="hand2", padx=20, pady=8
        )
        refresh_btn.grid(row=0, column=1)
    
    def _create_send_file_section(self, parent: tk.Frame) -> None:
        """创建发送界面的文件选择区域"""
        file_card = tk.Frame(parent, bg=self.secondary_bg, relief="solid", bd=1)
        file_card.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
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
        
        file_path_var = tk.StringVar(value=self.saved_file_path)
        path_entry = tk.Entry(
            path_frame, textvariable=file_path_var,
            font=("微软雅黑", 11), relief="solid", bd=1
        )
        path_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10), ipady=8)
        
        self.current_view_widgets["file_path_var"] = file_path_var
        
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

    # ==================== 接收视图 ====================
    
    def show_receive_view(self) -> None:
        """显示接收界面"""
        self.clear_current_view()
        
        # 主容器
        main_container = tk.Frame(self.root, bg=self.bg_color)
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_container.grid_configure(padx=20, pady=20)
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(3, weight=1)
        
        # 返回按钮和标题区域
        header_frame = tk.Frame(main_container, bg=self.bg_color)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        back_btn = tk.Button(
            header_frame,
            text="← 返回",
            font=("微软雅黑", 11),
            bg=self.secondary_bg,
            fg=self.text_color,
            activebackground=self.text_secondary,
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=self.show_mode_selection,
            padx=20,
            pady=8
        )
        back_btn.pack(side=tk.LEFT)
        
        title_label = tk.Label(
            header_frame,
            text="📥 接收文件",
            font=("微软雅黑", 20, "bold"),
            fg=self.success_color,
            bg=self.bg_color
        )
        title_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # 配置区域
        self._create_receive_config_section(main_container)
        
        # 保存目录区域
        self._create_receive_dir_section(main_container)
        
        # 日志和控制区域
        self._create_log_and_controls(main_container, "receive")
        
        # 刷新串口列表
        self.refresh_ports_for_view("receive")
        
        # 启动日志更新
        self.start_log_updates()
    
    def _create_receive_config_section(self, parent: tk.Frame) -> None:
        """创建接收界面的配置区域"""
        config_card = tk.Frame(parent, bg=self.secondary_bg, relief="solid", bd=1)
        config_card.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        config_card.grid_configure(padx=2, pady=2)
        
        config_inner = tk.Frame(config_card, bg=self.secondary_bg)
        config_inner.pack(fill="both", expand=True, padx=15, pady=15)
        config_inner.columnconfigure(1, weight=1)
        
        # 波特率
        tk.Label(
            config_inner, text="波特率:", font=("微软雅黑", 12, "bold"),
            bg=self.secondary_bg, fg=self.text_color
        ).grid(row=0, column=0, sticky=tk.W, pady=12, padx=(0, 20))
        
        baud_frame = tk.Frame(config_inner, bg=self.secondary_bg)
        baud_frame.grid(row=0, column=1, sticky=tk.W, pady=12)
        
        # 波特率选项
        baud_options = [
            ("1", "115200", "⭐⭐⭐⭐⭐"),
            ("2", "460800", "⭐⭐⭐⭐⭐"),
            ("3", "921600", "⭐⭐⭐"),
            ("4", "1728000", "⭐⭐")
        ]
        
        # 波特率按钮字典
        baud_buttons = {}
        
        def select_baud(value: str) -> None:
            self.saved_baudrate = value
            for v, btn in baud_buttons.items():
                if v == value:
                    btn.config(bg=self.primary_color, fg="white", bd=2)
                else:
                    btn.config(bg="white", fg=self.text_color, bd=1)
        
        for value, rate, stars in baud_options:
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
                command=lambda v=value: select_baud(v)
            )
            btn.pack(side=tk.LEFT, padx=(0, 8))
            baud_buttons[value] = btn
        
        # 设置默认选中
        select_baud(self.saved_baudrate)
        
        # 串口
        tk.Label(
            config_inner, text="串口:", font=("微软雅黑", 12, "bold"),
            bg=self.secondary_bg, fg=self.text_color
        ).grid(row=1, column=0, sticky=tk.W, pady=12, padx=(0, 20))
        
        port_frame = tk.Frame(config_inner, bg=self.secondary_bg)
        port_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=12)
        port_frame.columnconfigure(0, weight=1)
        
        port_var = tk.StringVar(value=self.saved_port or "")
        port_combo = ttk.Combobox(
            port_frame, textvariable=port_var, state="readonly",
            font=("微软雅黑", 11), width=50, height=10
        )
        port_combo.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        self.current_view_widgets["port_var"] = port_var
        self.current_view_widgets["port_combo"] = port_combo
        
        refresh_btn = tk.Button(
            port_frame, text="🔄 刷新", command=lambda: self.refresh_ports_for_view("receive"),
            font=("微软雅黑", 11), bg="white", fg=self.text_color,
            relief="solid", bd=1, cursor="hand2", padx=20, pady=8
        )
        refresh_btn.grid(row=0, column=1)
    
    def _create_receive_dir_section(self, parent: tk.Frame) -> None:
        """创建接收界面的保存目录区域"""
        dir_card = tk.Frame(parent, bg=self.secondary_bg, relief="solid", bd=1)
        dir_card.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
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
        
        recv_dir_var = tk.StringVar(value=self.saved_recv_dir)
        dir_entry = tk.Entry(
            dir_frame, textvariable=recv_dir_var,
            font=("微软雅黑", 11), relief="solid", bd=1
        )
        dir_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10), ipady=8)
        
        self.current_view_widgets["recv_dir_var"] = recv_dir_var
        
        dir_btn = tk.Button(
            dir_frame, text="📂 选择目录", command=self.select_recv_dir,
            font=("微软雅黑", 11), bg="white", fg=self.text_color,
            relief="solid", bd=1, cursor="hand2", padx=20, pady=8
        )
        dir_btn.grid(row=0, column=1)

    # ==================== 日志和控制区域（通用） ====================
    
    def _create_log_and_controls(self, parent: tk.Frame, mode: str) -> None:
        """创建日志和控制按钮区域
        
        Args:
            parent: 父容器
            mode: 模式（send/receive）
        """
        # 日志区域
        log_card = tk.Frame(parent, bg=self.secondary_bg, relief="solid", bd=1)
        log_card.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 15))
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
        log_text = scrolledtext.ScrolledText(
            log_inner,
            wrap=tk.WORD,
            width=80,
            height=12,
            font=("Consolas", 10),
            bg="#1e1e1e",
            fg="#d4d4d4",
            relief="flat"
        )
        log_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置日志文本标签
        log_text.tag_config("INFO", foreground="#4EC9B0")
        log_text.tag_config("WARNING", foreground="#CE9178")
        log_text.tag_config("ERROR", foreground="#F48771")
        log_text.tag_config("DEBUG", foreground="#9CDCFE")
        
        self.current_view_widgets["log_text"] = log_text
        
        # 控制按钮区域
        control_frame = tk.Frame(parent, bg=self.bg_color)
        control_frame.grid(row=4, column=0, sticky=(tk.W, tk.E))
        control_frame.columnconfigure(0, weight=1)
        
        # 进度条和状态
        progress_frame = tk.Frame(control_frame, bg=self.bg_color)
        progress_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 12))
        progress_frame.columnconfigure(0, weight=1)
        
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(
            progress_frame,
            variable=progress_var,
            maximum=100,
            mode="determinate",
            length=400,
        )
        progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 15))
        
        status_label = tk.Label(
            progress_frame, text="就绪", font=("微软雅黑", 12),
            fg=self.text_secondary, bg=self.bg_color
        )
        status_label.grid(row=0, column=1)
        
        self.current_view_widgets["progress_var"] = progress_var
        self.current_view_widgets["progress_bar"] = progress_bar
        self.current_view_widgets["status_label"] = status_label
        
        # 按钮区域
        button_frame = tk.Frame(control_frame, bg=self.bg_color)
        button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        button_frame.columnconfigure(0, weight=1)
        
        # 开始按钮
        start_button = tk.Button(
            button_frame,
            text="▶️  开始传输",
            command=lambda: self.start_transfer(mode),
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
        start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 停止按钮
        stop_button = tk.Button(
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
        stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
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
        
        self.current_view_widgets["start_button"] = start_button
        self.current_view_widgets["stop_button"] = stop_button

    # ==================== 工具方法 ====================
    
    def refresh_ports_for_view(self, mode: str) -> None:
        """刷新当前视图的串口列表
        
        Args:
            mode: 模式（send/receive）
        """
        ports = SerialManager.list_available_ports()
        port_list = [f"{p['device']} - {p['description']}" for p in ports]

        if not port_list:
            port_list = ["未检测到串口"]

        port_combo = self.current_view_widgets.get("port_combo")
        if port_combo:
            port_combo["values"] = port_list
            if port_list and port_list[0] != "未检测到串口":
                # 如果有保存的串口，尝试恢复
                if self.saved_port and self.saved_port in [p.split(" - ")[0] for p in port_list]:
                    for idx, port in enumerate(port_list):
                        if port.startswith(self.saved_port):
                            port_combo.current(idx)
                            break
                else:
                    port_combo.current(0)
                    # 保存第一个串口
                    self.saved_port = port_list[0].split(" - ")[0]

        self.log_info(f"检测到 {len(ports)} 个串口")

    def select_file(self) -> None:
        """选择文件"""
        filename = filedialog.askopenfilename(title="选择要发送的文件")
        if filename:
            file_path_var = self.current_view_widgets.get("file_path_var")
            if file_path_var:
                file_path_var.set(filename)
                self.saved_file_path = filename
                self.log_info(f"已选择文件: {filename}")

    def select_folder(self) -> None:
        """选择文件夹"""
        folder = filedialog.askdirectory(title="选择要发送的文件夹")
        if folder:
            file_path_var = self.current_view_widgets.get("file_path_var")
            if file_path_var:
                file_path_var.set(folder)
                self.saved_file_path = folder
                self.log_info(f"已选择文件夹: {folder}")

    def select_recv_dir(self) -> None:
        """选择接收目录"""
        folder = filedialog.askdirectory(title="选择接收文件保存目录")
        if folder:
            recv_dir_var = self.current_view_widgets.get("recv_dir_var")
            if recv_dir_var:
                recv_dir_var.set(folder)
                self.saved_recv_dir = folder
                self.log_info(f"接收目录: {folder}")

    def get_baudrate(self) -> int:
        """获取选中的波特率"""
        baudrate_map = {
            "1": 115200,
            "2": 460800,
            "3": 921600,
            "4": 1728000
        }
        return baudrate_map.get(self.saved_baudrate, 460800)

    def get_block_size(self) -> int:
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

    def get_selected_port(self) -> Optional[str]:
        """获取选中的串口"""
        port_var = self.current_view_widgets.get("port_var")
        if not port_var:
            return None
        
        port_text = port_var.get()
        if not port_text or "未检测到串口" in port_text:
            return None
        
        # 提取串口号（COM3 - xxx => COM3）
        port = port_text.split(" - ")[0].strip()
        self.saved_port = port
        return port

    # ==================== 传输控制 ====================
    
    def start_transfer(self, mode: str) -> None:
        """开始传输
        
        Args:
            mode: 模式（send/receive）
        """
        # 验证输入
        if self.is_transferring:
            messagebox.showwarning("警告", "传输正在进行中，请等待完成或停止当前传输")
            return

        port = self.get_selected_port()
        if not port:
            messagebox.showerror("错误", "请选择串口")
            return

        if mode == "send":
            file_path_var = self.current_view_widgets.get("file_path_var")
            if not file_path_var:
                return
            file_path = file_path_var.get()
            if not file_path:
                messagebox.showerror("错误", "请选择要发送的文件或文件夹")
                return
            if not Path(file_path).exists():
                messagebox.showerror("错误", f"文件或文件夹不存在: {file_path}")
                return
        else:
            recv_dir_var = self.current_view_widgets.get("recv_dir_var")
            if not recv_dir_var:
                return
            recv_dir = recv_dir_var.get()
            if not recv_dir:
                messagebox.showerror("错误", "请选择接收文件保存目录")
                return

        # 更新UI状态
        self.is_transferring = True
        start_button = self.current_view_widgets.get("start_button")
        stop_button = self.current_view_widgets.get("stop_button")
        progress_var = self.current_view_widgets.get("progress_var")
        
        if start_button:
            start_button.config(state="disabled")
        if stop_button:
            stop_button.config(state="normal")
        if progress_var:
            progress_var.set(0)
        
        self.update_status("传输中...", self.primary_color)

        # 在新线程中执行传输
        self.transfer_thread = threading.Thread(
            target=self.transfer_worker, 
            args=(mode,), 
            daemon=True
        )
        self.transfer_thread.start()

    def transfer_worker(self, mode: str) -> None:
        """传输工作线程
        
        Args:
            mode: 模式（send/receive）
        """
        try:
            port = self.get_selected_port()
            baudrate = self.get_baudrate()
            block_size = self.get_block_size()

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
                file_path_var = self.current_view_widgets.get("file_path_var")
                if not file_path_var:
                    return
                file_path = file_path_var.get()
                
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
                    progress_var = self.current_view_widgets.get("progress_var")
                    if progress_var:
                        progress_var.set(100)
                    self.root.after(0, lambda: messagebox.showinfo("成功", "文件传输完成！"))
                else:
                    self.log_error("❌ 传输失败")
                    self.update_status("传输失败", self.error_color)
                    self.root.after(0, lambda: messagebox.showerror("失败", "文件传输失败，请查看日志"))

            else:
                # 接收文件
                recv_dir_var = self.current_view_widgets.get("recv_dir_var")
                if not recv_dir_var:
                    return
                recv_dir = Path(recv_dir_var.get())
                recv_dir.mkdir(parents=True, exist_ok=True)

                receiver = FileReceiver(serial_manager, transfer_config)

                serial_manager.open()
                self.log_info(f"串口已打开: {port}")
                self.log_info(f"等待接收文件到: {recv_dir}")

                success = receiver.start_transfer()

                serial_manager.close()

                if success:
                    self.log_info("✅ 接收完成")
                    self.update_status("接收成功", self.success_color)
                    progress_var = self.current_view_widgets.get("progress_var")
                    if progress_var:
                        progress_var.set(100)
                    self.root.after(0, lambda: messagebox.showinfo("成功", f"文件已保存到: {recv_dir}"))
                else:
                    self.log_error("❌ 接收失败")
                    self.update_status("接收失败", self.error_color)
                    self.root.after(0, lambda: messagebox.showerror("失败", "文件接收失败，请查看日志"))

        except Exception as e:
            self.log_error(f"传输异常: {e}")
            self.update_status("传输异常", self.error_color)
            self.root.after(0, lambda: messagebox.showerror("错误", f"传输过程发生异常:\n{e}"))

        finally:
            self.is_transferring = False
            self.root.after(0, self.reset_ui)

    def stop_transfer(self) -> None:
        """停止传输"""
        if self.is_transferring:
            self.log_warning("用户请求停止传输...")
            self.is_transferring = False
            # TODO: 添加中断传输的逻辑

    def reset_ui(self) -> None:
        """重置UI状态"""
        start_button = self.current_view_widgets.get("start_button")
        stop_button = self.current_view_widgets.get("stop_button")
        
        if start_button:
            start_button.config(state="normal")
        if stop_button:
            stop_button.config(state="disabled")
        
        if not self.is_transferring:
            self.update_status("就绪", self.text_secondary)

    def update_status(self, text: str, color: str) -> None:
        """更新状态标签"""
        status_label = self.current_view_widgets.get("status_label")
        if status_label:
            self.root.after(0, lambda: status_label.config(text=text, fg=color))

    # ==================== 日志系统 ====================
    
    def log_info(self, message: str) -> None:
        """记录信息日志"""
        self.logger.info(message)

    def log_warning(self, message: str) -> None:
        """记录警告日志"""
        self.logger.warning(message)

    def log_error(self, message: str) -> None:
        """记录错误日志"""
        self.logger.error(message)

    def start_log_updates(self) -> None:
        """启动日志更新"""
        self.update_logs()

    def update_logs(self) -> None:
        """更新日志显示"""
        log_text = self.current_view_widgets.get("log_text")
        if not log_text:
            return
        
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

                log_text.insert(tk.END, log_entry + "\n", tag)
                log_text.see(tk.END)
        except queue.Empty:
            pass

        # 每100ms更新一次
        self.log_update_timer = self.root.after(100, self.update_logs)

    def clear_log(self) -> None:
        """清空日志"""
        log_text = self.current_view_widgets.get("log_text")
        if log_text:
            log_text.delete(1.0, tk.END)
            self.log_info("日志已清空")


def main() -> None:
    """主函数"""
    root = tk.Tk()
    app = SerialTransferGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
