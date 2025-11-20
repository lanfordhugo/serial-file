"""
文件接收模块
============

负责单个文件的接收逻辑。
"""

import os
import struct
import time
import threading
from pathlib import Path
from typing import Optional, Union

from ..config.constants import SerialCommand, VAL_REQUEST_FILE, MAX_FILE_NAME_LENGTH
from ..config.settings import TransferConfig
from ..core.frame_handler import FrameHandler
from ..core.frame_payload import FramePayload
from ..core.serial_manager import SerialManager
from ..core.sequence_recovery import SequenceRecoveryManager
from ..core.protocol_state_sync import ProtocolStateSynchronizer, ProtocolState
from ..utils.logger import get_console_logger
from ..utils.progress import TransferProgressTracker, progress_bar, ProgressBar
from ..utils.retry import retry_call

logger = get_console_logger(__name__)


class FileReceiver:
    """文件接收器"""

    def __init__(
        self,
        serial_manager: SerialManager,
        save_path: Optional[Union[str, Path]] = None,
        config: Optional[TransferConfig] = None,
        progress_callback: Optional[callable] = None,
        cancel_event: Optional[threading.Event] = None,
    ):
        """
        初始化文件接收器

        Args:
            serial_manager: 串口管理器
            save_path: 文件保存路径（可选）
            config: 传输配置（可选）
            progress_callback: 进度回调函数，签名为 callback(current, total)
        """
        self.serial_manager = serial_manager
        self.config = config or TransferConfig()
        self.progress_callback = progress_callback
        self.cancel_event = cancel_event

        # 接收状态
        self.save_path = Path(save_path) if save_path else None
        self.file_size = 0
        self.recv_size = 0
        self.file_data = b""
        self._file_handle = None  # 流式写入句柄
        # 序号追踪
        self._expected_seq: int = 0

        # 序号恢复管理器 (中期改进)
        self.sequence_recovery = SequenceRecoveryManager(
            enable_recovery=self.config.enable_sequence_recovery,
            mismatch_threshold=self.config.sequence_mismatch_threshold,
            sync_timeout=self.config.sync_timeout
        )

        # 协议状态同步器 (跨设备稳定性改进)
        self.protocol_sync = ProtocolStateSynchronizer(
            enable_sync=True,
            sync_interval=15.0,
            force_sync_on_error=True
        )

        # 进度条实例
        self.progress_bar: Optional[ProgressBar] = None

        # 取消传播控制
        self._cancel_signal_sent: bool = False  # 是否已向对端发送过取消命令
        self._propagate_cancel: bool = True     # 是否需要向对端传播本端的取消事件

    def _is_cancelled(self) -> bool:
        """检查是否已取消，并在需要时向对端发送取消命令"""
        if self.cancel_event is not None and self.cancel_event.is_set():
            self._send_cancel_if_needed()
            return True
        return False

    def _send_cancel_if_needed(self) -> None:
        """在本端取消时向对端发送取消传输命令（最多发送一次，连发3帧）"""
        if not self._propagate_cancel:
            return
        if self._cancel_signal_sent:
            return
        if not self.serial_manager or not self.serial_manager.is_open:
            return

        try:
            frame = FrameHandler.pack_frame(SerialCommand.CANCEL_TRANSFER, b"")
            if not frame:
                return
            for _ in range(3):
                self.serial_manager.write(frame)
            self._cancel_signal_sent = True
            logger.info("已向对端发送取消传输命令（3次）")
        except Exception as e:
            logger.error(f"发送取消传输命令失败: {e}")

    def _handle_remote_cancel(self, context: str) -> None:
        """处理从对端收到的取消命令，等同于本端点击取消"""
        logger.warning(f"收到对端取消传输请求，上下文: {context}，即将终止当前接收")
        # 远端取消不再向对端回传取消命令，避免相互触发
        self._propagate_cancel = False
        if self.cancel_event is not None:
            self.cancel_event.set()

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
            # 设置协议状态
            self.protocol_sync.set_local_state(ProtocolState.REQUESTING_FILENAME, "发送文件名请求")
            
            # 协议为了保持一致，这里也使用 0x55AA 作为占位符，两字节
            request_data = struct.pack("<H", VAL_REQUEST_FILE)
            frame = FrameHandler.pack_frame(
                SerialCommand.REQUEST_FILE_NAME, request_data
            )

            if frame and self.serial_manager.write(frame):
                logger.debug(f"📤 已发送文件名请求帧: cmd=0x{SerialCommand.REQUEST_FILE_NAME:02X}, data={request_data.hex()}, frame_len={len(frame)}")
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
            if self._is_cancelled():
                logger.info("接收被取消，停止等待文件大小")
                return None
            # 读取回复
            cmd, data = FrameHandler.read_frame(
                self.serial_manager.port,  # type: ignore[arg-type]
                6 + 4,  # 帧头+CRC+文件大小(4字节)
            )

            if cmd is None or data is None:
                return None

            if cmd == SerialCommand.CANCEL_TRANSFER:
                self._handle_remote_cancel("receive_file_size")
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
        接收文件名（支持相对路径）

        Returns:
            文件名或相对路径，失败时返回None
        """
        try:
            if self._is_cancelled():
                logger.info("接收被取消，停止等待文件名")
                return None
            # 读取回复（变长编码：2字节长度 + 数据）
            logger.debug(f"📥 等待接收文件名回复，期望命令: 0x{SerialCommand.REPLY_FILE_NAME:02X}")
            cmd, data = FrameHandler.read_frame(
                self.serial_manager.port,  # type: ignore[arg-type]
                6 + 2 + MAX_FILE_NAME_LENGTH,  # 帧头+CRC+长度字段+最大文件名长度
            )

            if cmd is None or data is None:
                logger.debug("📥 未接收到有效帧 (cmd或data为None)")
                return None

            if cmd == SerialCommand.CANCEL_TRANSFER:
                self._handle_remote_cancel("receive_filename")
                return None

            logger.debug(f"📥 接收到帧: cmd=0x{cmd:02X}, data_len={len(data) if data else 0}")

            if cmd != SerialCommand.REPLY_FILE_NAME:
                # 检测错误命令并处理协议状态不同步
                expected_commands = [SerialCommand.REPLY_FILE_NAME]
                if self.protocol_sync.detect_error_command(expected_commands, cmd):
                    logger.error(f"检测到严重协议状态不同步: 收到{hex(cmd)}, 期望{hex(SerialCommand.REPLY_FILE_NAME)}")
                    # 强制协议重置
                    if self.protocol_sync.force_protocol_reset(self.serial_manager):
                        logger.info("已发送协议重置命令")
                    else:
                        logger.error("协议重置失败")
                else:
                    logger.error(f"收到错误命令: {hex(cmd)}")
                return None

            # 解析变长编码的文件名
            if len(data) < 2:
                logger.error("文件名数据长度不足")
                return None

            filename_length = struct.unpack("<H", data[:2])[0]
            if len(data) < 2 + filename_length:
                logger.error("文件名数据不完整")
                return None

            filename_bytes = data[2:2 + filename_length]
            filename = filename_bytes.decode("utf-8")
            logger.info(f"接收到文件路径: [{filename}]")
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
            if self._is_cancelled():
                logger.info("接收被取消，放弃发送数据请求")
                return False
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
        接收数据包（vNext新格式：seq + offset + payload）

        Returns:
            成功返回True，失败返回False
        """
        try:
            if self._is_cancelled():
                logger.info("接收被取消，停止接收数据包")
                return False
            # 读取数据包
            cmd, data = FrameHandler.read_frame(
                self.serial_manager.port,  # type: ignore[arg-type]
                6 + self.config.max_data_length,  # 帧头+CRC+最大数据长度
            )

            if cmd == SerialCommand.CANCEL_TRANSFER:
                self._handle_remote_cancel("receive_data_package")
                return False

            # 解析失败，发送NACK
            if cmd is None or data is None:
                nack_data = FramePayload.pack_nack(self._expected_seq, self.recv_size)
                nack_frame = FrameHandler.pack_frame(SerialCommand.NACK, nack_data)
                if nack_frame:
                    self.serial_manager.write(nack_frame)
                    logger.debug(f"解析失败，发送NACK: seq={self._expected_seq} offset={self.recv_size}")
                return False

            if cmd != SerialCommand.SEND_DATA:
                logger.error(f"收到错误命令: {hex(cmd)}")
                return False

            # vNext: 解析新格式载荷（seq + offset + payload）
            result = FramePayload.unpack_send_data(data)
            if not result:
                logger.error("解析SEND_DATA载荷失败")
                return False

            seq_id, offset, payload = result
            logger.debug(f"收到数据包: seq={seq_id} offset={offset} len={len(payload)}")

            # === vNext关键：重复帧识别 ===
            if offset < self.recv_size:
                # 重复帧：已接收过的数据
                logger.warning(f"检测到重复帧: offset={offset} < recv_size={self.recv_size}")

                # 幂等处理：重发ACK但丢弃数据
                ack_data = FramePayload.pack_ack(seq_id, offset)
                ack_frame = FrameHandler.pack_frame(SerialCommand.ACK, ack_data)
                if ack_frame:
                    self.serial_manager.write(ack_frame)
                    logger.info(f"重发ACK（重复帧）: seq={seq_id} offset={offset}")

                return True  # 不算失败，继续接收

            # === 偏移量验证 ===
            if offset != self.recv_size:
                # 偏移量跳跃或倒退
                logger.error(f"偏移量不匹配: offset={offset} != recv_size={self.recv_size}")

                # 发送NACK
                nack_data = FramePayload.pack_nack(seq_id, self.recv_size)
                nack_frame = FrameHandler.pack_frame(SerialCommand.NACK, nack_data)
                if nack_frame:
                    self.serial_manager.write(nack_frame)

                # 检查是否需要序号同步
                if self.sequence_recovery.record_sequence_mismatch():
                    logger.info("触发序号同步...")
                    synced_seq = self.sequence_recovery.perform_sequence_sync(
                        self.serial_manager,
                        self._expected_seq,
                        self.recv_size
                    )
                    if synced_seq is not None:
                        self._expected_seq = synced_seq & 0xFFFF
                        logger.info(f"序号同步成功: {synced_seq}")

                return False

            # === 序号验证 ===
            if seq_id != self._expected_seq:
                logger.warning(f"序号不匹配: seq={seq_id} != expected={self._expected_seq}")
                # 发送NACK
                nack_data = FramePayload.pack_nack(seq_id, offset)
                nack_frame = FrameHandler.pack_frame(SerialCommand.NACK, nack_data)
                if nack_frame:
                    self.serial_manager.write(nack_frame)
                return False

            # === 数据有效：写入文件 ===
            self.recv_size += len(payload)
            if self._file_handle is not None:
                self._file_handle.write(payload)
            else:
                self.file_data += payload

            # 发送ACK（包含offset）
            ack_data = FramePayload.pack_ack(seq_id, offset)
            ack_frame = FrameHandler.pack_frame(SerialCommand.ACK, ack_data)
            if ack_frame:
                self.serial_manager.write(ack_frame)
                logger.debug(f"发送ACK: seq={seq_id} offset={offset}")

            # 更新期望序号
            self._expected_seq = (self._expected_seq + 1) & 0xFFFF

            # 重置序号不匹配计数器
            self.sequence_recovery.reset_mismatch_counter()

            return True

        except Exception as e:
            logger.error(f"接收数据包异常: {e}")
            return False

    def _receive_chunk_with_retry(self, addr: int, length: int) -> bool:
        """带强化串口重启机制的重试逻辑接收单个数据块
        
        恢复策略：
        1. 第一轮：快速重试（3次，约0.3-0.6秒）
        2. 立即串口重启：close → sleep → open
        3. 第二轮：重启后重试（5次，约1-2秒）
        """
        import time

        CANCELLED = object()

        def _try_receive() -> bool:
            """单次发送请求并接收数据包"""
            if self._is_cancelled():
                logger.info("接收被取消，跳过数据块重试")
                return False

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

        def _try_receive_or_cancel():
            if self._is_cancelled():
                logger.info("接收被取消，跳过数据块重试")
                return CANCELLED
            return _try_receive()

        # ===== 第一轮：快速重试 =====
        if self._is_cancelled():
            logger.info("接收被取消，跳过快速重试")
            return False

        result = retry_call(
            _try_receive_or_cancel,
            max_retry=3,
            base_delay=0.1,
            logger=logger,
        )

        if result is CANCELLED:
            return False
        if result:
            return True

        # ===== 串口重启恢复（跳过无效的清缓冲保守重试）=====
        logger.warning(f"地址 {addr} 快速重试失败，立即执行串口重启恢复...")

        try:
            # 记录当前串口配置
            original_baudrate = self.serial_manager.config.baudrate
            logger.info(f"准备重启串口（当前波特率: {original_baudrate}）...")

            # 关闭串口
            self.serial_manager.close()
            logger.debug("串口已关闭")
            time.sleep(1.0)  # 等待串口完全关闭和硬件稳定

            # 重新打开串口
            if self.serial_manager.open():
                logger.info(f"串口重启成功（波特率: {self.serial_manager.config.baudrate}）")
                time.sleep(0.5)  # 等待串口初始化稳定
            else:
                logger.error("串口重启失败，无法继续传输")
                return False

        except Exception as e:
            logger.error(f"串口重启过程发生异常: {e}")
            # 尝试确保串口处于可用状态
            try:
                if not self.serial_manager.is_open:
                    self.serial_manager.open()
            except Exception:
                pass
            return False

        # ===== 第二轮：串口重启后重试 =====
        if self._is_cancelled():
            logger.info("接收被取消，跳过重启后的重试")
            return False

        logger.info(f"地址 {addr} 串口重启完成，开始重启后重试...")
        result = retry_call(
            _try_receive_or_cancel,
            max_retry=5,
            base_delay=0.2,
            logger=logger,
        )

        if result is CANCELLED:
            return False
        if result:
            logger.info(f"✓ 地址 {addr} 串口重启后传输成功")
        else:
            logger.error(f"✗ 地址 {addr} 串口重启后仍然失败，该地址数据块无法传输")

        return bool(result)

    def start_transfer(self) -> bool:
        """开始文件传输

        Returns:
            成功返回True，失败返回False
        """
        if not self.save_path:
            logger.error("未设置保存路径")
            return False

        try:
            if self._is_cancelled():
                logger.info("接收被取消，终止文件传输")
                return False

            # 获取文件大小
            logger.info("请求文件大小...")
            logger.info(
                "传输配置: max_data_length=%d request_timeout=%s retry_count=%d max_retries=%d",
                self.config.max_data_length,
                self.config.request_timeout,
                self.config.retry_count,
                self.config.max_retries,
            )

            def _try_get_size():
                if self._is_cancelled():
                    return None
                if not self.send_file_size_request():
                    return None
                return self.receive_file_size()

            file_size = retry_call(
                _try_get_size,
                max_retry=3,
                base_delay=0.2,
                logger=logger,
            )

            if file_size is None or file_size <= 0:
                logger.error("无法获取有效的文件大小，终止传输。")
                return False

            self.file_size = file_size

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
                if self._is_cancelled():
                    logger.info("接收被取消，终止文件接收循环")
                    break

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

                # 调用进度回调
                if self.progress_callback:
                    self.progress_callback(self.recv_size, self.file_size)

            # 确保所有数据写入磁盘
            if self._file_handle and not self._file_handle.closed:
                self._file_handle.close()

            if self.config.show_progress and self.progress_bar:
                self.progress_bar.finish()

            if self.recv_size >= self.file_size:
                elapsed_time = time.time() - start_time
                speed_kbps = (self.file_size / elapsed_time) / 1024 if elapsed_time > 0 else 0
                logger.info(f"文件接收完成！用时: {elapsed_time:.2f}秒，平均速度: {speed_kbps:.2f} KB/s")

                # 最终校验文件大小
                if self.save_path.stat().st_size != self.file_size:
                    logger.error(
                        f"最终文件大小不匹配！预期: {self.file_size}，实际: {self.save_path.stat().st_size}"
                    )
                    return False

                return True
            else:
                logger.error("文件接收未完成")
                return False

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

    @property  
    def _debug_seq_info(self) -> dict:
        """
        仅用于测试的序号状态查询
        
        Returns:
            包含当前接收状态的字典
        
        Note:
            此方法仅供单元测试使用，不应在生产代码中调用
        """
        return {
            "expected_seq": self._expected_seq,
            "recv_size": self.recv_size,
            "file_size": self.file_size,
            "has_file_handle": self._file_handle is not None and not self._file_handle.closed,
            "save_path": str(self.save_path) if self.save_path else None,
        }

    def __del__(self):
        if self._file_handle and not self._file_handle.closed:
            try:
                self._file_handle.close()
            except Exception:
                pass


# 为了保持向后兼容，提供原类名的别名
Receiver = FileReceiver
