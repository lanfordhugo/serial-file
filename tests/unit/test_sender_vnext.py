"""
文件名称: test_sender_vnext.py
内容摘要: 发送端vNext协议单元测试
当前版本: v1.0.0
作者: AI Assistant
创建日期: 2025-10-01
"""

import struct
import pytest
from typing import Optional
from unittest.mock import Mock, patch, MagicMock

from src.serial_file_transfer.transfer.sender import FileSender
from src.serial_file_transfer.core.serial_manager import SerialManager
from src.serial_file_transfer.config.settings import TransferConfig
from src.serial_file_transfer.config.constants import SerialCommand
from src.serial_file_transfer.core.frame_handler import FrameHandler
from src.serial_file_transfer.core.frame_payload import FramePayload


class TestSenderVNext:
    """测试发送端vNext协议改进"""

    @pytest.fixture
    def mock_serial_manager(self):
        """创建模拟串口管理器"""
        manager = Mock(spec=SerialManager)
        manager.port = Mock()
        manager.write = Mock(return_value=True)
        return manager

    @pytest.fixture
    def config(self):
        """创建测试配置"""
        return TransferConfig(
            max_data_length=1024,
            retry_count=3,
            request_timeout=1.0,
            backoff_base=0.1,
        )

    @pytest.fixture
    def sender(self, mock_serial_manager, config, tmp_path):
        """创建发送端实例"""
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"A" * 4096)
        
        sender = FileSender(mock_serial_manager, test_file, config)
        return sender

    def test_send_data_with_offset(self, sender, mock_serial_manager):
        """测试发送数据包包含offset字段"""
        # 准备测试数据
        addr = 0
        length = 512
        
        # 模拟ACK响应（包含offset）
        ack_data = FramePayload.pack_ack(0, 0)
        ack_frame = FrameHandler.pack_frame(SerialCommand.ACK, ack_data)
        
        # 配置read_frame返回ACK
        mock_serial_manager.port.read = Mock(side_effect=[
            ack_frame[i:i+1] for i in range(len(ack_frame))
        ])
        
        with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.ACK, ack_data)):
            # 发送数据包
            result = sender._send_data_package(addr, length)
        
        # 验证结果
        assert result is True
        assert sender._seq_id == 1  # 序号应增加
        assert sender.send_size == length  # 进度应更新

    def test_ack_with_offset_verification(self, sender, mock_serial_manager):
        """测试基于offset验证ACK"""
        addr = 1024
        length = 512
        
        # 场景1：offset匹配，应该接受
        ack_data_correct = FramePayload.pack_ack(0, 1024)
        with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.ACK, ack_data_correct)):
            result = sender._send_data_package(addr, length)
        assert result is True
        
        # 场景2：offset不匹配，应该拒绝（通过超时失败）
        sender._seq_id = 0  # 重置序号
        ack_data_wrong = FramePayload.pack_ack(0, 2048)  # 错误的offset
        
        # 模拟一直返回错误的ACK，最终超时
        with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.ACK, ack_data_wrong)):
            # 减少超时时间和重试次数加快测试
            sender.config.request_timeout = 0.1
            sender.config.retry_count = 1
            result = sender._send_data_package(addr, length)
        
        assert result is False  # 应该失败

    def test_duplicate_ack_handling(self, sender, mock_serial_manager):
        """测试重复ACK处理（接收到旧offset的ACK）"""
        # 先成功发送第一个包
        ack_data_1 = FramePayload.pack_ack(0, 0)
        with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.ACK, ack_data_1)):
            result = sender._send_data_package(0, 512)
        assert result is True
        assert sender._seq_id == 1
        
        # 发送第二个包，但收到第一个包的ACK（重复ACK）
        ack_data_old = FramePayload.pack_ack(1, 0)  # 旧的offset
        ack_data_new = FramePayload.pack_ack(1, 512)  # 正确的offset
        
        call_count = 0
        def mock_read_duplicate_then_correct(*args, **kwargs):
            """先返回重复ACK，再返回正确ACK"""
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (SerialCommand.ACK, ack_data_old)  # 重复ACK
            else:
                return (SerialCommand.ACK, ack_data_new)  # 正确ACK
        
        with patch.object(FrameHandler, 'read_frame', side_effect=mock_read_duplicate_then_correct):
            result = sender._send_data_package(512, 512)
        
        assert result is True  # 最终应该成功
        assert sender._seq_id == 2

    def test_nack_retry(self, sender, mock_serial_manager):
        """测试收到NACK后重试"""
        addr = 0
        length = 512
        
        # 模拟：第一次NACK，第二次ACK
        nack_data = FramePayload.pack_nack(0, 0)
        ack_data = FramePayload.pack_ack(0, 0)
        
        call_count = 0
        def mock_read_nack_then_ack(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (SerialCommand.NACK, nack_data)
            else:
                return (SerialCommand.ACK, ack_data)
        
        with patch.object(FrameHandler, 'read_frame', side_effect=mock_read_nack_then_ack):
            result = sender._send_data_package(addr, length)
        
        assert result is True
        assert sender._seq_id == 1
        # 验证write被调用了多次（重试）
        assert mock_serial_manager.write.call_count >= 2

    def test_sequence_sync_handling(self, sender, mock_serial_manager):
        """测试序号同步流程"""
        addr = 0
        length = 512
        
        # 模拟：先收到SYNC_REQUEST，然后收到ACK
        sync_req_data = FramePayload.pack_sync_request(5, 2048)  # 接收端期望seq=5, offset=2048
        ack_data = FramePayload.pack_ack(0, 0)
        
        call_count = 0
        def mock_read_sync_then_ack(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (SerialCommand.SYNC_REQUEST, sync_req_data)
            else:
                return (SerialCommand.ACK, ack_data)
        
        with patch.object(FrameHandler, 'read_frame', side_effect=mock_read_sync_then_ack):
            result = sender._send_data_package(addr, length)
        
        assert result is True
        # 验证发送了SYNC_REPLY
        write_calls = mock_serial_manager.write.call_args_list
        assert len(write_calls) >= 2  # 至少发送了数据帧和同步回复

    def test_no_adaptive_strategy(self, sender):
        """验证未使用自适应策略"""
        # vNext版本不应该有adaptive_strategy属性
        assert not hasattr(sender, 'adaptive_strategy') or sender.adaptive_strategy is None

    def test_fixed_block_size_usage(self, sender, mock_serial_manager):
        """测试使用固定块长配置"""
        # 验证配置的块长
        assert sender.config.max_data_length == 1024
        
        # 模拟数据请求超过块长的场景
        request_data = struct.pack("<IH", 0, 2048)  # 请求2048字节
        
        with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.REQUEST_DATA, request_data)):
            with patch.object(sender, '_send_data_package', return_value=True) as mock_send:
                sender._wait_for_data_request()
                
                # 验证实际发送的长度被限制为配置块长
                mock_send.assert_called_once()
                call_args = mock_send.call_args
                assert call_args[0][1] == 1024  # 应该被调整为配置块长

    def test_offset_based_progress_tracking(self, sender, mock_serial_manager):
        """测试基于offset的进度跟踪"""
        # 发送多个数据包，验证进度更新
        packets = [
            (0, 512),
            (512, 512),
            (1024, 512),
        ]
        
        for addr, length in packets:
            ack_data = FramePayload.pack_ack(sender._seq_id, addr)
            with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.ACK, ack_data)):
                result = sender._send_data_package(addr, length)
                assert result is True
                assert sender.send_size == addr + length  # 进度应该基于offset更新

    def test_frame_packing_with_offset(self, sender, mock_serial_manager):
        """测试数据帧打包包含offset"""
        addr = 2048
        length = 256
        
        # 捕获打包的帧
        captured_frame = None
        original_write = mock_serial_manager.write
        def capture_write(data):
            nonlocal captured_frame
            captured_frame = data
            return True
        mock_serial_manager.write = capture_write
        
        ack_data = FramePayload.pack_ack(sender._seq_id, addr)
        with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.ACK, ack_data)):
            sender._send_data_package(addr, length)
        
        # 验证帧格式
        assert captured_frame is not None
        # 解析帧：帧头(2) + 长度(2) + 命令(1) + 数据(offset(4)+seq(2)+payload) + CRC(2)
        # 数据部分应该包含offset
        assert len(captured_frame) > 11  # 至少有帧头、长度、命令、offset、seq、CRC

    def test_ack_timeout_recovery(self, sender, mock_serial_manager):
        """测试ACK超时后的恢复"""
        addr = 0
        length = 512
        
        # 模拟ACK超时（read_frame一直返回None）
        # 减少超时时间和重试次数加快测试
        sender.config.request_timeout = 0.1
        sender.config.retry_count = 1
        sender.config.backoff_base = 0.01
        
        with patch.object(FrameHandler, 'read_frame', return_value=(None, None)):
            result = sender._send_data_package(addr, length)
        
        # 应该失败
        assert result is False
        # 序号不应该增加
        assert sender._seq_id == 0
        # 进度不应该更新
        assert sender.send_size == 0


class TestSenderEdgeCases:
    """测试发送端边界情况"""

    @pytest.fixture
    def mock_serial_manager(self):
        """创建模拟串口管理器"""
        manager = Mock(spec=SerialManager)
        manager.port = Mock()
        manager.write = Mock(return_value=True)
        return manager

    @pytest.fixture
    def config(self):
        """创建测试配置"""
        return TransferConfig(max_data_length=1024)

    def test_seq_id_rollover(self, mock_serial_manager, config, tmp_path):
        """测试序号回绕（0xFFFF -> 0x0000）"""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"X" * 2048)
        
        sender = FileSender(mock_serial_manager, test_file, config)
        sender._seq_id = 0xFFFF  # 设置为最大值
        
        ack_data = FramePayload.pack_ack(0xFFFF, 0)
        with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.ACK, ack_data)):
            result = sender._send_data_package(0, 512)
        
        assert result is True
        assert sender._seq_id == 0  # 应该回绕到0

    def test_zero_length_file(self, mock_serial_manager, config, tmp_path):
        """测试零字节文件"""
        test_file = tmp_path / "empty.txt"
        test_file.write_bytes(b"")
        
        sender = FileSender(mock_serial_manager, test_file, config)
        assert sender.file_size == 0

    def test_large_offset_handling(self, mock_serial_manager, config, tmp_path):
        """测试大偏移量处理（接近4GB）"""
        test_file = tmp_path / "test.txt"
        test_file.write_bytes(b"Y" * 1024)
        
        sender = FileSender(mock_serial_manager, test_file, config)
        
        # 模拟大偏移量
        large_offset = 0xFFFFFF00  # 接近32位最大值
        # 这应该能正确打包（offset是4字节）
        frame = FrameHandler.pack_send_data_frame(0, large_offset, b"test")
        assert frame is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

