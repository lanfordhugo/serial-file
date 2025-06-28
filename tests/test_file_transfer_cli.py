#!/usr/bin/env python3
"""
统一文件传输CLI测试
==================

测试FileTransferCLI类的各种功能。
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from serial_file_transfer.cli.file_transfer import FileTransferCLI


class TestFileTransferCLI:
    """FileTransferCLI测试类"""
    
    def test_detect_path_type_file(self, tmp_path):
        """测试文件路径检测"""
        # 创建临时文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        # 测试文件检测
        result = FileTransferCLI._detect_path_type(str(test_file))
        assert result == 'file'
    
    def test_detect_path_type_folder(self, tmp_path):
        """测试文件夹路径检测"""
        # 创建临时文件夹
        test_folder = tmp_path / "test_folder"
        test_folder.mkdir()
        
        # 测试文件夹检测
        result = FileTransferCLI._detect_path_type(str(test_folder))
        assert result == 'folder'
    
    def test_detect_path_type_invalid(self, tmp_path):
        """测试无效路径检测"""
        # 测试不存在的路径
        invalid_path = tmp_path / "nonexistent"
        
        with pytest.raises(ValueError, match="无效的路径类型"):
            FileTransferCLI._detect_path_type(str(invalid_path))
    
    @patch('builtins.input')
    @patch('serial_file_transfer.cli.file_transfer.SerialManager.print_available_ports')
    def test_get_user_input_port(self, mock_print_ports, mock_input):
        """测试获取用户输入串口号"""
        mock_input.return_value = "COM1"
        
        result = FileTransferCLI.get_user_input_port()
        
        assert result == "COM1"
        mock_print_ports.assert_called_once()
    
    @patch('builtins.input')
    @patch('serial_file_transfer.cli.file_transfer.SerialManager.print_available_ports')
    def test_get_user_input_port_empty_retry(self, mock_print_ports, mock_input):
        """测试空输入重试逻辑"""
        mock_input.side_effect = ["", "  ", "COM1"]
        
        result = FileTransferCLI.get_user_input_port()
        
        assert result == "COM1"
        assert mock_input.call_count == 3
    
    @patch('builtins.input')
    def test_get_user_input_source_path(self, mock_input, tmp_path):
        """测试获取源路径输入"""
        # 创建临时文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        
        mock_input.return_value = str(test_file)
        
        result = FileTransferCLI.get_user_input_source_path()
        
        assert result == str(test_file)
    
    @patch('builtins.input')
    def test_get_user_input_source_path_nonexistent_retry(self, mock_input, tmp_path):
        """测试不存在路径的重试逻辑"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        
        nonexistent = tmp_path / "nonexistent.txt"
        mock_input.side_effect = [str(nonexistent), str(test_file)]
        
        result = FileTransferCLI.get_user_input_source_path()
        
        assert result == str(test_file)
        assert mock_input.call_count == 2
    
    @patch('builtins.input')
    def test_get_baudrate_default(self, mock_input):
        """测试默认波特率"""
        mock_input.return_value = ""
        
        result = FileTransferCLI.get_baudrate()
        
        assert result == 1728000
    
    @patch('builtins.input')
    def test_get_baudrate_custom(self, mock_input):
        """测试自定义波特率"""
        mock_input.return_value = "115200"
        
        result = FileTransferCLI.get_baudrate()
        
        assert result == 115200
    
    @patch('builtins.input')
    def test_get_baudrate_invalid_fallback(self, mock_input):
        """测试无效波特率回退到默认值"""
        mock_input.return_value = "invalid"
        
        result = FileTransferCLI.get_baudrate()
        
        assert result == 1728000
    
    @patch('builtins.input')
    @patch('serial_file_transfer.cli.file_transfer.SerialManager')
    @patch('serial_file_transfer.cli.file_transfer.FileSender')
    def test_send_file_success(self, mock_sender, mock_serial_manager, mock_input, tmp_path):
        """测试文件发送成功"""
        # 创建临时文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        # 模拟用户输入
        mock_input.side_effect = ["COM1", str(test_file), "", ""]  # 串口号、文件路径、默认波特率、最后的按回车
        
        # 模拟串口管理器
        mock_serial_instance = MagicMock()
        mock_serial_manager.return_value.__enter__.return_value = mock_serial_instance
        
        # 模拟发送器
        mock_sender_instance = MagicMock()
        mock_sender_instance.start_transfer.return_value = True
        mock_sender.return_value = mock_sender_instance
        
        # 模拟print_available_ports
        with patch('serial_file_transfer.cli.file_transfer.SerialManager.print_available_ports'):
            result = FileTransferCLI.send()
        
        assert result is True
        mock_sender_instance.start_transfer.assert_called_once()
    
    @patch('builtins.input')
    @patch('serial_file_transfer.cli.file_transfer.SerialManager')
    @patch('serial_file_transfer.cli.file_transfer.SenderFileManager')
    def test_send_folder_success(self, mock_file_manager, mock_serial_manager, mock_input, tmp_path):
        """测试文件夹发送成功"""
        # 创建临时文件夹
        test_folder = tmp_path / "test_folder"
        test_folder.mkdir()
        (test_folder / "file1.txt").write_text("content1")
        (test_folder / "file2.txt").write_text("content2")
        
        # 模拟用户输入
        mock_input.side_effect = ["COM1", str(test_folder), "", ""]  # 串口号、文件夹路径、默认波特率、最后的按回车
        
        # 模拟串口管理器
        mock_serial_instance = MagicMock()
        mock_serial_manager.return_value.__enter__.return_value = mock_serial_instance
        
        # 模拟文件管理器
        mock_manager_instance = MagicMock()
        mock_manager_instance.start_batch_send.return_value = True
        mock_file_manager.return_value = mock_manager_instance
        
        # 模拟print_available_ports
        with patch('serial_file_transfer.cli.file_transfer.SerialManager.print_available_ports'):
            result = FileTransferCLI.send()
        
        assert result is True
        mock_manager_instance.start_batch_send.assert_called_once()
    
    @patch('builtins.input')
    @patch('serial_file_transfer.cli.file_transfer.SerialManager')
    @patch('serial_file_transfer.cli.file_transfer.FileReceiver')
    def test_receive_single_file_success(self, mock_receiver, mock_serial_manager, mock_input):
        """测试单文件接收成功"""
        # 模拟用户输入
        mock_input.side_effect = ["COM1", "/path/to/save.txt", "", "1", ""]  # 串口号、保存路径、默认波特率、单文件模式、最后的按回车
        
        # 模拟串口管理器
        mock_serial_instance = MagicMock()
        mock_serial_manager.return_value.__enter__.return_value = mock_serial_instance
        
        # 模拟接收器
        mock_receiver_instance = MagicMock()
        mock_receiver_instance.start_transfer.return_value = True
        mock_receiver.return_value = mock_receiver_instance
        
        # 模拟print_available_ports
        with patch('serial_file_transfer.cli.file_transfer.SerialManager.print_available_ports'):
            result = FileTransferCLI.receive()
        
        assert result is True
        mock_receiver_instance.start_transfer.assert_called_once()
    
    @patch('builtins.input')
    @patch('serial_file_transfer.cli.file_transfer.SerialManager')
    @patch('serial_file_transfer.cli.file_transfer.ReceiverFileManager')
    def test_receive_batch_files_success(self, mock_file_manager, mock_serial_manager, mock_input):
        """测试批量文件接收成功"""
        # 模拟用户输入
        mock_input.side_effect = ["COM1", "/path/to/folder", "", "2", ""]  # 串口号、保存文件夹、默认波特率、批量模式、最后的按回车
        
        # 模拟串口管理器
        mock_serial_instance = MagicMock()
        mock_serial_manager.return_value.__enter__.return_value = mock_serial_instance
        
        # 模拟文件管理器
        mock_manager_instance = MagicMock()
        mock_manager_instance.start_batch_receive.return_value = True
        mock_file_manager.return_value = mock_manager_instance
        
        # 模拟print_available_ports
        with patch('serial_file_transfer.cli.file_transfer.SerialManager.print_available_ports'):
            result = FileTransferCLI.receive()
        
        assert result is True
        mock_manager_instance.start_batch_receive.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__]) 