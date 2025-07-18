"""
智能CLI模式测试
==============

测试智能发送和接收CLI接口的基础功能。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.serial_file_transfer.cli.file_transfer import FileTransferCLI
from src.serial_file_transfer.core.probe_manager import ProbeManager
from src.serial_file_transfer.core.probe_structures import (
    ProbeResponseData,
    ProbeRequestData,
)
from pathlib import Path


class TestSmartCLI:
    """测试智能CLI接口"""

    def test_smart_send_method_exists(self):
        """测试智能发送方法是否存在"""
        assert hasattr(FileTransferCLI, "smart_send")
        assert callable(getattr(FileTransferCLI, "smart_send"))

    def test_smart_receive_method_exists(self):
        """测试智能接收方法是否存在"""
        assert hasattr(FileTransferCLI, "smart_receive")
        assert callable(getattr(FileTransferCLI, "smart_receive"))

    @patch("builtins.input")
    @patch(
        "src.serial_file_transfer.cli.file_transfer.FileTransferCLI.get_user_input_port",
        return_value="COM1",
    )
    @patch("src.serial_file_transfer.cli.file_transfer.Path")
    @patch("src.serial_file_transfer.cli.file_transfer.SerialManager")
    @patch("src.serial_file_transfer.cli.file_transfer.ProbeManager")
    def test_smart_send_basic_flow(
        self,
        mock_probe_manager_class,
        mock_serial_manager_class,
        mock_path,
        mock_get_port,
        mock_input,
    ):
        """测试智能发送的基本流程"""
        mock_input.side_effect = ["/test/file.txt", ""]  # 源路径  # 按回车退出

        # 模拟路径
        mock_path_obj = Mock()
        mock_path_obj.exists.return_value = True
        mock_path_obj.is_file.return_value = True
        mock_path_obj.stat.return_value.st_size = 1024
        mock_path.return_value = mock_path_obj

        # 模拟串口管理器
        mock_serial_manager = Mock()
        mock_serial_manager_class.return_value.__enter__.return_value = (
            mock_serial_manager
        )
        mock_serial_manager_class.return_value.__exit__.return_value = None

        # 模拟探测管理器
        mock_probe_manager = Mock(spec=ProbeManager)
        mock_probe_manager_class.return_value = mock_probe_manager

        # 模拟探测响应
        mock_response = ProbeResponseData(
            device_id=0x12345678,
            protocol_version=1,
            random_seed=0x87654321,
            supported_baudrates=[115200, 921600],
        )
        mock_probe_manager.send_probe_request.return_value = mock_response
        mock_probe_manager.negotiate_capability.return_value = 921600
        mock_probe_manager.switch_baudrate.return_value = True

        # 模拟文件发送器
        with patch(
            "src.serial_file_transfer.cli.file_transfer.FileSender"
        ) as mock_sender_class:
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

    @patch("builtins.input")
    @patch(
        "src.serial_file_transfer.cli.file_transfer.FileTransferCLI.get_user_input_port",
        return_value="COM1",
    )
    @patch("src.serial_file_transfer.cli.file_transfer.SerialManager")
    @patch("src.serial_file_transfer.cli.file_transfer.ProbeManager")
    def test_smart_receive_basic_flow(
        self,
        mock_probe_manager_class,
        mock_serial_manager_class,
        mock_get_port,
        mock_input,
    ):
        mock_input.side_effect = ["/test/output", ""]

        # 模拟串口管理器
        mock_serial_manager = Mock()
        mock_serial_manager_class.return_value.__enter__.return_value = (
            mock_serial_manager
        )
        mock_serial_manager_class.return_value.__exit__.return_value = None

        # 模拟探测管理器
        mock_probe_manager = Mock(spec=ProbeManager)
        mock_probe_manager_class.return_value = mock_probe_manager

        # 模拟探测请求
        mock_request = ProbeRequestData(
            device_id=0x12345678, protocol_version=1, random_seed=0x87654321
        )
        mock_probe_manager.wait_for_probe_request.return_value = mock_request
        mock_probe_manager.send_probe_response.return_value = True
        mock_probe_manager._receive_probe_frame.side_effect = [
            b"capability_data",  # 能力协商数据
            b"switch_data",  # 切换数据
        ]
        mock_probe_manager.handle_capability_nego.return_value = True
        mock_probe_manager.handle_baudrate_switch.return_value = True
        mock_probe_manager.target_baudrate = 921600

        # 模拟文件接收器
        with patch(
            "src.serial_file_transfer.cli.file_transfer.FileReceiver"
        ) as mock_receiver_class:
            mock_receiver = Mock()
            mock_receiver.start_transfer.return_value = True
            mock_receiver_class.return_value = mock_receiver

            # 执行测试
            result = FileTransferCLI.smart_receive()

            # 验证基本调用
            assert result is True
            mock_probe_manager.wait_for_probe_request.assert_called_once()
            mock_probe_manager.send_probe_response.assert_called_once()

    @patch("builtins.input")
    @patch(
        "src.serial_file_transfer.cli.file_transfer.FileTransferCLI.get_user_input_port",
        return_value="COM1",
    )
    @patch("src.serial_file_transfer.cli.file_transfer.Path")
    @patch("src.serial_file_transfer.cli.file_transfer.SerialManager")
    @patch("src.serial_file_transfer.cli.file_transfer.ProbeManager")
    def test_smart_send_no_device_found(
        self,
        mock_probe_manager_class,
        mock_serial_manager_class,
        mock_path,
        mock_get_port,
        mock_input,
    ):
        mock_input.side_effect = ["/test/file.txt", ""]

        # 模拟路径
        mock_path_obj = Mock()
        mock_path_obj.exists.return_value = True
        mock_path_obj.is_file.return_value = True
        mock_path.return_value = mock_path_obj

        # 模拟串口管理器
        mock_serial_manager = Mock()
        mock_serial_manager_class.return_value.__enter__.return_value = (
            mock_serial_manager
        )
        mock_serial_manager_class.return_value.__exit__.return_value = None

        # 模拟探测管理器 - 返回None表示未找到设备
        mock_probe_manager = Mock(spec=ProbeManager)
        mock_probe_manager_class.return_value = mock_probe_manager
        mock_probe_manager.send_probe_request.return_value = None

        # 执行测试
        result = FileTransferCLI.smart_send()

        # 验证结果
        assert result is False
        # 在3分钟重试逻辑下，应至少探测一次
        assert mock_probe_manager.send_probe_request.call_count >= 1

    @patch("builtins.input")
    @patch(
        "src.serial_file_transfer.cli.file_transfer.FileTransferCLI.get_user_input_port",
        return_value="COM1",
    )
    @patch("src.serial_file_transfer.cli.file_transfer.SerialManager")
    @patch("src.serial_file_transfer.cli.file_transfer.ProbeManager")
    def test_smart_receive_timeout(
        self,
        mock_probe_manager_class,
        mock_serial_manager_class,
        mock_get_port,
        mock_input,
    ):
        mock_input.side_effect = ["/test/output", ""]

        # 模拟串口管理器
        mock_serial_manager = Mock()
        mock_serial_manager_class.return_value.__enter__.return_value = (
            mock_serial_manager
        )
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
        from src.serial_file_transfer.config.constants import (
            PROBE_BAUDRATE,
            ProbeCommand,
        )
        from src.serial_file_transfer.core.probe_manager import ProbeManager

        # 验证常量存在
        assert PROBE_BAUDRATE == 115200
        assert hasattr(ProbeCommand, "PROBE_REQUEST")

    @patch(
        "src.serial_file_transfer.core.serial_manager.SerialManager.list_available_ports"
    )
    def test_get_user_input_port_no_ports(self, mock_list_ports):
        """测试没有可用串口时的行为"""
        # 模拟没有串口
        mock_list_ports.return_value = []

        # 调用函数
        result = FileTransferCLI.get_user_input_port()

        # 验证返回None
        assert result is None

    @patch(
        "src.serial_file_transfer.core.serial_manager.SerialManager.list_available_ports"
    )
    @patch("builtins.input")
    def test_get_user_input_port_with_ports(self, mock_input, mock_list_ports):
        """测试有可用串口时的选择功能"""
        # 模拟有两个串口
        mock_list_ports.return_value = [
            {"device": "COM1", "description": "USB串口设备1", "hwid": "USB\\VID_1234"},
            {"device": "COM2", "description": "USB串口设备2", "hwid": "USB\\VID_5678"},
        ]

        # 模拟用户选择第1个串口
        mock_input.return_value = "1"

        # 调用函数
        result = FileTransferCLI.get_user_input_port()

        # 验证返回正确的串口
        assert result == "COM1"

    @patch(
        "src.serial_file_transfer.core.serial_manager.SerialManager.list_available_ports"
    )
    @patch("builtins.input")
    def test_get_user_input_port_invalid_then_valid(self, mock_input, mock_list_ports):
        """测试用户输入无效选择后重新选择"""
        # 模拟有一个串口
        mock_list_ports.return_value = [
            {"device": "COM1", "description": "USB串口设备", "hwid": "USB\\VID_1234"}
        ]

        # 模拟用户先输入无效选择，然后输入有效选择
        mock_input.side_effect = ["5", "0", "abc", "1"]

        # 调用函数
        result = FileTransferCLI.get_user_input_port()

        # 验证返回正确的串口
        assert result == "COM1"
        # 验证调用了4次input
        assert mock_input.call_count == 4

    @patch(
        "src.serial_file_transfer.core.serial_manager.SerialManager.list_available_ports"
    )
    @patch("builtins.input")
    def test_get_user_input_port_keyboard_interrupt(self, mock_input, mock_list_ports):
        """测试用户按Ctrl+C取消选择"""
        # 模拟有一个串口
        mock_list_ports.return_value = [
            {"device": "COM1", "description": "USB串口设备", "hwid": "USB\\VID_1234"}
        ]

        # 模拟用户按Ctrl+C
        mock_input.side_effect = KeyboardInterrupt()

        # 调用函数
        result = FileTransferCLI.get_user_input_port()

        # 验证返回None
        assert result is None

    @patch("builtins.input")
    @patch(
        "src.serial_file_transfer.cli.file_transfer.FileTransferCLI.get_user_input_port"
    )
    @patch(
        "src.serial_file_transfer.cli.file_transfer.FileTransferCLI.get_user_input_source_path"
    )
    def test_smart_send_no_ports(self, mock_get_path, mock_get_port, mock_input):
        """测试智能发送在没有串口时的行为"""
        # 模拟没有串口
        mock_get_port.return_value = None
        # mock_get_path不应该被调用

        # 模拟按回车退出
        mock_input.return_value = ""

        # 调用智能发送
        result = FileTransferCLI.smart_send()

        # 验证返回False
        assert result is False
        # 验证没有调用获取路径函数
        mock_get_path.assert_not_called()

    @patch("builtins.input")
    @patch(
        "src.serial_file_transfer.cli.file_transfer.FileTransferCLI.get_user_input_port"
    )
    @patch(
        "src.serial_file_transfer.cli.file_transfer.FileTransferCLI.get_user_input_save_path"
    )
    def test_smart_receive_no_ports(
        self, mock_get_save_path, mock_get_port, mock_input
    ):
        """测试智能接收在没有串口时的行为"""
        # 模拟没有串口
        mock_get_port.return_value = None
        # mock_get_save_path不应该被调用

        # 模拟按回车退出
        mock_input.return_value = ""

        # 调用智能接收
        result = FileTransferCLI.smart_receive()

        # 验证返回False
        assert result is False
        # 验证没有调用获取保存路径函数
        mock_get_save_path.assert_not_called()


