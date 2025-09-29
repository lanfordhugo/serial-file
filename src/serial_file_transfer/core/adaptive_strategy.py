"""
文件名称: adaptive_strategy.py
内容摘要: 自适应传输策略 - 动态调整传输参数以优化性能和稳定性
当前版本: v1.0.0
作者: AI Assistant
创建日期: 2025-09-29
"""

import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from ..config.constants import MIN_CHUNK_SIZE, MAX_CHUNK_SIZE
from ..utils.logger import get_console_logger

logger = get_console_logger(__name__)


@dataclass
class TransmissionMetrics:
    """传输指标数据类"""
    
    # 基础统计
    total_packets: int = 0
    successful_packets: int = 0
    failed_packets: int = 0
    retransmitted_packets: int = 0
    
    # 时间统计
    total_transmission_time: float = 0.0
    last_packet_time: float = 0.0
    
    # 错误统计
    sequence_mismatches: int = 0
    timeout_errors: int = 0
    crc_errors: int = 0
    
    # 性能统计
    average_speed: float = 0.0  # KB/s
    current_block_size: int = 1024
    
    def get_success_rate(self) -> float:
        """计算成功率"""
        if self.total_packets == 0:
            return 1.0
        return self.successful_packets / self.total_packets
    
    def get_error_rate(self) -> float:
        """计算错误率"""
        return 1.0 - self.get_success_rate()
    
    def get_retransmission_rate(self) -> float:
        """计算重传率"""
        if self.total_packets == 0:
            return 0.0
        return self.retransmitted_packets / self.total_packets


@dataclass
class AdaptiveParameters:
    """自适应参数配置"""
    
    # 块大小调整参数
    min_block_size: int = MIN_CHUNK_SIZE
    max_block_size: int = MAX_CHUNK_SIZE
    block_size_step: int = 512  # 块大小调整步长
    
    # 成功率阈值
    good_threshold: float = 0.95    # 成功率超过95%认为良好
    poor_threshold: float = 0.80    # 成功率低于80%认为较差
    bad_threshold: float = 0.60     # 成功率低于60%认为很差
    
    # 调整策略参数
    aggressive_increase: bool = False  # 是否激进增长
    conservative_decrease: bool = True  # 是否保守减少
    
    # 样本窗口大小
    window_size: int = 20  # 最近N个包的统计窗口
    min_samples: int = 5   # 最少样本数才进行调整
    
    # 时间相关参数
    adjustment_interval: float = 10.0  # 调整间隔(秒)
    stability_period: float = 30.0     # 稳定期时间(秒)


class AdaptiveTransmissionStrategy:
    """自适应传输策略管理器 - 长期优化功能"""
    
    def __init__(self, initial_block_size: int = 4096, parameters: Optional[AdaptiveParameters] = None):
        """
        初始化自适应传输策略
        
        Args:
            initial_block_size: 初始块大小
            parameters: 自适应参数配置
        """
        self.parameters = parameters or AdaptiveParameters()
        self.metrics = TransmissionMetrics(current_block_size=initial_block_size)
        
        # 调整历史
        self.adjustment_history: list[Dict[str, Any]] = []
        self.last_adjustment_time = time.time()
        
        # 性能监控
        self.recent_packets: list[Dict[str, Any]] = []  # 最近的包统计
        self.is_stable = False
        self.stability_start_time = time.time()
        
        logger.info(f"自适应传输策略已初始化，初始块大小: {initial_block_size}字节")
    
    def record_packet_result(self, success: bool, block_size: int, transmission_time: float, 
                           error_type: Optional[str] = None) -> None:
        """
        记录数据包传输结果
        
        Args:
            success: 是否传输成功
            block_size: 数据包大小
            transmission_time: 传输时间
            error_type: 错误类型（'timeout', 'crc', 'sequence'等）
        """
        current_time = time.time()
        
        # 更新基础统计
        self.metrics.total_packets += 1
        if success:
            self.metrics.successful_packets += 1
        else:
            self.metrics.failed_packets += 1
            
        self.metrics.total_transmission_time += transmission_time
        self.metrics.last_packet_time = current_time
        
        # 记录错误类型
        if error_type:
            if error_type == 'timeout':
                self.metrics.timeout_errors += 1
            elif error_type == 'crc':
                self.metrics.crc_errors += 1
            elif error_type == 'sequence':
                self.metrics.sequence_mismatches += 1
        
        # 计算当前速度
        if transmission_time > 0:
            current_speed = (block_size / 1024) / transmission_time  # KB/s
            self.metrics.average_speed = (
                (self.metrics.average_speed * (self.metrics.total_packets - 1) + current_speed) 
                / self.metrics.total_packets
            )
        
        # 添加到最近包统计
        packet_info = {
            'timestamp': current_time,
            'success': success,
            'block_size': block_size,
            'transmission_time': transmission_time,
            'error_type': error_type,
            'speed': (block_size / 1024) / transmission_time if transmission_time > 0 else 0
        }
        
        self.recent_packets.append(packet_info)
        
        # 保持窗口大小
        if len(self.recent_packets) > self.parameters.window_size:
            self.recent_packets.pop(0)
        
        logger.debug(f"记录包结果: 成功={success}, 大小={block_size}, 时间={transmission_time:.3f}s")
    
    def record_retransmission(self) -> None:
        """记录重传事件"""
        self.metrics.retransmitted_packets += 1
        logger.debug("记录重传事件")
    
    def should_adjust_parameters(self) -> bool:
        """
        判断是否应该调整参数
        
        Returns:
            是否需要调整参数
        """
        current_time = time.time()
        
        # 检查样本数量
        if len(self.recent_packets) < self.parameters.min_samples:
            return False
        
        # 检查调整间隔
        if current_time - self.last_adjustment_time < self.parameters.adjustment_interval:
            return False
        
        # 检查稳定期
        if self.is_stable and current_time - self.stability_start_time < self.parameters.stability_period:
            return False
            
        return True
    
    def analyze_recent_performance(self) -> Dict[str, float]:
        """
        分析最近的传输性能
        
        Returns:
            包含性能指标的字典
        """
        if not self.recent_packets:
            return {}
        
        recent_success = sum(1 for p in self.recent_packets if p['success'])
        recent_total = len(self.recent_packets)
        success_rate = recent_success / recent_total if recent_total > 0 else 0.0
        
        # 计算平均传输时间
        total_time = sum(p['transmission_time'] for p in self.recent_packets)
        avg_transmission_time = total_time / recent_total if recent_total > 0 else 0.0
        
        # 计算平均速度
        speeds = [p['speed'] for p in self.recent_packets if p['speed'] > 0]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
        
        # 错误类型分析
        timeout_count = sum(1 for p in self.recent_packets if p.get('error_type') == 'timeout')
        crc_count = sum(1 for p in self.recent_packets if p.get('error_type') == 'crc')
        sequence_count = sum(1 for p in self.recent_packets if p.get('error_type') == 'sequence')
        
        return {
            'success_rate': success_rate,
            'avg_transmission_time': avg_transmission_time,
            'avg_speed': avg_speed,
            'timeout_rate': timeout_count / recent_total,
            'crc_error_rate': crc_count / recent_total,
            'sequence_error_rate': sequence_count / recent_total,
            'sample_count': recent_total
        }
    
    def calculate_optimal_block_size(self, performance: Dict[str, float]) -> int:
        """
        基于性能分析计算最优块大小
        
        Args:
            performance: 性能指标字典
            
        Returns:
            建议的块大小
        """
        current_size = self.metrics.current_block_size
        success_rate = performance.get('success_rate', 0.0)
        
        # 根据成功率调整策略
        if success_rate >= self.parameters.good_threshold:
            # 性能良好，尝试增加块大小
            if self.parameters.aggressive_increase:
                new_size = min(current_size * 2, self.parameters.max_block_size)
            else:
                new_size = min(current_size + self.parameters.block_size_step, self.parameters.max_block_size)
            
            logger.debug(f"性能良好(成功率:{success_rate:.2%})，增加块大小: {current_size} -> {new_size}")
            
        elif success_rate <= self.parameters.bad_threshold:
            # 性能很差，大幅减少块大小
            if self.parameters.conservative_decrease:
                new_size = max(current_size - self.parameters.block_size_step, self.parameters.min_block_size)
            else:
                new_size = max(current_size // 2, self.parameters.min_block_size)
            
            logger.warning(f"性能很差(成功率:{success_rate:.2%})，减少块大小: {current_size} -> {new_size}")
            
        elif success_rate <= self.parameters.poor_threshold:
            # 性能较差，适当减少块大小
            new_size = max(current_size - self.parameters.block_size_step // 2, self.parameters.min_block_size)
            
            logger.info(f"性能较差(成功率:{success_rate:.2%})，适当减少块大小: {current_size} -> {new_size}")
            
        else:
            # 性能中等，保持不变
            new_size = current_size
            logger.debug(f"性能中等(成功率:{success_rate:.2%})，保持块大小: {current_size}")
        
        # 特殊错误处理
        if performance.get('timeout_rate', 0) > 0.3:
            # 超时率过高，优先减小块大小
            new_size = max(new_size // 2, self.parameters.min_block_size)
            logger.warning(f"超时率过高({performance['timeout_rate']:.2%})，强制减小块大小")
        
        return new_size
    
    def adjust_parameters(self) -> Optional[Dict[str, Any]]:
        """
        执行参数调整
        
        Returns:
            调整结果字典，如果无需调整则返回None
        """
        if not self.should_adjust_parameters():
            return None
        
        # 分析性能
        performance = self.analyze_recent_performance()
        if not performance:
            return None
        
        # 计算新的块大小
        old_block_size = self.metrics.current_block_size
        new_block_size = self.calculate_optimal_block_size(performance)
        
        current_time = time.time()
        
        # 记录调整
        adjustment = {
            'timestamp': current_time,
            'old_block_size': old_block_size,
            'new_block_size': new_block_size,
            'performance': performance.copy(),
            'reason': self._get_adjustment_reason(performance)
        }
        
        self.adjustment_history.append(adjustment)
        self.last_adjustment_time = current_time
        
        # 更新参数
        if new_block_size != old_block_size:
            self.metrics.current_block_size = new_block_size
            self.is_stable = False
            self.stability_start_time = current_time
            
            logger.info(f"自适应调整完成: 块大小 {old_block_size} -> {new_block_size} 字节")
        else:
            # 如果没有调整，说明进入稳定期
            if not self.is_stable:
                self.is_stable = True
                self.stability_start_time = current_time
                logger.info("传输策略进入稳定期")
        
        return adjustment
    
    def _get_adjustment_reason(self, performance: Dict[str, float]) -> str:
        """获取调整原因描述"""
        success_rate = performance.get('success_rate', 0.0)
        timeout_rate = performance.get('timeout_rate', 0.0)
        
        if timeout_rate > 0.3:
            return f"超时率过高({timeout_rate:.1%})"
        elif success_rate >= self.parameters.good_threshold:
            return f"性能良好(成功率{success_rate:.1%})"
        elif success_rate <= self.parameters.bad_threshold:
            return f"性能很差(成功率{success_rate:.1%})"
        elif success_rate <= self.parameters.poor_threshold:
            return f"性能较差(成功率{success_rate:.1%})"
        else:
            return f"性能稳定(成功率{success_rate:.1%})"
    
    def get_current_block_size(self) -> int:
        """获取当前推荐的块大小"""
        return self.metrics.current_block_size
    
    def get_strategy_stats(self) -> Dict[str, Any]:
        """
        获取策略统计信息
        
        Returns:
            包含策略统计的字典
        """
        performance = self.analyze_recent_performance()
        
        return {
            'metrics': {
                'total_packets': self.metrics.total_packets,
                'success_rate': self.metrics.get_success_rate(),
                'error_rate': self.metrics.get_error_rate(),
                'retransmission_rate': self.metrics.get_retransmission_rate(),
                'average_speed': self.metrics.average_speed,
                'current_block_size': self.metrics.current_block_size,
            },
            'recent_performance': performance,
            'strategy_status': {
                'is_stable': self.is_stable,
                'adjustment_count': len(self.adjustment_history),
                'last_adjustment_time': self.last_adjustment_time,
            },
            'error_breakdown': {
                'timeout_errors': self.metrics.timeout_errors,
                'crc_errors': self.metrics.crc_errors,
                'sequence_mismatches': self.metrics.sequence_mismatches,
            }
        }
    
    def reset_strategy(self, new_block_size: Optional[int] = None) -> None:
        """
        重置策略状态
        
        Args:
            new_block_size: 新的初始块大小，如果为None则使用当前大小
        """
        if new_block_size is not None:
            self.metrics.current_block_size = new_block_size
        
        self.metrics.total_packets = 0
        self.metrics.successful_packets = 0
        self.metrics.failed_packets = 0
        self.metrics.retransmitted_packets = 0
        self.metrics.total_transmission_time = 0.0
        self.metrics.sequence_mismatches = 0
        self.metrics.timeout_errors = 0
        self.metrics.crc_errors = 0
        self.metrics.average_speed = 0.0
        
        self.recent_packets.clear()
        self.adjustment_history.clear()
        self.is_stable = False
        self.last_adjustment_time = time.time()
        self.stability_start_time = time.time()
        
        logger.info(f"自适应策略已重置，块大小: {self.metrics.current_block_size}字节")
