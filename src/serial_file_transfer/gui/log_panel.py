"""
文件名称: log_panel.py
内容摘要: 可复用的日志面板组件（包含日志显示、进度条、控制按钮）
当前版本: v1.4.1
作者: AI Assistant
创建日期: 2025-10-08
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import queue
from typing import Callable, Optional

from .theme import ThemeManager
from ..utils.format_utils import format_transfer_speed, format_progress_text, calculate_transfer_speed
import time


class LogPanel:
    """日志面板组件 - 可复用于发送和接收界面"""
    
    def __init__(
        self,
        parent: tk.Frame,
        theme: ThemeManager,
        log_queue: queue.Queue,
        on_start: Callable[[], None],
        on_clear_log: Callable[[], None],
        start_button_text: str = "开始传输",
        mode: str = "send"
    ):
        """
        初始化日志面板
        
        Args:
            parent: 父容器
            theme: 主题管理器
            log_queue: 日志队列
            on_start: 开始按钮回调函数
            on_clear_log: 清空日志回调函数
            start_button_text: 开始按钮文本
            mode: 模式（send/receive）
        """
        self.parent = parent
        self.theme = theme
        self.log_queue = log_queue
        self.on_start = on_start
        self.on_clear_log = on_clear_log
        self.mode = mode
        
        # 组件引用
        self.log_text: Optional[scrolledtext.ScrolledText] = None
        self.progress_var: Optional[tk.DoubleVar] = None
        self.progress_bar: Optional[ttk.Progressbar] = None
        self.progress_percent_label: Optional[tk.Label] = None
        self.speed_label: Optional[tk.Label] = None
        self.status_label: Optional[tk.Label] = None
        self.start_button: Optional[tk.Button] = None
        
        # 日志更新定时器
        self.log_update_timer: Optional[str] = None
        
        # 进度跟踪（用于速度计算）
        self.last_update_time = 0.0
        self.last_transferred_bytes = 0
        
        self._create_ui(start_button_text)
        self._start_log_updates()
    
    def _create_ui(self, start_button_text: str) -> None:
        """创建UI"""
        # 日志区域
        log_card = tk.Frame(self.parent, bg=self.theme.colors.secondary_bg, relief="solid", bd=1)
        log_card.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 15))
        log_card.grid_configure(padx=2, pady=2)
        
        log_inner = tk.Frame(log_card, bg=self.theme.colors.secondary_bg)
        log_inner.pack(fill="both", expand=True, padx=15, pady=15)
        log_inner.rowconfigure(1, weight=1)
        log_inner.columnconfigure(0, weight=1)
        
        tk.Label(
            log_inner, text="📋 传输日志", font=("微软雅黑", 12, "bold"),
            bg=self.theme.colors.secondary_bg, fg=self.theme.colors.text_color
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
        control_frame = tk.Frame(self.parent, bg=self.theme.colors.bg_color)
        control_frame.grid(row=4, column=0, sticky=(tk.W, tk.E))
        control_frame.columnconfigure(0, weight=1)
        
        # 进度条和状态（现代化设计）
        progress_container = tk.Frame(control_frame, bg=self.theme.colors.bg_color)
        progress_container.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        progress_container.columnconfigure(0, weight=1)
        
        # 进度信息行（百分比 + 速度）
        info_frame = tk.Frame(progress_container, bg=self.theme.colors.bg_color)
        info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        info_frame.columnconfigure(1, weight=1)
        
        # 百分比标签（左侧）
        self.progress_percent_label = tk.Label(
            info_frame, text="0%", font=("微软雅黑", 11, "bold"),
            fg=self.theme.colors.text_color, bg=self.theme.colors.bg_color
        )
        self.progress_percent_label.grid(row=0, column=0, sticky=tk.W)
        
        # 速度标签（右侧）
        self.speed_label = tk.Label(
            info_frame, text="", font=("微软雅黑", 10),
            fg=self.theme.colors.text_secondary, bg=self.theme.colors.bg_color
        )
        self.speed_label.grid(row=0, column=2, sticky=tk.E)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_container,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
            style="Green.Horizontal.TProgressbar",
            length=400
        )
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 状态文本（传输量信息）
        self.status_label = tk.Label(
            progress_container, text="就绪", font=("微软雅黑", 10),
            fg=self.theme.colors.text_secondary, bg=self.theme.colors.bg_color
        )
        self.status_label.grid(row=2, column=0, sticky=tk.W)
        
        # 按钮区域
        button_frame = tk.Frame(control_frame, bg=self.theme.colors.bg_color)
        button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        button_frame.columnconfigure(0, weight=1)
        
        # 开始按钮
        self.start_button = tk.Button(
            button_frame,
            text=start_button_text,
            command=self.on_start,
            font=("微软雅黑", 13, "bold"),
            bg=self.theme.colors.success_color,
            fg="white",
            activebackground="#059669",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            padx=40,
            pady=12
        )
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 清空日志按钮
        clear_button = tk.Button(
            button_frame,
            text="🗑️ 清空日志",
            command=self._handle_clear_log,
            font=("微软雅黑", 11),
            bg="white",
            fg=self.theme.colors.text_color,
            activebackground=self.theme.colors.secondary_bg,
            activeforeground=self.theme.colors.text_color,
            relief="solid",
            bd=1,
            cursor="hand2",
            padx=25,
            pady=12
        )
        clear_button.pack(side=tk.LEFT)
    
    def _handle_clear_log(self) -> None:
        """处理清空日志"""
        if self.log_text:
            self.log_text.delete(1.0, tk.END)
        self.on_clear_log()
    
    def _start_log_updates(self) -> None:
        """启动日志更新"""
        self._update_logs()
    
    def _update_logs(self) -> None:
        """更新日志显示"""
        if not self.log_text:
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
                
                self.log_text.insert(tk.END, log_entry + "\n", tag)
                self.log_text.see(tk.END)
        except queue.Empty:
            pass
        
        # 每100ms更新一次
        self.log_update_timer = self.parent.after(100, self._update_logs)
    
    def update_progress(self, current: int, total: int, status_text: str = "") -> None:
        """
        更新进度条
        
        Args:
            current: 当前进度（字节数）
            total: 总进度（字节数）
            status_text: 状态文本（可选）
        """
        if total <= 0 or not self.progress_var:
            return
        
        progress_percent = min(100.0, (current / total) * 100)
        
        # 计算传输速度
        current_time = time.time()
        speed_text = ""
        if self.last_update_time > 0:
            time_diff = current_time - self.last_update_time
            if time_diff >= 0.5:  # 至少0.5秒更新一次速度
                speed_bytes_per_sec = calculate_transfer_speed(
                    current, self.last_transferred_bytes, time_diff
                )
                if speed_bytes_per_sec > 0:
                    speed_text = format_transfer_speed(speed_bytes_per_sec)
                    self.last_update_time = current_time
                    self.last_transferred_bytes = current
        else:
            self.last_update_time = current_time
            self.last_transferred_bytes = current
        
        # 更新进度条
        self.progress_var.set(progress_percent)
        
        # 更新百分比标签
        if self.progress_percent_label:
            self.progress_percent_label.config(text=f"{progress_percent:.1f}%")
        
        # 更新速度标签
        if self.speed_label and speed_text:
            self.speed_label.config(text=speed_text)
        
        # 更新状态文本
        if self.status_label:
            if status_text:
                display_text = status_text
            else:
                display_text = format_progress_text(current, total)
            self.status_label.config(text=display_text)
    
    def update_status(self, text: str, color: str) -> None:
        """
        更新状态文本
        
        Args:
            text: 状态文本
            color: 文本颜色
        """
        if self.status_label:
            self.status_label.config(text=text, fg=color)
    
    def set_button_state(self, state: str, text: Optional[str] = None) -> None:
        """
        设置开始按钮状态
        
        Args:
            state: 按钮状态（normal/disabled）
            text: 按钮文本（可选）
        """
        if self.start_button:
            self.start_button.config(state=state)
            if text:
                self.start_button.config(text=text)
    
    def reset_progress(self) -> None:
        """重置进度"""
        if self.progress_var:
            self.progress_var.set(0)
        if self.progress_percent_label:
            self.progress_percent_label.config(text="0%")
        if self.speed_label:
            self.speed_label.config(text="")
        self.last_update_time = 0.0
        self.last_transferred_bytes = 0
    
    def destroy(self) -> None:
        """销毁面板"""
        # 停止日志更新定时器
        if self.log_update_timer:
            self.parent.after_cancel(self.log_update_timer)
            self.log_update_timer = None

