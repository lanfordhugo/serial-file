"""
文件传输简化功能测试
==================

专注核心传输行为的黑盒测试，避免复杂的协议细节。
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from serial_file_transfer.transfer.sender import FileSender
from serial_file_transfer.transfer.receiver import FileReceiver


class TestFileTransferCore:
    """文件传输核心功能测试"""

    def test_sender_initialization_and_file_loading(self, test_file_small, transfer_config_default):
        """测试发送器初始化和文件加载行为"""
        # Arrange
        mock_serial_manager = MagicMock()
        
        # Act
        sender = FileSender(mock_serial_manager, test_file_small, transfer_config_default)
        
        # Assert - 验证初始化行为
        assert sender.file_path == test_file_small
        assert sender.file_size == test_file_small.stat().st_size
        assert sender.file_size > 0, "文件大小应该大于0"

    def test_receiver_initialization_and_save_path(self, temp_dir, transfer_config_default):
        """测试接收器初始化和保存路径行为"""
        # Arrange
        mock_serial_manager = MagicMock()
        save_path = temp_dir / "test_receive.txt"
        
        # Act
        receiver = FileReceiver(mock_serial_manager, save_path, transfer_config_default)
        
        # Assert - 验证初始化行为
        assert receiver.save_path == save_path
        assert receiver.recv_size == 0, "初始接收大小应该为0"

    @pytest.mark.parametrize(
        "file_fixture", ["test_file_small", "test_file_medium", "test_file_large"]
    )
    def test_file_data_access_behavior(self, request, file_fixture, transfer_config_default):
        """测试文件数据访问行为 - 不同大小文件"""
        # Arrange
        test_file = request.getfixturevalue(file_fixture)
        mock_serial_manager = MagicMock()
        sender = FileSender(mock_serial_manager, test_file, transfer_config_default)
        
        # Act - 测试数据读取行为
        chunk_size = 1024
        file_data = sender.get_file_data(0, chunk_size)
        
        # Assert - 验证数据访问行为
        assert isinstance(file_data, bytes), "应该返回字节数据"
        assert len(file_data) <= chunk_size, "返回数据不应超过请求大小"
        if sender.file_size >= chunk_size:
            assert len(file_data) == chunk_size, "大文件应该返回完整块"
        else:
            assert len(file_data) == sender.file_size, "小文件应该返回全部数据"

    def test_transfer_configuration_behavior(self, test_file_small):
        """测试传输配置行为"""
        # Arrange
        mock_serial_manager = MagicMock()
        
        # 测试不同配置的行为差异
        configs = [
            TransferConfig(max_data_length=512, retry_count=1),    # 小块，少重试
            TransferConfig(max_data_length=2048, retry_count=5),   # 大块，多重试
        ]
        
        for config in configs:
            # Act
            sender = FileSender(mock_serial_manager, test_file_small, config)
            
            # Assert - 验证配置影响行为
            assert sender.config.max_data_length == config.max_data_length
            assert sender.config.retry_count == config.retry_count
            
            # 验证数据读取受配置影响
            data_chunk = sender.get_file_data(0, config.max_data_length)
            assert len(data_chunk) <= config.max_data_length

    def test_file_not_found_error_behavior(self, temp_dir, transfer_config_default):
        """测试文件不存在的错误处理行为"""
        # Arrange
        nonexistent_file = temp_dir / "does_not_exist.txt"
        mock_serial_manager = MagicMock()
        
        # Act - FileSender不会立即抛出异常，而是在init_file时处理
        sender = FileSender(mock_serial_manager, None, transfer_config_default)
        
        # Assert - 验证初始化不存在文件的行为
        result = sender.init_file(nonexistent_file)
        assert result == False, "初始化不存在的文件应该失败"
        assert sender.file_size == 0, "文件大小应该为0"

    def test_invalid_save_path_behavior(self, transfer_config_default):
        """测试无效保存路径的行为"""
        # Arrange
        mock_serial_manager = MagicMock()
        invalid_path = Path("/invalid/path/that/does/not/exist/file.txt")
        
        # Act - 创建接收器（注意：可能不会立即失败）
        receiver = FileReceiver(mock_serial_manager, invalid_path, transfer_config_default)
        
        # Assert - 验证路径设置行为
        assert receiver.save_path == invalid_path
        # 实际的错误可能在尝试写入文件时才会发生

    @pytest.mark.parametrize(
        "chunk_size,expected_chunks", [
            (512, 2),   # 小块：1024字节文件需要2个512字节块
            (1024, 1),  # 正好：1024字节文件需要1个1024字节块  
            (2048, 1),  # 大块：1024字节文件只需要1个块
        ]
    )
    def test_chunked_reading_behavior(self, test_file_small, transfer_config_default,
                                    chunk_size, expected_chunks):
        """测试分块读取行为"""
        # Arrange
        mock_serial_manager = MagicMock()
        sender = FileSender(mock_serial_manager, test_file_small, transfer_config_default)
        file_size = sender.file_size
        
        # Act - 模拟分块读取
        chunks_read = 0
        bytes_read = 0
        
        while bytes_read < file_size:
            remaining = file_size - bytes_read
            read_size = min(chunk_size, remaining)
            
            data = sender.get_file_data(bytes_read, read_size)
            
            assert len(data) == read_size, f"应该读取 {read_size} 字节"
            bytes_read += len(data)
            chunks_read += 1
        
        # Assert - 验证分块行为
        assert chunks_read == expected_chunks, f"应该读取 {expected_chunks} 个块"
        assert bytes_read == file_size, "应该读取完整文件"

    def test_empty_file_behavior(self, temp_dir, transfer_config_default):
        """测试空文件处理行为"""
        # Arrange
        empty_file = temp_dir / "empty.txt"
        empty_file.write_bytes(b"")  # 创建空文件
        
        mock_serial_manager = MagicMock()
        
        # Act
        sender = FileSender(mock_serial_manager, empty_file, transfer_config_default)
        
        # Assert - 验证空文件行为
        assert sender.file_size == 0, "空文件大小应该为0"
        
        # 尝试读取数据
        data = sender.get_file_data(0, 1024)
        assert data == b"", "空文件应该返回空字节"

    def test_filename_sending_behavior(self, test_file_small, transfer_config_default):
        """测试文件名发送行为 - 简化版"""
        # Arrange
        mock_serial_manager = MagicMock()
        mock_serial_manager.write.return_value = True
        
        sender = FileSender(mock_serial_manager, test_file_small, transfer_config_default)
        
        # Act - 测试发送文件名行为
        filename = test_file_small.name
        result = sender.send_filename(filename)
        
        # Assert - 验证文件名发送行为
        assert result == True, "发送文件名应该成功"
        assert mock_serial_manager.write.called, "应该调用串口写入"


# 导入必要的类
from serial_file_transfer.config.settings import TransferConfig
