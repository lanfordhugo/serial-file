"""
文件接收模块
============

负责单个文件的接收逻辑。
"""

import os
import struct
import time
from pathlib import Path
from typing import Optional, Union

from ..config.constants import SerialCommand, VAL_REQUEST_FILE, MAX_FILE_NAME_LENGTH
from ..config.settings import TransferConfig
from ..core.frame_handler import FrameHandler
from ..core.serial_manager import SerialManager
from ..utils.logger import get_logger
from ..utils.progress import TransferProgressTracker, progress_bar, ProgressBar
from ..utils.retry import retry_call

logger = get_logger(__name__)


class FileReceiver:
    """文件接收器"""

    def __init__(
        self,
        serial_manager: SerialManager,
        save_path: Optional[Union[str, Path]] = None,
        config: Optional[TransferConfig] = None,
    ):
        """
        初始化文件接收器

        Args:
            serial_manager: 串口管理器
            save_path: 文件保存路径（可选）
            config: 传输配置（可选）
        """
        self.serial_manager = serial_manager
        self.config = config or TransferConfig()

        # 接收状态
        self.save_path = Path(save_path) if save_path else None
        self.file_size = 0
        self.recv_size = 0
        self.file_data = b""
        self._file_handle = None  # 流式写入句柄
        # 序号追踪
        self._expected_seq: int = 0

        # 进度条实例
        self.progress_bar: Optional[ProgressBar] = None

    def init_receive_params(self, save_path: Union[str, Path]) -> None:
        """
        初始化接收参数

        Args:
            save_path: 文件保存路径
        """
        self.save_path = Path(save_path)
        self.file_size = 0
        self.recv_size = 0
        self.file_data = b""

    def send_file_size_request(self) -> bool:
        """
        发送文件大小请求

        Returns:
            成功返回True，失败返回False
        """
        try:
            # 协议要求固定值0x55AA，占用2字节
            request_data = struct.pack("<H", VAL_REQUEST_FILE)
            frame = FrameHandler.pack_frame(
                SerialCommand.REQUEST_FILE_SIZE, request_data
            )

            if frame and self.serial_manager.write(frame):
                return True
            else:
                logger.error("发送文件大小请求失败")
                return False

        except Exception as e:
            logger.error(f"发送文件大小请求异常: {e}")
            return False

    def send_filename_request(self) -> bool:
        """
        发送文件名请求

        Returns:
            成功返回True，失败返回False
        """
        try:
            # 协议为了保持一致，这里也使用 0x55AA 作为占位符，两字节
            request_data = struct.pack("<H", VAL_REQUEST_FILE)
            frame = FrameHandler.pack_frame(
                SerialCommand.REQUEST_FILE_NAME, request_data
            )

            if frame and self.serial_manager.write(frame):
                return True
            else:
                logger.error("发送文件名请求失败")
                return False

        except Exception as e:
            logger.error(f"发送文件名请求异常: {e}")
            return False

    def receive_file_size(self) -> Optional[int]:
        """
        接收文件大小

        Returns:
            文件大小，失败时返回None
        """
        try:
            # 读取回复
            cmd, data = FrameHandler.read_frame(
                self.serial_manager.port,  # type: ignore[arg-type]
                6 + 4,  # 帧头+CRC+文件大小(4字节)
            )

            if cmd is None or data is None:
                return None

            if cmd != SerialCommand.REPLY_FILE_SIZE:
                logger.error(f"收到错误命令: {hex(cmd)}")
                return None

            # 解析文件大小
            self.file_size = int.from_bytes(data, byteorder="little")
            logger.info(f"接收到文件大小: {self.file_size / 1024:.2f} KB")
            return self.file_size

        except Exception as e:
            logger.error(f"接收文件大小异常: {e}")
            return None

    def receive_filename(self) -> Optional[str]:
        """
        接收文件名

        Returns:
            文件名，失败时返回None
        """
        try:
            # 读取回复
            cmd, data = FrameHandler.read_frame(
                self.serial_manager.port,  # type: ignore[arg-type]
                6 + MAX_FILE_NAME_LENGTH,  # 帧头+CRC+文件名
            )

            if cmd is None or data is None:
                return None

            if cmd != SerialCommand.REPLY_FILE_NAME:
                logger.error(f"收到错误命令: {hex(cmd)}")
                return None

            # 解析文件名
            filename_bytes = data.rstrip(b"\x00")
            filename = filename_bytes.decode("utf-8")
            logger.info(f"接收到文件名: [{filename}]")
            return filename

        except Exception as e:
            logger.error(f"接收文件名异常: {e}")
            return None

    def send_data_request(self, addr: int, length: int) -> bool:
        """
        发送数据请求

        Args:
            addr: 请求的起始地址
            length: 请求的数据长度

        Returns:
            成功返回True，失败返回False
        """
        try:
            request_data = struct.pack("<IH", addr, length)
            frame = FrameHandler.pack_frame(SerialCommand.REQUEST_DATA, request_data)

            if frame and self.serial_manager.write(frame):
                return True
            else:
                logger.error("发送数据请求失败")
                return False

        except Exception as e:
            logger.error(f"发送数据请求异常: {e}")
            return False

    def receive_data_package(self) -> bool:
        """
        接收数据包

        Returns:
            成功返回True，失败返回False
        """
        try:
            # 读取数据包
            cmd, data = FrameHandler.read_frame(
                self.serial_manager.port,  # type: ignore[arg-type]
                6 + self.config.max_data_length,  # 帧头+CRC+最大数据长度
            )

            if cmd is None or data is None:
                return False

            if cmd == SerialCommand.NACK:
                seq, corr_len = struct.unpack("<HH", data[:4])
                logger.warning(f"收到 NACK，调整块长 {corr_len}")
                self.config.max_data_length = corr_len
                return False  # 触发重试

            if cmd != SerialCommand.SEND_DATA:
                logger.error(f"收到错误命令: {hex(cmd)}")
                return False

            # 解析序号
            seq_id = struct.unpack("<H", data[:2])[0]
            payload = data[2:]

            # 发送ACK/NACK
            ack_cmd = (
                SerialCommand.ACK
                if seq_id == self._expected_seq
                else SerialCommand.NACK
            )
            ack_frame = FrameHandler.pack_frame(ack_cmd, struct.pack("<H", seq_id))
            if ack_frame:
                self.serial_manager.write(ack_frame)

            if ack_cmd == SerialCommand.NACK:
                logger.warning(f"收到序号 {seq_id} 与预期 {self._expected_seq} 不符，发送NACK")
                return False

            # 序号符合，保存数据
            self.recv_size += len(payload)

            if self._file_handle is not None:
                self._file_handle.write(payload)
            else:
                self.file_data += payload
            self._expected_seq = (self._expected_seq + 1) & 0xFFFF
            return True

        except Exception as e:
            logger.error(f"接收数据包异常: {e}")
            return False

    def _receive_chunk_with_retry(self, addr: int, length: int) -> bool:
        """带重试逻辑接收单个数据块"""

        def _try_receive():
            # 发送请求
            if not self.send_data_request(addr, length):
                logger.warning(f"发送数据请求失败，地址: {addr}")
                return False

            # 接收数据包
            if self.receive_data_package():
                return True
            else:
                logger.warning(f"接收地址 {addr} 的数据包超时或失败")
                return False

        # 使用 retry_call 执行
        success = retry_call(
            _try_receive,
            max_retry=self.config.max_retries,
            base_delay=0.1,
            logger=logger,
        )

        return success if success is not None else False

    def start_transfer(self) -> bool:
        """
        开始文件传输

        Returns:
            成功返回True，失败返回False
        """
        if not self.save_path:
            logger.error("未设置保存路径")
            return False

        try:
            # 获取文件大小
            logger.info("请求文件大小...")

            def _try_get_size():
                if not self.send_file_size_request():
                    return None
                return self.receive_file_size()

            file_size = retry_call(
                _try_get_size, max_retry=3, base_delay=0.2, logger=logger
            )

            if file_size is None or file_size <= 0:
                logger.error("无法获取有效的文件大小，终止传输。")
                return False

            # 打开文件保存句柄
            self.save_path.parent.mkdir(parents=True, exist_ok=True)
            self._file_handle = self.save_path.open("wb")

            # 开始接收文件
            start_time = time.time()
            logger.info("开始接收文件...")

            # 初始化进度条
            if self.config.show_progress:
                self.progress_bar = ProgressBar(total=self.file_size, show_rate=True)

            while self.recv_size < self.file_size:
                # 计算请求长度
                remain_len = self.file_size - self.recv_size
                request_len = min(remain_len, self.config.max_data_length)

                # 使用重试逻辑获取数据块
                if not self._receive_chunk_with_retry(self.recv_size, request_len):
                    logger.error(
                        f"连续多次接收数据块失败，终止于 {self.recv_size}/{self.file_size} 字节。"
                    )
                    if self._file_handle:
                        self._file_handle.close()
                    if self.save_path.exists():
                        try:
                            self.save_path.unlink()
                            logger.info(f"已删除不完整的文件: {self.save_path}")
                        except OSError as e:
                            logger.error(f"删除不完整文件失败: {e}")
                    return False

                # 更新进度条
                if self.config.show_progress and self.progress_bar:
                    self.progress_bar.update(self.recv_size)

            # 确保所有数据写入磁盘
            if self._file_handle and not self._file_handle.closed:
                self._file_handle.close()

            if self.config.show_progress and self.progress_bar:
                self.progress_bar.finish()

            elapsed_time = time.time() - start_time
            logger.info(f"文件接收完成！用时: {elapsed_time:.2f}秒")

            # 最终校验文件大小
            if self.save_path.stat().st_size != self.file_size:
                logger.error(
                    f"最终文件大小不匹配！预期: {self.file_size}，实际: {self.save_path.stat().st_size}"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"文件传输异常: {e}", exc_info=True)
            if self._file_handle and not self._file_handle.closed:
                self._file_handle.close()
            # 传输失败，删除不完整的文件
            if self.save_path and self.save_path.exists():
                try:
                    self.save_path.unlink()
                    logger.info(f"已删除不完整的文件: {self.save_path}")
                except OSError as a:
                    logger.error(f"删除不完整文件失败: {a}")
            return False

    def _save_file(self) -> bool:
        """
        保存接收的文件

        Returns:
            成功返回True，失败返回False
        """
        try:
            if self.save_path is None:
                logger.error("保存路径未设置")
                return False

            # 确保父目录存在
            self.save_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入文件
            with self.save_path.open("wb") as f:
                f.write(self.file_data)

            logger.info(f"文件已保存: {self.save_path}")
            return True

        except Exception as e:
            logger.error(f"保存文件失败: {e}")
            return False

    def __del__(self):
        if self._file_handle and not self._file_handle.closed:
            try:
                self._file_handle.close()
            except Exception:
                pass


# 为了保持向后兼容，提供原类名的别名
Receiver = FileReceiver
