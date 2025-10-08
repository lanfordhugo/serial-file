"""
文件名称: send_panel.py
内容摘要: 发送面板 - 文件发送界面和逻辑
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
import logging

from .theme import ThemeManager
from .log_panel import LogPanel
from ..core.serial_manager import SerialManager
from ..config.settings import SerialConfig, TransferConfig
from ..config.config_loader import ConfigLoader
from ..transfer.sender import FileSender
from ..transfer.file_manager import SenderFileManager


class SendPanel:
    """发送面板 - UI + 发送逻辑"""
    
    def __init__(
        self,
        parent: tk.Tk,
        theme: ThemeManager,
        saved_config: Dict[str, Any],
        log_queue: queue.Queue,
        on_back: Callable[[], None]
    ):
        """
        初始化发送面板
        
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
        self.logger = logging.getLogger("serial_file_transfer.gui.send")
        
        # UI 组件引用
        self.container: Optional[tk.Frame] = None
        self.port_var: Optional[tk.StringVar] = None
        self.port_combo: Optional[ttk.Combobox] = None
        self.file_path_var: Optional[tk.StringVar] = None
        self.log_panel: Optional[LogPanel] = None
        
        # 传输状态
        self.is_transferring = False
        self.transfer_thread: Optional[threading.Thread] = None
        
        self._create_ui()
        self._refresh_ports()
    
    def _create_ui(self) -> None:
        """创建发送界面"""
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
        
        # 文件选择区域
        self._create_file_section()
        
        # 日志和控制区域
        self.log_panel = LogPanel(
            self.container,
            self.theme,
            self.log_queue,
            on_start=self._start_transfer,
            on_clear_log=self._clear_log,
            start_button_text="📤 发送文件",
            mode="send"
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
            text="📤 发送文件",
            font=("微软雅黑", 20, "bold"),
            fg=self.theme.colors.primary_color,
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
    
    def _create_file_section(self) -> None:
        """创建文件选择区域"""
        file_card = tk.Frame(self.container, bg=self.theme.colors.secondary_bg, relief="solid", bd=1)
        file_card.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        file_card.grid_configure(padx=2, pady=2)
        
        file_inner = tk.Frame(file_card, bg=self.theme.colors.secondary_bg)
        file_inner.pack(fill="both", expand=True, padx=15, pady=15)
        file_inner.columnconfigure(1, weight=1)
        
        tk.Label(
            file_inner, text="选择发送内容:", font=("微软雅黑", 12, "bold"),
            bg=self.theme.colors.secondary_bg, fg=self.theme.colors.text_color
        ).grid(row=0, column=0, sticky=tk.W, pady=12)
        
        path_frame = tk.Frame(file_inner, bg=self.theme.colors.secondary_bg)
        path_frame.grid(row=0, column=1, sticky="ew", pady=12)
        path_frame.columnconfigure(0, weight=1)
        
        self.file_path_var = tk.StringVar(value=self.config['file_path'])
        path_entry = tk.Entry(
            path_frame, textvariable=self.file_path_var,
            font=("微软雅黑", 11), relief="solid", bd=1
        )
        path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10), ipady=8)
        
        btn_frame = tk.Frame(path_frame, bg=self.theme.colors.secondary_bg)
        btn_frame.grid(row=0, column=1)
        
        file_btn = tk.Button(
            btn_frame, text="📄 选择文件", command=self._select_file,
            font=("微软雅黑", 11), bg="white", fg=self.theme.colors.text_color,
            relief="solid", bd=1, cursor="hand2", padx=15, pady=8
        )
        file_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        folder_btn = tk.Button(
            btn_frame, text="📁 选择文件夹", command=self._select_folder,
            font=("微软雅黑", 11), bg="white", fg=self.theme.colors.text_color,
            relief="solid", bd=1, cursor="hand2", padx=15, pady=8
        )
        folder_btn.pack(side=tk.LEFT)
    
    def _handle_back(self) -> None:
        """处理返回"""
        if self.is_transferring:
            messagebox.showwarning("警告", "传输正在进行中，请等待完成")
            return
        self.on_back()
    
    def _on_port_select(self, event) -> None:
        """串口选择事件"""
        if self.is_transferring:
            messagebox.showwarning("警告", "传输过程中无法修改串口配置")
            # 恢复之前的值
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
    
    def _select_file(self) -> None:
        """选择文件"""
        filename = filedialog.askopenfilename(title="选择要发送的文件")
        if filename:
            self.file_path_var.set(filename)
            self.config['file_path'] = filename
            self.logger.info(f"已选择文件: {filename}")
    
    def _select_folder(self) -> None:
        """选择文件夹"""
        folder = filedialog.askdirectory(title="选择要发送的文件夹")
        if folder:
            self.file_path_var.set(folder)
            self.config['file_path'] = folder
            
            # 列出文件夹第一层的文件
            folder_path = Path(folder)
            files = [f for f in folder_path.iterdir() if f.is_file()]
            file_count = len(files)
            
            self.logger.info(f"已选择文件夹: {folder}")
            if file_count > 0:
                display_files = files[:10]
                self.logger.info(f"  包含 {file_count} 个文件:")
                for idx, file in enumerate(display_files, 1):
                    self.logger.info(f"    {idx}. {file.name}")
                if file_count > 10:
                    self.logger.info(f"    ... 还有 {file_count - 10} 个文件未显示")
            else:
                self.logger.warning(f"  警告: 文件夹中没有文件")
    
    def _get_baudrate(self) -> int:
        """获取波特率"""
        baudrate_map = {"1": 115200, "2": 460800, "3": 921600, "4": 1728000}
        return baudrate_map.get(self.config['baudrate'], 460800)
    
    def _clear_log(self) -> None:
        """清空日志"""
        self.logger.info("日志已清空")
    
    def _start_transfer(self) -> None:
        """开始传输"""
        if self.is_transferring:
            messagebox.showwarning("警告", "传输正在进行中，请等待完成或停止当前传输")
            return
        
        port = self.config['port']
        if not port or port == "请选择串口...":
            messagebox.showerror("错误", "请选择串口")
            return
        
        # 验证串口可用性
        self.logger.info(f"正在验证串口 {port} 的可用性...")
        available, error_msg = SerialManager.test_port_availability(port, self._get_baudrate())
        if not available:
            self.logger.error(f"❌ 串口 {port} 验证失败: {error_msg}")
            messagebox.showerror(
                "串口不可用",
                f"无法开始发送，串口 {port} 不可用：\n\n{error_msg}\n\n请检查串口连接或关闭占用该串口的程序。"
            )
            return
        
        file_path = self.file_path_var.get()
        if not file_path:
            messagebox.showerror("错误", "请选择要发送的文件或文件夹")
            return
        if not Path(file_path).exists():
            messagebox.showerror("错误", f"文件或文件夹不存在: {file_path}")
            return
        
        # 更新UI状态
        self.is_transferring = True
        if self.log_panel:
            self.log_panel.set_button_state("disabled")
            self.log_panel.reset_progress()
            self.log_panel.update_status("传输中...", self.theme.colors.primary_color)
        
        # 在新线程中执行传输
        self.transfer_thread = threading.Thread(
            target=self._transfer_worker,
            daemon=True
        )
        self.transfer_thread.start()
    
    def _transfer_worker(self) -> None:
        """传输工作线程"""
        try:
            port = self.config['port']
            file_path = self.file_path_var.get()
            
            # 使用ConfigLoader加载配置
            serial_config = ConfigLoader.create_serial_config(port)
            transfer_config = ConfigLoader.create_transfer_config()
            
            # 使用用户指定波特率
            user_baudrate = self._get_baudrate()
            if serial_config.baudrate != user_baudrate:
                serial_config.baudrate = user_baudrate
                self.logger.info(f"使用用户指定波特率: {user_baudrate}")
            
            self.logger.info(f"开始传输 - 串口: {port}, 波特率: {serial_config.baudrate}")
            self.logger.info(f"传输参数 - 块大小: {transfer_config.max_data_length}, 超时: {transfer_config.request_timeout}s")
            
            serial_manager = SerialManager(serial_config)
            path_obj = Path(file_path)
            
            serial_manager.open()
            self.logger.info(f"串口已打开: {port}")
            
            success = True
            if path_obj.is_file():
                # 单文件传输
                self.logger.info(f"开始发送文件: {file_path}")
                
                sender = FileSender(
                    serial_manager,
                    file_path,
                    transfer_config,
                    progress_callback=self._progress_callback
                )
                
                self.logger.info("等待接收端请求文件名...")
                if not sender.wait_for_filename_request():
                    self.logger.error("❌ 等待文件名请求超时")
                    success = False
                else:
                    import os
                    filename = os.path.basename(file_path)
                    self.logger.info(f"发送文件名: {filename}")
                    if not sender.send_filename(filename):
                        self.logger.error("❌ 发送文件名失败")
                        success = False
                    else:
                        success = sender.start_transfer()
            
            elif path_obj.is_dir():
                # 文件夹传输
                self.logger.info(f"开始发送文件夹: {file_path}")
                
                file_manager = SenderFileManager(
                    folder_path=file_path,
                    serial_manager=serial_manager,
                    config=transfer_config,
                    progress_callback=self._progress_callback
                )
                
                success = file_manager.start_batch_send()
                
                if success:
                    self.logger.info("✅ 文件夹发送完成")
                else:
                    self.logger.error("❌ 文件夹发送失败")
            else:
                self.logger.error(f"路径无效: {file_path}")
                success = False
            
            serial_manager.close()
            
            if success:
                self.logger.info("✅ 传输完成")
                if self.log_panel:
                    self.parent.after(0, lambda: self.log_panel.update_status("传输成功", self.theme.colors.success_color))
                    self.parent.after(0, lambda: self.log_panel.progress_var.set(100))
                self.parent.after(0, lambda: messagebox.showinfo("成功", "文件传输完成！"))
            else:
                self.logger.error("❌ 传输失败")
                if self.log_panel:
                    self.parent.after(0, lambda: self.log_panel.update_status("传输失败", self.theme.colors.error_color))
                self.parent.after(0, lambda: messagebox.showerror("失败", "文件传输失败，请查看日志"))
        
        except Exception as e:
            error_msg = f"传输异常: {e}"
            self.logger.error(error_msg)
            if self.log_panel:
                self.parent.after(0, lambda: self.log_panel.update_status("传输异常", self.theme.colors.error_color))
            self.parent.after(0, lambda: messagebox.showerror("错误", f"传输过程发生异常:\n{e}"))
        
        finally:
            self.is_transferring = False
            if self.log_panel:
                self.parent.after(0, lambda: self.log_panel.set_button_state("normal"))
                self.parent.after(0, lambda: self.log_panel.update_status("就绪", self.theme.colors.text_secondary))
    
    def _progress_callback(self, current: int, total: int, status_text: str = "") -> None:
        """进度回调"""
        if self.log_panel:
            self.parent.after(0, lambda: self.log_panel.update_progress(current, total, status_text))
    
    def destroy(self) -> None:
        """销毁面板"""
        # 停止传输线程
        self.is_transferring = False
        if self.transfer_thread and self.transfer_thread.is_alive():
            self.transfer_thread.join(timeout=2.0)
        
        # 销毁UI
        if self.log_panel:
            self.log_panel.destroy()
        if self.container:
            self.container.destroy()

