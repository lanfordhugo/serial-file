#!/usr/bin/env python3
"""
文件接收器测试
==============

测试 serial_file_transfer.transfer.receiver 模块中的文件接收功能。

这是系统的核心模块之一，负责文件的接收逻辑。
测试重点关注：
- 文件接收和保存
- 数据验证和完整性
- 传输协议处理
- 错误处理和重试
- NACK帧处理和块大小调整
"""

import pytest
import sys
import struct
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from serial_file_transfer.transfer.receiver import FileReceiver
from serial_file_transfer.core.serial_manager import SerialManager
from serial_file_transfer.config.settings import SerialConfig, TransferConfig
from serial_file_transfer.config.constants import SerialCommand


class TestFileReceiverInit:
    """
    测试FileReceiver的初始化功能

    文件接收器的初始化是整个接收过程的基础
    """

    def test_init_without_save_path(self):
        """
        测试不提供保存路径的初始化

        应该创建一个空的接收器，等待后续设置保存路径
        """
        # 创建mock串口管理器
        mock_serial_manager = MagicMock()

        # 创建接收器
        receiver = FileReceiver(mock_serial_manager)

        # 验证初始状态
        assert receiver.serial_manager is mock_serial_manager
        assert receiver.config is not None  # 应该有默认配置
        assert receiver.recv_size == 0
        assert receiver.file_size == 0
        assert receiver.file_data == b""
        assert receiver.save_path is None

    def test_init_with_config(self):
        """
        测试使用自定义配置初始化
        """
        mock_serial_manager = MagicMock()
        custom_config = TransferConfig(max_data_length=2048, retry_count=5)

        receiver = FileReceiver(mock_serial_manager, config=custom_config)

        assert receiver.config is custom_config
        assert receiver.config.max_data_length == 2048
        assert receiver.config.retry_count == 5

    def test_init_with_save_path(self):
        """
        测试使用保存路径初始化

        应该正确设置保存路径
        """
        mock_serial_manager = MagicMock()
        save_path = "/tmp/test_file.txt"

        receiver = FileReceiver(mock_serial_manager, save_path)

        assert receiver.save_path == Path(save_path)
        assert receiver.recv_size == 0
        assert receiver.file_size == 0


class TestFileReceiverProtocol:
    """
    测试FileReceiver的协议处理功能

    这些测试关注传输协议的实现
    """

    @patch("serial_file_transfer.transfer.receiver.FrameHandler")
    def test_send_file_size_request_success(self, mock_frame_handler):
        """
        测试成功发送文件大小请求
        """
        # 设置mock
        mock_frame_handler.pack_frame.return_value = b"packed_frame"
        mock_serial_manager = MagicMock()
        mock_serial_manager.write.return_value = True

        receiver = FileReceiver(mock_serial_manager)

        # 测试发送文件大小请求
        result = receiver.send_file_size_request()

        # 验证结果
        assert result is True
        mock_frame_handler.pack_frame.assert_called_once()
        mock_serial_manager.write.assert_called_once_with(b"packed_frame")

    @patch("serial_file_transfer.transfer.receiver.FrameHandler")
    def test_send_data_request_success(self, mock_frame_handler):
        """
        测试成功发送数据请求
        """
        # 设置mock
        mock_frame_handler.pack_frame.return_value = b"packed_frame"
        mock_serial_manager = MagicMock()
        mock_serial_manager.write.return_value = True

        receiver = FileReceiver(mock_serial_manager)

        # 测试发送数据请求
        result = receiver.send_data_request(addr=100, length=1024)

        # 验证结果
        assert result is True
        mock_frame_handler.pack_frame.assert_called_once()
        mock_serial_manager.write.assert_called_once_with(b"packed_frame")

    @patch("serial_file_transfer.transfer.receiver.FrameHandler.read_frame")
    def test_receive_data_package_nack_adjusts_chunk_size(self, mock_read_frame):
        """
        测试接收到NACK帧时，能够正确调整max_data_length并触发重试
        """
        mock_serial_manager = MagicMock()
        mock_serial_manager.port = MagicMock()

        # 初始配置
        initial_max_data_length = 1024
        config = TransferConfig(max_data_length=initial_max_data_length)
        receiver = FileReceiver(mock_serial_manager, config=config)

        # 模拟NACK帧的payload：序号(2字节) + 建议长度(2字节)
        seq_id = 5
        suggested_length = 512  # 建议调整为更小的块大小
        nack_payload = struct.pack("<HH", seq_id, suggested_length)

        # 模拟 FrameHandler.read_frame 返回 NACK 命令
        mock_read_frame.return_value = (SerialCommand.NACK, nack_payload)

        # Act
        result = receiver.receive_data_package()

        # Assert
        # 应该返回 False，触发重试
        assert result is False

        # 验证 max_data_length 被更新为建议的长度
        assert receiver.config.max_data_length == suggested_length

        # 验证读取帧被调用
        mock_read_frame.assert_called_once()

    @patch("serial_file_transfer.transfer.receiver.FrameHandler.read_frame")
    def test_receive_data_package_success(self, mock_read_frame):
        """
        测试成功接收数据包
        """
        mock_serial_manager = MagicMock()
        mock_serial_manager.port = MagicMock()
        mock_serial_manager.write = MagicMock(return_value=True)

        config = TransferConfig(max_data_length=1024)
        receiver = FileReceiver(mock_serial_manager, config=config)
        receiver._expected_seq = 0  # 设置期望的序号

        # 模拟SEND_DATA帧的payload：序号(2字节) + 实际数据
        seq_id = 0
        test_data = b"Hello, World!"
        data_payload = struct.pack("<H", seq_id) + test_data

        # 模拟 FrameHandler.read_frame 返回 SEND_DATA 命令
        mock_read_frame.return_value = (SerialCommand.SEND_DATA, data_payload)

        # Act
        result = receiver.receive_data_package()

        # Assert
        # 应该返回 True，表示成功接收
        assert result is True

        # 验证数据被正确保存
        assert receiver.file_data == test_data
        assert receiver.recv_size == len(test_data)

        # 验证序号递增
        assert receiver._expected_seq == 1

        # 验证发送了ACK
        mock_serial_manager.write.assert_called_once()

    @patch("serial_file_transfer.transfer.receiver.FrameHandler.read_frame")
    def test_receive_data_package_wrong_sequence(self, mock_read_frame):
        """
        测试接收到错误序号的数据包时发送NACK
        """
        mock_serial_manager = MagicMock()
        mock_serial_manager.port = MagicMock()
        mock_serial_manager.write = MagicMock(return_value=True)

        config = TransferConfig(max_data_length=1024)
        receiver = FileReceiver(mock_serial_manager, config=config)
        receiver._expected_seq = 0  # 期望序号为0

        # 模拟SEND_DATA帧的payload：错误序号(2字节) + 实际数据
        wrong_seq_id = 5  # 错误的序号
        test_data = b"Hello, World!"
        data_payload = struct.pack("<H", wrong_seq_id) + test_data

        # 模拟 FrameHandler.read_frame 返回 SEND_DATA 命令
        mock_read_frame.return_value = (SerialCommand.SEND_DATA, data_payload)

        # Act
        result = receiver.receive_data_package()

        # Assert
        # 应该返回 False，表示序号错误
        assert result is False

        # 验证数据没有被保存（因为序号错误）
        assert receiver.recv_size == 0

        # 验证期望序号没有改变
        assert receiver._expected_seq == 0

        # 验证发送了NACK
        mock_serial_manager.write.assert_called_once()


class TestFileReceiverErrorHandling:
    """
    测试FileReceiver的错误处理功能

    验证各种异常情况下的行为
    """

    @patch("serial_file_transfer.transfer.receiver.FrameHandler.read_frame")
    def test_receive_data_package_read_failure(self, mock_read_frame):
        """
        测试读取帧失败的处理
        """
        mock_serial_manager = MagicMock()
        mock_serial_manager.port = MagicMock()

        receiver = FileReceiver(mock_serial_manager)

        # 模拟读取失败
        mock_read_frame.return_value = (None, None)

        # Act
        result = receiver.receive_data_package()

        # Assert
        # 应该返回 False
        assert result is False

    @patch("serial_file_transfer.transfer.receiver.FrameHandler.read_frame")
    def test_receive_data_package_wrong_command(self, mock_read_frame):
        """
        测试接收到错误命令的处理
        """
        mock_serial_manager = MagicMock()
        mock_serial_manager.port = MagicMock()

        receiver = FileReceiver(mock_serial_manager)

        # 模拟错误的命令
        mock_read_frame.return_value = (SerialCommand.REQUEST_FILE_SIZE, b"some_data")

        # Act
        result = receiver.receive_data_package()

        # Assert
        # 应该返回 False
        assert result is False

    def test_init_receive_params(self):
        """
        测试初始化接收参数
        """
        mock_serial_manager = MagicMock()
        receiver = FileReceiver(mock_serial_manager)

        # 初始化接收参数
        save_path = "/tmp/new_file.txt"
        receiver.init_receive_params(save_path)

        # 验证参数被正确设置
        assert receiver.save_path == Path(save_path)
        assert receiver.file_size == 0
        assert receiver.recv_size == 0
        assert receiver.file_data == b""


# 如果直接运行这个文件，执行所有测试
if __name__ == "__main__":
    """
    运行测试的说明：

    1. 运行所有测试：pytest test_receiver.py -v
    2. 运行特定测试类：pytest test_receiver.py::TestFileReceiverProtocol -v
    3. 运行带覆盖率的测试：pytest test_receiver.py --cov=serial_file_transfer.transfer.receiver
    4. 测试NACK处理：pytest test_receiver.py::TestFileReceiverProtocol::test_receive_data_package_nack_adjusts_chunk_size -v
    """
    pytest.main([__file__, "-v"])
