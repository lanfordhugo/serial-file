"""
文件名称: test_sequence_recovery.py
内容摘要: 序号恢复机制的单元测试
当前版本: v1.0.0
作者: AI Assistant
创建日期: 2025-09-29
"""

import pytest
import struct
from unittest.mock import Mock, MagicMock, patch

from src.serial_file_transfer.core.sequence_recovery import SequenceRecoveryManager
from src.serial_file_transfer.config.constants import SerialCommand
from src.serial_file_transfer.core.frame_handler import FrameHandler


class TestSequenceRecoveryManager:
    """测试序号恢复管理器"""

    @pytest.fixture
    def recovery_manager(self):
        """创建序号恢复管理器实例"""
        return SequenceRecoveryManager(
            enable_recovery=True,
            mismatch_threshold=3,
            sync_timeout=2
        )

    @pytest.fixture
    def mock_serial_port(self):
        """创建模拟串口对象"""
        mock_port = Mock()
        mock_port.write.return_value = True
        mock_port.read.return_value = b""
        return mock_port

    def test_sequence_recovery_initialization(self, recovery_manager):
        """测试序号恢复管理器初始化"""
        assert recovery_manager.enable_recovery is True
        assert recovery_manager.mismatch_threshold == 3
        assert recovery_manager.sync_timeout == 2
        assert recovery_manager.consecutive_mismatches == 0
        assert recovery_manager.total_sync_attempts == 0
        assert recovery_manager.successful_syncs == 0

    def test_record_sequence_mismatch_below_threshold(self, recovery_manager):
        """测试序号不匹配记录 - 未达到阈值"""
        # Act: 记录两次不匹配，未达到阈值3
        should_sync_1 = recovery_manager.record_sequence_mismatch()
        should_sync_2 = recovery_manager.record_sequence_mismatch()
        
        # Assert
        assert should_sync_1 is False
        assert should_sync_2 is False
        assert recovery_manager.consecutive_mismatches == 2

    def test_record_sequence_mismatch_reach_threshold(self, recovery_manager):
        """测试序号不匹配记录 - 达到阈值触发同步"""
        # Act: 记录3次不匹配，达到阈值
        recovery_manager.record_sequence_mismatch()  # 1次
        recovery_manager.record_sequence_mismatch()  # 2次
        should_sync = recovery_manager.record_sequence_mismatch()  # 3次，触发
        
        # Assert
        assert should_sync is True
        assert recovery_manager.consecutive_mismatches == 3

    def test_reset_mismatch_counter(self, recovery_manager):
        """测试重置序号不匹配计数器"""
        # Arrange: 先记录一些不匹配
        recovery_manager.record_sequence_mismatch()
        recovery_manager.record_sequence_mismatch()
        assert recovery_manager.consecutive_mismatches == 2
        
        # Act: 重置计数器
        recovery_manager.reset_mismatch_counter()
        
        # Assert
        assert recovery_manager.consecutive_mismatches == 0

    def test_send_sync_request_success(self, recovery_manager, mock_serial_port):
        """测试发送序号同步请求 - 成功"""
        # Arrange
        expected_seq = 15
        current_seq = 10
        
        with patch.object(FrameHandler, 'pack_frame') as mock_pack:
            mock_pack.return_value = b"mock_frame_data"
            
            # Act
            result = recovery_manager.send_sync_request(mock_serial_port, expected_seq, current_seq)
            
            # Assert
            assert result is True
            assert recovery_manager.total_sync_attempts == 1
            mock_pack.assert_called_once_with(
                SerialCommand.SYNC_REQUEST,
                struct.pack("<HH", expected_seq & 0xFFFF, current_seq & 0xFFFF)
            )
            mock_serial_port.write.assert_called_once_with(b"mock_frame_data")

    def test_send_sync_request_disabled(self):
        """测试发送序号同步请求 - 功能禁用"""
        # Arrange
        disabled_manager = SequenceRecoveryManager(enable_recovery=False)
        mock_port = Mock()
        
        # Act
        result = disabled_manager.send_sync_request(mock_port, 15, 10)
        
        # Assert
        assert result is False
        mock_port.write.assert_not_called()

    def test_handle_sync_request_success(self, recovery_manager, mock_serial_port):
        """测试处理序号同步请求 - 成功"""
        # Arrange: 构造同步请求数据
        receiver_expected = 20
        receiver_current = 15
        request_data = struct.pack("<HH", receiver_expected, receiver_current)
        
        with patch.object(FrameHandler, 'pack_frame') as mock_pack:
            mock_pack.return_value = b"mock_reply_frame"
            
            # Act
            result = recovery_manager.handle_sync_request(mock_serial_port, request_data)
            
            # Assert
            assert result is not None
            expected_seq, current_seq = result
            assert expected_seq == receiver_expected
            assert current_seq == receiver_current
            
            mock_pack.assert_called_once_with(
                SerialCommand.SYNC_REPLY,
                struct.pack("<HH", receiver_expected & 0xFFFF, receiver_current & 0xFFFF)
            )
            mock_serial_port.write.assert_called_once_with(b"mock_reply_frame")

    def test_handle_sync_request_invalid_data(self, recovery_manager, mock_serial_port):
        """测试处理序号同步请求 - 数据长度不足"""
        # Arrange: 无效的请求数据（长度不足）
        invalid_request_data = b"abc"  # 少于4字节
        
        # Act
        result = recovery_manager.handle_sync_request(mock_serial_port, invalid_request_data)
        
        # Assert
        assert result is None
        mock_serial_port.write.assert_not_called()

    def test_wait_for_sync_reply_success(self, recovery_manager, mock_serial_port):
        """测试等待序号同步回复 - 成功"""
        # Arrange: 模拟收到同步回复
        confirmed_expected = 25
        confirmed_current = 20
        reply_data = struct.pack("<HH", confirmed_expected, confirmed_current)
        
        with patch.object(FrameHandler, 'read_frame') as mock_read:
            mock_read.return_value = (SerialCommand.SYNC_REPLY, reply_data)
            
            # Act
            result = recovery_manager.wait_for_sync_reply(mock_serial_port)
            
            # Assert
            assert result is not None
            expected_seq, current_seq = result
            assert expected_seq == confirmed_expected
            assert current_seq == confirmed_current
            assert recovery_manager.successful_syncs == 1
            assert recovery_manager.consecutive_mismatches == 0  # 应该被重置

    def test_wait_for_sync_reply_timeout(self, recovery_manager, mock_serial_port):
        """测试等待序号同步回复 - 超时"""
        # Arrange: 模拟超时（总是返回None）
        with patch.object(FrameHandler, 'read_frame') as mock_read:
            mock_read.return_value = (None, None)
            
            with patch('src.serial_file_transfer.core.sequence_recovery.time.time') as mock_time:
                # 模拟时间流逝超过超时时间
                mock_time.side_effect = [0, 0.5, 1.0, 1.5, 2.1, 2.5, 3.0]  # 足够多的值
                
                # Act
                result = recovery_manager.wait_for_sync_reply(mock_serial_port)
                
                # Assert
                assert result is None
                assert recovery_manager.successful_syncs == 0

    def test_wait_for_sync_reply_other_command(self, recovery_manager, mock_serial_port):
        """测试等待序号同步回复 - 收到其他命令"""
        # Arrange: 先收到其他命令，再收到正确的同步回复
        confirmed_expected = 30
        confirmed_current = 25
        reply_data = struct.pack("<HH", confirmed_expected, confirmed_current)
        
        with patch.object(FrameHandler, 'read_frame') as mock_read:
            # 模拟先收到ACK命令，再收到SYNC_REPLY命令
            mock_read.side_effect = [
                (SerialCommand.ACK, b"other_data"),  # 其他命令
                (SerialCommand.SYNC_REPLY, reply_data)  # 正确的同步回复
            ]
            
            # Act
            result = recovery_manager.wait_for_sync_reply(mock_serial_port)
            
            # Assert
            assert result is not None
            expected_seq, current_seq = result
            assert expected_seq == confirmed_expected
            assert current_seq == confirmed_current

    def test_perform_sequence_sync_complete_flow(self, recovery_manager, mock_serial_port):
        """测试执行完整序号同步流程"""
        # Arrange
        expected_seq = 35
        current_seq = 30
        
        with patch.object(recovery_manager, 'send_sync_request') as mock_send:
            with patch.object(recovery_manager, 'wait_for_sync_reply') as mock_wait:
                mock_send.return_value = True
                mock_wait.return_value = (expected_seq, current_seq)
                
                # Act
                result = recovery_manager.perform_sequence_sync(mock_serial_port, expected_seq, current_seq)
                
                # Assert
                assert result == expected_seq
                mock_send.assert_called_once_with(mock_serial_port, expected_seq, current_seq)
                mock_wait.assert_called_once_with(mock_serial_port)

    def test_perform_sequence_sync_send_failed(self, recovery_manager, mock_serial_port):
        """测试执行序号同步流程 - 发送请求失败"""
        # Arrange
        with patch.object(recovery_manager, 'send_sync_request') as mock_send:
            mock_send.return_value = False
            
            # Act
            result = recovery_manager.perform_sequence_sync(mock_serial_port, 35, 30)
            
            # Assert
            assert result is None

    def test_perform_sequence_sync_wait_failed(self, recovery_manager, mock_serial_port):
        """测试执行序号同步流程 - 等待回复失败"""
        # Arrange
        with patch.object(recovery_manager, 'send_sync_request') as mock_send:
            with patch.object(recovery_manager, 'wait_for_sync_reply') as mock_wait:
                mock_send.return_value = True
                mock_wait.return_value = None
                
                # Act
                result = recovery_manager.perform_sequence_sync(mock_serial_port, 35, 30)
                
                # Assert
                assert result is None

    def test_perform_sequence_sync_inconsistent_response(self, recovery_manager, mock_serial_port):
        """测试执行序号同步流程 - 回复序号不一致"""
        # Arrange
        expected_seq = 40
        current_seq = 35
        different_confirmed = 42  # 发送端确认的序号与期望不同
        
        with patch.object(recovery_manager, 'send_sync_request') as mock_send:
            with patch.object(recovery_manager, 'wait_for_sync_reply') as mock_wait:
                mock_send.return_value = True
                mock_wait.return_value = (different_confirmed, current_seq)
                
                # Act
                result = recovery_manager.perform_sequence_sync(mock_serial_port, expected_seq, current_seq)
                
                # Assert
                assert result == different_confirmed  # 应该使用发送端确认的序号

    def test_get_recovery_stats(self, recovery_manager):
        """测试获取序号恢复统计信息"""
        # Arrange: 模拟一些操作
        recovery_manager.total_sync_attempts = 5
        recovery_manager.successful_syncs = 4
        recovery_manager.consecutive_mismatches = 2
        
        # Act
        stats = recovery_manager.get_recovery_stats()
        
        # Assert
        assert stats["enable_recovery"] is True
        assert stats["mismatch_threshold"] == 3
        assert stats["consecutive_mismatches"] == 2
        assert stats["total_sync_attempts"] == 5
        assert stats["successful_syncs"] == 4
        assert stats["sync_success_rate"] == 0.8  # 4/5

    def test_get_recovery_stats_no_attempts(self, recovery_manager):
        """测试获取统计信息 - 无同步尝试"""
        # Act
        stats = recovery_manager.get_recovery_stats()
        
        # Assert
        assert stats["sync_success_rate"] == 0.0

    def test_reset_stats(self, recovery_manager):
        """测试重置统计信息"""
        # Arrange: 设置一些统计数据
        recovery_manager.consecutive_mismatches = 2
        recovery_manager.total_sync_attempts = 3
        recovery_manager.successful_syncs = 2
        
        # Act
        recovery_manager.reset_stats()
        
        # Assert
        assert recovery_manager.consecutive_mismatches == 0
        assert recovery_manager.total_sync_attempts == 0
        assert recovery_manager.successful_syncs == 0

    @pytest.mark.parametrize("enable_recovery", [True, False])
    def test_recovery_manager_enable_flag(self, enable_recovery):
        """测试序号恢复功能启用/禁用标志"""
        # Arrange & Act
        manager = SequenceRecoveryManager(enable_recovery=enable_recovery)
        mock_port = Mock()
        
        # Test various methods respect the enable flag
        record_result = manager.record_sequence_mismatch()
        send_result = manager.send_sync_request(mock_port, 10, 5)
        handle_result = manager.handle_sync_request(mock_port, b"1234")
        wait_result = manager.wait_for_sync_reply(mock_port)
        sync_result = manager.perform_sequence_sync(mock_port, 10, 5)
        
        # Assert
        if enable_recovery:
            # 启用时，方法会正常执行（虽然可能失败，但不会直接返回False/None）
            assert isinstance(record_result, bool)
        else:
            # 禁用时，方法应该直接返回False/None
            assert send_result is False
            assert handle_result is None
            assert wait_result is None
            assert sync_result is None

    def test_edge_case_sequence_number_overflow(self, recovery_manager, mock_serial_port):
        """测试边缘情况：序号溢出处理"""
        # Arrange: 测试16位序号溢出
        max_seq = 0xFFFF
        overflow_seq = max_seq + 5  # 会溢出到4
        
        with patch.object(FrameHandler, 'pack_frame') as mock_pack:
            mock_pack.return_value = b"mock_frame"
            
            # Act
            recovery_manager.send_sync_request(mock_serial_port, overflow_seq, max_seq)
            
            # Assert: 验证序号被正确截断到16位
            mock_pack.assert_called_once_with(
                SerialCommand.SYNC_REQUEST,
                struct.pack("<HH", overflow_seq & 0xFFFF, max_seq & 0xFFFF)
            )

    def test_integration_with_actual_frame_handler(self, recovery_manager):
        """测试与实际FrameHandler的集成"""
        # Arrange
        expected_seq = 100
        current_seq = 95
        
        # Act: 测试实际的帧封装
        sync_data = struct.pack("<HH", expected_seq & 0xFFFF, current_seq & 0xFFFF)
        frame = FrameHandler.pack_frame(SerialCommand.SYNC_REQUEST, sync_data)
        
        # Assert
        assert frame is not None
        assert len(frame) > 0
        
        # 测试帧解析
        unpacked = FrameHandler.unpack_frame(frame)
        assert unpacked is not None
        cmd, data_len, data, crc = unpacked
        assert cmd == SerialCommand.SYNC_REQUEST
        assert len(data) == 4
        
        # 验证数据内容
        parsed_expected, parsed_current = struct.unpack("<HH", data)
        assert parsed_expected == expected_seq
        assert parsed_current == current_seq
