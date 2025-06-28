"""
智能CLI模式测试
==============

测试智能发送和接收CLI接口的基础功能。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.serial_file_transfer.cli.file_transfer import FileTransferCLI
from src.serial_file_transfer.core.probe_manager import ProbeManager
from src.serial_file_transfer.core.probe_structures import ProbeResponseData, ProbeRequestData


class TestSmartCLI:
    """测试智能CLI接口"""
    
    def test_smart_send_method_exists(self):
        """测试智能发送方法是否存在"""
        assert hasattr(FileTransferCLI, 'smart_send')
        assert callable(getattr(FileTransferCLI, 'smart_send'))
    
    def test_smart_receive_method_exists(self):
        """测试智能接收方法是否存在"""
        assert hasattr(FileTransferCLI, 'smart_receive')
        assert callable(getattr(FileTransferCLI, 'smart_receive'))
    
    @patch('src.serial_file_transfer.cli.file_transfer.input')
    @patch('src.serial_file_transfer.cli.file_transfer.Path')
    @patch('src.serial_file_transfer.cli.file_transfer.SerialManager')
    @patch('src.serial_file_transfer.cli.file_transfer.ProbeManager')
    def test_smart_send_basic_flow(self, mock_probe_manager_class, mock_serial_manager_class, 
                                  mock_path, mock_input):
        """测试智能发送的基本流程"""
        # 模拟用户输入
        mock_input.side_effect = [
            '/test/file.txt',  # 源路径
            'COM1',           # 串口号
            ''                # 确认退出
        ]
        
        # 模拟路径
        mock_path_obj = Mock()
        mock_path_obj.exists.return_value = True
        mock_path_obj.is_file.return_value = True
        mock_path_obj.stat.return_value.st_size = 1024
        mock_path.return_value = mock_path_obj
        
        # 模拟串口管理器
        mock_serial_manager = Mock()
        mock_serial_manager_class.return_value.__enter__.return_value = mock_serial_manager
        mock_serial_manager_class.return_value.__exit__.return_value = None
        
        # 模拟探测管理器
        mock_probe_manager = Mock(spec=ProbeManager)
        mock_probe_manager_class.return_value = mock_probe_manager
        
        # 模拟探测响应
        mock_response = ProbeResponseData(
            device_id=0x12345678,
            protocol_version=1,
            random_seed=0x87654321,
            supported_baudrates=[115200, 921600]
        )
        mock_probe_manager.send_probe_request.return_value = mock_response
        mock_probe_manager.negotiate_capability.return_value = 921600
        mock_probe_manager.switch_baudrate.return_value = True
        
        # 模拟文件发送器
        with patch('src.serial_file_transfer.cli.file_transfer.FileSender') as mock_sender_class:
            mock_sender = Mock()
            mock_sender.start_transfer.return_value = True
            mock_sender_class.return_value = mock_sender
            
            # 执行测试
            result = FileTransferCLI.smart_send()
            
            # 验证基本调用
            assert result is True
            mock_probe_manager.send_probe_request.assert_called_once()
            mock_probe_manager.negotiate_capability.assert_called_once()
            mock_probe_manager.switch_baudrate.assert_called_once()
    
    @patch('src.serial_file_transfer.cli.file_transfer.input')
    @patch('src.serial_file_transfer.cli.file_transfer.SerialManager')
    @patch('src.serial_file_transfer.cli.file_transfer.ProbeManager')
    def test_smart_receive_basic_flow(self, mock_probe_manager_class, mock_serial_manager_class, 
                                     mock_input):
        """测试智能接收的基本流程"""
        # 模拟用户输入
        mock_input.side_effect = [
            'COM1',           # 串口号
            '/test/output',   # 保存路径
            ''                # 确认退出
        ]
        
        # 模拟串口管理器
        mock_serial_manager = Mock()
        mock_serial_manager_class.return_value.__enter__.return_value = mock_serial_manager
        mock_serial_manager_class.return_value.__exit__.return_value = None
        
        # 模拟探测管理器
        mock_probe_manager = Mock(spec=ProbeManager)
        mock_probe_manager_class.return_value = mock_probe_manager
        
        # 模拟探测请求
        mock_request = ProbeRequestData(
            device_id=0x12345678,
            protocol_version=1,
            random_seed=0x87654321
        )
        mock_probe_manager.wait_for_probe_request.return_value = mock_request
        mock_probe_manager.send_probe_response.return_value = True
        mock_probe_manager._receive_probe_frame.side_effect = [
            b'capability_data',  # 能力协商数据
            b'switch_data'       # 切换数据
        ]
        mock_probe_manager.handle_capability_nego.return_value = True
        mock_probe_manager.handle_baudrate_switch.return_value = True
        mock_probe_manager.target_baudrate = 921600
        
        # 模拟文件接收器
        with patch('src.serial_file_transfer.cli.file_transfer.FileReceiver') as mock_receiver_class:
            mock_receiver = Mock()
            mock_receiver.start_transfer.return_value = True
            mock_receiver_class.return_value = mock_receiver
            
            # 执行测试
            result = FileTransferCLI.smart_receive()
            
            # 验证基本调用
            assert result is True
            mock_probe_manager.wait_for_probe_request.assert_called_once()
            mock_probe_manager.send_probe_response.assert_called_once()
    
    @patch('src.serial_file_transfer.cli.file_transfer.input')
    @patch('src.serial_file_transfer.cli.file_transfer.Path')
    @patch('src.serial_file_transfer.cli.file_transfer.SerialManager')
    @patch('src.serial_file_transfer.cli.file_transfer.ProbeManager')
    def test_smart_send_no_device_found(self, mock_probe_manager_class, mock_serial_manager_class, 
                                       mock_path, mock_input):
        """测试智能发送找不到设备的情况"""
        # 模拟用户输入
        mock_input.side_effect = [
            '/test/file.txt',  # 源路径
            'COM1',           # 串口号
            ''                # 确认退出
        ]
        
        # 模拟路径
        mock_path_obj = Mock()
        mock_path_obj.exists.return_value = True
        mock_path_obj.is_file.return_value = True
        mock_path.return_value = mock_path_obj
        
        # 模拟串口管理器
        mock_serial_manager = Mock()
        mock_serial_manager_class.return_value.__enter__.return_value = mock_serial_manager
        mock_serial_manager_class.return_value.__exit__.return_value = None
        
        # 模拟探测管理器 - 返回None表示未找到设备
        mock_probe_manager = Mock(spec=ProbeManager)
        mock_probe_manager_class.return_value = mock_probe_manager
        mock_probe_manager.send_probe_request.return_value = None
        
        # 执行测试
        result = FileTransferCLI.smart_send()
        
        # 验证结果
        assert result is False
        mock_probe_manager.send_probe_request.assert_called_once()
    
    @patch('src.serial_file_transfer.cli.file_transfer.input')
    @patch('src.serial_file_transfer.cli.file_transfer.SerialManager')
    @patch('src.serial_file_transfer.cli.file_transfer.ProbeManager')
    def test_smart_receive_timeout(self, mock_probe_manager_class, mock_serial_manager_class, 
                                  mock_input):
        """测试智能接收超时的情况"""
        # 模拟用户输入
        mock_input.side_effect = [
            'COM1',           # 串口号
            '/test/output',   # 保存路径
            ''                # 确认退出
        ]
        
        # 模拟串口管理器
        mock_serial_manager = Mock()
        mock_serial_manager_class.return_value.__enter__.return_value = mock_serial_manager
        mock_serial_manager_class.return_value.__exit__.return_value = None
        
        # 模拟探测管理器 - 返回None表示超时
        mock_probe_manager = Mock(spec=ProbeManager)
        mock_probe_manager_class.return_value = mock_probe_manager
        mock_probe_manager.wait_for_probe_request.return_value = None
        
        # 执行测试
        result = FileTransferCLI.smart_receive()
        
        # 验证结果
        assert result is False
        mock_probe_manager.wait_for_probe_request.assert_called_once()
    
    def test_imports_available(self):
        """测试所需的导入是否可用"""
        # 验证关键模块都可以导入
        from src.serial_file_transfer.cli.file_transfer import FileTransferCLI
        from src.serial_file_transfer.config.constants import PROBE_BAUDRATE, ProbeCommand
        from src.serial_file_transfer.core.probe_manager import ProbeManager
        
        # 验证常量存在
        assert PROBE_BAUDRATE == 115200
        assert hasattr(ProbeCommand, 'PROBE_REQUEST') 