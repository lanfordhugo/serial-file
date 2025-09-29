"""
文件名称: test_cli_minimal.py
内容摘要: FileTransferCLI类的最小化测试 - 只测试核心无交互功能
当前版本: v1.0.0
作者: AI Assistant
创建日期: 2025-09-29

说明: 由于CLI涉及大量用户交互，自动化测试容易出现无限循环等问题
此文件只测试最核心的、无用户交互的功能
"""

import pytest
from unittest.mock import patch

from serial_file_transfer.cli.file_transfer import FileTransferCLI


class TestFileTransferCLIMinimal:
    """最小化CLI测试 - 只测试核心功能"""

    def test_clear_temp_params(self):
        """测试清理临时参数功能"""
        # Arrange - 设置临时参数
        FileTransferCLI._temp_port = "COM1"
        FileTransferCLI._temp_path = "/test/path"
        FileTransferCLI._temp_save_path = "/save/path"
        FileTransferCLI._temp_baudrate = 9600
        
        # Act - 清理参数
        FileTransferCLI._clear_temp_params()
        
        # Assert - 验证参数被清理
        assert FileTransferCLI._temp_port is None
        assert FileTransferCLI._temp_path is None
        assert FileTransferCLI._temp_save_path is None
        assert FileTransferCLI._temp_baudrate is None

    def test_show_available_ports(self):
        """测试显示可用串口功能"""
        # 这个方法只是调用SerialManager.print_available_ports()
        # 我们Mock这个调用来验证它被正确调用
        with patch('serial_file_transfer.cli.file_transfer.SerialManager.print_available_ports') as mock_print:
            # Act
            FileTransferCLI.show_available_ports()
            
            # Assert
            mock_print.assert_called_once()

    def test_get_baudrate_with_temp_param(self):
        """测试使用临时参数获取波特率（非交互式）"""
        # Arrange
        FileTransferCLI._temp_baudrate = 9600
        
        try:
            # Act
            with patch('builtins.print'):  # 抑制打印输出
                result = FileTransferCLI.get_baudrate()
                
            # Assert
            assert result == 9600
        finally:
            # Cleanup
            FileTransferCLI._clear_temp_params()

    def test_get_baudrate_default(self):
        """测试获取默认波特率"""
        # Arrange
        FileTransferCLI._clear_temp_params()
        
        # Act
        with patch('builtins.print'):  # 抑制打印输出
            result = FileTransferCLI.get_baudrate()
            
        # Assert
        assert result == 115200

    def test_get_user_input_port_with_temp_param(self):
        """测试使用临时参数获取串口（非交互式）"""
        # Arrange
        FileTransferCLI._temp_port = "COM1"
        
        try:
            # Act
            result = FileTransferCLI.get_user_input_port()
            
            # Assert
            assert result == "COM1"
        finally:
            # Cleanup
            FileTransferCLI._clear_temp_params()


# 注意事项:
# 1. CLI的大部分功能涉及用户交互，不适合自动化测试
# 2. 交互式功能如get_path(), get_save_path()等需要手动测试
# 3. smart_send()和smart_receive()等复杂流程需要集成测试
# 4. 本测试只覆盖最基础的、无交互的功能
# 5. 更全面的CLI测试应该通过端到端测试或手动测试完成
