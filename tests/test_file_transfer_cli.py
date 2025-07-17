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
        assert result == "file"

    def test_detect_path_type_folder(self, tmp_path):
        """测试文件夹路径检测"""
        # 创建临时文件夹
        test_folder = tmp_path / "test_folder"
        test_folder.mkdir()

        # 测试文件夹检测
        result = FileTransferCLI._detect_path_type(str(test_folder))
        assert result == "folder"

    def test_detect_path_type_invalid(self, tmp_path):
        """测试无效路径检测"""
        # 测试不存在的路径
        invalid_path = tmp_path / "nonexistent"

        with pytest.raises(ValueError, match="无效的路径类型"):
            FileTransferCLI._detect_path_type(str(invalid_path))

    @patch("builtins.input")
    @patch(
        "serial_file_transfer.core.serial_manager.SerialManager.list_available_ports"
    )
    def test_get_user_input_port(self, mock_list_ports, mock_input):
        """测试获取用户输入串口号"""
        # 模拟有可用串口
        mock_list_ports.return_value = [
            {"device": "COM1", "description": "USB串口", "hwid": "USB\\VID_1234"}
        ]
        mock_input.return_value = "1"

        result = FileTransferCLI.get_user_input_port()

        assert result == "COM1"
        mock_list_ports.assert_called_once()

    @patch("builtins.input")
    @patch(
        "serial_file_transfer.core.serial_manager.SerialManager.list_available_ports"
    )
    def test_get_user_input_port_empty_retry(self, mock_list_ports, mock_input):
        """测试空输入重试逻辑"""
        # 模拟有可用串口
        mock_list_ports.return_value = [
            {"device": "COM1", "description": "USB串口", "hwid": "USB\\VID_1234"}
        ]
        mock_input.side_effect = ["", "  ", "1"]

        result = FileTransferCLI.get_user_input_port()

        assert result == "COM1"
        assert mock_input.call_count == 3

    @patch("builtins.input")
    def test_get_user_input_source_path(self, mock_input, tmp_path):
        """测试获取源路径输入"""
        # 创建临时文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        mock_input.return_value = str(test_file)

        result = FileTransferCLI.get_user_input_source_path()

        assert result == str(test_file)

    @patch("builtins.input")
    def test_get_user_input_source_path_nonexistent_retry(self, mock_input, tmp_path):
        """测试不存在路径的重试逻辑"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        nonexistent = tmp_path / "nonexistent.txt"
        mock_input.side_effect = [str(nonexistent), str(test_file)]

        result = FileTransferCLI.get_user_input_source_path()

        assert result == str(test_file)
        assert mock_input.call_count == 2

    @patch("builtins.input")
    def test_get_baudrate_default(self, mock_input):
        """测试默认波特率"""
        mock_input.return_value = ""

        result = FileTransferCLI.get_baudrate()

        assert result == 1728000

    @patch("builtins.input")
    def test_get_baudrate_custom(self, mock_input):
        """测试自定义波特率"""
        mock_input.return_value = "115200"

        result = FileTransferCLI.get_baudrate()

        assert result == 115200

    @patch("builtins.input")
    def test_get_baudrate_invalid_fallback(self, mock_input):
        """测试无效波特率回退到默认值"""
        mock_input.return_value = "invalid"

        result = FileTransferCLI.get_baudrate()

        assert result == 1728000

    @patch("builtins.input")
    @patch(
        "serial_file_transfer.cli.file_transfer.FileTransferCLI.get_user_input_port",
        return_value="COM1",
    )
    @patch("serial_file_transfer.cli.file_transfer.SerialManager")
    @patch("serial_file_transfer.cli.file_transfer.FileSender")
    def test_send_file_success(
        self, mock_sender, mock_serial_manager, mock_get_port, mock_input, tmp_path
    ):
        """测试文件发送成功"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        mock_input.side_effect = [str(test_file), "", ""]
        mock_serial_instance = MagicMock()
        mock_serial_manager.return_value.__enter__.return_value = mock_serial_instance
        mock_sender_instance = MagicMock()
        mock_sender_instance.start_transfer.return_value = True
        mock_sender.return_value = mock_sender_instance
        result = FileTransferCLI.send()
        assert result is True
        mock_sender_instance.start_transfer.assert_called_once()

    @patch("builtins.input")
    @patch(
        "serial_file_transfer.cli.file_transfer.FileTransferCLI.get_user_input_port",
        return_value="COM1",
    )
    @patch("serial_file_transfer.cli.file_transfer.SerialManager")
    @patch("serial_file_transfer.cli.file_transfer.SenderFileManager")
    def test_send_folder_success(
        self,
        mock_file_manager,
        mock_serial_manager,
        mock_get_port,
        mock_input,
        tmp_path,
    ):
        test_folder = tmp_path / "test_folder"
        test_folder.mkdir()
        (test_folder / "file1.txt").write_text("1")
        mock_input.side_effect = [str(test_folder), "", ""]
        mock_serial_instance = MagicMock()
        mock_serial_manager.return_value.__enter__.return_value = mock_serial_instance
        mock_manager_instance = MagicMock()
        mock_manager_instance.start_batch_send.return_value = True
        mock_file_manager.return_value = mock_manager_instance
        result = FileTransferCLI.send()
        assert result is True
        mock_manager_instance.start_batch_send.assert_called_once()

    @patch("builtins.input")
    @patch(
        "serial_file_transfer.cli.file_transfer.FileTransferCLI.get_user_input_port",
        return_value="COM1",
    )
    @patch("serial_file_transfer.cli.file_transfer.SerialManager")
    @patch("serial_file_transfer.cli.file_transfer.FileReceiver")
    def test_receive_single_file_success(
        self, mock_receiver, mock_serial_manager, mock_get_port, mock_input
    ):
        mock_input.side_effect = ["/path/to/save.txt", "", "1", ""]
        mock_serial_instance = MagicMock()
        mock_serial_manager.return_value.__enter__.return_value = mock_serial_instance
        mock_receiver_instance = MagicMock()
        mock_receiver_instance.start_transfer.return_value = True
        mock_receiver.return_value = mock_receiver_instance
        result = FileTransferCLI.receive()
        assert result is True
        mock_receiver_instance.start_transfer.assert_called_once()

    @patch("builtins.input")
    @patch(
        "serial_file_transfer.cli.file_transfer.FileTransferCLI.get_user_input_port",
        return_value="COM1",
    )
    @patch("serial_file_transfer.cli.file_transfer.SerialManager")
    @patch("serial_file_transfer.cli.file_transfer.ReceiverFileManager")
    def test_receive_batch_files_success(
        self, mock_file_manager, mock_serial_manager, mock_get_port, mock_input
    ):
        mock_input.side_effect = ["/path/to/folder", "", "2", ""]
        mock_serial_instance = MagicMock()
        mock_serial_manager.return_value.__enter__.return_value = mock_serial_instance
        mock_manager_instance = MagicMock()
        mock_manager_instance.start_batch_receive.return_value = True
        mock_file_manager.return_value = mock_manager_instance
        result = FileTransferCLI.receive()
        assert result is True
        mock_manager_instance.start_batch_receive.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
