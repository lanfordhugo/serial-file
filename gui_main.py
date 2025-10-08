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
from enum import Enum

# 添加src路径到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from serial_file_transfer.core.serial_manager import SerialManager
from serial_file_transfer.config.settings import SerialConfig, TransferConfig
from serial_file_transfer.config.config_loader import ConfigLoader
from serial_file_transfer.transfer.sender import FileSender
from serial_file_transfer.transfer.receiver import FileReceiver
from serial_file_transfer.transfer.file_manager import SenderFileManager, ReceiverFileManager
from serial_file_transfer.utils.logger import register_extra_handler, unregister_extra_handler
import logging


class ReceiveUIState(Enum):
    """接收界面状态枚举"""
    READY = "就绪"
    CONFIGURING = "配置中"
    WAITING = "等待连接"
    RECEIVING = "正在接收"
    COMPLETED = "接收完成"
    FAILED = "监听失败"


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

        # 接收状态管理
        self.receive_state = ReceiveUIState.READY
        self.receive_thread: Optional[threading.Thread] = None
        self.receive_manager: Optional[ReceiverFileManager] = None
        
        # 进度跟踪
        self.current_progress = 0.0
        self.total_bytes = 0
        self.transferred_bytes = 0
        self.last_update_time = 0.0
        self.last_transferred_bytes = 0
        
        # 日志系统（全局共享，但每个视图有独立的显示组件）
        self.log_queue: queue.Queue = queue.Queue()
        self.setup_logger()
        
        # 日志更新定时器ID
        self.log_update_timer: Optional[str] = None

        # 绑定窗口关闭事件，确保清理资源
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

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

        # 配置根日志记录器和serial_file_transfer专用日志器
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)

        # 配置serial_file_transfer专用日志器
        self.serial_logger = logging.getLogger("serial_file_transfer")
        self.serial_logger.setLevel(logging.INFO)

        # 清除现有处理器
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        for handler in self.serial_logger.handlers[:]:
            self.serial_logger.removeHandler(handler)

        # 创建队列处理器
        self.queue_handler = QueueHandler(self.log_queue)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
        )
        self.queue_handler.setFormatter(formatter)
        
        # 添加到GUI层的日志器
        self.logger.addHandler(self.queue_handler)
        self.serial_logger.addHandler(self.queue_handler)
        
        # 【关键】注册到全局日志系统，让所有底层模块的日志也能进入UI
        # 这样FileSender/FileReceiver等模块的logger.info也会显示在GUI中
        register_extra_handler(self.queue_handler)

    # ==================== 视图切换核心方法 ====================
    
    def clear_current_view(self) -> None:
        """清空当前视图的所有组件"""
        # 停止日志更新定时器
        if self.log_update_timer:
            self.root.after_cancel(self.log_update_timer)
            self.log_update_timer = None

        # 停止接收监听线程
        self._stop_receive_monitoring()

        # 销毁所有子组件
        for widget in self.root.winfo_children():
            widget.destroy()

        # 清空组件引用
        self.current_view_widgets.clear()

    def _stop_receive_monitoring(self) -> None:
        """停止接收监听"""
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_state = ReceiveUIState.FAILED
            # 通知线程停止（通过设置状态）
            self.is_transferring = False
            self.receive_thread.join(timeout=2.0)
            self.log_info("接收监听已停止")

        self.receive_thread = None
        self.receive_manager = None
        self.receive_state = ReceiveUIState.READY

    def _start_receive_monitoring(self) -> None:
        """开始接收监听"""
        # 如果正在监听中，禁止重复启动
        if self.receive_thread and self.receive_thread.is_alive():
            messagebox.showwarning("警告", "监听已在进行中")
            return

        # 验证配置
        port = self.get_selected_port()
        if not port:
            messagebox.showerror("错误", "请选择串口")
            return

        recv_dir_var = self.current_view_widgets.get("recv_dir_var")
        if not recv_dir_var:
            return
        recv_dir = recv_dir_var.get()
        if not recv_dir:
            messagebox.showerror("错误", "请选择接收文件保存目录")
            return

        # 如果已有监听线程，先停止
        self._stop_receive_monitoring()

        # 更新UI状态
        start_button = self.current_view_widgets.get("start_button")
        if start_button:
            start_button.config(state="disabled", text="🔄 监听中...")

        self.receive_state = ReceiveUIState.WAITING
        self.update_status("🔄 等待连接中...", self.primary_color)

        # 在后台线程中启动接收监听
        self.receive_thread = threading.Thread(
            target=self._receive_monitor_worker,
            args=(port, Path(recv_dir)),
            daemon=True
        )
        self.receive_thread.start()

        self.log_info(f"开始监听串口 {port}，保存目录: {recv_dir}")

    def _receive_monitor_worker(self, port: str, save_path: Path) -> None:
        """接收监听工作线程"""
        try:
            # 创建串口配置
            serial_config = ConfigLoader.create_serial_config(port)
            transfer_config = ConfigLoader.create_transfer_config()

            # 如果用户选择了非默认波特率，覆盖配置文件设置
            user_baudrate = self.get_baudrate()
            if serial_config.baudrate != user_baudrate:
                serial_config.baudrate = user_baudrate
                self.log_info(f"使用用户指定波特率: {user_baudrate}")

            self.log_info(f"监听参数 - 串口: {port}, 波特率: {serial_config.baudrate}")

            # 创建串口管理器
            serial_manager = SerialManager(serial_config)
            serial_manager.open()
            self.log_info(f"串口已打开: {port}")

            # 创建接收管理器
            self.receive_manager = ReceiverFileManager(
                folder_path=save_path,
                serial_manager=serial_manager,
                config=transfer_config,
                progress_callback=self._get_progress_callback("receive")
            )

            # 启动批量接收（阻塞调用，会持续监听）
            self.log_info("📡 启动持续监听模式...")
            success = self.receive_manager.start_batch_receive()

            serial_manager.close()

            if success:
                self.receive_state = ReceiveUIState.COMPLETED
                self.log_info("✅ 接收完成")
                self.root.after(0, lambda: self.update_status("✅ 接收完成", self.success_color))
                self.root.after(0, lambda: messagebox.showinfo("成功", f"文件已保存到: {save_path}"))
            else:
                self.receive_state = ReceiveUIState.FAILED
                self.log_error("❌ 接收失败")
                self.root.after(0, lambda: self.update_status("❌ 监听失败", self.error_color))
                self.root.after(0, lambda: messagebox.showerror("失败", "文件接收失败，请查看日志"))

        except Exception as e:
            error_msg = f"监听异常: {e}"
            self.log_error(error_msg)
            self.receive_state = ReceiveUIState.FAILED
            self.root.after(0, lambda: self.update_status("❌ 监听失败", self.error_color))
            self.root.after(0, lambda msg=error_msg: messagebox.showerror("错误", f"监听过程发生异常:\n{msg}"))

        finally:
            # 重置UI状态
            self.root.after(0, self._reset_receive_ui)

    def _reset_receive_ui(self) -> None:
        """重置接收UI状态"""
        start_button = self.current_view_widgets.get("start_button")
        if start_button:
            start_button.config(state="normal", text="🔄 开始监听")

        # 重置接收状态
        if self.receive_state not in [ReceiveUIState.WAITING, ReceiveUIState.RECEIVING]:
            self.receive_state = ReceiveUIState.READY
            self.update_status("就绪", self.text_secondary)

    def _get_progress_callback(self, mode: str):
        """获取带模式参数的进度回调函数"""
        def progress_callback(current: int, total: int, status_text: str = ""):
            self.update_progress(current, total, status_text, mode)
        return progress_callback

    def show_mode_selection(self) -> None:
        """显示模式选择界面"""
        # 如果正在传输或接收监听，禁止返回
        if self.is_transferring or (self.receive_thread and self.receive_thread.is_alive()):
            messagebox.showwarning("警告", "传输或监听正在进行中，请等待完成")
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
        
        # 使用占位提示，提示用户选择串口
        port_var = tk.StringVar(value=self.saved_port or "请选择串口...")
        port_combo = ttk.Combobox(
            port_frame, textvariable=port_var, state="readonly",
            font=("微软雅黑", 11), width=50, height=10
        )
        port_combo.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))

        # 绑定串口选择事件，检查传输状态和串口可用性
        def on_port_select(event):
            if self.is_transferring:
                messagebox.showwarning("警告", "传输过程中无法修改串口配置")
                # 恢复之前的值
                if self.saved_port:
                    for idx, port in enumerate(port_combo["values"]):
                        if port.startswith(self.saved_port):
                            port_combo.current(idx)
                            break
                return

            # 获取选择的串口
            selected = port_var.get()
            if selected and "未检测到串口" not in selected and selected != "请选择串口...":
                port_name = selected.split(" - ")[0].strip()

                # 测试串口可用性
                self.log_info(f"正在测试串口 {port_name} 的可用性...")
                available, error_msg = self.test_port_availability(port_name)

                if available:
                    self.saved_port = port_name
                    self.log_info(f"✅ 串口 {port_name} 测试通过")
                    # 更新状态显示为正常
                    self.update_status("🔌 串口连接正常", self.success_color)
                else:
                    self.log_error(f"❌ 串口 {port_name} 不可用: {error_msg}")
                    # 弹出警告对话框
                    messagebox.showwarning("串口不可用", f"所选串口 {port_name} 不可用：\n\n{error_msg}\n\n请检查串口连接或关闭占用该串口的程序。")
                    # 重置为占位状态
                    port_var.set("请选择串口...")
                    self.update_status("请选择有效的串口", self.warning_color)

        port_combo.bind("<<ComboboxSelected>>", on_port_select)

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
            # 检查是否正在监听中
            if self.receive_thread and self.receive_thread.is_alive():
                messagebox.showwarning("警告", "监听过程中无法修改波特率配置")
                return

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

        # 使用占位提示，提示用户选择串口
        port_var = tk.StringVar(value=self.saved_port or "请选择串口...")
        port_combo = ttk.Combobox(
            port_frame, textvariable=port_var, state="readonly",
            font=("微软雅黑", 11), width=50, height=10
        )
        port_combo.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))

        # 绑定串口选择事件，检查监听状态和串口可用性
        def on_port_select(event):
            if self.receive_thread and self.receive_thread.is_alive():
                messagebox.showwarning("警告", "监听过程中无法修改串口配置")
                # 恢复之前的值
                if self.saved_port:
                    for idx, port in enumerate(port_combo["values"]):
                        if port.startswith(self.saved_port):
                            port_combo.current(idx)
                            break
                return

            # 获取选择的串口
            selected = port_var.get()
            if selected and "未检测到串口" not in selected and selected != "请选择串口...":
                port_name = selected.split(" - ")[0].strip()

                # 测试串口可用性
                self.log_info(f"正在测试串口 {port_name} 的可用性...")
                available, error_msg = self.test_port_availability(port_name)

                if available:
                    self.saved_port = port_name
                    self.log_info(f"✅ 串口 {port_name} 测试通过")
                    # 更新状态显示为正常
                    self.update_status("🔌 串口连接正常", self.success_color)
                else:
                    self.log_error(f"❌ 串口 {port_name} 不可用: {error_msg}")
                    # 弹出警告对话框
                    messagebox.showwarning("串口不可用", f"所选串口 {port_name} 不可用：\n\n{error_msg}\n\n请检查串口连接或关闭占用该串口的程序。")
                    # 重置为占位状态
                    port_var.set("请选择串口...")
                    self.update_status("请选择有效的串口", self.warning_color)

        port_combo.bind("<<ComboboxSelected>>", on_port_select)

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
        
        # 进度条和状态（现代化设计）
        progress_container = tk.Frame(control_frame, bg=self.bg_color)
        progress_container.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        progress_container.columnconfigure(0, weight=1)
        
        # 进度信息行（百分比 + 速度）
        info_frame = tk.Frame(progress_container, bg=self.bg_color)
        info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        info_frame.columnconfigure(1, weight=1)
        
        # 百分比标签（左侧）
        progress_percent_label = tk.Label(
            info_frame, text="0%", font=("微软雅黑", 11, "bold"),
            fg=self.text_color, bg=self.bg_color
        )
        progress_percent_label.grid(row=0, column=0, sticky=tk.W)
        
        # 速度标签（右侧）
        speed_label = tk.Label(
            info_frame, text="", font=("微软雅黑", 10),
            fg=self.text_secondary, bg=self.bg_color
        )
        speed_label.grid(row=0, column=2, sticky=tk.E)
        
        # 进度条（使用自定义样式）
        progress_var = tk.DoubleVar()
        
        # 配置绿色进度条样式
        style = ttk.Style()
        style.configure(
            "Green.Horizontal.TProgressbar",
            troughcolor=self.secondary_bg,
            background=self.success_color,
            borderwidth=0,
            thickness=20
        )
        
        progress_bar = ttk.Progressbar(
            progress_container,
            variable=progress_var,
            maximum=100,
            mode="determinate",
            style="Green.Horizontal.TProgressbar",
            length=400
        )
        progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 状态文本（传输量信息）
        status_label = tk.Label(
            progress_container, text="就绪", font=("微软雅黑", 10),
            fg=self.text_secondary, bg=self.bg_color
        )
        status_label.grid(row=2, column=0, sticky=tk.W)
        
        self.current_view_widgets["progress_var"] = progress_var
        self.current_view_widgets["progress_bar"] = progress_bar
        self.current_view_widgets["progress_percent_label"] = progress_percent_label
        self.current_view_widgets["speed_label"] = speed_label
        self.current_view_widgets["status_label"] = status_label
        
        # 按钮区域
        button_frame = tk.Frame(control_frame, bg=self.bg_color)
        button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        button_frame.columnconfigure(0, weight=1)
        
        # 开始按钮
        start_button_text = "📤 发送文件" if mode == "send" else "🔄 开始监听"
        start_button = tk.Button(
            button_frame,
            text=start_button_text,
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
        port_var = self.current_view_widgets.get("port_var")
        if port_combo and port_var:
            port_combo["values"] = port_list
            if port_list and port_list[0] != "未检测到串口":
                # 如果有保存的串口，尝试恢复
                if self.saved_port and self.saved_port in [p.split(" - ")[0] for p in port_list]:
                    for idx, port in enumerate(port_list):
                        if port.startswith(self.saved_port):
                            port_combo.current(idx)
                            break
                else:
                    # 没有保存的串口，保持占位提示状态
                    current_value = port_var.get()
                    if current_value == "请选择串口..." or not current_value:
                        # 保持占位状态，不自动选择
                        pass
                    else:
                        # 如果当前有其他值，尝试匹配
                        found = False
                        for idx, port in enumerate(port_list):
                            if port.split(" - ")[0] == current_value.split(" - ")[0]:
                                port_combo.current(idx)
                                found = True
                                break
                        if not found:
                            # 如果找不到匹配，重置为占位状态
                            port_var.set("请选择串口...")

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
                
                # 列出文件夹第一层的文件（最多10个）
                folder_path = Path(folder)
                files = [f for f in folder_path.iterdir() if f.is_file()]
                file_count = len(files)
                
                self.log_info(f"已选择文件夹: {folder}")
                
                if file_count > 0:
                    # 显示前10个文件
                    display_files = files[:10]
                    self.log_info(f"  包含 {file_count} 个文件:")
                    for idx, file in enumerate(display_files, 1):
                        self.log_info(f"    {idx}. {file.name}")
                    
                    # 如果超过10个，显示省略信息
                    if file_count > 10:
                        self.log_info(f"    ... 还有 {file_count - 10} 个文件未显示")
                else:
                    self.log_warning(f"  警告: 文件夹中没有文件")

    def select_recv_dir(self) -> None:
        """选择接收目录"""
        # 检查是否正在监听中
        if self.receive_thread and self.receive_thread.is_alive():
            messagebox.showwarning("警告", "监听过程中无法修改保存目录配置")
            return

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

    def get_selected_port(self) -> Optional[str]:
        """获取选中的串口"""
        port_var = self.current_view_widgets.get("port_var")
        if not port_var:
            return None

        port_text = port_var.get()
        if not port_text or "未检测到串口" in port_text or port_text == "请选择串口...":
            return None

        # 提取串口号（COM3 - xxx => COM3）
        port = port_text.split(" - ")[0].strip()
        self.saved_port = port
        return port

    def test_port_availability(self, port: str) -> tuple[bool, str]:
        """测试串口是否可用

        Args:
            port: 串口号（如COM3）

        Returns:
            tuple: (是否可用, 错误信息)
        """
        try:
            # 创建测试用的串口配置，使用当前波特率
            baudrate = self.get_baudrate()
            test_config = SerialConfig(port=port, baudrate=baudrate, timeout=1.0)

            # 创建SerialManager进行测试
            test_manager = SerialManager(test_config)

            # 尝试打开串口
            if test_manager.open():
                # 打开成功，立即关闭
                test_manager.close()
                return True, ""
            else:
                return False, "串口打开失败"

        except Exception as e:
            error_str = str(e)
            # 将技术错误转换为用户友好的提示
            if "Permission denied" in error_str or "Access is denied" in error_str:
                return False, "串口权限不足，可能被其他程序占用"
            elif "Device or resource busy" in error_str or "busy" in error_str:
                return False, "串口被其他程序占用"
            elif "No such file or directory" in error_str:
                return False, "串口设备不存在，请检查设备连接"
            elif "timeout" in error_str.lower():
                return False, "串口连接超时"
            else:
                return False, f"串口不可用: {error_str}"

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
            # 在发送前再次验证串口可用性
            self.log_info(f"正在验证串口 {port} 的可用性...")
            available, error_msg = self.test_port_availability(port)
            if not available:
                self.log_error(f"❌ 串口 {port} 验证失败: {error_msg}")
                messagebox.showerror("串口不可用",
                    f"无法开始发送，串口 {port} 不可用：\n\n{error_msg}\n\n请检查串口连接或关闭占用该串口的程序。")
                return

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
        elif mode == "receive":
            # 接收端：启动监听模式
            self._start_receive_monitoring()
            return

        # 更新UI状态
        self.is_transferring = True
        start_button = self.current_view_widgets.get("start_button")
        progress_var = self.current_view_widgets.get("progress_var")
        progress_percent_label = self.current_view_widgets.get("progress_percent_label")
        speed_label = self.current_view_widgets.get("speed_label")

        if start_button:
            start_button.config(state="disabled")
        if progress_var:
            progress_var.set(0)
        if progress_percent_label:
            progress_percent_label.config(text="0%")
        if speed_label:
            speed_label.config(text="")
        
        # 重置速度计算变量
        self.last_update_time = 0.0
        self.last_transferred_bytes = 0
        
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
            
            # 使用ConfigLoader加载配置（从config/transfer.yaml读取）
            serial_config = ConfigLoader.create_serial_config(port)
            transfer_config = ConfigLoader.create_transfer_config()
            
            # 如果用户选择了非默认波特率，覆盖配置文件设置
            user_baudrate = self.get_baudrate()
            if serial_config.baudrate != user_baudrate:
                serial_config.baudrate = user_baudrate
                self.log_info(f"使用用户指定波特率: {user_baudrate}")

            self.log_info(f"开始传输 - 模式: {mode}, 串口: {port}, 波特率: {serial_config.baudrate}")
            self.log_info(f"传输参数 - 块大小: {transfer_config.max_data_length}, 超时: {transfer_config.request_timeout}s")

            serial_manager = SerialManager(serial_config)

            if mode == "send":
                # 发送文件
                file_path_var = self.current_view_widgets.get("file_path_var")
                if not file_path_var:
                    return
                file_path = file_path_var.get()
                path_obj = Path(file_path)
                
                serial_manager.open()
                self.log_info(f"串口已打开: {port}")

                success = True
                if path_obj.is_file():
                    # 单文件传输 - 与CLI保持一致的流程
                    self.log_info(f"开始发送文件: {file_path}")
                    
                    # 创建FileSender时传入文件路径和进度回调
                    sender = FileSender(
                        serial_manager,
                        file_path,
                        transfer_config,
                        progress_callback=self._get_progress_callback("send")
                    )
                    
                    # 等待接收端请求文件名
                    self.log_info("等待接收端请求文件名...")
                    if not sender.wait_for_filename_request():
                        self.log_error("❌ 等待文件名请求超时")
                        success = False
                    else:
                        # 发送文件名（只发送文件名，不包含路径）
                        import os
                        filename = os.path.basename(file_path)
                        self.log_info(f"发送文件名: {filename}")
                        if not sender.send_filename(filename):
                            self.log_error("❌ 发送文件名失败")
                            success = False
                        else:
                            # 开始传输
                            success = sender.start_transfer()
                elif path_obj.is_dir():
                    # 文件夹传输 - 复用SenderFileManager
                    self.log_info(f"开始发送文件夹: {file_path}")
                    
                    # 使用SenderFileManager处理批量发送（与CLI保持一致）
                    file_manager = SenderFileManager(
                        folder_path=file_path,
                        serial_manager=serial_manager,
                        config=transfer_config,
                        progress_callback=self._get_progress_callback("send")
                    )
                    
                    # 批量发送会自动处理文件遍历、发送、进度等
                    success = file_manager.start_batch_send()
                    
                    if success:
                        self.log_info("✅ 文件夹发送完成")
                    else:
                        self.log_error("❌ 文件夹发送失败")
                else:
                    self.log_error(f"路径无效: {file_path}")
                    success = False

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

                serial_manager.open()
                self.log_info(f"串口已打开: {port}")
                self.log_info(f"等待接收文件到: {recv_dir}")
                
                # 使用ReceiverFileManager处理批量接收（与CLI保持一致）
                # 自动适配单文件和文件夹传输
                receiver_manager = ReceiverFileManager(
                    folder_path=recv_dir,
                    serial_manager=serial_manager,
                    config=transfer_config,
                    progress_callback=self._get_progress_callback("receive")
                )
                
                self.log_info("📡 启动统一批量接收模式（自动适配单文件/文件夹）")
                success = receiver_manager.start_batch_receive()

                serial_manager.close()

                if success:
                    self.log_info("✅ 接收完成")
                    self.update_status("接收成功", self.success_color)
                    progress_var = self.current_view_widgets.get("progress_var")
                    if progress_var:
                        progress_var.set(100)
                    
                    # 统计接收的文件
                    received_files = list(recv_dir.rglob("*"))
                    received_files = [f for f in received_files if f.is_file()]
                    file_count = len(received_files)
                    
                    self.log_info(f"📋 共接收 {file_count} 个文件")
                    self.root.after(0, lambda: messagebox.showinfo("成功", f"文件已保存到: {recv_dir}\n共接收 {file_count} 个文件"))
                else:
                    self.log_error("❌ 接收失败")
                    self.update_status("接收失败", self.error_color)
                    self.root.after(0, lambda: messagebox.showerror("失败", "文件接收失败，请查看日志"))

        except Exception as e:
            error_msg = f"传输异常: {e}"
            self.log_error(error_msg)
            self.update_status("传输异常", self.error_color)
            # 捕获异常消息到局部变量，避免闭包问题
            error_detail = str(e)
            def show_error():
                messagebox.showerror("错误", f"传输过程发生异常:\n{error_detail}")
            self.root.after(0, show_error)

        finally:
            self.is_transferring = False
            self.root.after(0, self.reset_ui)


    def reset_ui(self) -> None:
        """重置UI状态"""
        start_button = self.current_view_widgets.get("start_button")

        if start_button:
            start_button.config(state="normal")

        if not self.is_transferring:
            self.update_status("就绪", self.text_secondary)

    def update_status(self, text: str, color: str) -> None:
        """更新状态标签"""
        status_label = self.current_view_widgets.get("status_label")
        if status_label:
            self.root.after(0, lambda: status_label.config(text=text, fg=color))
    
    def update_progress(self, current: int, total: int, status_text: str = "", mode: str = "send") -> None:
        """更新进度条（现代化UI版本）

        Args:
            current: 当前进度值（字节数）
            total: 总进度值（字节数）
            status_text: 状态文本（可选）
            mode: 模式（send/receive）
        """
        if total <= 0:
            return
        
        import time
        
        progress_percent = min(100.0, (current / total) * 100)
        self.current_progress = progress_percent
        self.transferred_bytes = current
        self.total_bytes = total
        
        # 计算传输速度
        current_time = time.time()
        speed_text = ""
        if self.last_update_time > 0:
            time_diff = current_time - self.last_update_time
            if time_diff >= 0.5:  # 至少0.5秒更新一次速度
                bytes_diff = current - self.last_transferred_bytes
                if bytes_diff > 0:
                    speed_bytes_per_sec = bytes_diff / time_diff
                    speed_kb = speed_bytes_per_sec / 1024
                    if speed_kb >= 1024:
                        speed_mb = speed_kb / 1024
                        speed_text = f"{speed_mb:.2f} MB/s"
                    else:
                        speed_text = f"{speed_kb:.2f} KB/s"
                    self.last_update_time = current_time
                    self.last_transferred_bytes = current
        else:
            self.last_update_time = current_time
            self.last_transferred_bytes = current
        
        # 更新进度条
        progress_var = self.current_view_widgets.get("progress_var")
        if progress_var:
            self.root.after(0, lambda: progress_var.set(progress_percent))
        
        # 更新百分比标签
        progress_percent_label = self.current_view_widgets.get("progress_percent_label")
        if progress_percent_label:
            percent_text = f"{progress_percent:.1f}%"
            self.root.after(0, lambda: progress_percent_label.config(text=percent_text))
        
        # 更新速度标签
        speed_label = self.current_view_widgets.get("speed_label")
        if speed_label and speed_text:
            self.root.after(0, lambda st=speed_text: speed_label.config(text=st))
        
        # 更新状态文本（传输量信息）
        status_label = self.current_view_widgets.get("status_label")
        if status_label:
            if status_text:
                display_text = status_text
            else:
                # 计算并显示传输量
                current_mb = current / (1024 * 1024)
                total_mb = total / (1024 * 1024)
                if total_mb < 1:
                    # 小于1MB时显示KB
                    current_kb = current / 1024
                    total_kb = total / 1024
                    display_text = f"{current_kb:.1f} / {total_kb:.1f} KB"
                else:
                    display_text = f"{current_mb:.2f} / {total_mb:.2f} MB"
            self.root.after(0, lambda dt=display_text: status_label.config(text=dt))

        # 接收模式：更新接收状态
        if mode == "receive" and self.receive_state == ReceiveUIState.WAITING:
            self.receive_state = ReceiveUIState.RECEIVING
            self.root.after(0, lambda: self.update_status("📥 正在接收文件...", self.primary_color))

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

    def on_closing(self) -> None:
        """窗口关闭时的清理操作"""
        # 停止所有传输线程
        self.is_transferring = False
        self._stop_receive_monitoring()
        
        # 停止日志更新定时器
        if self.log_update_timer:
            self.root.after_cancel(self.log_update_timer)
            self.log_update_timer = None
        
        # 注销全局日志处理器
        if hasattr(self, 'queue_handler'):
            unregister_extra_handler(self.queue_handler)
        
        # 关闭窗口
        self.root.destroy()


def main() -> None:
    """主函数"""
    root = tk.Tk()
    app = SerialTransferGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
