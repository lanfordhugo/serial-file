"""
文件名称: theme.py
内容摘要: GUI 主题配置和样式管理
当前版本: v1.4.1
作者: AI Assistant
创建日期: 2025-10-08
"""

from dataclasses import dataclass
from tkinter import ttk
import tkinter as tk
from typing import Optional


@dataclass
class ThemeColors:
    """主题颜色配置"""
    
    bg_color: str = "#ffffff"
    secondary_bg: str = "#f5f7fa"
    primary_color: str = "#3b82f6"
    primary_hover: str = "#2563eb"
    success_color: str = "#10b981"
    warning_color: str = "#f59e0b"
    error_color: str = "#ef4444"
    text_color: str = "#1f2937"
    text_secondary: str = "#6b7280"


class ThemeManager:
    """主题管理器 - 管理 GUI 主题和样式"""
    
    def __init__(self, colors: Optional[ThemeColors] = None):
        """
        初始化主题管理器
        
        Args:
            colors: 主题颜色配置，默认使用标准配置
        """
        self.colors = colors or ThemeColors()
    
    def setup_ttk_styles(self, root: tk.Tk) -> None:
        """
        配置 TTK 样式
        
        Args:
            root: Tkinter 根窗口
        """
        style = ttk.Style()
        style.theme_use("clam")
        
        # 配置下拉框样式
        style.configure(
            "TCombobox",
            font=("微软雅黑", 11),
            padding=10,
            fieldbackground="white",
            background="white",
            foreground=self.colors.text_color,
            arrowcolor=self.colors.primary_color,
            borderwidth=1,
            relief="solid"
        )
        
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", "white")],
            selectbackground=[("readonly", self.colors.primary_color)],
            selectforeground=[("readonly", "white")]
        )
        
        # 配置下拉列表样式
        root.option_add("*TCombobox*Listbox.font", ("微软雅黑", 11))
        root.option_add("*TCombobox*Listbox.background", "white")
        root.option_add("*TCombobox*Listbox.foreground", self.colors.text_color)
        root.option_add("*TCombobox*Listbox.selectBackground", self.colors.primary_color)
        root.option_add("*TCombobox*Listbox.selectForeground", "white")
        
        # 配置绿色进度条样式
        style.configure(
            "Green.Horizontal.TProgressbar",
            troughcolor=self.colors.secondary_bg,
            background=self.colors.success_color,
            borderwidth=0,
            thickness=20
        )
    
    def apply_to_root(self, root: tk.Tk) -> None:
        """
        应用主题到根窗口
        
        Args:
            root: Tkinter 根窗口
        """
        root.configure(bg=self.colors.bg_color)
        self.setup_ttk_styles(root)

