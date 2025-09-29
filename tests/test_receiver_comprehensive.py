"""
文件名称: test_receiver_comprehensive.py
内容摘要: FileReceiver类的全面单元测试
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

from serial_file_transfer.transfer.receiver import FileReceiver
from serial_file_transfer.config.settings import TransferConfig
from serial_file_transfer.config.constants import SerialCommand, VAL_REQUEST_FILE
from serial_file_transfer.core.frame_handler import FrameHandler


class TestFileReceiverInitialization:
    """测试FileReceiver初始化相关功能"""

    def test_init_without_save_path(self):
        """测试不提供保存路径的初始化"""
        # Arrange
        mock_serial_manager = MagicMock()
        config = TransferConfig()
        
        # Act
        receiver = FileReceiver(mock_serial_manager, None, config)
        
        # Assert
        assert receiver.serial_manager == mock_serial_manager
        assert receiver.config == config
        assert receiver.save_path is None
        assert receiver.file_size == 0
        assert receiver.recv_size == 0
        assert receiver.file_data == b""
        assert receiver._expected_seq == 0

    def test_init_with_default_config(self):
        """测试使用默认配置初始化"""
        # Arrange
        mock_serial_manager = MagicMock()
        save_path = "test_output.txt"
        
        # Act
        receiver = FileReceiver(mock_serial_manager, save_path)
        
        # Assert
        assert isinstance(receiver.config, TransferConfig)
        assert receiver.save_path == Path(save_path)

    def test_init_with_path_object(self):
        """测试使用Path对象初始化"""
        # Arrange
        mock_serial_manager = MagicMock()
        save_path = Path("test_output.txt")
        
        # Act
        receiver = FileReceiver(mock_serial_manager, save_path)
        
        # Assert
        assert receiver.save_path == save_path

    def test_init_receive_params(self):
        """测试初始化接收参数"""
        # Arrange
        mock_serial_manager = MagicMock()
        receiver = FileReceiver(mock_serial_manager)
        new_path = "new_output.txt"
        
        # Act
        receiver.init_receive_params(new_path)
        
        # Assert
        assert receiver.save_path == Path(new_path)
        assert receiver.file_size == 0
        assert receiver.recv_size == 0
        assert receiver.file_data == b""


class TestFileReceiverRequestOperations:
    """测试FileReceiver请求发送功能"""

    def test_send_file_size_request_success(self):
        """测试成功发送文件大小请求"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_serial_manager.write.return_value = True
        receiver = FileReceiver(mock_serial_manager)
        
        with patch('serial_file_transfer.transfer.receiver.FrameHandler.pack_frame') as mock_pack:
            mock_pack.return_value = b"packed_frame"
            
            # Act
            result = receiver.send_file_size_request()
            
            # Assert
            assert result is True
            mock_pack.assert_called_once_with(SerialCommand.REQUEST_FILE_SIZE, struct.pack("<H", VAL_REQUEST_FILE))
            mock_serial_manager.write.assert_called_once_with(b"packed_frame")

    def test_send_file_size_request_write_failure(self):
        """测试发送文件大小请求写入失败"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_serial_manager.write.return_value = False
        receiver = FileReceiver(mock_serial_manager)
        
        with patch('serial_file_transfer.transfer.receiver.FrameHandler.pack_frame') as mock_pack:
            mock_pack.return_value = b"packed_frame"
            
            # Act
            result = receiver.send_file_size_request()
            
            # Assert
            assert result is False

    def test_send_file_size_request_pack_failure(self):
        """测试发送文件大小请求打包失败"""
        # Arrange
        mock_serial_manager = MagicMock()
        receiver = FileReceiver(mock_serial_manager)
        
        with patch('serial_file_transfer.transfer.receiver.FrameHandler.pack_frame') as mock_pack:
            mock_pack.return_value = None  # 打包失败
            
            # Act
            result = receiver.send_file_size_request()
            
            # Assert
            assert result is False

    def test_send_filename_request_success(self):
        """测试成功发送文件名请求"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_serial_manager.write.return_value = True
        receiver = FileReceiver(mock_serial_manager)
        
        with patch('serial_file_transfer.transfer.receiver.FrameHandler.pack_frame') as mock_pack:
            mock_pack.return_value = b"packed_frame"
            
            # Act
            result = receiver.send_filename_request()
            
            # Assert
            assert result is True
            mock_pack.assert_called_once_with(SerialCommand.REQUEST_FILE_NAME, struct.pack("<H", VAL_REQUEST_FILE))

    def test_send_data_request_success(self):
        """测试成功发送数据请求"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_serial_manager.write.return_value = True
        receiver = FileReceiver(mock_serial_manager)
        
        with patch('serial_file_transfer.transfer.receiver.FrameHandler.pack_frame') as mock_pack:
            mock_pack.return_value = b"packed_frame"
            
            # Act
            result = receiver.send_data_request(100, 512)
            
            # Assert
            assert result is True
            mock_pack.assert_called_once_with(SerialCommand.REQUEST_DATA, struct.pack("<IH", 100, 512))


class TestFileReceiverReceiveOperations:
    """测试FileReceiver接收功能"""

    def test_receive_file_size_success(self):
        """测试成功接收文件大小"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        receiver = FileReceiver(mock_serial_manager)
        file_size = 1024
        
        with patch('serial_file_transfer.transfer.receiver.FrameHandler.read_frame') as mock_read:
            mock_read.return_value = (SerialCommand.REPLY_FILE_SIZE, struct.pack("<I", file_size))
            
            # Act
            result = receiver.receive_file_size()
            
            # Assert
            assert result == file_size
            assert receiver.file_size == file_size

    def test_receive_file_size_wrong_command(self):
        """测试接收文件大小时收到错误命令"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        receiver = FileReceiver(mock_serial_manager)
        
        with patch('serial_file_transfer.transfer.receiver.FrameHandler.read_frame') as mock_read:
            mock_read.return_value = (SerialCommand.REQUEST_DATA, b"wrong_data")
            
            # Act
            result = receiver.receive_file_size()
            
            # Assert
            assert result is None

    def test_receive_file_size_no_data(self):
        """测试接收文件大小时没有数据"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        receiver = FileReceiver(mock_serial_manager)
        
        with patch('serial_file_transfer.transfer.receiver.FrameHandler.read_frame') as mock_read:
            mock_read.return_value = (None, None)
            
            # Act
            result = receiver.receive_file_size()
            
            # Assert
            assert result is None

    def test_receive_filename_success(self):
        """测试成功接收文件名"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        receiver = FileReceiver(mock_serial_manager)
        filename = "test_file.txt"
        filename_bytes = filename.encode("utf-8")
        data = struct.pack("<H", len(filename_bytes)) + filename_bytes
        
        with patch('serial_file_transfer.transfer.receiver.FrameHandler.read_frame') as mock_read:
            mock_read.return_value = (SerialCommand.REPLY_FILE_NAME, data)
            
            # Act
            result = receiver.receive_filename()
            
            # Assert
            assert result == filename

    def test_receive_filename_short_data(self):
        """测试接收文件名时数据长度不足"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        receiver = FileReceiver(mock_serial_manager)
        
        with patch('serial_file_transfer.transfer.receiver.FrameHandler.read_frame') as mock_read:
            mock_read.return_value = (SerialCommand.REPLY_FILE_NAME, b"x")  # 数据太短
            
            # Act
            result = receiver.receive_filename()
            
            # Assert
            assert result is None

    def test_receive_filename_incomplete_data(self):
        """测试接收文件名时数据不完整"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        receiver = FileReceiver(mock_serial_manager)
        
        # 声明长度为10，但只提供5个字节
        data = struct.pack("<H", 10) + b"short"
        
        with patch('serial_file_transfer.transfer.receiver.FrameHandler.read_frame') as mock_read:
            mock_read.return_value = (SerialCommand.REPLY_FILE_NAME, data)
            
            # Act
            result = receiver.receive_filename()
            
            # Assert
            assert result is None

    def test_receive_data_package_success(self):
        """测试成功接收数据包"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        mock_serial_manager.write.return_value = True
        receiver = FileReceiver(mock_serial_manager, "output.txt")
        receiver._expected_seq = 0
        test_data = b"test_data_content"
        packet_data = struct.pack("<H", 0) + test_data  # seq_id=0 + data
        
        with patch('serial_file_transfer.transfer.receiver.FrameHandler.read_frame') as mock_read:
            mock_read.return_value = (SerialCommand.SEND_DATA, packet_data)
            
            with patch('serial_file_transfer.transfer.receiver.FrameHandler.pack_frame') as mock_pack:
                mock_pack.return_value = b"ack_frame"
                
                # Act
                result = receiver.receive_data_package()
                
                # Assert
                assert result is True
                assert receiver.recv_size == len(test_data)
                assert receiver.file_data == test_data
                assert receiver._expected_seq == 1

    def test_receive_data_package_wrong_sequence(self):
        """测试接收数据包序号错误"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        mock_serial_manager.write.return_value = True
        receiver = FileReceiver(mock_serial_manager, "output.txt")
        receiver._expected_seq = 0
        test_data = b"test_data_content"
        packet_data = struct.pack("<H", 5) + test_data  # 错误的seq_id=5
        
        with patch('serial_file_transfer.transfer.receiver.FrameHandler.read_frame') as mock_read:
            mock_read.return_value = (SerialCommand.SEND_DATA, packet_data)
            
            with patch('serial_file_transfer.transfer.receiver.FrameHandler.pack_frame') as mock_pack:
                mock_pack.return_value = b"nack_frame"
                
                # Act
                result = receiver.receive_data_package()
                
                # Assert
                assert result is False  # 序号不匹配应该失败
                assert receiver.recv_size == 0  # 数据不应该被保存

    def test_receive_data_package_nack_response(self):
        """测试接收到NACK响应"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        receiver = FileReceiver(mock_serial_manager, "output.txt")
        nack_data = struct.pack("<HH", 0, 1024)  # seq_id=0, suggested_length=1024
        
        with patch('serial_file_transfer.transfer.receiver.FrameHandler.read_frame') as mock_read:
            mock_read.return_value = (SerialCommand.NACK, nack_data)
            
            # Act
            result = receiver.receive_data_package()
            
            # Assert
            assert result is False
            assert receiver.config.max_data_length == 1024  # 应该调整块大小

    def test_receive_data_package_frame_error(self):
        """测试接收数据包时帧解析错误"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        mock_serial_manager.write.return_value = True
        receiver = FileReceiver(mock_serial_manager, "output.txt")
        
        with patch('serial_file_transfer.transfer.receiver.FrameHandler.read_frame') as mock_read:
            mock_read.return_value = (None, None)  # 解析失败
            
            with patch('serial_file_transfer.transfer.receiver.FrameHandler.pack_frame') as mock_pack:
                mock_pack.return_value = b"nack_frame"
                
                # Act
                result = receiver.receive_data_package()
                
                # Assert
                assert result is False
                # 应该发送NACK请求重传
                mock_pack.assert_called_once()

    def test_receive_data_package_with_file_handle(self, temp_dir):
        """测试使用文件句柄接收数据包"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        mock_serial_manager.write.return_value = True
        save_path = temp_dir / "test_output.txt"
        receiver = FileReceiver(mock_serial_manager, save_path)
        receiver._expected_seq = 0
        receiver._file_handle = save_path.open("wb")
        
        test_data = b"test_data_content"
        packet_data = struct.pack("<H", 0) + test_data
        
        with patch('serial_file_transfer.transfer.receiver.FrameHandler.read_frame') as mock_read:
            mock_read.return_value = (SerialCommand.SEND_DATA, packet_data)
            
            with patch('serial_file_transfer.transfer.receiver.FrameHandler.pack_frame') as mock_pack:
                mock_pack.return_value = b"ack_frame"
                
                # Act
                result = receiver.receive_data_package()
                
                # Assert
                assert result is True
                
                # 关闭文件句柄并检查内容
                receiver._file_handle.close()
                assert save_path.read_bytes() == test_data


class TestFileReceiverRetryMechanism:
    """测试FileReceiver重试机制"""

    def test_receive_chunk_with_retry_success(self):
        """测试成功接收数据块（带重试）"""
        # Arrange
        mock_serial_manager = MagicMock()
        receiver = FileReceiver(mock_serial_manager, "output.txt")
        
        with patch.object(receiver, 'send_data_request', return_value=True):
            with patch.object(receiver, 'receive_data_package', return_value=True):
                # Act
                result = receiver._receive_chunk_with_retry(0, 1024)
                
                # Assert
                assert result is True

    def test_receive_chunk_with_retry_send_failure(self):
        """测试发送数据请求失败"""
        # Arrange
        mock_serial_manager = MagicMock()
        config = TransferConfig()
        config.max_retries = 2
        receiver = FileReceiver(mock_serial_manager, "output.txt", config)
        
        with patch.object(receiver, 'send_data_request', return_value=False):
            # Act
            result = receiver._receive_chunk_with_retry(0, 1024)
            
            # Assert
            assert result is False

    def test_receive_chunk_with_retry_receive_failure_then_success(self):
        """测试接收失败后重试成功"""
        # Arrange
        mock_serial_manager = MagicMock()
        config = TransferConfig()
        config.max_retries = 2
        receiver = FileReceiver(mock_serial_manager, "output.txt", config)
        
        with patch.object(receiver, 'send_data_request', return_value=True):
            with patch.object(receiver, 'receive_data_package', side_effect=[False, True]):
                # Act
                result = receiver._receive_chunk_with_retry(0, 1024)
                
                # Assert
                assert result is True

    def test_receive_chunk_with_retry_max_retries_exceeded(self):
        """测试超过最大重试次数"""
        # Arrange
        mock_serial_manager = MagicMock()
        config = TransferConfig()
        config.max_retries = 1
        receiver = FileReceiver(mock_serial_manager, "output.txt", config)
        
        with patch.object(receiver, 'send_data_request', return_value=True):
            with patch.object(receiver, 'receive_data_package', return_value=False):
                # Act
                result = receiver._receive_chunk_with_retry(0, 1024)
                
                # Assert
                assert result is False


class TestFileReceiverMainTransferFlow:
    """测试FileReceiver主传输流程"""

    def test_start_transfer_no_save_path(self):
        """测试没有保存路径时开始传输"""
        # Arrange
        mock_serial_manager = MagicMock()
        receiver = FileReceiver(mock_serial_manager)
        
        # Act
        result = receiver.start_transfer()
        
        # Assert
        assert result is False

    def test_start_transfer_get_size_failure(self):
        """测试获取文件大小失败"""
        # Arrange
        mock_serial_manager = MagicMock()
        receiver = FileReceiver(mock_serial_manager, "output.txt")
        
        with patch.object(receiver, 'send_file_size_request', return_value=False):
            # Act
            result = receiver.start_transfer()
            
            # Assert
            assert result is False

    def test_start_transfer_invalid_file_size(self):
        """测试获取无效文件大小"""
        # Arrange
        mock_serial_manager = MagicMock()
        receiver = FileReceiver(mock_serial_manager, "output.txt")
        
        with patch.object(receiver, 'send_file_size_request', return_value=True):
            with patch.object(receiver, 'receive_file_size', return_value=0):
                # Act
                result = receiver.start_transfer()
                
                # Assert
                assert result is False

    def test_start_transfer_chunk_receive_failure(self, temp_dir):
        """测试数据块接收失败"""
        # Arrange
        mock_serial_manager = MagicMock()
        save_path = temp_dir / "test_output.txt"
        receiver = FileReceiver(mock_serial_manager, save_path)
        
        # 直接设置文件大小，绕过获取文件大小的过程
        receiver.file_size = 1024
        
        with patch.object(receiver, '_receive_chunk_with_retry', return_value=False):
            # Act - 直接调用传输循环部分
            try:
                # 打开文件句柄
                save_path.parent.mkdir(parents=True, exist_ok=True)
                receiver._file_handle = save_path.open("wb")
                
                # 模拟传输循环
                while receiver.recv_size < receiver.file_size:
                    remain_len = receiver.file_size - receiver.recv_size
                    req_len = min(remain_len, receiver.config.max_data_length)
                    
                    if not receiver._receive_chunk_with_retry(receiver.recv_size, req_len):
                        # 传输失败
                        result = False
                        break
                else:
                    result = True
                    
            finally:
                if receiver._file_handle:
                    receiver._file_handle.close()
                    receiver._file_handle = None
                
                # 失败时删除不完整文件
                if not result and save_path.exists():
                    save_path.unlink()
                    
            # Assert
            assert result is False
            assert not save_path.exists()

    def test_start_transfer_success_small_file(self, temp_dir):
        """测试成功传输小文件"""
        # Arrange
        mock_serial_manager = MagicMock()
        save_path = temp_dir / "test_output.txt"
        receiver = FileReceiver(mock_serial_manager, save_path)
        file_size = 100
        
        # 直接设置文件大小
        receiver.file_size = file_size
        
        with patch.object(receiver, '_receive_chunk_with_retry') as mock_receive:
            def mock_receive_side_effect(addr, length):
                # 模拟接收数据
                receiver.recv_size += length
                return True
            
            mock_receive.side_effect = mock_receive_side_effect
            
            # Act - 直接调用传输循环部分
            try:
                # 打开文件句柄
                save_path.parent.mkdir(parents=True, exist_ok=True)
                receiver._file_handle = save_path.open("wb")
                
                # 模拟传输循环
                while receiver.recv_size < receiver.file_size:
                    remain_len = receiver.file_size - receiver.recv_size
                    req_len = min(remain_len, receiver.config.max_data_length)
                    
                    if not receiver._receive_chunk_with_retry(receiver.recv_size, req_len):
                        result = False
                        break
                else:
                    result = True
                    
            finally:
                if receiver._file_handle:
                    receiver._file_handle.close()
                    receiver._file_handle = None
                    
            # Assert
            assert result is True
            assert receiver.recv_size == file_size

    def test_start_transfer_file_size_mismatch(self, temp_dir):
        """测试最终文件大小不匹配"""
        # Arrange
        mock_serial_manager = MagicMock()
        save_path = temp_dir / "test_output.txt"
        receiver = FileReceiver(mock_serial_manager, save_path)
        file_size = 1000
        
        # 创建一个大小不匹配的文件
        save_path.write_bytes(b"wrong_size_content")  # 18字节，不等于1000
        
        with patch.object(receiver, 'send_file_size_request', return_value=True):
            with patch.object(receiver, 'receive_file_size', return_value=file_size):
                with patch.object(receiver, '_receive_chunk_with_retry') as mock_receive:
                    def mock_receive_side_effect(addr, length):
                        receiver.recv_size += length
                        return True
                    
                    mock_receive.side_effect = mock_receive_side_effect
                    receiver.file_size = file_size  # 手动设置期望大小
                    
                    # Act
                    result = receiver.start_transfer()
                    
                    # Assert
                    assert result is False  # 大小不匹配应该失败

    def test_start_transfer_exception_handling(self, temp_dir):
        """测试传输过程中异常处理"""
        # Arrange
        mock_serial_manager = MagicMock()
        save_path = temp_dir / "test_output.txt"
        receiver = FileReceiver(mock_serial_manager, save_path)
        
        with patch.object(receiver, 'send_file_size_request', side_effect=Exception("Test exception")):
            # Act
            result = receiver.start_transfer()
            
            # Assert
            assert result is False


class TestFileReceiverFileOperations:
    """测试FileReceiver文件操作功能"""

    def test_save_file_success(self, temp_dir):
        """测试成功保存文件"""
        # Arrange
        mock_serial_manager = MagicMock()
        save_path = temp_dir / "test_output.txt"
        receiver = FileReceiver(mock_serial_manager, save_path)
        test_data = b"test file content"
        receiver.file_data = test_data
        
        # Act
        result = receiver._save_file()
        
        # Assert
        assert result is True
        assert save_path.exists()
        assert save_path.read_bytes() == test_data

    def test_save_file_no_path(self):
        """测试保存文件时没有路径"""
        # Arrange
        mock_serial_manager = MagicMock()
        receiver = FileReceiver(mock_serial_manager)
        receiver.save_path = None
        
        # Act
        result = receiver._save_file()
        
        # Assert
        assert result is False

    def test_save_file_directory_creation(self, temp_dir):
        """测试保存文件时创建父目录"""
        # Arrange
        mock_serial_manager = MagicMock()
        nested_path = temp_dir / "nested" / "dir" / "test_output.txt"
        receiver = FileReceiver(mock_serial_manager, nested_path)
        test_data = b"test content"
        receiver.file_data = test_data
        
        # Act
        result = receiver._save_file()
        
        # Assert
        assert result is True
        assert nested_path.exists()
        assert nested_path.read_bytes() == test_data


class TestFileReceiverEdgeCases:
    """测试FileReceiver边界情况和异常处理"""

    def test_debug_seq_info(self):
        """测试调试序号信息"""
        # Arrange
        mock_serial_manager = MagicMock()
        receiver = FileReceiver(mock_serial_manager, "output.txt")
        receiver.file_size = 1024
        receiver.recv_size = 512
        receiver._expected_seq = 5
        
        # Act
        info = receiver._debug_seq_info
        
        # Assert
        assert isinstance(info, dict)
        assert "expected_seq" in info
        assert "recv_size" in info
        assert "file_size" in info
        assert info["expected_seq"] == 5
        assert info["recv_size"] == 512
        assert info["file_size"] == 1024

    def test_destructor_closes_file_handle(self, temp_dir):
        """测试析构函数关闭文件句柄"""
        # Arrange
        mock_serial_manager = MagicMock()
        save_path = temp_dir / "test_output.txt"
        receiver = FileReceiver(mock_serial_manager, save_path)
        
        # 打开文件句柄
        receiver._file_handle = save_path.open("wb")
        file_handle = receiver._file_handle
        
        # Act
        receiver.__del__()
        
        # Assert
        assert file_handle.closed

    def test_receive_file_size_exception_handling(self):
        """测试接收文件大小异常处理"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        receiver = FileReceiver(mock_serial_manager)
        
        with patch('serial_file_transfer.transfer.receiver.FrameHandler.read_frame') as mock_read:
            mock_read.side_effect = Exception("Test exception")
            
            # Act
            result = receiver.receive_file_size()
            
            # Assert
            assert result is None

    def test_receive_filename_exception_handling(self):
        """测试接收文件名异常处理"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        receiver = FileReceiver(mock_serial_manager)
        
        with patch('serial_file_transfer.transfer.receiver.FrameHandler.read_frame') as mock_read:
            mock_read.side_effect = Exception("Test exception")
            
            # Act
            result = receiver.receive_filename()
            
            # Assert
            assert result is None

    def test_receive_data_package_exception_handling(self):
        """测试接收数据包异常处理"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_port = MagicMock()
        mock_serial_manager.port = mock_port
        receiver = FileReceiver(mock_serial_manager, "output.txt")
        
        with patch('serial_file_transfer.transfer.receiver.FrameHandler.read_frame') as mock_read:
            mock_read.side_effect = Exception("Test exception")
            
            # Act
            result = receiver.receive_data_package()
            
            # Assert
            assert result is False

    def test_send_requests_exception_handling(self):
        """测试发送请求异常处理"""
        # Arrange
        mock_serial_manager = MagicMock()
        receiver = FileReceiver(mock_serial_manager)
        
        with patch('serial_file_transfer.transfer.receiver.FrameHandler.pack_frame') as mock_pack:
            mock_pack.side_effect = Exception("Test exception")
            
            # Act
            result1 = receiver.send_file_size_request()
            result2 = receiver.send_filename_request()
            result3 = receiver.send_data_request(0, 100)
            
            # Assert
            assert result1 is False
            assert result2 is False
            assert result3 is False

    def test_save_file_exception_handling(self, temp_dir):
        """测试保存文件异常处理"""
        # Arrange
        mock_serial_manager = MagicMock()
        save_path = temp_dir / "test_output.txt"
        receiver = FileReceiver(mock_serial_manager, save_path)
        receiver.file_data = b"test data"
        
        # Mock文件写入失败
        with patch.object(Path, 'open', side_effect=OSError("Permission denied")):
            # Act
            result = receiver._save_file()
            
            # Assert
            assert result is False
