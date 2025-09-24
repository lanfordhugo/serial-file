"""
CLI简化功能测试
==============

专注CLI核心功能的简单测试，避免复杂的Mock设置。
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from serial_file_transfer.cli.file_transfer import FileTransferCLI


class TestCLIBasicFunctionality:
    """CLI基础功能测试"""

    @pytest.mark.parametrize(
        "path_type,expected_result", [
            ("file", "file"),
            ("folder", "folder"), 
        ]
    )
    def test_path_detection_behavior(self, temp_dir, path_type, expected_result):
        """测试路径类型检测行为"""
        # Arrange
        if path_type == "file":
            test_path = temp_dir / "test.txt"
            test_path.write_text("test content")
        else:  # folder
            test_path = temp_dir / "test_folder"
            test_path.mkdir()
        
        # Act
        result = FileTransferCLI._detect_path_type(test_path)
        
        # Assert - 验证路径检测行为
        assert result == expected_result, f"应该检测出 {expected_result} 类型"

    def test_invalid_path_detection_behavior(self, temp_dir):
        """测试无效路径检测行为"""
        # Arrange
        invalid_path = temp_dir / "nonexistent"
        
        # Act & Assert - 验证错误处理行为
        with pytest.raises(ValueError, match="无效的路径类型"):
            FileTransferCLI._detect_path_type(invalid_path)

    def test_cli_initialization(self):
        """测试CLI初始化行为"""
        # Act
        cli = FileTransferCLI()
        
        # Assert - 验证初始化行为
        assert cli is not None, "CLI应该能正常初始化"

    @patch("builtins.input")
    def test_basic_input_handling(self, mock_input, test_file_small):
        """测试基本输入处理"""
        # Arrange
        mock_input.return_value = str(test_file_small)
        
        # Act
        cli = FileTransferCLI()
        result = cli.get_user_input_source_path()
        
        # Assert - CLI返回的是Path对象
        assert result == test_file_small or str(result) == str(test_file_small), "应该返回正确的文件路径"

    @patch("builtins.input")  
    def test_input_retry_behavior(self, mock_input, test_file_small, temp_dir):
        """测试输入重试行为"""
        # Arrange - 先输入无效路径，再输入有效路径
        nonexistent = temp_dir / "nonexistent.txt"
        mock_input.side_effect = [str(nonexistent), str(test_file_small)]
        
        # Act
        cli = FileTransferCLI()
        result = cli.get_user_input_source_path()
        
        # Assert - CLI返回的是Path对象
        assert result == test_file_small or str(result) == str(test_file_small), "重试后应该返回有效路径"
        assert mock_input.call_count == 2, "应该重试了一次"

    @patch("serial_file_transfer.core.serial_manager.SerialManager.list_available_ports")
    @patch("builtins.input")
    def test_port_selection_simple(self, mock_input, mock_list_ports):
        """测试端口选择的简单场景"""
        # Arrange
        mock_ports = [
            {"device": "COM1", "description": "USB Serial", "hwid": "USB123"},
        ]
        mock_list_ports.return_value = mock_ports
        mock_input.return_value = "1"  # 选择第一个端口
        
        # Act
        cli = FileTransferCLI()
        result = cli.get_user_input_port()
        
        # Assert
        assert result == "COM1", "应该返回选择的端口"

    def test_cli_methods_exist(self):
        """测试CLI方法存在性"""
        # Arrange
        cli = FileTransferCLI()
        
        # Act & Assert - 验证关键方法存在
        assert hasattr(cli, 'get_user_input_port'), "应该有端口输入方法"
        assert hasattr(cli, 'get_user_input_source_path'), "应该有路径输入方法"
        assert callable(getattr(cli, 'get_user_input_port')), "端口输入方法应该可调用"
        assert callable(getattr(cli, 'get_user_input_source_path')), "路径输入方法应该可调用"


class TestCLIWorkflowSimulation:
    """CLI工作流模拟测试"""

    def test_smart_send_basic_simulation(self, test_file_small):
        """测试智能发送的基本模拟"""
        # 这个测试不使用复杂的Mock，只验证基本的对象创建和方法存在
        
        # Arrange
        cli = FileTransferCLI()
        
        # Act & Assert - 验证方法存在
        assert hasattr(cli, 'smart_send'), "应该有smart_send方法"
        assert hasattr(cli, 'smart_receive'), "应该有smart_receive方法"
        assert hasattr(cli, 'get_user_input_port'), "应该有端口输入方法"
        assert hasattr(cli, 'get_user_input_source_path'), "应该有路径输入方法"

    def test_path_validation_workflow(self, temp_dir):
        """测试路径验证工作流"""
        # Arrange
        valid_file = temp_dir / "valid.txt"
        valid_file.write_text("test")
        valid_folder = temp_dir / "valid_folder"
        valid_folder.mkdir()
        
        cli = FileTransferCLI()
        
        # Act & Assert - 验证路径验证流程
        assert FileTransferCLI._detect_path_type(valid_file) == "file"
        assert FileTransferCLI._detect_path_type(valid_folder) == "folder"
        
        # 验证无效路径处理
        invalid_path = temp_dir / "invalid"
        with pytest.raises(ValueError):
            FileTransferCLI._detect_path_type(invalid_path)
