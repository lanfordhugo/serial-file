"""
P1-C IO线程测试
===============

测试IO线程与协议线程解耦功能。
"""

import pytest
import time
import threading
from unittest.mock import Mock, MagicMock, patch

from src.serial_file_transfer.core.io_thread import IoThread, IoFrame
from src.serial_file_transfer.core.serial_manager import SerialManager
from src.serial_file_transfer.config.settings import SerialConfig
from src.serial_file_transfer.config.constants import SerialCommand


class TestIoFrame:
    """测试IoFrame数据类"""

    def test_io_frame_creation(self):
        """测试IoFrame创建"""
        timestamp = time.time()
        frame = IoFrame(
            command=SerialCommand.REQUEST_FILE_SIZE, data=b"\xAA", timestamp=timestamp
        )

        assert frame.command == SerialCommand.REQUEST_FILE_SIZE
        assert frame.data == b"\xAA"
        assert frame.timestamp == timestamp

    def test_io_frame_auto_timestamp(self):
        """测试IoFrame自动添加时间戳"""
        before = time.time()
        frame = IoFrame(
            command=SerialCommand.REQUEST_FILE_SIZE,
            data=b"\xAA",
            timestamp=0.0,  # 会被post_init重新设置
        )
        after = time.time()

        # 验证时间戳在合理范围内
        assert before <= frame.timestamp <= after


class TestIoThread:
    """测试IO线程功能"""

    @pytest.fixture
    def mock_serial_manager(self):
        """创建模拟串口管理器"""
        mock_manager = Mock(spec=SerialManager)
        mock_manager.is_open = True
        mock_manager.read.return_value = b""
        return mock_manager

    @pytest.fixture
    def io_thread(self, mock_serial_manager):
        """创建IO线程实例"""
        return IoThread(mock_serial_manager, frame_queue_size=10)

    def test_io_thread_init(self, io_thread, mock_serial_manager):
        """测试IO线程初始化"""
        assert io_thread.serial_manager == mock_serial_manager
        assert io_thread.frame_queue.maxsize == 10
        assert not io_thread.is_running
        assert io_thread.frames_received == 0
        assert io_thread.frames_dropped == 0
        assert io_thread.read_errors == 0

    def test_io_thread_start_success(self, io_thread):
        """测试成功启动IO线程"""
        result = io_thread.start()

        assert result is True
        assert io_thread.is_running

        # 清理
        io_thread.stop()

    def test_io_thread_start_serial_not_open(self, io_thread):
        """测试串口未打开时启动IO线程"""
        io_thread.serial_manager.is_open = False

        result = io_thread.start()

        assert result is False
        assert not io_thread.is_running

    def test_io_thread_start_already_running(self, io_thread):
        """测试重复启动IO线程"""
        io_thread.start()

        # 再次启动
        result = io_thread.start()

        assert result is True  # 应该返回成功
        assert io_thread.is_running

        # 清理
        io_thread.stop()

    def test_io_thread_stop(self, io_thread):
        """测试停止IO线程"""
        io_thread.start()
        assert io_thread.is_running

        result = io_thread.stop(timeout=1.0)

        assert result is True
        assert not io_thread.is_running

    def test_io_thread_stop_not_running(self, io_thread):
        """测试停止未运行的IO线程"""
        result = io_thread.stop()
        assert result is True

    def test_get_frame_timeout(self, io_thread):
        """测试获取帧超时"""
        frame = io_thread.get_frame(timeout=0.1)
        assert frame is None

    def test_queue_size_and_statistics(self, io_thread):
        """测试队列大小和统计信息"""
        assert io_thread.queue_size == 0

        stats = io_thread.get_statistics()
        expected_keys = [
            "running",
            "queue_size",
            "frames_received",
            "frames_dropped",
            "read_errors",
        ]

        for key in expected_keys:
            assert key in stats

        assert stats["running"] == io_thread.is_running
        assert stats["queue_size"] == 0

    def test_context_manager(self, io_thread):
        """测试上下文管理器支持"""
        with io_thread as thread:
            assert thread.is_running

        assert not io_thread.is_running


class TestIoThreadFrameParsing:
    """测试IO线程帧解析功能"""

    @pytest.fixture
    def mock_serial_manager(self):
        """创建可控的模拟串口管理器"""
        mock_manager = Mock(spec=SerialManager)
        mock_manager.is_open = True
        return mock_manager

    @pytest.fixture
    def io_thread(self, mock_serial_manager):
        """创建IO线程实例"""
        return IoThread(mock_serial_manager, frame_queue_size=10)

    def test_parse_frame_from_buffer_incomplete(self, io_thread):
        """测试解析不完整的帧"""
        # 不足头部长度的数据
        result = io_thread._parse_frame_from_buffer(b"\x61\x01")
        assert result is None

        # 不足完整帧长度的数据
        result = io_thread._parse_frame_from_buffer(
            b"\x61\x05\x00\xAA"
        )  # 头部指示5字节数据，但只有1字节
        assert result is None

    @patch("src.serial_file_transfer.core.io_thread.FrameHandler.unpack_frame")
    def test_parse_frame_from_buffer_success(self, mock_unpack, io_thread):
        """测试成功解析帧"""
        # 模拟FrameHandler.unpack_frame返回
        mock_unpack.return_value = (SerialCommand.REQUEST_FILE_SIZE, 3, b"\xAA", 0x1234)

        # 构造一个有效的帧数据
        frame_data = b"\x61\x01\x00\xAA\x34\x12"  # cmd + len + data + crc

        result = io_thread._parse_frame_from_buffer(frame_data)

        assert result is not None
        frame, remaining = result
        assert frame is not None
        assert frame.command == SerialCommand.REQUEST_FILE_SIZE
        assert frame.data == b"\xAA"
        assert remaining == b""

    @patch("src.serial_file_transfer.core.io_thread.FrameHandler.unpack_frame")
    def test_parse_frame_from_buffer_parse_failure(self, mock_unpack, io_thread):
        """测试解析失败的情况"""
        # 模拟解析失败
        mock_unpack.return_value = None

        frame_data = b"\x61\x01\x00\xAA\x34\x12extra"

        result = io_thread._parse_frame_from_buffer(frame_data)

        assert result is not None
        frame, remaining = result
        assert frame is None
        assert remaining == b"\x01\x00\xAA\x34\x12extra"  # 丢弃了第一个字节

    def test_queue_frame_normal(self, io_thread):
        """测试正常加入帧到队列"""
        frame = IoFrame(
            command=SerialCommand.REQUEST_FILE_SIZE, data=b"\xAA", timestamp=time.time()
        )

        io_thread._queue_frame(frame)

        assert io_thread.frames_received == 1
        assert io_thread.queue_size == 1

        # 验证可以获取到帧
        retrieved_frame = io_thread.get_frame(timeout=0.1)
        assert retrieved_frame is not None
        assert retrieved_frame.command == frame.command
        assert retrieved_frame.data == frame.data

    def test_queue_frame_full_queue(self, io_thread):
        """测试队列满时的处理"""
        # 填满队列
        for i in range(io_thread.frame_queue.maxsize):
            frame = IoFrame(
                SerialCommand.REQUEST_FILE_SIZE, f"data{i}".encode(), time.time()
            )
            io_thread._queue_frame(frame)

        assert io_thread.queue_size == io_thread.frame_queue.maxsize

        # 添加额外的帧，应该丢弃最老的
        extra_frame = IoFrame(SerialCommand.SEND_DATA, b"extra", time.time())
        io_thread._queue_frame(extra_frame)

        assert io_thread.frames_dropped >= 1
        assert io_thread.queue_size == io_thread.frame_queue.maxsize


class TestIoThreadIntegration:
    """测试IO线程集成功能"""

    @pytest.fixture
    def mock_serial_manager_with_data(self):
        """创建包含测试数据的模拟串口管理器"""
        mock_manager = Mock(spec=SerialManager)
        mock_manager.is_open = True

        # 模拟读取数据序列
        test_frames = [
            b"\x61\x01\x00\xAA\x34\x12",  # 第一个完整帧
            b"\x62\x04\x00\x00\x04\x00\x00\x56\x78",  # 第二个完整帧
        ]

        # 设置读取数据的序列
        mock_manager.read.side_effect = test_frames + [b""] * 100  # 后续返回空数据

        return mock_manager

    @patch("src.serial_file_transfer.core.io_thread.FrameHandler.unpack_frame")
    def test_io_thread_integration(self, mock_unpack, mock_serial_manager_with_data):
        """测试IO线程集成功能"""
        # 配置FrameHandler mock
        mock_unpack.side_effect = [
            (SerialCommand.REQUEST_FILE_SIZE, 3, b"\xAA", 0x1234),
            (SerialCommand.REPLY_FILE_SIZE, 7, b"\x00\x04\x00\x00", 0x7856),
        ]

        io_thread = IoThread(mock_serial_manager_with_data, frame_queue_size=10)

        try:
            # 启动IO线程
            assert io_thread.start() is True

            # 等待线程处理数据
            time.sleep(0.1)

            # 验证接收到帧
            frame1 = io_thread.get_frame(timeout=1.0)
            assert frame1 is not None
            assert frame1.command == SerialCommand.REQUEST_FILE_SIZE
            assert frame1.data == b"\xAA"

            frame2 = io_thread.get_frame(timeout=1.0)
            assert frame2 is not None
            assert frame2.command == SerialCommand.REPLY_FILE_SIZE
            assert frame2.data == b"\x00\x04\x00\x00"

            # 验证统计信息
            stats = io_thread.get_statistics()
            assert stats["frames_received"] >= 2

        finally:
            # 确保停止线程
            io_thread.stop()


# 如果直接运行这个文件，执行所有测试
if __name__ == "__main__":
    pytest.main([__file__])
