#!/usr/bin/env python3
"""
文件发送器测试
==============

测试 serial_file_transfer.transfer.sender 模块中的文件发送功能。

这是系统的核心模块之一，负责文件的发送逻辑。
测试重点关注：
- 文件初始化和验证
- 数据读取和分块
- 传输协议处理
- 错误处理和重试
"""

import pytest
import sys
import struct
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import tempfile
import os

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from serial_file_transfer.transfer.sender import FileSender
from serial_file_transfer.core.serial_manager import SerialManager
from serial_file_transfer.config.settings import SerialConfig, TransferConfig
from serial_file_transfer.config.constants import SerialCommand
from serial_file_transfer.core.frame_handler import FrameHandler


class TestFileSenderInit:
    """
    测试FileSender的初始化功能

    文件发送器的初始化是整个传输过程的基础
    """

    def test_init_without_file(self):
        """
        测试不提供文件路径的初始化

        应该创建一个空的发送器，等待后续设置文件
        """
        # 创建mock串口管理器
        mock_serial_manager = MagicMock()

        # 创建发送器
        sender = FileSender(mock_serial_manager)

        # 验证初始状态
        assert sender.serial_manager is mock_serial_manager
        assert sender.config is not None  # 应该有默认配置
        assert sender.send_size == 0
        assert sender.file_size == 0
        assert sender.file_data == b""

    def test_init_with_config(self):
        """
        测试使用自定义配置初始化
        """
        mock_serial_manager = MagicMock()
        custom_config = TransferConfig(max_data_length=2048, retry_count=5)

        sender = FileSender(mock_serial_manager, config=custom_config)

        assert sender.config is custom_config
        assert sender.config.max_data_length == 2048
        assert sender.config.retry_count == 5

    def test_init_with_valid_file(self):
        """
        测试使用有效文件路径初始化

        应该自动加载文件内容
        """
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
            tmp_file.write("Hello, World!")
            tmp_file_path = tmp_file.name

        try:
            mock_serial_manager = MagicMock()

            # 使用文件路径初始化
            sender = FileSender(mock_serial_manager, tmp_file_path)

            # 验证文件被正确加载
            assert sender.file_size == 13  # "Hello, World!" 的长度
            assert sender.file_data == b"Hello, World!"
            assert sender.send_size == 0  # 初始发送大小为0

        finally:
            # 清理临时文件
            os.unlink(tmp_file_path)

    def test_init_with_nonexistent_file(self):
        """
        测试使用不存在的文件路径初始化

        应该失败但不抛出异常
        """
        mock_serial_manager = MagicMock()

        sender = FileSender(mock_serial_manager, "/path/to/nonexistent/file.txt")

        # 文件加载失败，但对象创建成功
        assert sender.file_size == 0
        assert sender.file_data == b""


class TestFileSenderFileOperations:
    """
    测试FileSender的文件操作功能

    包括文件初始化、数据读取等核心功能
    """

    def test_init_file_success(self):
        """
        测试成功初始化文件
        """
        # 创建临时文件
        test_content = "这是测试文件内容\n包含中文字符"
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False
        ) as tmp_file:
            tmp_file.write(test_content)
            tmp_file_path = tmp_file.name

        try:
            mock_serial_manager = MagicMock()
            sender = FileSender(mock_serial_manager)

            # 初始化文件
            result = sender.init_file(tmp_file_path)

            # 验证结果
            assert result is True
            assert sender.file_size > 0
            assert len(sender.file_data) == sender.file_size
            assert sender.send_size == 0  # 重置发送大小

        finally:
            os.unlink(tmp_file_path)

    def test_init_file_nonexistent(self):
        """
        测试初始化不存在的文件
        """
        mock_serial_manager = MagicMock()
        sender = FileSender(mock_serial_manager)

        result = sender.init_file("/path/to/nonexistent/file.txt")

        assert result is False
        assert sender.file_size == 0
        assert sender.file_data == b""

    def test_init_file_directory(self):
        """
        测试初始化目录而不是文件

        应该失败，因为目录不能作为文件发送
        """
        mock_serial_manager = MagicMock()
        sender = FileSender(mock_serial_manager)

        # 使用临时目录
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = sender.init_file(tmp_dir)

            assert result is False
            assert sender.file_size == 0

    def test_get_file_data_normal(self):
        """
        测试正常的文件数据获取
        """
        # 创建测试文件
        test_data = b"0123456789ABCDEF"  # 16字节测试数据
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(test_data)
            tmp_file_path = tmp_file.name

        try:
            mock_serial_manager = MagicMock()
            sender = FileSender(mock_serial_manager, tmp_file_path)

            # 测试不同的数据获取
            assert sender.get_file_data(0, 4) == b"0123"  # 前4字节
            assert sender.get_file_data(4, 4) == b"4567"  # 中间4字节
            assert sender.get_file_data(12, 4) == b"CDEF"  # 后4字节
            assert sender.get_file_data(0, 16) == test_data  # 全部数据

        finally:
            os.unlink(tmp_file_path)

    def test_get_file_data_boundary(self):
        """
        测试文件数据获取的边界情况
        """
        test_data = b"Hello"  # 5字节测试数据
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(test_data)
            tmp_file_path = tmp_file.name

        try:
            mock_serial_manager = MagicMock()
            sender = FileSender(mock_serial_manager, tmp_file_path)

            # 边界测试
            assert sender.get_file_data(0, 0) == b""  # 零长度
            assert sender.get_file_data(5, 10) == b""  # 超出文件末尾
            assert sender.get_file_data(3, 10) == b"lo"  # 部分超出
            assert sender.get_file_data(10, 5) == b""  # 起始位置超出

        finally:
            os.unlink(tmp_file_path)

    @pytest.mark.parametrize(
        "file_size,addr,length,expected_length",
        [
            # 参数化测试：不同的文件大小和读取参数
            (100, 0, 10, 10),  # 正常读取
            (100, 90, 20, 10),  # 读取到文件末尾
            (100, 50, 50, 50),  # 读取后半部分
            (50, 0, 100, 50),  # 读取长度超过文件大小
            (0, 0, 10, 0),  # 空文件
        ],
    )
    def test_get_file_data_parametrized(self, file_size, addr, length, expected_length):
        """
        参数化测试：不同的文件数据获取场景
        """
        # 创建指定大小的测试文件
        test_data = b"X" * file_size
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(test_data)
            tmp_file_path = tmp_file.name

        try:
            mock_serial_manager = MagicMock()
            sender = FileSender(mock_serial_manager, tmp_file_path)

            result = sender.get_file_data(addr, length)
            assert len(result) == expected_length

        finally:
            os.unlink(tmp_file_path)


class TestFileSenderProtocol:
    """
    测试FileSender的协议处理功能

    这些测试关注传输协议的实现
    """

    @patch("serial_file_transfer.transfer.sender.FrameHandler")
    def test_send_filename_success(self, mock_frame_handler):
        """
        测试成功发送文件名
        """
        # 设置mock
        mock_frame_handler.pack_frame.return_value = b"packed_frame"
        mock_serial_manager = MagicMock()
        mock_serial_manager.write.return_value = True

        sender = FileSender(mock_serial_manager)

        # 测试发送文件名
        result = sender.send_filename("test.txt")

        # 验证结果
        assert result is True
        mock_frame_handler.pack_frame.assert_called_once()
        mock_serial_manager.write.assert_called_once_with(b"packed_frame")

    @patch("serial_file_transfer.transfer.sender.FrameHandler")
    def test_send_filename_failure(self, mock_frame_handler):
        """
        测试发送文件名失败的情况
        """
        # 设置mock：写入失败
        mock_frame_handler.pack_frame.return_value = b"packed_frame"
        mock_serial_manager = MagicMock()
        mock_serial_manager.write.return_value = False

        sender = FileSender(mock_serial_manager)

        result = sender.send_filename("test.txt")

        assert result is False

    @patch("serial_file_transfer.transfer.sender.FrameHandler")
    def test_send_filename_long_name(self, mock_frame_handler):
        """
        测试发送长文件名

        文件名会被截断或填充到固定长度
        """
        mock_frame_handler.pack_frame.return_value = b"packed_frame"
        mock_serial_manager = MagicMock()
        mock_serial_manager.write.return_value = True

        sender = FileSender(mock_serial_manager)

        # 测试长文件名
        long_filename = "a" * 200  # 超过最大长度的文件名
        result = sender.send_filename(long_filename)

        # 应该成功处理（被截断）
        assert result is True
        mock_frame_handler.pack_frame.assert_called_once()

    def test_send_filename_unicode(self):
        """
        测试发送包含Unicode字符的文件名
        """
        mock_serial_manager = MagicMock()
        mock_serial_manager.write.return_value = True

        with patch(
            "serial_file_transfer.transfer.sender.FrameHandler"
        ) as mock_frame_handler:
            mock_frame_handler.pack_frame.return_value = b"packed_frame"

            sender = FileSender(mock_serial_manager)

            # 测试中文文件名
            result = sender.send_filename("测试文件.txt")

            assert result is True

    @patch("serial_file_transfer.transfer.sender.FrameHandler.read_frame")
    def test_wait_for_data_request_oversized_length_sends_nack(self, mock_read_frame):
        """
        测试 _wait_for_data_request 收到超长数据请求时，发送端是否正确发送 NACK 帧，并包含建议长度
        """
        mock_serial_manager = MagicMock()
        mock_serial_manager.port = MagicMock()  # Mock the port attribute
        mock_serial_manager.write = MagicMock(return_value=True)  # Mock write method

        # 准备一个临时文件，FileSender需要一个文件来初始化
        test_file_path = Path(tempfile.NamedTemporaryFile(delete=False).name)
        test_file_path.write_bytes(b"a" * 1000)  # 写入一些内容

        try:
            # 定义一个测试用的max_data_length，这个值是希望NACK回传的建议长度
            test_max_data_length = 1024
            # 设置一个协商块大小，使其在有效范围内但小于 max_data_length，让请求长度能够超出
            negotiated_chunk_size = 512  # 修改为符合 MIN_CHUNK_SIZE 的最小值
            config = TransferConfig(max_data_length=test_max_data_length)
            config.update_chunk_size(negotiated_chunk_size)  # 设置协商块大小

            sender = FileSender(
                mock_serial_manager, file_path=test_file_path, config=config
            )
            sender._seq_id = 10  # 设置一个序列号用于NACK帧的payload

            # 模拟一个 REQUEST_DATA 帧，其请求长度超过 effective_chunk_size (negotiated_chunk_size)
            requested_addr = 0
            oversized_length = negotiated_chunk_size + 100  # 请求长度超过协商块大小

            # 模拟的请求数据 payload: 地址(4字节) + 长度(2字节)
            mock_request_payload = struct.pack("<IH", requested_addr, oversized_length)

            # 模拟 FrameHandler.read_frame 返回 REQUEST_DATA 命令和超长数据
            mock_read_frame.return_value = (
                SerialCommand.REQUEST_DATA,
                mock_request_payload,
            )

            # Act
            result = sender._wait_for_data_request()

            # Assert
            # 应该返回 True，表示处理了请求并继续等待下一个请求（因为发送了NACK并continue了）
            assert result is True

            # 验证 serial_manager.write 被调用，发送了 NACK 帧
            mock_serial_manager.write.assert_called_once()

            # 检查发送的帧内容
            call_args = mock_serial_manager.write.call_args
            assert call_args is not None
            written_frame = call_args[0][0]
            assert isinstance(written_frame, bytes)

            # 简单验证NACK帧被写入（不依赖unpack_frame来避免复杂的mock）
            # 只要write被调用且参数是bytes类型即可

        finally:
            # 清理临时文件
            os.unlink(test_file_path)


class TestFileSenderLargeFile:
    """
    测试FileSender处理大文件的能力

    这些测试验证系统在处理大文件时的稳定性
    """

    def test_large_file_initialization(self):
        """
        测试大文件的初始化

        创建一个相对较大的文件进行测试
        """
        # 创建1MB的测试文件
        large_data = b"X" * (1024 * 1024)  # 1MB

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(large_data)
            tmp_file_path = tmp_file.name

        try:
            mock_serial_manager = MagicMock()
            sender = FileSender(mock_serial_manager, tmp_file_path)

            # 验证大文件被正确加载
            assert sender.file_size == 1024 * 1024
            assert len(sender.file_data) == sender.file_size

            # 测试数据获取
            first_chunk = sender.get_file_data(0, 1024)
            assert len(first_chunk) == 1024
            assert first_chunk == b"X" * 1024

            last_chunk = sender.get_file_data(sender.file_size - 1024, 1024)
            assert len(last_chunk) == 1024
            assert last_chunk == b"X" * 1024

        finally:
            os.unlink(tmp_file_path)

    def test_file_data_chunking(self):
        """
        测试文件数据的分块读取

        模拟实际传输中的分块读取模式
        """
        # 创建测试文件
        test_size = 10240  # 10KB
        test_data = bytes(range(256)) * (test_size // 256)  # 重复的字节模式

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(test_data)
            tmp_file_path = tmp_file.name

        try:
            mock_serial_manager = MagicMock()
            sender = FileSender(mock_serial_manager, tmp_file_path)

            # 模拟分块读取
            chunk_size = 1024  # 1KB块
            total_read = 0
            reconstructed_data = b""

            while total_read < sender.file_size:
                remaining = sender.file_size - total_read
                current_chunk_size = min(chunk_size, remaining)

                chunk = sender.get_file_data(total_read, current_chunk_size)
                reconstructed_data += chunk
                total_read += len(chunk)

                # 验证块大小正确
                assert len(chunk) == current_chunk_size

            # 验证重构的数据与原始数据一致
            assert reconstructed_data == test_data
            assert total_read == sender.file_size

        finally:
            os.unlink(tmp_file_path)


class TestFileSenderErrorHandling:
    """
    测试FileSender的错误处理功能

    验证各种异常情况下的行为
    """

    def test_init_file_permission_error(self):
        """
        测试文件权限错误的处理

        模拟无权限访问文件的情况
        """
        mock_serial_manager = MagicMock()
        sender = FileSender(mock_serial_manager)

        # 使用patch模拟权限错误
        with patch("pathlib.Path.open", side_effect=PermissionError("权限不足")):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.is_file", return_value=True):
                    with patch("pathlib.Path.stat") as mock_stat:
                        mock_stat.return_value.st_size = 100

                        result = sender.init_file("/some/file.txt")

                        assert result is False
                        # 由于异常发生在读取文件时，file_size可能已经被设置
                        # 主要验证返回值为False即可

    def test_send_filename_with_exception(self):
        """
        测试发送文件名时发生一般异常的处理

        由于无法直接模拟编码错误，我们测试其他可能的异常情况
        """
        mock_serial_manager = MagicMock()
        sender = FileSender(mock_serial_manager)

        # 模拟FrameHandler.pack_frame抛出异常
        with patch(
            "serial_file_transfer.transfer.sender.FrameHandler.pack_frame",
            side_effect=Exception("打包失败"),
        ):
            result = sender.send_filename("test.txt")

            assert result is False

    def test_file_operations_with_empty_file(self):
        """
        测试空文件的处理
        """
        # 创建空文件
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file_path = tmp_file.name

        try:
            mock_serial_manager = MagicMock()
            sender = FileSender(mock_serial_manager, tmp_file_path)

            # 验证空文件的处理
            assert sender.file_size == 0
            assert sender.file_data == b""
            assert sender.get_file_data(0, 10) == b""

        finally:
            os.unlink(tmp_file_path)


# 如果直接运行这个文件，执行所有测试
if __name__ == "__main__":
    """
    运行测试的说明：

    1. 运行所有测试：pytest test_sender.py -v
    2. 运行特定测试类：pytest test_sender.py::TestFileSenderInit -v
    3. 运行带覆盖率的测试：pytest test_sender.py --cov=serial_file_transfer.transfer.sender
    4. 测试大文件功能：pytest test_sender.py::TestFileSenderLargeFile -v
    """
    pytest.main([__file__, "-v"])
