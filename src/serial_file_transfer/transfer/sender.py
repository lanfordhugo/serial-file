"""
文件发送模块
============

负责单个文件的发送逻辑。
"""

import os
import struct
import time
from pathlib import Path
from typing import Optional, Union, cast

from ..config.constants import SerialCommand, VAL_REQUEST_FILE, MAX_FILE_NAME_LENGTH
from ..config.settings import TransferConfig
from ..core.frame_handler import FrameHandler
from ..core.frame_payload import FramePayload
from ..core.serial_manager import SerialManager
from ..core.sequence_recovery import SequenceRecoveryManager
from ..utils.logger import get_console_logger
from ..utils.progress import TransferProgressTracker, progress_bar, ProgressBar
from ..utils.retry import retry_call, exponential_backoff

logger = get_console_logger(__name__)


class FileSender:
    """文件发送器"""

    def __init__(
        self,
        serial_manager: SerialManager,
        file_path: Optional[Union[str, Path]] = None,
        config: Optional[TransferConfig] = None,
    ):
        """
        初始化文件发送器

        Args:
            serial_manager: 串口管理器
            file_path: 要发送的文件路径（可选）
            config: 传输配置（可选）
        """
        self.serial_manager = serial_manager
        self.config = config or TransferConfig()

        # 传输状态
        self.send_size = 0
        self.file_size = 0
        # 小文件缓存；流式模式下为 None，防止误判为空字节
        self.file_data: bytes | None = None
        self.file_path: Path | None = None  # 文件路径
        self._file_handle = None  # 大文件流式读取句柄
        self._seq_id: int = 0  # 数据包序号

        # 序号恢复管理器 (中期改进)
        self.sequence_recovery = SequenceRecoveryManager(
            enable_recovery=self.config.enable_sequence_recovery,
            mismatch_threshold=self.config.sequence_mismatch_threshold,
            sync_timeout=self.config.sync_timeout
        )

        # vNext: 删除自适应传输策略（改为固定块长配置）
        # 块长由 config.max_data_length 固定指定，不再动态调整

        # 进度条实例
        self.progress_bar: Optional[ProgressBar] = None

        # 如果提供了文件路径，立即初始化
        if file_path:
            self.init_file(file_path)

    def init_file(self, file_path: Union[str, Path]) -> bool:
        """
        初始化要发送的文件

        Args:
            file_path: 文件路径

        Returns:
            成功返回True，失败返回False
        """
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                logger.error(f"文件不存在: {file_path}")
                return False

            if not file_path.is_file():
                logger.error(f"路径不是文件: {file_path}")
                return False

            self.send_size = 0
            self.file_size = file_path.stat().st_size
            self.file_path = file_path

            # 如果小于阈值，加载到内存；否则启用流式读取
            if self.file_size <= self.config.max_cache_size:
                # 小文件，直接一次性读入内存
                with file_path.open("rb") as f:
                    self.file_data = f.read()
                self._file_handle = None
                logger.debug("小文件已缓存到内存")
            else:
                # 大文件，使用流式读取模式
                self._file_handle = file_path.open("rb")
                self.file_data = None  # 避免 get_file_data 误判
                logger.debug("启用流式读取模式")

            logger.info(f"已加载文件: {file_path.name}, 大小: {self.file_size / 1024:.2f} KB")
            return True

        except Exception as e:
            logger.error(f"初始化文件失败: {e}")
            return False

    def get_file_data(self, addr: int, length: int) -> bytes:
        """
        根据地址和长度获取文件数据

        Args:
            addr: 起始地址
            length: 数据长度

        Returns:
            指定区间的文件数据
        """
        if self.file_data is not None:
            return self.file_data[addr : addr + length]

        if self._file_handle is not None:
            self._file_handle.seek(addr)
            return self._file_handle.read(length)

        # 兜底：重新打开文件一次性读取（不应发生）
        if self.file_path and self.file_path.exists():
            with self.file_path.open("rb") as f:
                f.seek(addr)
                return f.read(length)
        return b""

    def wait_for_file_size_request(self) -> bool:
        """
        等待接收端请求文件大小

        Returns:
            成功返回True，超时返回False
        """
        logger.info("等待接收端请求文件大小...")

        start_time = time.time()
        while True:
            # 检查超时 - 使用数据传输超时，因为这是传输过程中的步骤
            if time.time() - start_time > self.config.data_timeout:
                logger.error(f"等待文件大小请求超时: {self.config.data_timeout}秒")
                return False

            # 读取命令
            cmd, data = FrameHandler.read_frame(
                self.serial_manager.port,  # type: ignore[arg-type]
                6 + 2,  # 帧头+CRC+数据(2字节固定值)
            )

            if cmd is None or data is None:
                continue

            if cmd != SerialCommand.REQUEST_FILE_SIZE:
                # 检查是否是预期的协议命令
                if cmd == SerialCommand.SYNC_REQUEST:
                    logger.debug(f"在等待文件大小请求时收到序号同步请求: {hex(cmd)}")
                    # 处理序号同步
                    sync_result = self.sequence_recovery.handle_sync_request(self.serial_manager, data)
                    if sync_result:
                        expected_seq, current_seq = sync_result
                        self._seq_id = expected_seq
                        logger.info(f"序号同步完成: 发送端序号调整为 {expected_seq}")
                    continue
                elif cmd == SerialCommand.REQUEST_FILE_NAME:
                    logger.debug(f"在等待文件大小请求时收到文件名请求，可能是协议时序问题")
                    # 这可能是正常的协议时序，不算错误
                    continue
                else:
                    # 真正的错误命令
                    logger.warning(f"等待文件大小请求时收到未预期命令: {hex(cmd)}")
                    continue

            # 验证请求数据
            if int.from_bytes(data, byteorder="little") == VAL_REQUEST_FILE:
                logger.info("收到文件大小请求")
                self._send_file_size()
                return True

    def wait_for_filename_request(self) -> bool:
        """
        等待接收端请求文件名

        Returns:
            成功返回True，超时返回False
        """
        logger.info("等待接收端请求文件名...")

        start_time = time.time()
        request_count = 0
        while True:
            # 检查超时
            elapsed = time.time() - start_time
            if elapsed > self.config.request_timeout:
                logger.error(f"等待文件名请求超时: {self.config.request_timeout}秒，共尝试接收 {request_count} 次")
                return False

            # 读取命令
            logger.debug(f"📥 等待接收文件名请求 (已等待 {elapsed:.1f}秒)...")
            cmd, data = FrameHandler.read_frame(
                self.serial_manager.port,  # type: ignore[arg-type]
                6 + 2,  # 帧头+CRC+数据(2字节固定值)
            )

            request_count += 1

            if cmd is None or data is None:
                logger.debug(f"📥 未接收到有效帧 (第 {request_count} 次)")
                continue

            logger.debug(f"📥 接收到帧: cmd=0x{cmd:02X}, data={data.hex() if data else 'None'}")

            if cmd != SerialCommand.REQUEST_FILE_NAME:
                # 检查是否是序号同步命令（预期的协议命令）
                if cmd == SerialCommand.SYNC_REQUEST:
                    logger.debug(f"在等待文件名请求时收到序号同步请求: {hex(cmd)}")
                    # 处理序号同步（如果需要的话）
                    sync_result = self.sequence_recovery.handle_sync_request(self.serial_manager, data)
                    if sync_result:
                        expected_seq, current_seq = sync_result
                        self._seq_id = expected_seq  # 调整发送端序号
                        logger.info(f"序号同步完成: 发送端序号调整为 {expected_seq}")
                    continue
                else:
                    # 真正的错误命令
                    logger.warning(f"等待文件名请求时收到未预期命令: {hex(cmd)}")
                    continue

            logger.info("📥 收到文件名请求！")
            return True

    def send_filename(self, filename: str) -> bool:
        """
        发送文件名（支持相对路径）

        Args:
            filename: 文件名或相对路径

        Returns:
            成功返回True，失败返回False
        """
        try:
            # 1) UTF-8 编码
            encoded_name = filename.encode("utf-8")

            # 2) 如果过长则截断，同时给出日志提示
            if len(encoded_name) > MAX_FILE_NAME_LENGTH:
                logger.warning(
                    "文件路径过长(%d > %d)，自动截断: %s",  # noqa: E501
                    len(encoded_name),
                    MAX_FILE_NAME_LENGTH,
                    filename,
                )
                encoded_name = encoded_name[:MAX_FILE_NAME_LENGTH]

            # 3) 使用变长编码：2字节长度 + 实际数据
            length_bytes = struct.pack("<H", len(encoded_name))
            data = length_bytes + encoded_name

            # 4) 打包并发送
            frame = FrameHandler.pack_frame(SerialCommand.REPLY_FILE_NAME, data)

            if frame is None:
                logger.error("打包文件名帧失败")
                return False

            if self.serial_manager.write(frame):
                logger.info("📤 已发送文件路径: %s (cmd=0x%02X, frame_len=%d)", filename, SerialCommand.REPLY_FILE_NAME, len(frame))
                return True

            logger.error("📤 发送文件名失败")
            return False

        except Exception as e:
            logger.error("发送文件名异常: %s", e)
            return False

    def _send_file_size(self) -> bool:
        """
        发送文件大小

        Returns:
            成功返回True，失败返回False
        """
        try:
            # 打包文件大小（4字节）
            size_data = struct.pack("<I", self.file_size)
            frame = FrameHandler.pack_frame(SerialCommand.REPLY_FILE_SIZE, size_data)

            if frame and self.serial_manager.write(frame):
                logger.info(f"已发送文件大小: {self.file_size / 1024:.2f} KB")
                return True
            else:
                logger.error("发送文件大小失败")
                return False

        except Exception as e:
            logger.error(f"发送文件大小异常: {e}")
            return False

    def _send_data_package(self, addr: int, length: int) -> bool:
        """
        发送数据包（vNext新格式：seq + offset + payload）

        Args:
            addr: 起始地址（即offset）
            length: 数据长度

        Returns:
            成功返回True，失败返回False
        """
        try:
            seq_id = self._seq_id & 0xFFFF
            offset = addr  # vNext: offset即请求地址

            # 获取文件数据
            payload = self.get_file_data(addr, length)

            # vNext: 使用新的帧打包函数（包含offset）
            frame = FrameHandler.pack_send_data_frame(seq_id, offset, payload)

            if not frame:
                logger.error(f"打包数据帧失败: seq={seq_id} offset={offset}")
                return False

            def _write_and_wait_ack() -> bool:
                # 发送数据
                if not self.serial_manager.write(frame):
                    return False

                # 等待ACK
                ack_start = time.time()
                port = self.serial_manager.port
                if port is None:
                    logger.error("串口未打开，无法等待ACK")
                    return False

                while time.time() - ack_start < self.config.request_timeout:
                    cmd, ack_data = FrameHandler.read_frame(port, 6 + 10)
                    
                    if cmd is None:
                        continue
                    
                    if cmd == SerialCommand.ACK:
                        # vNext: 解析ACK中的offset
                        result = FramePayload.unpack_ack(ack_data)
                        if result:
                            ack_seq, ack_offset = result
                            # vNext关键：基于offset确认
                            if ack_offset == offset:
                                logger.debug(f"收到ACK确认: seq={ack_seq} offset={ack_offset}")
                                return True
                            else:
                                logger.warning(f"ACK偏移量不匹配: {ack_offset} != {offset}")
                    
                    elif cmd == SerialCommand.NACK:
                        result = FramePayload.unpack_nack(ack_data)
                        if result:
                            nack_seq, nack_offset = result
                            logger.warning(f"收到NACK: seq={nack_seq} offset={nack_offset}")
                        return False  # 触发重试
                    
                    elif cmd == SerialCommand.SYNC_REQUEST:
                        # 处理序号同步请求
                        logger.info("收到序号同步请求")
                        result = FramePayload.unpack_sync_request(ack_data)
                        if result:
                            sync_seq, sync_offset = result
                            # 发送同步回复
                            reply_data = FramePayload.pack_sync_reply(
                                self._seq_id, offset, sync_seq
                            )
                            reply_frame = FrameHandler.pack_frame(
                                SerialCommand.SYNC_REPLY, reply_data
                            )
                            if reply_frame:
                                self.serial_manager.write(reply_frame)
                                logger.info(f"已发送同步回复: seq={self._seq_id} offset={offset}")
                        continue  # 继续等待ACK/NACK
                
                # ACK超时
                return False

            # 重试逻辑（保持简单，不使用自适应）
            result = retry_call(
                _write_and_wait_ack,
                max_retry=self.config.retry_count,
                base_delay=self.config.backoff_base,
                logger=logger,
            )

            if result:
                # 成功：更新序号和进度
                self._seq_id = (self._seq_id + 1) & 0xFFFF
                self.send_size = offset + length
                logger.debug(f"数据包发送成功: offset={offset} len={length} new_seq={self._seq_id}")
                return True
            else:
                logger.error(f"数据包多次发送失败: offset={offset}")
                return False

        except Exception as e:
            logger.error(f"发送数据包异常: {e}")
            return False

    def _wait_for_data_request(self) -> bool:
        """
        等待并处理数据请求

        Returns:
            成功返回True，传输完成或失败返回False
        """
        try:
            # 读取数据请求
            cmd, data = FrameHandler.read_frame(
                self.serial_manager.port,  # type: ignore[arg-type]
                6 + 4 + 2,  # 帧头+CRC+地址(4字节)+长度(2字节)
            )

            if cmd is None or data is None:
                return True  # 继续等待

            if cmd != SerialCommand.REQUEST_DATA:
                # 检查是否是预期的协议命令
                if cmd == SerialCommand.SYNC_REQUEST:
                    logger.debug(f"在等待数据请求时收到序号同步请求: {hex(cmd)}")
                    # 处理序号同步
                    sync_result = self.sequence_recovery.handle_sync_request(self.serial_manager, data)
                    if sync_result:
                        expected_seq, current_seq = sync_result
                        self._seq_id = expected_seq
                        logger.info(f"序号同步完成: 发送端序号调整为 {expected_seq}")
                    return True  # 继续等待
                elif cmd in [SerialCommand.REQUEST_FILE_SIZE, SerialCommand.REQUEST_FILE_NAME]:
                    logger.debug(f"在等待数据请求时收到其他请求命令: {hex(cmd)}，可能是协议重新开始")
                    return True  # 继续等待
                else:
                    # 真正的错误命令
                    logger.warning(f"等待数据请求时收到未预期命令: {hex(cmd)}")
                    return True  # 继续等待

            # 解析请求地址和长度
            addr, length = struct.unpack("<IH", cast(bytes, data))

            # vNext: 使用固定块长配置，简化逻辑
            # 限制请求长度不超过配置块大小
            if length > self.config.max_data_length:
                logger.warning(f"请求长度 {length} 超过配置块大小 {self.config.max_data_length}，调整为配置值")
                # vNext: 不发送NACK，直接调整为配置块长
                length = self.config.max_data_length

            # 验证请求有效性
            if addr + length > self.file_size:
                if addr > self.file_size:
                    logger.error(f"请求地址超出文件范围: {addr} > {self.file_size}")
                    return False
                else:
                    logger.warning(f"请求长度超出文件范围，调整为: {self.file_size - addr}")
                    length = self.file_size - addr

            # 发送数据包
            if self._send_data_package(addr, length):
                self.send_size = addr + length
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"处理数据请求异常: {e}")
            return False

    def start_transfer(self) -> bool:
        """
        开始文件传输

        Returns:
            成功返回True，失败返回False
        """
        if self.file_size == 0:
            logger.error("没有要发送的文件")
            return False

        try:
            # 等待文件大小请求
            if not self.wait_for_file_size_request():
                return False

            # 开始传输进度跟踪
            start_time = time.time()
            logger.info(
                "传输配置: max_data_length=%d request_timeout=%s retry_count=%d backoff_base=%.2f",
                self.config.max_data_length,
                self.config.request_timeout,
                self.config.retry_count,
                self.config.backoff_base,
            )

            logger.info("开始文件传输...")

            # 初始化进度条
            self.progress_bar = ProgressBar(
                total=self.file_size, show_rate=self.config.show_progress
            )

            while self.send_size < self.file_size:
                # 等待并处理数据请求
                if not self._wait_for_data_request():
                    break

                # 显示进度
                if self.config.show_progress and self.progress_bar:
                    self.progress_bar.update(self.send_size)

            # 检查是否传输完成
            if self.send_size >= self.file_size:
                if self.config.show_progress and self.progress_bar:
                    self.progress_bar.finish()  # 完成时换行，并输出统计信息

                elapsed_time = time.time() - start_time
                speed_kbps = (self.file_size / elapsed_time) / 1024 if elapsed_time > 0 else 0
                logger.info(
                    f"文件发送完成！用时: {elapsed_time:.2f}秒，平均速度: {speed_kbps:.2f} KB/s"
                )
                return True
            else:
                logger.error("文件传输未完成")
                return False

        except Exception as e:
            logger.error(f"文件传输异常: {e}")
            return False

    @property
    def _debug_seq_info(self) -> dict:
        """
        仅用于测试的序号状态查询
        
        Returns:
            包含当前序号状态的字典
        
        Note:
            此方法仅供单元测试使用，不应在生产代码中调用
        """
        return {
            "seq_id": self._seq_id,
            "send_size": self.send_size,
            "file_size": self.file_size,
            "has_file_handle": self._file_handle is not None,
            "has_file_data": self.file_data is not None,
        }

    def __del__(self):
        """确保文件句柄关闭"""
        if self._file_handle:
            try:
                self._file_handle.close()
            except Exception:
                pass


# 为了保持向后兼容，提供原类名的别名
Sender = FileSender
