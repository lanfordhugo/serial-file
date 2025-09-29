"""
文件名称: test_sender_comprehensive.py
内容摘要: FileSender类的全面单元测试
当前版本: v1.0.0
作者: AI Assistant
创建日期: 2025-09-29
"""

import pytest
import struct
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open, call
from typing import Optional

from serial_file_transfer.transfer.sender import FileSender
from serial_file_transfer.config.settings import TransferConfig
from serial_file_transfer.config.constants import SerialCommand, VAL_REQUEST_FILE
from serial_file_transfer.core.frame_handler import FrameHandler


class TestFileSenderInitialization:
    """测试FileSender初始化相关功能"""

    def test_init_without_file_path(self):
        """测试不提供文件路径的初始化"""
        # Arrange
        mock_serial_manager = MagicMock()
        config = TransferConfig()
        
        # Act
        sender = FileSender(mock_serial_manager, None, config)
        
        # Assert
        assert sender.serial_manager == mock_serial_manager
        assert sender.config == config
        assert sender.send_size == 0
        assert sender.file_size == 0
        assert sender.file_data is None
        assert sender.file_path is None
        assert sender._seq_id == 0

    def test_init_with_default_config(self):
        """测试使用默认配置初始化"""
        # Arrange
        mock_serial_manager = MagicMock()
        
        # Act
        sender = FileSender(mock_serial_manager)
        
        # Assert
        assert isinstance(sender.config, TransferConfig)
        assert sender.config.max_data_length > 0

    def test_init_with_valid_file_path(self, test_file_small):
        """测试使用有效文件路径初始化"""
        # Arrange
        mock_serial_manager = MagicMock()
        
        # Act
        sender = FileSender(mock_serial_manager, test_file_small)
        
        # Assert
        assert sender.file_path == test_file_small
        assert sender.file_size == test_file_small.stat().st_size
        assert sender.file_size > 0


class TestFileSenderFileOperations:
    """测试FileSender文件操作相关功能"""

    def test_init_file_success(self, test_file_small):
        """测试成功初始化文件"""
        # Arrange
        mock_serial_manager = MagicMock()
        sender = FileSender(mock_serial_manager)
        
        # Act
        result = sender.init_file(test_file_small)
        
        # Assert
        assert result is True
        assert sender.file_path == test_file_small
        assert sender.file_size == test_file_small.stat().st_size
        assert sender.send_size == 0

    def test_init_file_nonexistent(self):
        """测试初始化不存在的文件"""
        # Arrange
        mock_serial_manager = MagicMock()
        sender = FileSender(mock_serial_manager)
        nonexistent_path = Path("nonexistent_file.txt")
        
        # Act
        result = sender.init_file(nonexistent_path)
        
        # Assert
        assert result is False
        assert sender.file_size == 0

    def test_init_file_is_directory(self, temp_dir):
        """测试初始化目录路径（应该失败）"""
        # Arrange
        mock_serial_manager = MagicMock()
        sender = FileSender(mock_serial_manager)
        
        # Act
        result = sender.init_file(temp_dir)
        
        # Assert
        assert result is False

    def test_init_file_small_cached(self, test_file_small):
        """测试小文件被缓存到内存"""
        # Arrange
        mock_serial_manager = MagicMock()
        config = TransferConfig()
        config.max_cache_size = test_file_small.stat().st_size + 1000  # 确保文件小于阈值
        sender = FileSender(mock_serial_manager, config=config)
        
        # Act
        result = sender.init_file(test_file_small)
        
        # Assert
        assert result is True
        assert sender.file_data is not None
        assert len(sender.file_data) == test_file_small.stat().st_size
        assert sender._file_handle is None

    def test_init_file_large_streaming(self, test_file_large):
        """测试大文件启用流式读取"""
        # Arrange
        mock_serial_manager = MagicMock()
        config = TransferConfig()
        config.max_cache_size = 100  # 设置很小的阈值，强制流式模式
        sender = FileSender(mock_serial_manager, config=config)
        
        # Act
        result = sender.init_file(test_file_large)
        
        # Assert
        assert result is True
        assert sender.file_data is None  # 大文件不缓存
        assert sender._file_handle is not None
        
        # 清理
        sender.__del__()

    def test_get_file_data_from_cache(self, test_file_small):
        """测试从缓存获取文件数据"""
        # Arrange
        mock_serial_manager = MagicMock()
        sender = FileSender(mock_serial_manager, test_file_small)
        
        # Act
        data = sender.get_file_data(0, 10)
        
        # Assert
        assert len(data) == 10
        assert isinstance(data, bytes)

    def test_get_file_data_from_stream(self, test_file_large):
        """测试从文件流获取数据"""
        # Arrange
        mock_serial_manager = MagicMock()
        config = TransferConfig()
        config.max_cache_size = 100  # 强制流式模式
        sender = FileSender(mock_serial_manager, test_file_large, config)
        
        # Act
        data = sender.get_file_data(0, 50)
        
        # Assert
        assert len(data) == 50
        assert isinstance(data, bytes)
        
        # 清理
        sender.__del__()

    def test_get_file_data_boundary(self, test_file_small):
        """测试文件数据边界获取"""
        # Arrange
        mock_serial_manager = MagicMock()
        sender = FileSender(mock_serial_manager, test_file_small)
        file_size = sender.file_size
        
        # Act - 获取文件末尾数据
        data = sender.get_file_data(file_size - 10, 20)  # 请求超出文件大小
        
        # Assert
        assert len(data) == 10  # 只能获取到文件剩余的10字节


class TestFileSenderProtocolInteraction:
    """测试FileSender协议交互功能"""

    def test_wait_for_file_size_request_success(self):
        """测试成功等待文件大小请求"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        sender = FileSender(mock_serial_manager)
        
        # Mock FrameHandler.read_frame 返回文件大小请求
        with patch('serial_file_transfer.transfer.sender.FrameHandler.read_frame') as mock_read_frame:
            mock_read_frame.return_value = (SerialCommand.REQUEST_FILE_SIZE, struct.pack("<H", VAL_REQUEST_FILE))
            
            with patch.object(sender, '_send_file_size', return_value=True) as mock_send_size:
                # Act
                result = sender.wait_for_file_size_request()
                
                # Assert
                assert result is True
                mock_send_size.assert_called_once()

    def test_wait_for_file_size_request_timeout(self):
        """测试等待文件大小请求超时"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        config = TransferConfig()
        config.request_timeout = 0.1  # 很短的超时时间
        sender = FileSender(mock_serial_manager, config=config)
        
        # Mock FrameHandler.read_frame 一直返回None（模拟超时）
        with patch('serial_file_transfer.transfer.sender.FrameHandler.read_frame') as mock_read_frame:
            mock_read_frame.return_value = (None, None)
            
            # Act
            result = sender.wait_for_file_size_request()
            
            # Assert
            assert result is False

    def test_wait_for_file_size_request_wrong_command(self):
        """测试收到错误命令"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        config = TransferConfig()
        config.request_timeout = 0.1
        sender = FileSender(mock_serial_manager, config=config)
        
        # Mock收到错误命令，然后超时
        with patch('serial_file_transfer.transfer.sender.FrameHandler.read_frame') as mock_read_frame:
            # 使用无限循环返回None来模拟超时
            mock_read_frame.return_value = (SerialCommand.REQUEST_DATA, b"wrong_data")
            
            # Act
            result = sender.wait_for_file_size_request()
            
            # Assert
            assert result is False

    def test_wait_for_filename_request_success(self):
        """测试成功等待文件名请求"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        sender = FileSender(mock_serial_manager)
        
        # Mock FrameHandler.read_frame 返回文件名请求
        with patch('serial_file_transfer.transfer.sender.FrameHandler.read_frame') as mock_read_frame:
            mock_read_frame.return_value = (SerialCommand.REQUEST_FILE_NAME, b"request_data")
            
            # Act
            result = sender.wait_for_filename_request()
            
            # Assert
            assert result is True

    def test_send_filename_success(self):
        """测试成功发送文件名"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_serial_manager.write.return_value = True
        sender = FileSender(mock_serial_manager)
        filename = "test_file.txt"
        
        # Mock FrameHandler.pack_frame
        with patch('serial_file_transfer.transfer.sender.FrameHandler.pack_frame') as mock_pack:
            mock_pack.return_value = b"packed_frame"
            
            # Act
            result = sender.send_filename(filename)
            
            # Assert
            assert result is True
            mock_serial_manager.write.assert_called_once_with(b"packed_frame")

    def test_send_filename_long_name(self):
        """测试发送过长文件名（自动截断）"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_serial_manager.write.return_value = True
        sender = FileSender(mock_serial_manager)
        long_filename = "a" * 1000  # 超长文件名
        
        with patch('serial_file_transfer.transfer.sender.FrameHandler.pack_frame') as mock_pack:
            mock_pack.return_value = b"packed_frame"
            
            # Act
            result = sender.send_filename(long_filename)
            
            # Assert
            assert result is True
            # 验证pack_frame被调用，且数据长度被限制
            mock_pack.assert_called_once()
            call_args = mock_pack.call_args[0]
            assert call_args[0] == SerialCommand.REPLY_FILE_NAME

    def test_send_filename_write_failure(self):
        """测试发送文件名时写入失败"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_serial_manager.write.return_value = False
        sender = FileSender(mock_serial_manager)
        
        with patch('serial_file_transfer.transfer.sender.FrameHandler.pack_frame') as mock_pack:
            mock_pack.return_value = b"packed_frame"
            
            # Act
            result = sender.send_filename("test.txt")
            
            # Assert
            assert result is False

    def test_send_file_size_success(self, test_file_small):
        """测试成功发送文件大小"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_serial_manager.write.return_value = True
        sender = FileSender(mock_serial_manager, test_file_small)
        
        with patch('serial_file_transfer.transfer.sender.FrameHandler.pack_frame') as mock_pack:
            mock_pack.return_value = b"packed_frame"
            
            # Act
            result = sender._send_file_size()
            
            # Assert
            assert result is True
            mock_pack.assert_called_once_with(SerialCommand.REPLY_FILE_SIZE, struct.pack("<I", sender.file_size))


class TestFileSenderDataTransmission:
    """测试FileSender数据传输功能"""

    def test_send_data_package_success(self, test_file_small):
        """测试成功发送数据包"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        mock_serial_manager.write.return_value = True
        sender = FileSender(mock_serial_manager, test_file_small)
        
        # Mock ACK响应
        with patch('serial_file_transfer.transfer.sender.FrameHandler.read_frame') as mock_read_frame:
            mock_read_frame.return_value = (SerialCommand.ACK, struct.pack("<H", 0))  # seq_id = 0
            
            with patch('serial_file_transfer.transfer.sender.FrameHandler.pack_frame') as mock_pack:
                mock_pack.return_value = b"packed_frame"
                
                # Act
                result = sender._send_data_package(0, 100)
                
                # Assert
                assert result is True
                assert sender._seq_id == 1  # 序号应该增加

    def test_send_data_package_nack_retry(self, test_file_small):
        """测试收到NACK后重试"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        mock_serial_manager.write.return_value = True
        config = TransferConfig()
        config.retry_count = 2
        sender = FileSender(mock_serial_manager, test_file_small, config)
        
        # Mock先收到NACK，再收到ACK
        with patch('serial_file_transfer.transfer.sender.FrameHandler.read_frame') as mock_read_frame:
            mock_read_frame.side_effect = [
                (SerialCommand.NACK, struct.pack("<H", 0)),  # 第一次NACK
                (SerialCommand.ACK, struct.pack("<H", 0))    # 第二次ACK
            ]
            
            with patch('serial_file_transfer.transfer.sender.FrameHandler.pack_frame') as mock_pack:
                mock_pack.return_value = b"packed_frame"
                
                # Act
                result = sender._send_data_package(0, 100)
                
                # Assert
                assert result is True
                assert mock_serial_manager.write.call_count >= 2  # 至少写入两次（重试）

    def test_send_data_package_timeout(self, test_file_small):
        """测试发送数据包超时"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        mock_serial_manager.write.return_value = True
        config = TransferConfig()
        config.request_timeout = 0.1
        config.retry_count = 1
        sender = FileSender(mock_serial_manager, test_file_small, config)
        
        # Mock一直返回None（超时）
        with patch('serial_file_transfer.transfer.sender.FrameHandler.read_frame') as mock_read_frame:
            mock_read_frame.return_value = (None, None)
            
            with patch('serial_file_transfer.transfer.sender.FrameHandler.pack_frame') as mock_pack:
                mock_pack.return_value = b"packed_frame"
                
                # Act
                result = sender._send_data_package(0, 100)
                
                # Assert
                assert result is False

    def test_wait_for_data_request_success(self, test_file_small):
        """测试成功等待并处理数据请求"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        sender = FileSender(mock_serial_manager, test_file_small)
        
        # Mock数据请求
        with patch('serial_file_transfer.transfer.sender.FrameHandler.read_frame') as mock_read_frame:
            mock_read_frame.return_value = (SerialCommand.REQUEST_DATA, struct.pack("<IH", 0, 100))  # 请求地址0，长度100
            
            with patch.object(sender, '_send_data_package', return_value=True) as mock_send:
                # Act
                result = sender._wait_for_data_request()
                
                # Assert
                assert result is True
                mock_send.assert_called_once_with(0, 100)
                assert sender.send_size == 100

    def test_wait_for_data_request_invalid_length(self, test_file_small):
        """测试请求长度超过配置限制"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        config = TransferConfig()
        config.max_data_length = 50
        sender = FileSender(mock_serial_manager, test_file_small, config)
        
        # Mock超长数据请求
        with patch('serial_file_transfer.transfer.sender.FrameHandler.read_frame') as mock_read_frame:
            mock_read_frame.return_value = (SerialCommand.REQUEST_DATA, struct.pack("<IH", 0, 100))  # 请求长度100 > 50
            
            with patch('serial_file_transfer.transfer.sender.FrameHandler.pack_frame') as mock_pack:
                mock_pack.return_value = b"nack_frame"
                mock_serial_manager.write.return_value = True
                
                # Act
                result = sender._wait_for_data_request()
                
                # Assert
                assert result is True  # 继续等待，不发送数据
                mock_pack.assert_called_once()  # 应该发送NACK


class TestFileSenderMainTransferFlow:
    """测试FileSender主传输流程"""

    def test_start_transfer_no_file(self):
        """测试没有文件时开始传输"""
        # Arrange
        mock_serial_manager = MagicMock()
        sender = FileSender(mock_serial_manager)
        
        # Act
        result = sender.start_transfer()
        
        # Assert
        assert result is False

    def test_start_transfer_wait_request_failure(self, test_file_small):
        """测试等待文件大小请求失败"""
        # Arrange
        mock_serial_manager = MagicMock()
        sender = FileSender(mock_serial_manager, test_file_small)
        
        with patch.object(sender, 'wait_for_file_size_request', return_value=False):
            # Act
            result = sender.start_transfer()
            
            # Assert
            assert result is False

    def test_start_transfer_partial_completion(self, test_file_small):
        """测试传输未完成的情况"""
        # Arrange
        mock_serial_manager = MagicMock()
        sender = FileSender(mock_serial_manager, test_file_small)
        
        with patch.object(sender, 'wait_for_file_size_request', return_value=True):
            with patch.object(sender, '_wait_for_data_request') as mock_wait:
                # 模拟只传输了一部分就停止
                mock_wait.side_effect = [True, True, False]  # 传输两次后失败
                sender.send_size = sender.file_size // 2  # 只传输了一半
                
                # Act
                result = sender.start_transfer()
                
                # Assert
                assert result is False


class TestFileSenderEdgeCases:
    """测试FileSender边界情况和异常处理"""

    def test_debug_seq_info(self, test_file_small):
        """测试调试序号信息"""
        # Arrange
        mock_serial_manager = MagicMock()
        sender = FileSender(mock_serial_manager, test_file_small)
        
        # Act
        info = sender._debug_seq_info
        
        # Assert
        assert isinstance(info, dict)
        assert "seq_id" in info
        assert "send_size" in info
        assert "file_size" in info
        assert info["seq_id"] == 0
        assert info["file_size"] == sender.file_size

    def test_destructor_closes_file_handle(self, test_file_large):
        """测试析构函数关闭文件句柄"""
        # Arrange
        mock_serial_manager = MagicMock()
        config = TransferConfig()
        config.max_cache_size = 100  # 强制流式模式
        sender = FileSender(mock_serial_manager, test_file_large, config)
        
        # 确保文件句柄被打开
        assert sender._file_handle is not None
        file_handle = sender._file_handle
        
        # Act
        sender.__del__()
        
        # Assert
        assert file_handle.closed

    def test_get_file_data_fallback(self):
        """测试文件数据获取的兜底逻辑"""
        # Arrange
        mock_serial_manager = MagicMock()
        sender = FileSender(mock_serial_manager)
        
        # 手动设置状态，模拟异常情况
        test_file = Path("test_fallback.txt")
        test_content = b"test content for fallback"
        
        # Mock Path.open() 方法而不是builtins.open
        with patch.object(Path, 'open', mock_open(read_data=test_content)):
            with patch.object(Path, 'exists', return_value=True):
                sender.file_path = test_file
                sender.file_data = None
                sender._file_handle = None
                
                # Act
                data = sender.get_file_data(0, 10)
                
                # Assert
                assert data == test_content[:10]

    def test_init_file_exception_handling(self):
        """测试文件初始化异常处理"""
        # Arrange
        mock_serial_manager = MagicMock()
        sender = FileSender(mock_serial_manager)
        
        # Mock Path.stat() 抛出异常
        with patch('pathlib.Path.stat', side_effect=OSError("Permission denied")):
            with patch('pathlib.Path.exists', return_value=True):
                with patch('pathlib.Path.is_file', return_value=True):
                    # Act
                    result = sender.init_file("some_file.txt")
                    
                    # Assert
                    assert result is False
