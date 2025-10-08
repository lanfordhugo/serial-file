"""
文件名称: app.py
内容摘要: GUI 主应用类 - 应用生命周期管理、视图切换、状态管理
当前版本: v1.4.1
作者: AI Assistant
创建日期: 2025-10-08
"""

import tkinter as tk
from typing import Optional, Dict, Any
import queue
import threading
import logging

from .theme import ThemeManager
from .mode_selection_view import ModeSelectionView
# send_panel 和 receive_panel 将在后续导入
# from .send_panel import SendPanel
# from .receive_panel import ReceivePanel

from ..utils.logger import register_extra_handler, unregister_extra_handler


class SerialTransferApp:
    """串口文件传输工具主应用"""
    
    def __init__(self, root: tk.Tk):
        """
        初始化主应用
        
        Args:
            root: Tkinter 根窗口
        """
        self.root = root
        self.root.title("串口文件传输工具 v1.4.1")
        self.root.geometry("1100x800")
        self.root.resizable(True, True)
        self.root.minsize(900, 700)
        
        # 主题管理
        self.theme = ThemeManager()
        self.theme.apply_to_root(self.root)
        
        # 全局配置（跨界面保持）
        self.saved_config: Dict[str, Any] = {
            'baudrate': '2',  # 默认460800
            'port': None,
            'file_path': '',
            'recv_dir': 'received_files'
        }
        
        # 当前视图
        self.current_view = None
        
        # 日志队列
        self.log_queue: queue.Queue = queue.Queue()
        self.setup_logger()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 显示模式选择
        self.show_mode_selection()
    
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
        
        # 添加到日志器
        self.logger.addHandler(self.queue_handler)
        self.serial_logger.addHandler(self.queue_handler)
        
        # 注册到全局日志系统
        register_extra_handler(self.queue_handler)
    
    def show_mode_selection(self) -> None:
        """显示模式选择视图"""
        self.clear_current_view()
        self.current_view = ModeSelectionView(
            self.root,
            self.theme,
            on_send_clicked=self.show_send_panel,
            on_receive_clicked=self.show_receive_panel
        )
    
    def show_send_panel(self) -> None:
        """显示发送面板"""
        self.clear_current_view()
        # 导入延迟到使用时，避免循环依赖
        from .send_panel import SendPanel
        self.current_view = SendPanel(
            self.root,
            self.theme,
            self.saved_config,
            self.log_queue,
            on_back=self.show_mode_selection
        )
    
    def show_receive_panel(self) -> None:
        """显示接收面板"""
        self.clear_current_view()
        # 导入延迟到使用时，避免循环依赖
        from .receive_panel import ReceivePanel
        self.current_view = ReceivePanel(
            self.root,
            self.theme,
            self.saved_config,
            self.log_queue,
            on_back=self.show_mode_selection
        )
    
    def clear_current_view(self) -> None:
        """清空当前视图"""
        if self.current_view:
            self.current_view.destroy()
            self.current_view = None
        
        # 清空所有子组件
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def on_closing(self) -> None:
        """窗口关闭时的清理操作"""
        # 清理当前视图
        if self.current_view:
            self.current_view.destroy()
        
        # 注销全局日志处理器
        if hasattr(self, 'queue_handler'):
            unregister_extra_handler(self.queue_handler)
        
        # 关闭窗口
        self.root.destroy()

