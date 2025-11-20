"""
文件名称: receive_panel.py
内容摘要: 接收面板 - 文件接收界面和逻辑
当前版本: v1.4.1
作者: AI Assistant
创建日期: 2025-10-08
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading
import queue
from typing import Dict, Any, Optional, Callable
from enum import Enum
import logging

from .theme import ThemeManager
from .log_panel import LogPanel
from ..core.serial_manager import SerialManager
from ..config.settings import SerialConfig, TransferConfig
from ..config.config_loader import ConfigLoader
from ..transfer.file_manager import ReceiverFileManager


class ReceiveUIState(Enum):
    """接收界面状态枚举"""
    READY = "就绪"
    WAITING = "等待连接"
    RECEIVING = "正在接收"
    COMPLETED = "接收完成"
    FAILED = "监听失败"


class ReceivePanel:
    """接收面板 - UI + 接收逻辑"""
    
    def __init__(
        self,
        parent: tk.Tk,
        theme: ThemeManager,
        saved_config: Dict[str, Any],
        log_queue: queue.Queue,
        on_back: Callable[[], None]
    ):
        """
        初始化接收面板
        
        Args:
            parent: 父窗口
            theme: 主题管理器
            saved_config: 保存的配置
            log_queue: 日志队列
            on_back: 返回回调
        """
        self.parent = parent
        self.theme = theme
        self.config = saved_config
        self.log_queue = log_queue
        self.on_back = on_back
        
        # 日志记录器
        self.logger = logging.getLogger("serial_file_transfer.gui.receive")
        
        # UI 组件引用
        self.container: Optional[tk.Frame] = None
        self.port_var: Optional[tk.StringVar] = None
        self.port_combo: Optional[ttk.Combobox] = None
        self.recv_dir_var: Optional[tk.StringVar] = None
        self.log_panel: Optional[LogPanel] = None
        
        # 接收状态
        self.receive_state = ReceiveUIState.READY
        self.receive_thread: Optional[threading.Thread] = None
        self.receive_manager: Optional[ReceiverFileManager] = None
        self.cancel_event: Optional[threading.Event] = None
        
        self._create_ui()
        self._refresh_ports()
    
    def _create_ui(self) -> None:
        """创建接收界面"""
        # 主容器
        self.container = tk.Frame(self.parent, bg=self.theme.colors.bg_color)
        self.container.grid(row=0, column=0, sticky="nsew")
        
        self.parent.columnconfigure(0, weight=1)
        self.parent.rowconfigure(0, weight=1)
        self.container.columnconfigure(0, weight=1)
        self.container.rowconfigure(3, weight=1)
        
        # 返回按钮和标题
        self._create_header()
        
        # 配置区域
        self._create_config_section()
        
        # 保存目录区域
        self._create_dir_section()
        
        # 日志和控制区域
        self.log_panel = LogPanel(
            self.container,
            self.theme,
            self.log_queue,
            on_start=self._start_monitoring,
            on_clear_log=self._clear_log,
            start_button_text="🔄 开始监听",
            mode="receive",
            on_cancel=self._cancel_monitoring,
            cancel_button_text="⏹ 取消接收",
        )
    
    def _create_header(self) -> None:
        """创建头部区域"""
        header_frame = tk.Frame(self.container, bg=self.theme.colors.bg_color)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        
        back_btn = tk.Button(
            header_frame,
            text="← 返回",
            font=("微软雅黑", 11),
            bg=self.theme.colors.secondary_bg,
            fg=self.theme.colors.text_color,
            activebackground=self.theme.colors.text_secondary,
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=self._handle_back,
            padx=20,
            pady=8
        )
        back_btn.pack(side=tk.LEFT)
        
        title_label = tk.Label(
            header_frame,
            text="📥 接收文件",
            font=("微软雅黑", 20, "bold"),
            fg=self.theme.colors.success_color,
            bg=self.theme.colors.bg_color
        )
        title_label.pack(side=tk.LEFT, padx=(20, 0))
    
    def _create_config_section(self) -> None:
        """创建配置区域"""
        config_card = tk.Frame(self.container, bg=self.theme.colors.secondary_bg, relief="solid", bd=1)
        config_card.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        config_card.grid_configure(padx=2, pady=2)
        
        config_inner = tk.Frame(config_card, bg=self.theme.colors.secondary_bg)
        config_inner.pack(fill="both", expand=True, padx=15, pady=15)
        config_inner.columnconfigure(1, weight=1)
        
        # 波特率
        tk.Label(
            config_inner, text="波特率:", font=("微软雅黑", 12, "bold"),
            bg=self.theme.colors.secondary_bg, fg=self.theme.colors.text_color
        ).grid(row=0, column=0, sticky=tk.W, pady=12, padx=(0, 20))
        
        baud_frame = tk.Frame(config_inner, bg=self.theme.colors.secondary_bg)
        baud_frame.grid(row=0, column=1, sticky=tk.W, pady=12)
        
        # 波特率选项
        baud_options = [
            ("1", "115200", "⭐⭐⭐⭐⭐"),
            ("2", "460800", "⭐⭐⭐⭐⭐"),
            ("3", "921600", "⭐⭐⭐"),
            ("4", "1728000", "⭐⭐")
        ]
        
        baud_buttons = {}
        
        def select_baud(value: str) -> None:
            if self.receive_thread and self.receive_thread.is_alive():
                messagebox.showwarning("警告", "监听过程中无法修改波特率配置")
                return
            
            self.config['baudrate'] = value
            for v, btn in baud_buttons.items():
                if v == value:
                    btn.config(bg=self.theme.colors.primary_color, fg="white", bd=2)
                else:
                    btn.config(bg="white", fg=self.theme.colors.text_color, bd=1)
        
        for value, rate, stars in baud_options:
            btn = tk.Button(
                baud_frame,
                text=f"{rate}\n{stars}",
                font=("微软雅黑", 10),
                bg="white",
                fg=self.theme.colors.text_color,
                activebackground=self.theme.colors.primary_color,
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
        select_baud(self.config['baudrate'])
        
        # 串口
        tk.Label(
            config_inner, text="串口:", font=("微软雅黑", 12, "bold"),
            bg=self.theme.colors.secondary_bg, fg=self.theme.colors.text_color
        ).grid(row=1, column=0, sticky=tk.W, pady=12, padx=(0, 20))
        
        port_frame = tk.Frame(config_inner, bg=self.theme.colors.secondary_bg)
        port_frame.grid(row=1, column=1, sticky="ew", pady=12)
        port_frame.columnconfigure(0, weight=1)
        
        self.port_var = tk.StringVar(value=self.config['port'] or "请选择串口...")
        self.port_combo = ttk.Combobox(
            port_frame, textvariable=self.port_var, state="readonly",
            font=("微软雅黑", 11), width=50, height=10
        )
        self.port_combo.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.port_combo.bind("<<ComboboxSelected>>", self._on_port_select)
        
        refresh_btn = tk.Button(
            port_frame, text="🔄 刷新", command=self._refresh_ports,
            font=("微软雅黑", 11), bg="white", fg=self.theme.colors.text_color,
            relief="solid", bd=1, cursor="hand2", padx=20, pady=8
        )
        refresh_btn.grid(row=0, column=1)
    
    def _create_dir_section(self) -> None:
        """创建保存目录区域"""
        dir_card = tk.Frame(self.container, bg=self.theme.colors.secondary_bg, relief="solid", bd=1)
        dir_card.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        dir_card.grid_configure(padx=2, pady=2)
        
        dir_inner = tk.Frame(dir_card, bg=self.theme.colors.secondary_bg)
        dir_inner.pack(fill="both", expand=True, padx=15, pady=15)
        dir_inner.columnconfigure(1, weight=1)
        
        tk.Label(
            dir_inner, text="保存目录:", font=("微软雅黑", 12, "bold"),
            bg=self.theme.colors.secondary_bg, fg=self.theme.colors.text_color
        ).grid(row=0, column=0, sticky=tk.W, pady=12)
        
        dir_frame = tk.Frame(dir_inner, bg=self.theme.colors.secondary_bg)
        dir_frame.grid(row=0, column=1, sticky="ew", pady=12)
        dir_frame.columnconfigure(0, weight=1)
        
        self.recv_dir_var = tk.StringVar(value=self.config['recv_dir'])
        dir_entry = tk.Entry(
            dir_frame, textvariable=self.recv_dir_var,
            font=("微软雅黑", 11), relief="solid", bd=1
        )
        dir_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10), ipady=8)
        
        dir_btn = tk.Button(
            dir_frame, text="📂 选择目录", command=self._select_recv_dir,
            font=("微软雅黑", 11), bg="white", fg=self.theme.colors.text_color,
            relief="solid", bd=1, cursor="hand2", padx=20, pady=8
        )
        dir_btn.grid(row=0, column=1)
    
    def _handle_back(self) -> None:
        """处理返回"""
        if self.receive_thread and self.receive_thread.is_alive():
            messagebox.showwarning("警告", "监听正在进行中，请等待完成")
            return
        self._stop_monitoring()
        self.on_back()
    
    def _on_port_select(self, event) -> None:
        """串口选择事件"""
        if self.receive_thread and self.receive_thread.is_alive():
            messagebox.showwarning("警告", "监听过程中无法修改串口配置")
            if self.config['port']:
                for idx, port in enumerate(self.port_combo["values"]):
                    if port.startswith(self.config['port']):
                        self.port_combo.current(idx)
                        break
            return
        
        selected = self.port_var.get()
        if selected and "未检测到串口" not in selected and selected != "请选择串口...":
            port_name = selected.split(" - ")[0].strip()
            
            # 测试串口可用性
            self.logger.info(f"正在测试串口 {port_name} 的可用性...")
            available, error_msg = SerialManager.test_port_availability(
                port_name, self._get_baudrate()
            )
            
            if available:
                self.config['port'] = port_name
                self.logger.info(f"✅ 串口 {port_name} 测试通过")
                if self.log_panel:
                    self.log_panel.update_status("🔌 串口连接正常", self.theme.colors.success_color)
            else:
                self.logger.error(f"❌ 串口 {port_name} 不可用: {error_msg}")
                messagebox.showwarning(
                    "串口不可用",
                    f"所选串口 {port_name} 不可用：\n\n{error_msg}\n\n请检查串口连接或关闭占用该串口的程序。"
                )
                self.port_var.set("请选择串口...")
                if self.log_panel:
                    self.log_panel.update_status("请选择有效的串口", self.theme.colors.warning_color)
    
    def _refresh_ports(self) -> None:
        """刷新串口列表"""
        ports = SerialManager.list_available_ports()
        port_list = [f"{p['device']} - {p['description']}" for p in ports]
        
        if not port_list:
            port_list = ["未检测到串口"]
        
        if self.port_combo:
            self.port_combo["values"] = port_list
            if port_list and port_list[0] != "未检测到串口":
                if self.config['port'] and self.config['port'] in [p.split(" - ")[0] for p in port_list]:
                    for idx, port in enumerate(port_list):
                        if port.startswith(self.config['port']):
                            self.port_combo.current(idx)
                            break
        
        self.logger.info(f"检测到 {len(ports)} 个串口")
    
    def _select_recv_dir(self) -> None:
        """选择接收目录"""
        if self.receive_thread and self.receive_thread.is_alive():
            messagebox.showwarning("警告", "监听过程中无法修改保存目录配置")
            return
        
        folder = filedialog.askdirectory(title="选择接收文件保存目录")
        if folder:
            self.recv_dir_var.set(folder)
            self.config['recv_dir'] = folder
            self.logger.info(f"接收目录: {folder}")
    
    def _get_baudrate(self) -> int:
        """获取波特率"""
        baudrate_map = {"1": 115200, "2": 460800, "3": 921600, "4": 1728000}
        return baudrate_map.get(self.config['baudrate'], 460800)
    
    def _clear_log(self) -> None:
        """清空日志"""
        self.logger.info("日志已清空")
    
    def _start_monitoring(self) -> None:
        """开始监听"""
        if self.receive_thread and self.receive_thread.is_alive():
            messagebox.showwarning("警告", "监听已在进行中")
            return
        
        port = self.config['port']
        if not port or port == "请选择串口...":
            messagebox.showerror("错误", "请选择串口")
            return
        
        recv_dir = self.recv_dir_var.get()
        if not recv_dir:
            messagebox.showerror("错误", "请选择接收文件保存目录")
            return
        
        self.cancel_event = threading.Event()
        
        # 更新UI状态
        if self.log_panel:
            self.log_panel.set_button_state("disabled", "🔄 监听中...")
            self.log_panel.update_status("🔄 等待连接中...", self.theme.colors.primary_color)
        
        self.receive_state = ReceiveUIState.WAITING
        
        # 在后台线程中启动接收监听
        self.receive_thread = threading.Thread(
            target=self._receive_monitor_worker,
            args=(port, Path(recv_dir)),
            daemon=True
        )
        self.receive_thread.start()
        
        self.logger.info(f"开始监听串口 {port}，保存目录: {recv_dir}")

    def _cancel_monitoring(self) -> None:
        """取消监听"""
        if not (self.receive_thread and self.receive_thread.is_alive()):
            return
        if self.cancel_event:
            self.cancel_event.set()
        if self.log_panel:
            self.log_panel.update_status("监听取消中...", self.theme.colors.warning_color)
    
    def _receive_monitor_worker(self, port: str, save_path: Path) -> None:
        """接收监听工作线程"""
        try:
            # 创建串口配置
            serial_config = ConfigLoader.create_serial_config(port)
            transfer_config = ConfigLoader.create_transfer_config()
            
            # 使用用户指定波特率
            user_baudrate = self._get_baudrate()
            if serial_config.baudrate != user_baudrate:
                serial_config.baudrate = user_baudrate
                self.logger.info(f"使用用户指定波特率: {user_baudrate}")
            
            self.logger.info(f"监听参数 - 串口: {port}, 波特率: {serial_config.baudrate}")
            
            # 创建串口管理器
            serial_manager = SerialManager(serial_config)
            serial_manager.open()
            self.logger.info(f"串口已打开: {port}")
            
            # 创建接收管理器
            self.receive_manager = ReceiverFileManager(
                folder_path=save_path,
                serial_manager=serial_manager,
                config=transfer_config,
                progress_callback=self._progress_callback,
                cancel_event=self.cancel_event,
            )
            
            # 启动批量接收（阻塞调用）
            self.logger.info("📡 启动持续监听模式...")
            success = self.receive_manager.start_batch_receive()
            
            serial_manager.close()
            
            cancelled = self.cancel_event is not None and self.cancel_event.is_set()
            
            if success:
                self.receive_state = ReceiveUIState.COMPLETED
                self.logger.info("✅ 接收完成")
                self.parent.after(0, lambda: self.log_panel.update_status("✅ 接收完成", self.theme.colors.success_color))
                self.parent.after(0, lambda: messagebox.showinfo("成功", f"文件已保存到: {save_path}"))
            elif cancelled:
                self.receive_state = ReceiveUIState.FAILED
                self.logger.info("⚠ 接收已被用户取消")
                self.parent.after(0, lambda: self.log_panel.update_status("监听已取消", self.theme.colors.warning_color))
            else:
                self.receive_state = ReceiveUIState.FAILED
                self.logger.error("❌ 接收失败")
                self.parent.after(0, lambda: self.log_panel.update_status("❌ 监听失败", self.theme.colors.error_color))
                self.parent.after(0, lambda: messagebox.showerror("失败", "文件接收失败，请查看日志"))
        
        except Exception as e:
            error_msg = f"监听异常: {e}"
            self.logger.error(error_msg)
            self.receive_state = ReceiveUIState.FAILED
            self.parent.after(0, lambda: self.log_panel.update_status("❌ 监听失败", self.theme.colors.error_color))
            self.parent.after(0, lambda: messagebox.showerror("错误", f"监听过程发生异常:\n{e}"))
        
        finally:
            # 重置UI状态
            self.parent.after(0, self._reset_receive_ui)
    
    def _reset_receive_ui(self) -> None:
        """重置接收UI状态"""
        if self.log_panel:
            self.log_panel.set_button_state("normal", "🔄 开始监听")
        
        if self.receive_state not in [ReceiveUIState.WAITING, ReceiveUIState.RECEIVING]:
            self.receive_state = ReceiveUIState.READY
            if self.log_panel:
                self.log_panel.update_status("就绪", self.theme.colors.text_secondary)
    
    def _stop_monitoring(self) -> None:
        """停止接收监听"""
        if self.receive_thread and self.receive_thread.is_alive():
            if self.cancel_event:
                self.cancel_event.set()
            self.receive_state = ReceiveUIState.FAILED
            self.receive_thread.join(timeout=2.0)
            self.logger.info("接收监听已停止")
        
        self.receive_thread = None
        self.receive_manager = None
        self.receive_state = ReceiveUIState.READY
        self.cancel_event = None
    
    def _progress_callback(self, current: int, total: int, status_text: str = "") -> None:
        """进度回调"""
        if self.receive_state == ReceiveUIState.WAITING:
            self.receive_state = ReceiveUIState.RECEIVING
            self.parent.after(0, lambda: self.log_panel.update_status("📥 正在接收文件...", self.theme.colors.primary_color))
        
        if self.log_panel:
            self.parent.after(0, lambda: self.log_panel.update_progress(current, total, status_text))
    
    def destroy(self) -> None:
        """销毁面板"""
        # 停止监听线程
        self._stop_monitoring()
        
        # 销毁UI
        if self.log_panel:
            self.log_panel.destroy()
        if self.container:
            self.container.destroy()

