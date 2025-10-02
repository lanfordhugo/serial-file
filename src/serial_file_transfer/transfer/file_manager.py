"""
批量文件管理模块
================

负责多个文件的批量发送和接收管理。
"""

import os
import time
from pathlib import Path
from typing import List, Optional, Union

from ..config.settings import TransferConfig
from ..config.constants import BatchTransferState
from ..core.serial_manager import SerialManager
from ..utils.logger import get_console_logger
from ..utils.path_utils import create_safe_path, ensure_directory_exists
from .sender import FileSender
from .receiver import FileReceiver

logger = get_console_logger(__name__)


class SenderFileManager:
    """发送端文件管理器"""

    def __init__(
        self,
        folder_path: Union[str, Path],
        serial_manager: SerialManager,
        config: Optional[TransferConfig] = None,
        progress_callback: Optional[callable] = None,
    ):
        """
        初始化发送端文件管理器

        Args:
            folder_path: 要发送的文件夹路径
            serial_manager: 串口管理器
            config: 传输配置（可选）
            progress_callback: 进度回调函数，签名为 callback(current, total)
        """
        self.folder_path = Path(folder_path)
        self.serial_manager = serial_manager
        self.config = config or TransferConfig()
        self.progress_callback = progress_callback

        self.file_list: List[str] = []
        self.sender = FileSender(serial_manager, config=config, progress_callback=progress_callback)

        # 扫描文件
        self._scan_files()

    def _scan_files(self) -> None:
        """递归扫描文件夹中的所有文件，保存相对路径"""
        try:
            if not self.folder_path.exists():
                logger.error(f"文件夹不存在: {self.folder_path}")
                return

            if not self.folder_path.is_dir():
                logger.error(f"路径不是文件夹: {self.folder_path}")
                return

            # 递归扫描所有文件，保存相对路径
            for file_path in self.folder_path.rglob("*"):
                if file_path.is_file():
                    # 计算相对于根文件夹的路径
                    relative_path = file_path.relative_to(self.folder_path)
                    # 使用正斜杠作为路径分隔符，确保跨平台兼容性
                    relative_path_str = str(relative_path).replace("\\", "/")
                    self.file_list.append(relative_path_str)

            # 添加结束标记
            self.file_list.append("")

            logger.info(f"发现 {len(self.file_list) - 1} 个文件待发送")
            logger.debug(f"文件列表: {self.file_list}")

        except Exception as e:
            logger.error(f"扫描文件夹失败: {e}")

    def get_next_filename(self) -> Optional[str]:
        """
        获取下一个要发送的文件名

        Returns:
            文件名，没有更多文件时返回空字符串，错误时返回None
        """
        if self.file_list:
            return self.file_list.pop(0)
        return None

    def start_batch_send(self) -> bool:
        """
        开始批量发送文件

        Returns:
            成功返回True，失败返回False
        """
        try:
            logger.info("开始批量文件发送...")

            while True:
                # 获取下一个文件名
                filename = self.get_next_filename()
                if filename is None:
                    logger.error("获取文件名失败")
                    return False

                logger.info(f"准备发送文件: [{filename}]")

                # 等待接收端请求文件名
                if not self.sender.wait_for_filename_request():
                    logger.error("等待文件名请求超时")
                    return False

                # 发送文件名
                if not self.sender.send_filename(filename):
                    logger.error("发送文件名失败")
                    return False

                # 如果文件名为空，表示发送完毕
                if filename == "":
                    logger.info("所有文件发送完毕")
                    return True

                # 初始化文件并开始传输
                # filename现在包含相对路径，需要转换为绝对路径
                file_path = self.folder_path / filename
                if not self.sender.init_file(file_path):
                    logger.error(f"初始化文件失败: {file_path}")
                    continue

                if not self.sender.start_transfer():
                    logger.error(f"文件传输失败: {filename}")
                    # 根据配置决定是否继续
                    continue

                logger.info(f"文件 [{filename}] 发送完成")

        except Exception as e:
            logger.error(f"批量发送异常: {e}")
            return False


class ReceiverFileManager:
    """接收端文件管理器"""

    def __init__(
        self,
        folder_path: Union[str, Path],
        serial_manager: SerialManager,
        config: Optional[TransferConfig] = None,
        progress_callback: Optional[callable] = None,
    ):
        """
        初始化接收端文件管理器

        Args:
            folder_path: 文件保存文件夹路径
            serial_manager: 串口管理器
            config: 传输配置（可选）
            progress_callback: 进度回调函数，签名为 callback(current, total)
        """
        self.folder_path = Path(folder_path)
        self.serial_manager = serial_manager
        self.config = config or TransferConfig()
        self.progress_callback = progress_callback

        self.receiver = FileReceiver(serial_manager, config=config, progress_callback=progress_callback)
        
        # 批量传输状态机
        self.state = BatchTransferState.IDLE
        self.current_filename: Optional[str] = None
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5

        # 创建保存文件夹
        self._create_folder()

    def _create_folder(self) -> None:
        """创建接收文件夹"""
        try:
            self.folder_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"接收文件夹: {self.folder_path}")
        except Exception as e:
            logger.error(f"创建接收文件夹失败: {e}")

    def _set_state(self, new_state: BatchTransferState, reason: str = "") -> None:
        """设置状态并记录日志"""
        if self.state != new_state:
            logger.debug(f"状态切换: {self.state.name} -> {new_state.name} {reason}")
            self.state = new_state

    def _request_filename(self) -> Optional[str]:
        """请求并接收文件名"""
        self._set_state(BatchTransferState.REQUESTING_NAME, "开始请求文件名")
        
        for attempt in range(3):  # 最多尝试3次
            if self.receiver.send_filename_request():
                filename = self.receiver.receive_filename()
                if filename is not None:
                    self.current_filename = filename
                    return filename
            
            logger.debug(f"获取文件名失败，第{attempt + 1}/3次尝试")
            time.sleep(0.2)
        
        return None

    def _transfer_single_file(self, filename: str) -> bool:
        """传输单个文件"""
        self._set_state(BatchTransferState.TRANSFERRING, f"开始传输文件: {filename}")
        
        # 设置保存路径并开始接收
        safe_path = create_safe_path(self.folder_path, filename)
        
        # 确保父目录存在
        if not ensure_directory_exists(safe_path.parent):
            logger.error(f"无法创建目录: {safe_path.parent}")
            return False
        
        self.receiver.init_receive_params(safe_path)
        
        # 执行文件传输
        return self.receiver.start_transfer()

    def start_batch_receive(self) -> bool:
        """
        开始批量接收文件

        使用状态机管理传输流程，依靠单次请求超时和重试机制

        Returns:
            成功返回True，失败返回False
        """
        try:
            logger.info("开始批量文件接收...")
            self._set_state(BatchTransferState.IDLE, "初始化批量接收")

            while self.state not in [BatchTransferState.COMPLETED, BatchTransferState.FAILED, BatchTransferState.TERMINATED]:
                # 1. 请求文件名
                filename = self._request_filename()
                
                if filename is None:
                    self.consecutive_failures += 1
                    logger.warning(f"获取文件名失败，连续失败次数: {self.consecutive_failures}")
                    
                    if self.consecutive_failures >= self.max_consecutive_failures:
                        logger.error(f"连续{self.max_consecutive_failures}次获取文件名失败")
                        self._set_state(BatchTransferState.FAILED, "连续失败次数过多")
                        break
                    
                    time.sleep(0.5)
                    continue
                
                # 2. 检查是否传输完毕
                if filename == "":
                    logger.info("所有文件接收完毕")
                    self._set_state(BatchTransferState.COMPLETED, "传输完成")
                    break
                
                # 3. 传输单个文件
                logger.info(f"开始接收文件: [{filename}]")
                success = self._transfer_single_file(filename)
                
                if success:
                    logger.info(f"文件 [{filename}] 接收完成")
                    self.consecutive_failures = 0  # 重置失败计数
                else:
                    logger.error(f"文件 [{filename}] 接收失败")
                    self.consecutive_failures += 1
                    
                    if self.consecutive_failures >= self.max_consecutive_failures:
                        logger.error(f"连续{self.max_consecutive_failures}次文件传输失败")
                        self._set_state(BatchTransferState.FAILED, "连续传输失败")
                        break
                    
                    logger.info("继续尝试接收下一个文件...")
            
            # 返回结果
            return self.state == BatchTransferState.COMPLETED

        except Exception as e:
            logger.error(f"批量接收异常: {e}")
            self._set_state(BatchTransferState.FAILED, f"异常: {e}")
            return False
