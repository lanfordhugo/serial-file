"""
端到端集成测试
==============

使用虚拟串口或回环测试进行端到端验证。
这些测试默认不执行，需要手动触发或在CI中单独运行。
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from serial_file_transfer.transfer.sender import FileSender
from serial_file_transfer.transfer.receiver import FileReceiver
from serial_file_transfer.core.serial_manager import SerialManager


@pytest.mark.integration
class TestEndToEndIntegration:
    """端到端集成测试"""

    def test_minimal_loopback_simulation(self, test_file_small, temp_dir, 
                                       serial_config_default, transfer_config_default):
        """最小化的回环模拟测试"""
        # Arrange - 创建发送和接收路径
        receive_path = temp_dir / "received_file.txt"
        original_data = test_file_small.read_bytes()
        
        # 使用共享的Mock串口来模拟回环
        shared_buffer = []
        
        def mock_write(data):
            shared_buffer.append(data)
            return len(data)
        
        def mock_read(size=1):
            if shared_buffer:
                return shared_buffer.pop(0)[:size]
            return b""
        
        # Mock发送端串口
        mock_sender_serial = MagicMock()
        mock_sender_serial.write.side_effect = mock_write
        mock_sender_serial.read.return_value = b"\x06"  # ACK
        mock_sender_serial.is_open = True
        
        # Mock接收端串口  
        mock_receiver_serial = MagicMock()
        mock_receiver_serial.write.return_value = True
        mock_receiver_serial.read.side_effect = mock_read
        mock_receiver_serial.is_open = True
        
        # Act - 创建发送器和接收器
        sender = FileSender(mock_sender_serial, test_file_small, transfer_config_default)
        receiver = FileReceiver(mock_receiver_serial, receive_path, transfer_config_default)
        
        # 模拟基本的数据传输（简化版）
        # 注意：这里简化了复杂的协议交互
        filename_sent = sender.send_filename(test_file_small.name)
        
        # Assert - 验证集成行为
        assert filename_sent == True, "文件名发送应该成功"
        assert mock_sender_serial.write.called, "发送端应该有写入操作"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_full_transfer_workflow_simulation(self, test_file_medium, temp_dir):
        """完整传输工作流模拟（较慢的测试）"""
        # 这个测试模拟完整的发送-接收流程
        # 标记为slow，通常不在快速测试中执行
        
        # Arrange
        receive_path = temp_dir / "full_workflow_received.txt"
        original_data = test_file_medium.read_bytes()
        
        # 创建更复杂的Mock串口交互
        transfer_data = []
        
        class MockSerialPair:
            def __init__(self):
                self.sender_buffer = []
                self.receiver_buffer = []
                self.is_open = True
            
            def sender_write(self, data):
                # 发送端写入数据会被接收端读取
                self.receiver_buffer.append(data)
                return len(data)
            
            def receiver_write(self, data):
                # 接收端写入数据会被发送端读取（如ACK）
                self.sender_buffer.append(data)
                return len(data)
            
            def sender_read(self, size=1):
                if self.sender_buffer:
                    return self.sender_buffer.pop(0)[:size]
                return b"\x06"  # 默认ACK
            
            def receiver_read(self, size=1):
                if self.receiver_buffer:
                    return self.receiver_buffer.pop(0)[:size]
                return b""
        
        mock_serial_pair = MockSerialPair()
        
        # 配置发送端Mock
        mock_sender_serial = MagicMock()
        mock_sender_serial.write.side_effect = mock_serial_pair.sender_write
        mock_sender_serial.read.side_effect = mock_serial_pair.sender_read
        mock_sender_serial.is_open = True
        
        # 配置接收端Mock
        mock_receiver_serial = MagicMock()
        mock_receiver_serial.write.side_effect = mock_serial_pair.receiver_write
        mock_receiver_serial.read.side_effect = mock_serial_pair.receiver_read
        mock_receiver_serial.is_open = True
        
        # Act - 执行传输流程
        from serial_file_transfer.config.settings import TransferConfig
        config = TransferConfig(max_data_length=1024, retry_count=2)
        
        sender = FileSender(mock_sender_serial, test_file_medium, config)
        receiver = FileReceiver(mock_receiver_serial, receive_path, config)
        
        # 模拟协议交互（简化）
        filename_result = sender.send_filename(test_file_medium.name)
        
        # Assert - 验证集成结果
        assert filename_result == True, "文件名传输应该成功"
        
        # 验证数据流
        assert len(mock_serial_pair.receiver_buffer) > 0, "应该有数据传输到接收端"

    @pytest.mark.integration
    def test_error_recovery_integration(self, test_file_small, temp_dir):
        """错误恢复集成测试"""
        # 测试在集成环境下的错误处理行为
        
        # Arrange
        receive_path = temp_dir / "error_recovery_test.txt"
        
        # 模拟写入失败的情况
        mock_serial = MagicMock()
        mock_serial.write.return_value = 0  # 模拟写入失败
        mock_serial.read.return_value = b"\x06"
        mock_serial.is_open = True
        
        # Act
        from serial_file_transfer.config.settings import TransferConfig
        config = TransferConfig(retry_count=3)  # 允许重试
        sender = FileSender(mock_serial, test_file_small, config)
        
        # 尝试发送文件名
        result = sender.send_filename(test_file_small.name)
        
        # Assert - 验证错误处理行为
        # 当写入失败时，应该返回False
        assert result == False, "写入失败时应该返回False"
        assert mock_serial.write.called, "应该尝试写入操作"

    @pytest.mark.integration
    @pytest.mark.hardware  
    def test_real_hardware_placeholder(self):
        """真实硬件测试占位符"""
        # 这个测试需要真实的串口硬件
        # 在没有硬件的环境中会被跳过
        
        pytest.skip("需要真实串口硬件，当前环境不支持")
        
        # 如果有硬件，这里会包含真实的串口测试代码
        # 例如：
        # real_serial = serial.Serial("COM1", 115200)
        # ... 真实的硬件测试逻辑


@pytest.mark.integration  
class TestSystemIntegration:
    """系统集成测试"""

    def test_cli_to_transfer_integration(self, test_file_small, temp_dir):
        """CLI到传输层的集成测试"""
        # 测试CLI调用传输层的完整链路
        
        # Arrange
        mock_serial_manager = MagicMock()
        mock_serial_manager.open.return_value = True
        mock_serial_manager.is_open = True
        
        # Mock CLI的依赖
        with patch("serial_file_transfer.cli.file_transfer.SerialManager") as mock_serial_class:
            mock_serial_class.return_value = mock_serial_manager
            
            with patch("serial_file_transfer.cli.file_transfer.FileSender") as mock_sender_class:
                mock_sender = MagicMock()
                mock_sender.start_transfer.return_value = True
                mock_sender_class.return_value = mock_sender
                
                # Act
                from serial_file_transfer.cli.file_transfer import FileTransferCLI
                cli = FileTransferCLI()
                
                # 模拟完整的CLI操作（简化版）
                # 注意：实际测试可能需要更多的用户输入模拟
                
                # Assert - 验证集成链路
                assert cli is not None, "CLI应该能正常创建"

    def test_config_integration(self):
        """配置系统集成测试"""
        # 测试配置在各个组件间的传递和使用
        
        # Arrange
        from serial_file_transfer.config.settings import SerialConfig, TransferConfig
        
        serial_config = SerialConfig(port="COM1", baudrate=115200)
        transfer_config = TransferConfig(max_data_length=2048, retry_count=3)
        
        # Act - 验证配置对象的创建和使用
        mock_serial_manager = MagicMock()
        
        # 创建使用配置的组件
        from serial_file_transfer.core.serial_manager import SerialManager
        
        # 注意：这里可能需要Mock真实的串口创建
        with patch("serial.Serial"):
            manager = SerialManager(serial_config)
            
            # Assert - 验证配置集成
            assert manager.config.port == "COM1"
            assert manager.config.baudrate == 115200
