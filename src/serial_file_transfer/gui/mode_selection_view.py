"""
文件名称: mode_selection_view.py
内容摘要: 模式选择视图 - 选择发送或接收模式
当前版本: v1.4.1
作者: AI Assistant
创建日期: 2025-10-08
"""

import tkinter as tk
from typing import Callable

from .theme import ThemeManager


class ModeSelectionView:
    """模式选择视图"""
    
    def __init__(
        self,
        parent: tk.Tk,
        theme: ThemeManager,
        on_send_clicked: Callable[[], None],
        on_receive_clicked: Callable[[], None],
        version: str = "v1.4.1"
    ):
        """
        初始化模式选择视图
        
        Args:
            parent: 父窗口
            theme: 主题管理器
            on_send_clicked: 发送按钮点击回调
            on_receive_clicked: 接收按钮点击回调
            version: 版本号
        """
        self.parent = parent
        self.theme = theme
        self.on_send_clicked = on_send_clicked
        self.on_receive_clicked = on_receive_clicked
        self.version = version
        
        self.container: tk.Frame = None
        
        self._create_ui()
    
    def _create_ui(self) -> None:
        """创建UI"""
        # 主容器
        self.container = tk.Frame(self.parent, bg=self.theme.colors.bg_color)
        self.container.place(relx=0.5, rely=0.5, anchor="center")
        
        # 大标题
        title_label = tk.Label(
            self.container,
            text="🚀 串口文件传输工具",
            font=("微软雅黑", 32, "bold"),
            fg=self.theme.colors.primary_color,
            bg=self.theme.colors.bg_color
        )
        title_label.pack(pady=(0, 20))
        
        # 副标题
        subtitle_label = tk.Label(
            self.container,
            text="请选择您要执行的操作模式",
            font=("微软雅黑", 14),
            fg=self.theme.colors.text_secondary,
            bg=self.theme.colors.bg_color
        )
        subtitle_label.pack(pady=(0, 50))
        
        # 按钮容器
        button_container = tk.Frame(self.container, bg=self.theme.colors.bg_color)
        button_container.pack()
        
        # 发送模式按钮
        send_btn = tk.Button(
            button_container,
            text="📤\n\n发送文件/文件夹\n\n适用于发送端设备",
            font=("微软雅黑", 16, "bold"),
            bg=self.theme.colors.primary_color,
            fg="white",
            activebackground=self.theme.colors.primary_hover,
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=self.on_send_clicked,
            width=20,
            height=8,
            bd=0
        )
        send_btn.pack(side=tk.LEFT, padx=20)
        
        # 发送按钮悬停效果
        def on_send_enter(e):
            send_btn.config(bg=self.theme.colors.primary_hover)
        
        def on_send_leave(e):
            send_btn.config(bg=self.theme.colors.primary_color)
        
        send_btn.bind("<Enter>", on_send_enter)
        send_btn.bind("<Leave>", on_send_leave)
        
        # 接收模式按钮
        receive_btn = tk.Button(
            button_container,
            text="📥\n\n接收文件\n\n适用于接收端设备",
            font=("微软雅黑", 16, "bold"),
            bg=self.theme.colors.success_color,
            fg="white",
            activebackground="#059669",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=self.on_receive_clicked,
            width=20,
            height=8,
            bd=0
        )
        receive_btn.pack(side=tk.LEFT, padx=20)
        
        # 接收按钮悬停效果
        def on_receive_enter(e):
            receive_btn.config(bg="#059669")
        
        def on_receive_leave(e):
            receive_btn.config(bg=self.theme.colors.success_color)
        
        receive_btn.bind("<Enter>", on_receive_enter)
        receive_btn.bind("<Leave>", on_receive_leave)
        
        # 版本信息
        version_label = tk.Label(
            self.container,
            text=self.version,
            font=("微软雅黑", 10),
            fg=self.theme.colors.text_secondary,
            bg=self.theme.colors.bg_color
        )
        version_label.pack(pady=(50, 0))
    
    def destroy(self) -> None:
        """销毁视图"""
        if self.container:
            self.container.destroy()
            self.container = None

