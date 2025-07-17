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

    def test_get_baudrate_smart_mode(self):
        """测试智能模式下的波特率获取"""
        result = FileTransferCLI.get_baudrate()
        # 智能模式下使用固定的探测波特率115200
        assert result == 115200




if __name__ == "__main__":
    pytest.main([__file__])
