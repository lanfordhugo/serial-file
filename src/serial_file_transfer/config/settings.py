"""
配置管理
========

提供串口和传输相关的配置类。
"""

from dataclasses import dataclass
import serial

from .constants import (
    DEFAULT_BAUDRATE,
    DEFAULT_TIMEOUT,
    DEFAULT_MAX_DATA_LENGTH,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_CONNECTION_TIMEOUT,
    DEFAULT_DATA_TIMEOUT,
    DEFAULT_RETRY_COUNT,
    DEFAULT_SEQUENCE_MISMATCH_THRESHOLD,
    DEFAULT_SYNC_TIMEOUT,
)


@dataclass
class SerialConfig:
    """串口配置类"""

    port: str  # 串口号
    baudrate: int = DEFAULT_BAUDRATE  # 波特率
    bytesize: int = serial.EIGHTBITS  # 数据位
    parity: str = serial.PARITY_NONE  # 校验位
    stopbits: float = serial.STOPBITS_ONE  # 停止位
    timeout: float = DEFAULT_TIMEOUT  # 超时时间

    def to_serial_kwargs(self) -> dict:
        """转换为serial.Serial的参数字典"""
        return {
            "port": self.port,
            "baudrate": self.baudrate,
            "bytesize": self.bytesize,
            "parity": self.parity,
            "stopbits": self.stopbits,
            "timeout": self.timeout,
        }


@dataclass
class TransferConfig:
    """传输配置类"""

    max_data_length: int = DEFAULT_MAX_DATA_LENGTH  # 单次传输最大数据长度
    request_timeout: int = DEFAULT_REQUEST_TIMEOUT  # 请求超时时间(秒) - 用于初始连接
    connection_timeout: int = DEFAULT_CONNECTION_TIMEOUT  # 连接建立超时时间(秒)
    data_timeout: int = DEFAULT_DATA_TIMEOUT  # 数据传输超时时间(秒)
    retry_count: int = DEFAULT_RETRY_COUNT  # 重试次数
    backoff_base: float = 0.5  # 指数退避基础秒数
    show_progress: bool = True  # 是否显示进度
    max_cache_size: int = 4 * 1024 * 1024  # 触发流式读取阈值(4MB)
    max_retries: int = 5  # 最大重试次数
    
    # 序号恢复机制配置 (中期改进)
    sequence_mismatch_threshold: int = DEFAULT_SEQUENCE_MISMATCH_THRESHOLD  # 序号不匹配阈值
    sync_timeout: int = DEFAULT_SYNC_TIMEOUT  # 序号同步超时时间
    enable_sequence_recovery: bool = True  # 是否启用序号恢复机制
    
    # 自适应传输策略配置 (长期优化)
    enable_adaptive_strategy: bool = True  # 是否启用自适应传输策略
    adaptive_good_threshold: float = 0.95  # 成功率良好阈值
    adaptive_poor_threshold: float = 0.80  # 成功率较差阈值
    adaptive_bad_threshold: float = 0.60   # 成功率很差阈值
    adaptive_window_size: int = 20         # 自适应策略的样本窗口大小
    adaptive_adjustment_interval: float = 10.0  # 自适应调整间隔(秒)

    def __post_init__(self):
        """参数验证"""
        if self.max_data_length <= 0:
            raise ValueError("max_data_length必须大于0")
        if self.request_timeout <= 0:
            raise ValueError("request_timeout必须大于0")
        if self.connection_timeout <= 0:
            raise ValueError("connection_timeout必须大于0")
        if self.data_timeout <= 0:
            raise ValueError("data_timeout必须大于0")
        if self.retry_count < 0:
            raise ValueError("retry_count不能为负数")
        if self.backoff_base <= 0:
            raise ValueError("backoff_base必须大于0")
        if self.max_cache_size <= 0:
            raise ValueError("max_cache_size必须大于0")
        if self.sequence_mismatch_threshold <= 0:
            raise ValueError("sequence_mismatch_threshold必须大于0")
        if self.sync_timeout <= 0:
            raise ValueError("sync_timeout必须大于0")
        if self.adaptive_good_threshold <= 0 or self.adaptive_good_threshold > 1:
            raise ValueError("adaptive_good_threshold必须在0-1之间")
        if self.adaptive_poor_threshold <= 0 or self.adaptive_poor_threshold > 1:
            raise ValueError("adaptive_poor_threshold必须在0-1之间")
        if self.adaptive_bad_threshold <= 0 or self.adaptive_bad_threshold > 1:
            raise ValueError("adaptive_bad_threshold必须在0-1之间")
        if self.adaptive_window_size <= 0:
            raise ValueError("adaptive_window_size必须大于0")
        if self.adaptive_adjustment_interval <= 0:
            raise ValueError("adaptive_adjustment_interval必须大于0")
