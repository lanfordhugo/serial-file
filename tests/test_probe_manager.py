"""
探测管理器测试
==============

测试智能探测协商管理器的核心功能。
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.serial_file_transfer.core.probe_manager import ProbeManager, ProbeTimeoutError
from src.serial_file_transfer.core.serial_manager import SerialManager
from src.serial_file_transfer.core.probe_structures import (
    ProbeRequestData,
    ProbeResponseData,
)
from src.serial_file_transfer.config.constants import ProbeCommand
from src.serial_file_transfer.config.settings import SerialConfig


class TestProbeManager:
    """测试探测管理器基础功能"""

    @pytest.fixture
    def mock_serial_manager(self):
        """创建模拟串口管理器"""
        mock_manager = Mock(spec=SerialManager)
        mock_manager.write.return_value = True
        mock_manager.read.return_value = b""
        return mock_manager

    @pytest.fixture
    def probe_manager(self, mock_serial_manager):
        """创建探测管理器实例"""
        return ProbeManager(mock_serial_manager)

    def test_init(self, probe_manager, mock_serial_manager):
        """测试初始化"""
        assert probe_manager.serial_manager == mock_serial_manager
        assert probe_manager.session_id is None
        assert probe_manager.target_baudrate is None
        assert probe_manager.device_id is None
        assert len(probe_manager.supported_baudrates) > 0

    def test_generate_session_id(self, probe_manager):
        """测试生成会话ID"""
        session_id = probe_manager._generate_session_id()
        assert isinstance(session_id, int)
        assert 0x10000000 <= session_id <= 0xFFFFFFFF

        # 多次生成应该不同
        session_id2 = probe_manager._generate_session_id()
        assert session_id != session_id2

    def test_send_probe_frame_success(self, probe_manager, mock_serial_manager):
        """测试成功发送探测帧"""
        data = b"\x01\x02\x03"

        with patch(
            "src.serial_file_transfer.core.probe_manager.FrameHandler.pack_frame"
        ) as mock_pack:
            mock_pack.return_value = b"\x41\x03\x00\x01\x02\x03\x06\x01"

            result = probe_manager._send_probe_frame(ProbeCommand.PROBE_REQUEST, data)

            assert result is True
            mock_pack.assert_called_once_with(ProbeCommand.PROBE_REQUEST, data)
            mock_serial_manager.write.assert_called_once()

    def test_send_probe_frame_pack_failed(self, probe_manager, mock_serial_manager):
        """测试打包失败时的处理"""
        data = b"\x01\x02\x03"

        with patch(
            "src.serial_file_transfer.core.probe_manager.FrameHandler.pack_frame"
        ) as mock_pack:
            mock_pack.return_value = None

            result = probe_manager._send_probe_frame(ProbeCommand.PROBE_REQUEST, data)

            assert result is False
            mock_serial_manager.write.assert_not_called()

    def test_send_probe_frame_write_failed(self, probe_manager, mock_serial_manager):
        """测试写入失败时的处理"""
        data = b"\x01\x02\x03"
        mock_serial_manager.write.return_value = False

        with patch(
            "src.serial_file_transfer.core.probe_manager.FrameHandler.pack_frame"
        ) as mock_pack:
            mock_pack.return_value = b"\x41\x03\x00\x01\x02\x03\x06\x01"

            result = probe_manager._send_probe_frame(ProbeCommand.PROBE_REQUEST, data)

            assert result is False

    def test_receive_probe_frame_timeout(self, probe_manager, mock_serial_manager):
        """测试接收探测帧超时"""
        # 模拟没有数据可读
        mock_serial_manager.read.return_value = b""

        result = probe_manager._receive_probe_frame(ProbeCommand.PROBE_RESPONSE, 0.1)
        assert result is None

    def test_receive_probe_frame_success(self, probe_manager, mock_serial_manager):
        """测试成功接收探测帧"""
        # 准备测试数据
        test_data = b"\x01\x02\x03"
        packed_frame = b"\x42\x03\x00\x01\x02\x03\x06\x01"  # 模拟的完整帧

        # 模拟串口返回数据
        mock_serial_manager.read.side_effect = [packed_frame, b""]

        with patch(
            "src.serial_file_transfer.core.probe_manager.FrameHandler.unpack_frame"
        ) as mock_unpack:
            mock_unpack.return_value = (
                ProbeCommand.PROBE_RESPONSE,
                3,
                test_data,
                0x0106,
            )

            result = probe_manager._receive_probe_frame(
                ProbeCommand.PROBE_RESPONSE, 1.0
            )

            assert result == test_data

    def test_send_probe_request_success(self, probe_manager, mock_serial_manager):
        """测试成功发送探测请求"""
        # 使用patch来控制ProbeRequestData.create，确保一致性
        with patch(
            "src.serial_file_transfer.core.probe_structures.ProbeRequestData.create"
        ) as mock_create:
            # 创建固定的请求数据
            request_data = ProbeRequestData(
                device_id=0x12345678, protocol_version=1, random_seed=0x87654321
            )
            mock_create.return_value = request_data

            # 创建对应的响应数据
            response_data = ProbeResponseData.create_response(
                request_data, [115200, 921600]
            )

            with patch.object(probe_manager, "_send_probe_frame") as mock_send:
                with patch.object(
                    probe_manager, "_receive_probe_frame"
                ) as mock_receive:
                    mock_send.return_value = True
                    mock_receive.return_value = response_data.pack()

                    result = probe_manager.send_probe_request()

                    assert result is not None
                    assert result.supported_baudrates == [115200, 921600]
                    assert probe_manager.device_id == 0x12345678

                    mock_send.assert_called_once()
                    mock_receive.assert_called_once()

    def test_send_probe_request_send_failed(self, probe_manager, mock_serial_manager):
        """测试发送探测请求失败"""
        with patch.object(probe_manager, "_send_probe_frame") as mock_send:
            mock_send.return_value = False

            result = probe_manager.send_probe_request()
            assert result is None

    def test_send_probe_request_no_response(self, probe_manager, mock_serial_manager):
        """测试发送探测请求后无响应"""
        with patch.object(probe_manager, "_send_probe_frame") as mock_send:
            with patch.object(probe_manager, "_receive_probe_frame") as mock_receive:
                mock_send.return_value = True
                mock_receive.return_value = None

                result = probe_manager.send_probe_request()
                assert result is None

    def test_wait_for_probe_request_success(self, probe_manager, mock_serial_manager):
        """测试成功等待探测请求"""
        request_data = ProbeRequestData.create()

        with patch.object(probe_manager, "_receive_probe_frame") as mock_receive:
            mock_receive.return_value = request_data.pack()

            result = probe_manager.wait_for_probe_request(1.0)

            assert result is not None
            assert result.device_id == request_data.device_id
            assert result.protocol_version == request_data.protocol_version

    def test_wait_for_probe_request_timeout(self, probe_manager, mock_serial_manager):
        """测试等待探测请求超时"""
        with patch.object(probe_manager, "_receive_probe_frame") as mock_receive:
            mock_receive.return_value = None

            result = probe_manager.wait_for_probe_request(0.1)
            assert result is None

    def test_send_probe_response_success(self, probe_manager, mock_serial_manager):
        """测试成功发送探测响应"""
        request = ProbeRequestData.create()

        with patch.object(probe_manager, "_send_probe_frame") as mock_send:
            mock_send.return_value = True

            result = probe_manager.send_probe_response(request)

            assert result is True
            mock_send.assert_called_once()

            # 验证调用参数
            call_args = mock_send.call_args
            assert call_args[0][0] == ProbeCommand.PROBE_RESPONSE

    def test_send_probe_response_failed(self, probe_manager, mock_serial_manager):
        """测试发送探测响应失败"""
        request = ProbeRequestData.create()

        with patch.object(probe_manager, "_send_probe_frame") as mock_send:
            mock_send.return_value = False

            result = probe_manager.send_probe_response(request)
            assert result is False
