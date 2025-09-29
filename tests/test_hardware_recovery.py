"""
文件名称: test_hardware_recovery.py
内容摘要: 硬件恢复机制的单元测试
当前版本: v1.0.0
作者: AI Assistant
创建日期: 2025-09-29
"""

import pytest
from unittest.mock import Mock, patch, call
import time

from src.serial_file_transfer.transfer.receiver import FileReceiver
from src.serial_file_transfer.config.settings import TransferConfig


class TestHardwareRecoveryMechanism:
    """测试硬件恢复机制"""

    @pytest.fixture
    def mock_serial_manager(self):
        """创建模拟串口管理器"""
        mock = Mock()
        mock.port = Mock()
        mock.port.reset_input_buffer = Mock()
        mock.port.reset_output_buffer = Mock()
        return mock

    @pytest.fixture
    def receiver(self, mock_serial_manager):
        """创建接收器"""
        config = TransferConfig()
        return FileReceiver(mock_serial_manager, config=config)

    def test_first_round_success_no_recovery(self, receiver):
        """测试第一轮重试成功，不触发硬件恢复"""
        with patch.object(receiver, 'send_data_request', return_value=True), \
             patch.object(receiver, 'receive_data_package', return_value=True), \
             patch('src.serial_file_transfer.transfer.receiver.retry_call') as mock_retry:
            
            # 模拟第一轮重试成功
            mock_retry.return_value = True
            
            result = receiver._receive_chunk_with_retry(1024, 4096)
            
            assert result is True
            # 只调用一次retry_call（第一轮）
            assert mock_retry.call_count == 1
            # 第一次调用参数验证
            first_call_args = mock_retry.call_args_list[0]
            assert first_call_args[1]['max_retry'] == 3
            assert first_call_args[1]['base_delay'] == 0.1

    def test_first_round_fails_triggers_recovery(self, receiver):
        """测试第一轮失败触发硬件恢复机制"""
        with patch.object(receiver, 'send_data_request', return_value=True), \
             patch.object(receiver, 'receive_data_package', return_value=False), \
             patch('src.serial_file_transfer.transfer.receiver.retry_call') as mock_retry, \
             patch('time.sleep') as mock_sleep:
            
            # 模拟第一轮失败，第二轮成功
            mock_retry.side_effect = [False, True]
            
            result = receiver._receive_chunk_with_retry(1024, 4096)
            
            assert result is True
            # 调用两次retry_call（第一轮 + 第二轮）
            assert mock_retry.call_count == 2
            
            # 验证硬件恢复延时
            mock_sleep.assert_called_once_with(1.0)
            
            # 验证缓冲区清理
            receiver.serial_manager.port.reset_input_buffer.assert_called_once()
            receiver.serial_manager.port.reset_output_buffer.assert_called_once()
            
            # 验证两轮重试参数
            first_call = mock_retry.call_args_list[0]
            second_call = mock_retry.call_args_list[1]
            
            # 第一轮：快速重试
            assert first_call[1]['max_retry'] == 3
            assert first_call[1]['base_delay'] == 0.1
            
            # 第二轮：保守重试
            assert second_call[1]['max_retry'] == 5
            assert second_call[1]['base_delay'] == 0.2

    def test_both_rounds_fail(self, receiver):
        """测试两轮重试都失败的情况"""
        with patch.object(receiver, 'send_data_request', return_value=True), \
             patch.object(receiver, 'receive_data_package', return_value=False), \
             patch('src.serial_file_transfer.transfer.receiver.retry_call') as mock_retry, \
             patch('time.sleep') as mock_sleep:
            
            # 模拟两轮都失败
            mock_retry.return_value = False
            
            result = receiver._receive_chunk_with_retry(1024, 4096)
            
            assert result is False
            # 两轮都尝试了
            assert mock_retry.call_count == 2
            # 硬件恢复被触发
            mock_sleep.assert_called_once_with(1.0)
            receiver.serial_manager.port.reset_input_buffer.assert_called_once()
            receiver.serial_manager.port.reset_output_buffer.assert_called_once()

    def test_buffer_cleanup_exception_handling(self, receiver):
        """测试缓冲区清理异常处理"""
        with patch.object(receiver, 'send_data_request', return_value=True), \
             patch.object(receiver, 'receive_data_package', return_value=False), \
             patch('src.serial_file_transfer.transfer.receiver.retry_call') as mock_retry, \
             patch('time.sleep'):
            
            # 模拟缓冲区清理异常
            receiver.serial_manager.port.reset_input_buffer.side_effect = Exception("缓冲区清理失败")
            mock_retry.side_effect = [False, True]  # 第一轮失败，第二轮成功
            
            # 应该不会因为缓冲区清理异常而崩溃
            result = receiver._receive_chunk_with_retry(1024, 4096)
            
            assert result is True
            assert mock_retry.call_count == 2

    def test_send_request_fails_multiple_times(self, receiver):
        """测试发送请求多次失败的情况"""
        with patch.object(receiver, 'send_data_request', return_value=False), \
             patch('src.serial_file_transfer.transfer.receiver.retry_call') as mock_retry, \
             patch('time.sleep'):
            
            # 模拟retry_call返回False（所有重试都失败）
            mock_retry.return_value = False
            
            result = receiver._receive_chunk_with_retry(1024, 4096)
            
            assert result is False
            # 两轮重试都被调用
            assert mock_retry.call_count == 2

    def test_hardware_recovery_timing(self, receiver):
        """测试硬件恢复的时序"""
        with patch.object(receiver, 'send_data_request', return_value=True), \
             patch.object(receiver, 'receive_data_package', return_value=False), \
             patch('src.serial_file_transfer.transfer.receiver.retry_call') as mock_retry, \
             patch('time.sleep') as mock_sleep:
            
            mock_retry.side_effect = [False, True]
            
            start_time = time.time()
            result = receiver._receive_chunk_with_retry(1024, 4096)
            end_time = time.time()
            
            assert result is True
            # 验证调用了硬件恢复延时
            mock_sleep.assert_called_once_with(1.0)

    @pytest.mark.parametrize("first_success,second_success,expected_result,expected_calls", [
        (True, None, True, 1),    # 第一轮成功，不需要第二轮
        (False, True, True, 2),   # 第一轮失败，第二轮成功
        (False, False, False, 2), # 两轮都失败
    ])
    def test_retry_scenarios(self, receiver, first_success, second_success, expected_result, expected_calls):
        """测试各种重试场景"""
        with patch.object(receiver, 'send_data_request', return_value=True), \
             patch.object(receiver, 'receive_data_package', return_value=False), \
             patch('src.serial_file_transfer.transfer.receiver.retry_call') as mock_retry, \
             patch('time.sleep'):
            
            if second_success is None:
                mock_retry.return_value = first_success
            else:
                mock_retry.side_effect = [first_success, second_success]
            
            result = receiver._receive_chunk_with_retry(1024, 4096)
            
            assert result == expected_result
            assert mock_retry.call_count == expected_calls

    def test_logging_behavior_functional(self, receiver):
        """测试日志记录的功能性行为（不验证具体内容，只验证没有异常）"""
        with patch.object(receiver, 'send_data_request', return_value=True), \
             patch.object(receiver, 'receive_data_package', return_value=False), \
             patch('src.serial_file_transfer.transfer.receiver.retry_call') as mock_retry, \
             patch('time.sleep'):
            
            mock_retry.side_effect = [False, True]  # 第一轮失败，第二轮成功
            
            # 验证日志记录不会导致异常
            result = receiver._receive_chunk_with_retry(1024, 4096)
            
            assert result is True
            # 验证两轮重试都被调用
            assert mock_retry.call_count == 2

    def test_multiple_chunk_recovery_sequence(self, receiver):
        """测试多个数据块的恢复序列"""
        with patch.object(receiver, 'send_data_request', return_value=True), \
             patch.object(receiver, 'receive_data_package', return_value=False), \
             patch('src.serial_file_transfer.transfer.receiver.retry_call') as mock_retry, \
             patch('time.sleep') as mock_sleep:
            
            # 模拟前两个块第一轮失败，第二轮成功
            mock_retry.side_effect = [False, True, False, True]
            
            result1 = receiver._receive_chunk_with_retry(1024, 4096)
            result2 = receiver._receive_chunk_with_retry(5120, 4096)
            
            assert result1 is True
            assert result2 is True
            
            # 每个块都触发了硬件恢复
            assert mock_sleep.call_count == 2
            assert all(call(1.0) == call_arg for call_arg in mock_sleep.call_args_list)
            
            # 每个块都清理了缓冲区
            assert receiver.serial_manager.port.reset_input_buffer.call_count == 2
            assert receiver.serial_manager.port.reset_output_buffer.call_count == 2
