"""
文件名称: test_adaptive_strategy.py
内容摘要: 自适应传输策略的单元测试
当前版本: v1.0.0
作者: AI Assistant
创建日期: 2025-09-29
"""

import pytest
import time
from unittest.mock import patch

from src.serial_file_transfer.core.adaptive_strategy import (
    TransmissionMetrics,
    AdaptiveParameters, 
    AdaptiveTransmissionStrategy
)


class TestTransmissionMetrics:
    """测试传输指标数据类"""

    def test_transmission_metrics_initialization(self):
        """测试传输指标初始化"""
        metrics = TransmissionMetrics()
        
        assert metrics.total_packets == 0
        assert metrics.successful_packets == 0
        assert metrics.failed_packets == 0
        assert metrics.retransmitted_packets == 0
        assert metrics.total_transmission_time == 0.0
        assert metrics.sequence_mismatches == 0
        assert metrics.timeout_errors == 0
        assert metrics.crc_errors == 0
        assert metrics.average_speed == 0.0
        assert metrics.current_block_size == 1024

    def test_get_success_rate_no_packets(self):
        """测试获取成功率 - 无数据包"""
        metrics = TransmissionMetrics()
        assert metrics.get_success_rate() == 1.0

    def test_get_success_rate_with_packets(self):
        """测试获取成功率 - 有数据包"""
        metrics = TransmissionMetrics()
        metrics.total_packets = 10
        metrics.successful_packets = 8
        
        assert metrics.get_success_rate() == 0.8

    def test_get_error_rate(self):
        """测试获取错误率"""
        metrics = TransmissionMetrics()
        metrics.total_packets = 10
        metrics.successful_packets = 7
        
        assert abs(metrics.get_error_rate() - 0.3) < 0.001  # 使用近似比较避免浮点精度问题

    def test_get_retransmission_rate_no_packets(self):
        """测试获取重传率 - 无数据包"""
        metrics = TransmissionMetrics()
        assert metrics.get_retransmission_rate() == 0.0

    def test_get_retransmission_rate_with_packets(self):
        """测试获取重传率 - 有数据包"""
        metrics = TransmissionMetrics()
        metrics.total_packets = 20
        metrics.retransmitted_packets = 3
        
        assert metrics.get_retransmission_rate() == 0.15


class TestAdaptiveParameters:
    """测试自适应参数配置"""

    def test_adaptive_parameters_default_values(self):
        """测试自适应参数默认值"""
        params = AdaptiveParameters()
        
        assert params.min_block_size == 512  # MIN_CHUNK_SIZE
        assert params.max_block_size == 16384  # MAX_CHUNK_SIZE
        assert params.block_size_step == 512
        assert params.good_threshold == 0.95
        assert params.poor_threshold == 0.80
        assert params.bad_threshold == 0.60
        assert params.aggressive_increase is False
        assert params.conservative_decrease is True
        assert params.window_size == 20
        assert params.min_samples == 5
        assert params.adjustment_interval == 10.0
        assert params.stability_period == 30.0

    def test_adaptive_parameters_custom_values(self):
        """测试自适应参数自定义值"""
        params = AdaptiveParameters(
            min_block_size=1024,
            max_block_size=8192,
            good_threshold=0.90,
            poor_threshold=0.75,
            window_size=15
        )
        
        assert params.min_block_size == 1024
        assert params.max_block_size == 8192
        assert params.good_threshold == 0.90
        assert params.poor_threshold == 0.75
        assert params.window_size == 15


class TestAdaptiveTransmissionStrategy:
    """测试自适应传输策略"""

    @pytest.fixture
    def strategy(self):
        """创建自适应传输策略实例"""
        return AdaptiveTransmissionStrategy(initial_block_size=2048)

    @pytest.fixture
    def custom_strategy(self):
        """创建带自定义参数的自适应传输策略实例"""
        params = AdaptiveParameters(
            window_size=10,
            min_samples=3,
            adjustment_interval=5.0,
            good_threshold=0.90,
            poor_threshold=0.75
        )
        return AdaptiveTransmissionStrategy(initial_block_size=1024, parameters=params)

    def test_strategy_initialization(self, strategy):
        """测试自适应策略初始化"""
        assert strategy.metrics.current_block_size == 2048
        assert strategy.metrics.total_packets == 0
        assert len(strategy.recent_packets) == 0
        assert len(strategy.adjustment_history) == 0
        assert strategy.is_stable is False

    def test_record_packet_result_success(self, strategy):
        """测试记录数据包结果 - 成功"""
        strategy.record_packet_result(
            success=True,
            block_size=2048,
            transmission_time=0.1
        )
        
        assert strategy.metrics.total_packets == 1
        assert strategy.metrics.successful_packets == 1
        assert strategy.metrics.failed_packets == 0
        assert len(strategy.recent_packets) == 1
        
        packet = strategy.recent_packets[0]
        assert packet['success'] is True
        assert packet['block_size'] == 2048
        assert packet['transmission_time'] == 0.1

    def test_record_packet_result_failure_with_error_type(self, strategy):
        """测试记录数据包结果 - 失败并带错误类型"""
        strategy.record_packet_result(
            success=False,
            block_size=2048,
            transmission_time=0.2,
            error_type='timeout'
        )
        
        assert strategy.metrics.total_packets == 1
        assert strategy.metrics.successful_packets == 0
        assert strategy.metrics.failed_packets == 1
        assert strategy.metrics.timeout_errors == 1
        
        packet = strategy.recent_packets[0]
        assert packet['success'] is False
        assert packet['error_type'] == 'timeout'

    def test_record_packet_result_different_error_types(self, strategy):
        """测试记录不同错误类型"""
        # 超时错误
        strategy.record_packet_result(False, 1024, 0.1, 'timeout')
        assert strategy.metrics.timeout_errors == 1
        
        # CRC错误
        strategy.record_packet_result(False, 1024, 0.1, 'crc')
        assert strategy.metrics.crc_errors == 1
        
        # 序号错误
        strategy.record_packet_result(False, 1024, 0.1, 'sequence')
        assert strategy.metrics.sequence_mismatches == 1

    def test_record_retransmission(self, strategy):
        """测试记录重传事件"""
        strategy.record_retransmission()
        assert strategy.metrics.retransmitted_packets == 1
        
        strategy.record_retransmission()
        assert strategy.metrics.retransmitted_packets == 2

    def test_recent_packets_window_size_limit(self, custom_strategy):
        """测试最近包统计的窗口大小限制"""
        # 添加超过窗口大小的包
        for i in range(15):  # 窗口大小为10
            custom_strategy.record_packet_result(True, 1024, 0.1)
        
        # 应该只保留最近的10个包
        assert len(custom_strategy.recent_packets) == 10

    def test_should_adjust_parameters_insufficient_samples(self, custom_strategy):
        """测试是否应该调整参数 - 样本不足"""
        # 只添加2个样本，少于最小样本数3
        custom_strategy.record_packet_result(True, 1024, 0.1)
        custom_strategy.record_packet_result(True, 1024, 0.1)
        
        assert custom_strategy.should_adjust_parameters() is False

    def test_should_adjust_parameters_sufficient_samples(self, custom_strategy):
        """测试是否应该调整参数 - 样本充足"""
        # 添加足够的样本
        for i in range(5):
            custom_strategy.record_packet_result(True, 1024, 0.1)
        
        # 模拟时间流逝超过调整间隔
        with patch('time.time') as mock_time:
            mock_time.return_value = custom_strategy.last_adjustment_time + 10.0
            assert custom_strategy.should_adjust_parameters() is True

    def test_should_adjust_parameters_too_soon(self, custom_strategy):
        """测试是否应该调整参数 - 时间间隔不够"""
        # 添加足够的样本
        for i in range(5):
            custom_strategy.record_packet_result(True, 1024, 0.1)
        
        # 时间间隔不够（少于5秒）
        with patch('time.time') as mock_time:
            mock_time.return_value = custom_strategy.last_adjustment_time + 3.0
            assert custom_strategy.should_adjust_parameters() is False

    def test_analyze_recent_performance(self, strategy):
        """测试分析最近的传输性能"""
        # 添加一些传输记录
        strategy.record_packet_result(True, 2048, 0.1)
        strategy.record_packet_result(True, 2048, 0.12)
        strategy.record_packet_result(False, 2048, 0.2, 'timeout')
        strategy.record_packet_result(True, 2048, 0.08)
        
        performance = strategy.analyze_recent_performance()
        
        assert performance['success_rate'] == 0.75  # 3/4
        assert performance['sample_count'] == 4
        assert performance['timeout_rate'] == 0.25  # 1/4
        assert performance['crc_error_rate'] == 0.0
        assert performance['sequence_error_rate'] == 0.0
        assert performance['avg_transmission_time'] > 0

    def test_calculate_optimal_block_size_good_performance(self, strategy):
        """测试计算最优块大小 - 性能良好"""
        strategy.metrics.current_block_size = 2048
        
        # 模拟良好性能（成功率95%）
        performance = {'success_rate': 0.95, 'timeout_rate': 0.0}
        
        new_size = strategy.calculate_optimal_block_size(performance)
        
        # 应该增加块大小
        assert new_size > 2048
        assert new_size <= strategy.parameters.max_block_size

    def test_calculate_optimal_block_size_poor_performance(self, strategy):
        """测试计算最优块大小 - 性能较差"""
        strategy.metrics.current_block_size = 2048
        
        # 模拟较差性能（成功率75%）
        performance = {'success_rate': 0.75, 'timeout_rate': 0.1}
        
        new_size = strategy.calculate_optimal_block_size(performance)
        
        # 应该减少块大小
        assert new_size < 2048
        assert new_size >= strategy.parameters.min_block_size

    def test_calculate_optimal_block_size_bad_performance(self, strategy):
        """测试计算最优块大小 - 性能很差"""
        strategy.metrics.current_block_size = 2048
        
        # 模拟很差性能（成功率50%）
        performance = {'success_rate': 0.50, 'timeout_rate': 0.2}
        
        new_size = strategy.calculate_optimal_block_size(performance)
        
        # 应该大幅减少块大小
        assert new_size < 2048
        assert new_size >= strategy.parameters.min_block_size

    def test_calculate_optimal_block_size_high_timeout_rate(self, strategy):
        """测试计算最优块大小 - 高超时率"""
        strategy.metrics.current_block_size = 4096
        
        # 模拟高超时率（40%）
        performance = {'success_rate': 0.60, 'timeout_rate': 0.4}
        
        new_size = strategy.calculate_optimal_block_size(performance)
        
        # 应该强制减半
        assert new_size <= 2048

    def test_calculate_optimal_block_size_at_boundaries(self, strategy):
        """测试计算最优块大小 - 边界情况"""
        # 测试最小值边界
        strategy.metrics.current_block_size = strategy.parameters.min_block_size
        performance = {'success_rate': 0.40, 'timeout_rate': 0.1}
        
        new_size = strategy.calculate_optimal_block_size(performance)
        assert new_size == strategy.parameters.min_block_size  # 不能更小
        
        # 测试最大值边界
        strategy.metrics.current_block_size = strategy.parameters.max_block_size
        performance = {'success_rate': 0.98, 'timeout_rate': 0.0}
        
        new_size = strategy.calculate_optimal_block_size(performance)
        assert new_size == strategy.parameters.max_block_size  # 不能更大

    def test_adjust_parameters_successful_adjustment(self, custom_strategy):
        """测试执行参数调整 - 成功调整"""
        # 准备足够的样本
        for i in range(5):
            custom_strategy.record_packet_result(True, 1024, 0.1)
        
        with patch('time.time') as mock_time:
            mock_time.return_value = custom_strategy.last_adjustment_time + 10.0
            
            adjustment = custom_strategy.adjust_parameters()
            
            assert adjustment is not None
            assert 'old_block_size' in adjustment
            assert 'new_block_size' in adjustment
            assert 'performance' in adjustment
            assert 'reason' in adjustment
            assert len(custom_strategy.adjustment_history) == 1

    def test_adjust_parameters_no_adjustment_needed(self, custom_strategy):
        """测试执行参数调整 - 无需调整"""
        # 样本不足
        custom_strategy.record_packet_result(True, 1024, 0.1)
        
        adjustment = custom_strategy.adjust_parameters()
        assert adjustment is None

    def test_stability_detection(self, custom_strategy):
        """测试稳定性检测"""
        # 添加稳定的性能数据
        for i in range(5):
            custom_strategy.record_packet_result(True, 1024, 0.1)
        
        # 第一次调整
        with patch('time.time') as mock_time:
            mock_time.return_value = custom_strategy.last_adjustment_time + 10.0
            adjustment = custom_strategy.adjust_parameters()
            
            if adjustment and adjustment['new_block_size'] == adjustment['old_block_size']:
                assert custom_strategy.is_stable is True

    def test_get_current_block_size(self, strategy):
        """测试获取当前块大小"""
        assert strategy.get_current_block_size() == 2048
        
        strategy.metrics.current_block_size = 4096
        assert strategy.get_current_block_size() == 4096

    def test_get_strategy_stats(self, strategy):
        """测试获取策略统计信息"""
        # 添加一些数据
        strategy.record_packet_result(True, 2048, 0.1)
        strategy.record_packet_result(False, 2048, 0.2, 'timeout')
        strategy.record_retransmission()
        
        stats = strategy.get_strategy_stats()
        
        assert 'metrics' in stats
        assert 'recent_performance' in stats
        assert 'strategy_status' in stats
        assert 'error_breakdown' in stats
        
        assert stats['metrics']['total_packets'] == 2
        assert stats['metrics']['success_rate'] == 0.5
        assert stats['error_breakdown']['timeout_errors'] == 1

    def test_reset_strategy(self, strategy):
        """测试重置策略状态"""
        # 添加一些数据
        strategy.record_packet_result(True, 2048, 0.1)
        strategy.record_retransmission()
        
        # 重置策略
        strategy.reset_strategy(new_block_size=1024)
        
        assert strategy.metrics.current_block_size == 1024
        assert strategy.metrics.total_packets == 0
        assert strategy.metrics.successful_packets == 0
        assert strategy.metrics.retransmitted_packets == 0
        assert len(strategy.recent_packets) == 0
        assert len(strategy.adjustment_history) == 0
        assert strategy.is_stable is False

    def test_reset_strategy_keep_current_block_size(self, strategy):
        """测试重置策略状态 - 保持当前块大小"""
        original_block_size = strategy.metrics.current_block_size
        strategy.record_packet_result(True, 2048, 0.1)
        
        # 重置但不改变块大小
        strategy.reset_strategy()
        
        assert strategy.metrics.current_block_size == original_block_size
        assert strategy.metrics.total_packets == 0

    @pytest.mark.parametrize("success_rate,expected_adjustment", [
        (0.98, "increase"),  # 性能优秀，应该增加
        (0.96, "increase"),  # 性能良好，应该增加（调整到超过0.95阈值）
        (0.85, "maintain"),  # 性能中等，保持不变
        (0.75, "decrease"),  # 性能较差，应该减少
        (0.50, "decrease"),  # 性能很差，应该减少
    ])
    def test_adjustment_logic_with_different_success_rates(self, strategy, success_rate, expected_adjustment):
        """测试不同成功率下的调整逻辑"""
        current_size = strategy.metrics.current_block_size
        
        # 构造性能数据
        performance = {
            'success_rate': success_rate,
            'timeout_rate': 0.05,
            'sample_count': 10
        }
        
        new_size = strategy.calculate_optimal_block_size(performance)
        
        if expected_adjustment == "increase":
            assert new_size > current_size
        elif expected_adjustment == "decrease":
            assert new_size < current_size
        elif expected_adjustment == "maintain":
            assert new_size == current_size

    def test_integration_with_real_transmission_scenario(self, strategy):
        """测试与真实传输场景的集成"""
        # 模拟一个真实的传输过程
        
        # 开始阶段：良好的传输
        for i in range(10):
            strategy.record_packet_result(True, 2048, 0.1)
        
        # 中间阶段：出现一些问题
        for i in range(5):
            strategy.record_packet_result(False, 2048, 0.3, 'timeout')
        
        # 恢复阶段：重新稳定
        for i in range(10):
            strategy.record_packet_result(True, 1024, 0.08)  # 使用更小的块
        
        # 检查策略的适应性
        performance = strategy.analyze_recent_performance()
        assert performance['sample_count'] > 0
        
        # 策略应该记录了所有统计信息
        stats = strategy.get_strategy_stats()
        assert stats['metrics']['total_packets'] == 25
        assert stats['error_breakdown']['timeout_errors'] == 5
