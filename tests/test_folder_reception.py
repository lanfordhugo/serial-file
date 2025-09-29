"""
文件名称: test_folder_reception.py
内容摘要: 文件夹接收功能的单元测试
当前版本: v1.0.0
作者: AI Assistant
创建日期: 2025-09-29
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import tempfile

from src.serial_file_transfer.cli.file_transfer import FileTransferCLI
from src.serial_file_transfer.config.settings import TransferConfig
from src.serial_file_transfer.transfer.file_manager import ReceiverFileManager


class TestFileTransferCLIFolderReception:
    """测试文件传输CLI的文件夹接收功能"""

    @pytest.fixture
    def mock_serial_manager(self):
        """创建模拟串口管理器"""
        mock = Mock()
        mock.open.return_value = True
        mock.close.return_value = None
        return mock

    @pytest.fixture
    def transfer_config(self):
        """创建传输配置"""
        return TransferConfig()

    def test_detect_transmission_type_volume_file(self, mock_serial_manager, transfer_config):
        """测试检测传输类型 - 分卷文件"""
        with patch('src.serial_file_transfer.cli.file_transfer.FileReceiver') as mock_receiver:
            # 模拟接收到分卷文件名
            mock_instance = mock_receiver.return_value
            mock_instance.send_filename_request.return_value = True
            mock_instance.receive_filename.return_value = "archive.zip.001"
            
            result = FileTransferCLI._detect_transmission_type(mock_serial_manager, transfer_config)
            
            assert result == "folder"

    def test_detect_transmission_type_path_separator(self, mock_serial_manager, transfer_config):
        """测试检测传输类型 - 包含路径分隔符"""
        with patch('src.serial_file_transfer.cli.file_transfer.FileReceiver') as mock_receiver:
            # 模拟接收到包含路径的文件名
            mock_instance = mock_receiver.return_value
            mock_instance.send_filename_request.return_value = True
            mock_instance.receive_filename.return_value = "subfolder/document.txt"
            
            result = FileTransferCLI._detect_transmission_type(mock_serial_manager, transfer_config)
            
            assert result == "folder"

    def test_detect_transmission_type_single_file(self, mock_serial_manager, transfer_config):
        """测试检测传输类型 - 单文件"""
        with patch('src.serial_file_transfer.cli.file_transfer.FileReceiver') as mock_receiver:
            # 模拟接收到单个文件名
            mock_instance = mock_receiver.return_value
            mock_instance.send_filename_request.return_value = True
            mock_instance.receive_filename.return_value = "document.pdf"
            
            result = FileTransferCLI._detect_transmission_type(mock_serial_manager, transfer_config)
            
            assert result == "file"

    def test_detect_transmission_type_uncertain_defaults_to_folder(self, mock_serial_manager, transfer_config):
        """测试检测传输类型 - 不确定时默认为文件夹模式"""
        with patch('src.serial_file_transfer.cli.file_transfer.FileReceiver') as mock_receiver:
            # 模拟接收到未知类型文件名
            mock_instance = mock_receiver.return_value
            mock_instance.send_filename_request.return_value = True
            mock_instance.receive_filename.return_value = "unknown_file.xyz"
            
            result = FileTransferCLI._detect_transmission_type(mock_serial_manager, transfer_config)
            
            assert result == "folder"  # 默认为更安全的文件夹模式

    def test_detect_transmission_type_request_failed(self, mock_serial_manager, transfer_config):
        """测试检测传输类型 - 请求失败时默认为单文件"""
        with patch('src.serial_file_transfer.cli.file_transfer.FileReceiver') as mock_receiver:
            # 模拟文件名请求失败
            mock_instance = mock_receiver.return_value
            mock_instance.send_filename_request.return_value = False
            
            result = FileTransferCLI._detect_transmission_type(mock_serial_manager, transfer_config)
            
            assert result == "file"

    def test_detect_transmission_type_receive_failed(self, mock_serial_manager, transfer_config):
        """测试检测传输类型 - 接收文件名失败时默认为单文件"""
        with patch('src.serial_file_transfer.cli.file_transfer.FileReceiver') as mock_receiver:
            # 模拟接收文件名失败
            mock_instance = mock_receiver.return_value
            mock_instance.send_filename_request.return_value = True
            mock_instance.receive_filename.return_value = None
            
            result = FileTransferCLI._detect_transmission_type(mock_serial_manager, transfer_config)
            
            assert result == "file"

    @pytest.mark.parametrize("filename,expected_type", [
        # 分卷文件测试
        ("archive.zip.001", "folder"),
        ("backup.rar.002", "folder"), 
        ("data.part1", "folder"),
        ("split.z01", "folder"),
        ("file.r01", "folder"),
        
        # 路径分隔符测试
        ("folder/file.txt", "folder"),
        ("dir\\file.doc", "folder"),
        ("deep/nested/path/file.pdf", "folder"),
        
        # 单文件测试
        ("document.pdf", "file"),
        ("image.jpg", "file"),
        ("video.mp4", "file"),
        ("program.exe", "file"),
        
        # 不确定类型（默认为folder）
        ("unknown.xyz", "folder"),
        ("data", "folder"),
        ("config.conf", "folder"),
    ])
    def test_detect_transmission_type_various_filenames(self, mock_serial_manager, transfer_config, filename, expected_type):
        """测试各种文件名的传输类型检测"""
        with patch('src.serial_file_transfer.cli.file_transfer.FileReceiver') as mock_receiver:
            mock_instance = mock_receiver.return_value
            mock_instance.send_filename_request.return_value = True
            mock_instance.receive_filename.return_value = filename
            
            result = FileTransferCLI._detect_transmission_type(mock_serial_manager, transfer_config)
            
            assert result == expected_type, f"文件名 '{filename}' 应该被检测为 '{expected_type}' 类型"

    def test_handle_single_file_receive_success(self):
        """测试单文件接收处理 - 成功"""
        with tempfile.TemporaryDirectory() as temp_dir:
            recv_dir = Path(temp_dir)
            mock_serial = Mock()
            config = TransferConfig()
            
            with patch('src.serial_file_transfer.cli.file_transfer.FileReceiver') as mock_receiver:
                mock_instance = mock_receiver.return_value
                mock_instance.send_filename_request.return_value = True
                mock_instance.receive_filename.return_value = "test.txt"
                mock_instance.start_transfer.return_value = True
                
                result = FileTransferCLI._handle_single_file_receive(recv_dir, mock_serial, config)
                
                assert result is True
                mock_instance.init_receive_params.assert_called_once()
                mock_instance.start_transfer.assert_called_once()

    def test_handle_single_file_receive_filename_failed(self):
        """测试单文件接收处理 - 获取文件名失败"""
        with tempfile.TemporaryDirectory() as temp_dir:
            recv_dir = Path(temp_dir)
            mock_serial = Mock()
            config = TransferConfig()
            
            with patch('src.serial_file_transfer.cli.file_transfer.FileReceiver') as mock_receiver:
                mock_instance = mock_receiver.return_value
                mock_instance.send_filename_request.return_value = False
                
                result = FileTransferCLI._handle_single_file_receive(recv_dir, mock_serial, config)
                
                assert result is False

    def test_handle_single_file_receive_transfer_failed(self):
        """测试单文件接收处理 - 传输失败"""
        with tempfile.TemporaryDirectory() as temp_dir:
            recv_dir = Path(temp_dir)
            mock_serial = Mock()
            config = TransferConfig()
            
            with patch('src.serial_file_transfer.cli.file_transfer.FileReceiver') as mock_receiver:
                mock_instance = mock_receiver.return_value
                mock_instance.send_filename_request.return_value = True
                mock_instance.receive_filename.return_value = "test.txt"
                mock_instance.start_transfer.return_value = False
                
                result = FileTransferCLI._handle_single_file_receive(recv_dir, mock_serial, config)
                
                assert result is False

    def test_handle_folder_receive_success(self):
        """测试文件夹接收处理 - 成功"""
        with tempfile.TemporaryDirectory() as temp_dir:
            recv_dir = Path(temp_dir)
            mock_serial = Mock()
            config = TransferConfig()
            
            # 使用patch.object来更精确地模拟
            with patch('src.serial_file_transfer.transfer.file_manager.ReceiverFileManager') as mock_manager:
                mock_instance = mock_manager.return_value
                mock_instance.start_batch_receive.return_value = True
                
                result = FileTransferCLI._handle_folder_receive(recv_dir, mock_serial, config)
                
                assert result is True
                mock_manager.assert_called_once_with(recv_dir, mock_serial, config)
                mock_instance.start_batch_receive.assert_called_once()

    def test_handle_folder_receive_failed(self):
        """测试文件夹接收处理 - 失败"""
        with tempfile.TemporaryDirectory() as temp_dir:
            recv_dir = Path(temp_dir)
            mock_serial = Mock()
            config = TransferConfig()
            
            with patch('src.serial_file_transfer.transfer.file_manager.ReceiverFileManager') as mock_manager:
                mock_instance = mock_manager.return_value
                mock_instance.start_batch_receive.return_value = False
                
                result = FileTransferCLI._handle_folder_receive(recv_dir, mock_serial, config)
                
                assert result is False

    def test_handle_folder_receive_exception(self):
        """测试文件夹接收处理 - 异常"""
        with tempfile.TemporaryDirectory() as temp_dir:
            recv_dir = Path(temp_dir)
            mock_serial = Mock()
            config = TransferConfig()
            
            with patch('src.serial_file_transfer.transfer.file_manager.ReceiverFileManager') as mock_manager:
                mock_manager.side_effect = Exception("测试异常")
                
                result = FileTransferCLI._handle_folder_receive(recv_dir, mock_serial, config)
                
                assert result is False

    def test_smart_receive_folder_mode_integration(self):
        """测试智能接收模式 - 文件夹模式集成"""
        with patch.multiple(
            'src.serial_file_transfer.cli.file_transfer.FileTransferCLI',
            get_user_input_port=lambda: "COM1",
            _detect_transmission_type=lambda serial_mgr, config: "folder",
            _handle_folder_receive=lambda recv_dir, serial_mgr, config: True
        ):
            with patch('src.serial_file_transfer.cli.file_transfer.ConfigLoader'):
                with patch('src.serial_file_transfer.cli.file_transfer.SerialManager'):
                    with patch('os.getcwd', return_value="/tmp"):
                        result = FileTransferCLI.smart_receive()
                        
                        assert result is True

    def test_smart_receive_single_file_mode_integration(self):
        """测试智能接收模式 - 单文件模式集成"""
        with patch.multiple(
            'src.serial_file_transfer.cli.file_transfer.FileTransferCLI',
            get_user_input_port=lambda: "COM1",
            _detect_transmission_type=lambda serial_mgr, config: "file",
            _handle_single_file_receive=lambda recv_dir, serial_mgr, config: True
        ):
            with patch('src.serial_file_transfer.cli.file_transfer.ConfigLoader'):
                with patch('src.serial_file_transfer.cli.file_transfer.SerialManager'):
                    with patch('os.getcwd', return_value="/tmp"):
                        result = FileTransferCLI.smart_receive()
                        
                        assert result is True

    def test_smart_receive_port_selection_failed(self):
        """测试智能接收模式 - 端口选择失败"""
        with patch('src.serial_file_transfer.cli.file_transfer.FileTransferCLI.get_user_input_port', return_value=None):
            result = FileTransferCLI.smart_receive()
            
            assert result is False

    def test_volume_file_detection_comprehensive(self):
        """测试分卷文件检测的全面性"""
        volume_extensions = [
            '.001', '.002', '.003', '.004', '.005',
            '.part1', '.part2', '.part3', '.part4', '.part5', 
            '.z01', '.z02', '.z03', '.rar', '.r01', '.r02'
        ]
        
        for ext in volume_extensions:
            filename = f"archive{ext}"
            
            with patch('src.serial_file_transfer.cli.file_transfer.FileReceiver') as mock_receiver:
                mock_instance = mock_receiver.return_value
                mock_instance.send_filename_request.return_value = True
                mock_instance.receive_filename.return_value = filename
                
                result = FileTransferCLI._detect_transmission_type(Mock(), TransferConfig())
                
                assert result == "folder", f"分卷文件 {filename} 应该被检测为文件夹模式"

    def test_error_handling_in_detection(self):
        """测试检测过程中的错误处理"""
        mock_serial = Mock()
        config = TransferConfig()
        
        with patch('src.serial_file_transfer.cli.file_transfer.FileReceiver') as mock_receiver:
            # 模拟FileReceiver构造异常
            mock_receiver.side_effect = Exception("构造异常")
            
            result = FileTransferCLI._detect_transmission_type(mock_serial, config)
            
            assert result == "file"  # 异常时应该返回默认值
