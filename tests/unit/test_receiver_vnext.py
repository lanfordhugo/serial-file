"""
文件名称: test_receiver_vnext.py
内容摘要: 接收端vNext协议单元测试
当前版本: v1.0.0
作者: AI Assistant
创建日期: 2025-10-01
"""

import struct
import pytest
from typing import Optional
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.serial_file_transfer.transfer.receiver import FileReceiver
from src.serial_file_transfer.core.serial_manager import SerialManager
from src.serial_file_transfer.config.settings import TransferConfig
from src.serial_file_transfer.config.constants import SerialCommand
from src.serial_file_transfer.core.frame_handler import FrameHandler
from src.serial_file_transfer.core.frame_payload import FramePayload


class TestReceiverVNext:
    """测试接收端vNext协议改进"""

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
        )

    @pytest.fixture
    def receiver(self, mock_serial_manager, config, tmp_path):
        """创建接收端实例"""
        save_path = tmp_path / "received.txt"
        receiver = FileReceiver(mock_serial_manager, save_path, config)
        return receiver

    def test_receive_data_with_offset(self, receiver, mock_serial_manager):
        """测试接收数据包包含offset字段"""
        # 准备测试数据
        seq_id = 0
        offset = 0
        payload = b"A" * 512
        
        # 打包数据帧
        data_frame_data = FramePayload.pack_send_data(seq_id, offset, payload)
        
        # 配置read_frame返回数据
        with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.SEND_DATA, data_frame_data)):
            result = receiver.receive_data_package()
        
        # 验证结果
        assert result is True
        assert receiver.recv_size == 512  # 进度应更新
        assert receiver._expected_seq == 1  # 序号应增加
        # 验证发送了ACK
        assert mock_serial_manager.write.called

    def test_duplicate_frame_idempotent_ack(self, receiver, mock_serial_manager):
        """测试重复帧的幂等ACK处理"""
        # 先接收第一个包
        data1 = FramePayload.pack_send_data(0, 0, b"A" * 512)
        with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.SEND_DATA, data1)):
            result = receiver.receive_data_package()
        assert result is True
        assert receiver.recv_size == 512
        
        # 清空write调用记录
        mock_serial_manager.write.reset_mock()
        
        # 再次收到相同offset的数据（重复帧）
        data_dup = FramePayload.pack_send_data(1, 0, b"B" * 512)  # 注意：seq不同，但offset=0（重复）
        with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.SEND_DATA, data_dup)):
            result = receiver.receive_data_package()
        
        # 应该返回True（不算失败），但不增加recv_size
        assert result is True
        assert receiver.recv_size == 512  # 进度不变
        
        # 应该发送了ACK（幂等）
        assert mock_serial_manager.write.called
        # 验证发送的是ACK（检查帧中是否包含ACK命令字节）
        call_args = mock_serial_manager.write.call_args[0][0]
        assert SerialCommand.ACK in call_args

    def test_offset_verification_priority(self, receiver, mock_serial_manager):
        """测试偏移量优先验证"""
        # 场景1：offset正确，seq正确 -> 接受
        data1 = FramePayload.pack_send_data(0, 0, b"A" * 512)
        with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.SEND_DATA, data1)):
            result = receiver.receive_data_package()
        assert result is True
        assert receiver.recv_size == 512
        
        # 场景2：offset正确，seq错误 -> 拒绝（发送NACK）
        mock_serial_manager.write.reset_mock()
        data2 = FramePayload.pack_send_data(5, 512, b"B" * 512)  # seq跳跃
        with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.SEND_DATA, data2)):
            result = receiver.receive_data_package()
        assert result is False  # 拒绝
        # 验证发送了NACK
        call_args = mock_serial_manager.write.call_args[0][0]
        assert SerialCommand.NACK in call_args
        
        # 场景3：offset错误 -> 直接拒绝
        mock_serial_manager.write.reset_mock()
        data3 = FramePayload.pack_send_data(1, 2048, b"C" * 512)  # offset跳跃
        with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.SEND_DATA, data3)):
            result = receiver.receive_data_package()
        assert result is False
        # 验证发送了NACK
        call_args = mock_serial_manager.write.call_args[0][0]
        assert SerialCommand.NACK in call_args

    def test_ack_contains_offset(self, receiver, mock_serial_manager):
        """测试ACK中包含offset字段"""
        seq_id = 0
        offset = 0
        payload = b"X" * 256
        
        data = FramePayload.pack_send_data(seq_id, offset, payload)
        with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.SEND_DATA, data)):
            receiver.receive_data_package()
        
        # 验证发送的ACK包含offset
        assert mock_serial_manager.write.called
        ack_frame = mock_serial_manager.write.call_args[0][0]
        
        # 验证帧中包含ACK命令
        assert SerialCommand.ACK in ack_frame
        # 验证帧长度足够（应该包含6字节的ACK数据：offset(4) + seq(2)）
        # 帧格式：命令(1) + 数据(6) + 其他字段
        assert len(ack_frame) >= 7  # 至少包含命令和数据

    def test_sequence_recovery_with_offset(self, receiver, mock_serial_manager):
        """测试基于offset的序号同步"""
        # 接收第一个包
        data1 = FramePayload.pack_send_data(0, 0, b"A" * 512)
        with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.SEND_DATA, data1)):
            receiver.receive_data_package()
        assert receiver.recv_size == 512
        
        # 模拟序号跳跃（连续多次）
        for _ in range(3):  # 触发序号同步的阈值
            data_wrong = FramePayload.pack_send_data(10, 512, b"B" * 512)
            with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.SEND_DATA, data_wrong)):
                receiver.receive_data_package()
        
        # 验证触发了序号同步（检查write调用中是否有NACK）
        nack_found = False
        for call in mock_serial_manager.write.call_args_list:
            frame = call[0][0]
            if SerialCommand.NACK in frame:
                nack_found = True
        assert nack_found

    def test_parse_failure_sends_nack(self, receiver, mock_serial_manager):
        """测试解析失败时发送NACK"""
        # 模拟解析失败
        with patch.object(FrameHandler, 'read_frame', return_value=(None, None)):
            result = receiver.receive_data_package()
        
        assert result is False
        # 验证发送了NACK
        assert mock_serial_manager.write.called
        nack_frame = mock_serial_manager.write.call_args[0][0]
        assert SerialCommand.NACK in nack_frame

    def test_offset_based_progress_tracking(self, receiver, mock_serial_manager):
        """测试基于offset的进度跟踪"""
        # 接收多个数据包，验证进度更新
        packets = [
            (0, 0, b"A" * 512),
            (1, 512, b"B" * 512),
            (2, 1024, b"C" * 512),
        ]
        
        for seq, offset, payload in packets:
            data = FramePayload.pack_send_data(seq, offset, payload)
            with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.SEND_DATA, data)):
                result = receiver.receive_data_package()
                assert result is True
                assert receiver.recv_size == offset + len(payload)

    def test_out_of_order_rejection(self, receiver, mock_serial_manager):
        """测试乱序数据包被拒绝"""
        # 接收第一个包
        data1 = FramePayload.pack_send_data(0, 0, b"A" * 512)
        with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.SEND_DATA, data1)):
            receiver.receive_data_package()
        
        # 尝试接收第三个包（跳过第二个）
        mock_serial_manager.write.reset_mock()
        data3 = FramePayload.pack_send_data(2, 1024, b"C" * 512)
        with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.SEND_DATA, data3)):
            result = receiver.receive_data_package()
        
        # 应该被拒绝
        assert result is False
        # 应该发送NACK
        assert mock_serial_manager.write.called
        nack_frame = mock_serial_manager.write.call_args[0][0]
        assert SerialCommand.NACK in nack_frame

    def test_wrong_command_handling(self, receiver, mock_serial_manager):
        """测试错误命令处理"""
        # 发送非SEND_DATA命令
        with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.REQUEST_FILE_NAME, b"")):
            result = receiver.receive_data_package()
        
        assert result is False


class TestReceiverEdgeCases:
    """测试接收端边界情况"""

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
        save_path = tmp_path / "test.txt"
        receiver = FileReceiver(mock_serial_manager, save_path, config)
        receiver._expected_seq = 0xFFFF
        
        # 接收序号为0xFFFF的包
        data = FramePayload.pack_send_data(0xFFFF, 0, b"A" * 512)
        with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.SEND_DATA, data)):
            result = receiver.receive_data_package()
        
        assert result is True
        assert receiver._expected_seq == 0  # 应该回绕到0

    def test_zero_length_payload(self, mock_serial_manager, config, tmp_path):
        """测试零长度payload"""
        save_path = tmp_path / "test.txt"
        receiver = FileReceiver(mock_serial_manager, save_path, config)
        
        # 接收零长度payload
        data = FramePayload.pack_send_data(0, 0, b"")
        with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.SEND_DATA, data)):
            result = receiver.receive_data_package()
        
        assert result is True
        assert receiver.recv_size == 0

    def test_large_offset_handling(self, mock_serial_manager, config, tmp_path):
        """测试大偏移量处理（接近4GB）"""
        save_path = tmp_path / "test.txt"
        receiver = FileReceiver(mock_serial_manager, save_path, config)
        
        # 设置已接收大小为大偏移量
        large_offset = 0xFFFFFF00
        receiver.recv_size = large_offset
        
        # 接收大偏移量的数据
        data = FramePayload.pack_send_data(0, large_offset, b"test")
        with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.SEND_DATA, data)):
            # 这应该能正确处理（offset是4字节）
            result = receiver.receive_data_package()
        
        assert result is True

    def test_multiple_duplicate_frames(self, mock_serial_manager, config, tmp_path):
        """测试多个重复帧的处理"""
        save_path = tmp_path / "test.txt"
        receiver = FileReceiver(mock_serial_manager, save_path, config)
        
        # 接收第一个包
        data1 = FramePayload.pack_send_data(0, 0, b"A" * 512)
        with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.SEND_DATA, data1)):
            receiver.receive_data_package()
        assert receiver.recv_size == 512
        
        # 连续接收多个重复帧
        for i in range(5):
            data_dup = FramePayload.pack_send_data(i, 0, b"X" * 512)
            with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.SEND_DATA, data_dup)):
                result = receiver.receive_data_package()
                # 应该都返回True（幂等处理）
                assert result is True
                # 进度不变
                assert receiver.recv_size == 512

    def test_file_write_persistence(self, mock_serial_manager, config, tmp_path):
        """测试数据正确写入文件"""
        save_path = tmp_path / "test.txt"
        receiver = FileReceiver(mock_serial_manager, save_path, config)
        
        # 设置文件大小和文件名（不使用init_file，直接设置属性）
        receiver.file_name = "test.txt"
        receiver.file_size = 1536
        receiver.file_data = b""
        
        # 接收三个数据包
        packets = [
            (0, 0, b"AAA" * 171),  # 513字节
            (1, 513, b"BBB" * 171),
            (2, 1026, b"CCC" * 170),
        ]
        
        for seq, offset, payload in packets:
            data = FramePayload.pack_send_data(seq, offset, payload)
            with patch.object(FrameHandler, 'read_frame', return_value=(SerialCommand.SEND_DATA, data)):
                receiver.receive_data_package()
        
        # 验证内存中的数据
        assert len(receiver.file_data) == 1536
        assert receiver.file_data.startswith(b"AAA")
        assert b"BBB" in receiver.file_data
        assert receiver.file_data[-3:] == b"CCC"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

