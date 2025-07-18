"""
IO线程模块
==========

P1-C优化：将串口IO操作与协议业务逻辑解耦，避免主线程阻塞。
"""

import threading
import queue
import time
from typing import Optional, Tuple, Any
from dataclasses import dataclass

from ..core.serial_manager import SerialManager
from ..core.frame_handler import FrameHandler
from ..config.constants import FRAME_HEADER_SIZE, FRAME_CRC_SIZE
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class IoFrame:
    """IO线程读取的帧数据"""

    command: int
    data: bytes
    timestamp: float = 0.0

    def __post_init__(self):
        """添加接收时间戳"""
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class IoThread:
    """
    IO线程类 - P1-C优化

    负责独立的串口数据读取，将解析后的帧投递到队列中，
    业务线程通过队列获取数据进行处理。
    """

    def __init__(self, serial_manager: SerialManager, frame_queue_size: int = 100):
        """
        初始化IO线程

        Args:
            serial_manager: 串口管理器
            frame_queue_size: 帧队列大小
        """
        self.serial_manager = serial_manager
        self.frame_queue: queue.Queue[IoFrame] = queue.Queue(maxsize=frame_queue_size)

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

        # 统计信息
        self.frames_received = 0
        self.frames_dropped = 0
        self.read_errors = 0

    def start(self) -> bool:
        """
        启动IO线程

        Returns:
            启动成功返回True，失败返回False
        """
        if self._running:
            logger.warning("IO线程已经在运行")
            return True

        if not self.serial_manager.is_open:
            logger.error("串口未打开，无法启动IO线程")
            return False

        try:
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._io_loop, daemon=True)
            self._thread.start()
            self._running = True

            logger.info("IO线程已启动")
            return True

        except Exception as e:
            logger.error(f"启动IO线程失败: {e}")
            return False

    def stop(self, timeout: float = 2.0) -> bool:
        """
        停止IO线程

        Args:
            timeout: 等待线程结束的超时时间(秒)

        Returns:
            停止成功返回True，超时返回False
        """
        if not self._running:
            return True

        try:
            logger.info("正在停止IO线程...")
            self._stop_event.set()

            if self._thread and self._thread.is_alive():
                self._thread.join(timeout)

                if self._thread.is_alive():
                    logger.warning(f"IO线程未在{timeout}秒内结束")
                    return False

            self._running = False
            logger.info("IO线程已停止")
            return True

        except Exception as e:
            logger.error(f"停止IO线程异常: {e}")
            return False

    def get_frame(self, timeout: Optional[float] = None) -> Optional[IoFrame]:
        """
        从队列获取帧数据

        Args:
            timeout: 超时时间(秒)，None表示阻塞等待

        Returns:
            成功返回IoFrame，超时或队列空返回None
        """
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @property
    def is_running(self) -> bool:
        """检查IO线程是否在运行"""
        return self._running and self._thread is not None and self._thread.is_alive()

    @property
    def queue_size(self) -> int:
        """获取当前队列大小"""
        return self.frame_queue.qsize()

    def get_statistics(self) -> dict:
        """
        获取IO线程统计信息

        Returns:
            包含统计信息的字典
        """
        return {
            "running": self.is_running,
            "queue_size": self.queue_size,
            "frames_received": self.frames_received,
            "frames_dropped": self.frames_dropped,
            "read_errors": self.read_errors,
        }

    def _io_loop(self) -> None:
        """IO线程主循环"""
        logger.debug("IO线程开始运行")
        buffer = b""

        while not self._stop_event.is_set():
            try:
                # 读取串口数据
                new_data = self.serial_manager.read(1024)
                if new_data:
                    buffer += new_data

                    # 解析缓冲区中的完整帧
                    while True:
                        frame_data = self._parse_frame_from_buffer(buffer)
                        if frame_data is None:
                            break  # 没有完整帧

                        frame, remaining_buffer = frame_data
                        buffer = remaining_buffer

                        if frame is not None:
                            self._queue_frame(frame)

                # 避免忙循环，但保持响应性
                time.sleep(0.001)  # 1ms

            except Exception as e:
                self.read_errors += 1
                logger.error(f"IO线程读取异常: {e}")
                time.sleep(0.01)  # 错误时稍长等待

        logger.debug("IO线程已结束")

    def _parse_frame_from_buffer(
        self, buffer: bytes
    ) -> Optional[Tuple[Optional[IoFrame], bytes]]:
        """
        从缓冲区解析帧数据

        Args:
            buffer: 数据缓冲区

        Returns:
            如果解析到完整帧返回(frame, remaining_buffer)，否则返回None
        """
        HEADER_SIZE = FRAME_HEADER_SIZE  # 3字节

        if len(buffer) < HEADER_SIZE + FRAME_CRC_SIZE:
            return None  # 数据不足

        try:
            # 读取头部信息
            cmd = buffer[0]
            data_len = int.from_bytes(buffer[1:3], "little")

            frame_len = HEADER_SIZE + data_len + FRAME_CRC_SIZE

            if len(buffer) < frame_len:
                return None  # 不够一个完整帧

            # 提取完整帧
            frame_bytes = buffer[:frame_len]
            remaining_buffer = buffer[frame_len:]

            # 解析帧
            unpacked = FrameHandler.unpack_frame(frame_bytes)
            if unpacked is None:
                # 解析失败，丢弃1字节后重试
                logger.debug("帧解析失败，丢弃1字节")
                return None, buffer[1:]

            cmd_parsed, _, data_parsed, _ = unpacked

            # 创建IoFrame
            frame = IoFrame(command=cmd_parsed, data=data_parsed, timestamp=time.time())

            return frame, remaining_buffer

        except Exception as e:
            logger.error(f"解析帧异常: {e}")
            # 异常时丢弃1字节
            return None, buffer[1:] if len(buffer) > 1 else b""

    def _queue_frame(self, frame: IoFrame) -> None:
        """
        将帧加入队列

        Args:
            frame: 要加入的帧
        """
        try:
            self.frame_queue.put_nowait(frame)
            self.frames_received += 1

        except queue.Full:
            # 队列满，丢弃最老的帧
            try:
                self.frame_queue.get_nowait()  # 移除最老的
                self.frame_queue.put_nowait(frame)  # 加入新的
                self.frames_dropped += 1
                logger.warning("帧队列满，丢弃旧帧")
            except queue.Empty:
                pass  # 队列已空，直接重试
            except Exception as e:
                logger.error(f"处理队列满异常: {e}")

    def __enter__(self):
        """支持with语句"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持with语句"""
        self.stop()
