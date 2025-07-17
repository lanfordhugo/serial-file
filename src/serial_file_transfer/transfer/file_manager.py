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
from ..core.serial_manager import SerialManager
from ..utils.logger import get_logger
from .sender import FileSender
from .receiver import FileReceiver

logger = get_logger(__name__)


class SenderFileManager:
    """发送端文件管理器"""

    def __init__(
        self,
        folder_path: Union[str, Path],
        serial_manager: SerialManager,
        config: Optional[TransferConfig] = None,
    ):
        """
        初始化发送端文件管理器

        Args:
            folder_path: 要发送的文件夹路径
            serial_manager: 串口管理器
            config: 传输配置（可选）
        """
        self.folder_path = Path(folder_path)
        self.serial_manager = serial_manager
        self.config = config or TransferConfig()

        self.file_list: List[str] = []
        self.sender = FileSender(serial_manager, config=config)

        # 扫描文件
        self._scan_files()

    def _scan_files(self) -> None:
        """扫描文件夹中的所有文件"""
        try:
            if not self.folder_path.exists():
                logger.error(f"文件夹不存在: {self.folder_path}")
                return

            if not self.folder_path.is_dir():
                logger.error(f"路径不是文件夹: {self.folder_path}")
                return

            # 扫描所有文件
            for file_path in self.folder_path.iterdir():
                if file_path.is_file():
                    self.file_list.append(file_path.name)

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
    ):
        """
        初始化接收端文件管理器

        Args:
            folder_path: 文件保存文件夹路径
            serial_manager: 串口管理器
            config: 传输配置（可选）
        """
        self.folder_path = Path(folder_path)
        self.serial_manager = serial_manager
        self.config = config or TransferConfig()

        self.receiver = FileReceiver(serial_manager, config=config)

        # 创建保存文件夹
        self._create_folder()

    def _create_folder(self) -> None:
        """创建接收文件夹"""
        try:
            self.folder_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"接收文件夹: {self.folder_path}")
        except Exception as e:
            logger.error(f"创建接收文件夹失败: {e}")

    def start_batch_receive(self) -> bool:
        """
        开始批量接收文件

        Returns:
            成功返回True，失败返回False
        """
        try:
            logger.info("开始批量文件接收...")

            start_time = time.time()

            while True:
                # 检查总体超时
                if time.time() - start_time > self.config.request_timeout:
                    logger.error(f"批量接收总体超时: {self.config.request_timeout}秒")
                    return False

                # 请求文件名
                if not self.receiver.send_filename_request():
                    time.sleep(0.1)
                    continue

                # 接收文件名
                filename = self.receiver.receive_filename()
                if filename is None:
                    time.sleep(0.1)
                    continue

                # 如果文件名为空，表示接收完毕
                if filename == "":
                    logger.info("所有文件接收完毕")
                    return True

                logger.info(f"开始接收文件: [{filename}]")

                # 设置保存路径并开始接收
                save_path = self.folder_path / filename
                self.receiver.init_receive_params(save_path)

                if self.receiver.start_transfer():
                    logger.info(f"文件 [{filename}] 接收完成")
                else:
                    logger.error(f"文件 [{filename}] 接收失败")
                    # 根据配置决定是否继续
                    continue

        except Exception as e:
            logger.error(f"批量接收异常: {e}")
            return False
