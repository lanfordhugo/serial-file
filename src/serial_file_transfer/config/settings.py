"""
配置管理
========

提供串口和传输相关的配置类。
"""

from dataclasses import dataclass
from typing import Optional
import serial

from .constants import (
    DEFAULT_BAUDRATE,
    DEFAULT_TIMEOUT,
    DEFAULT_MAX_DATA_LENGTH,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_RETRY_COUNT,
    MIN_CHUNK_SIZE,
    MAX_CHUNK_SIZE,
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
    request_timeout: int = DEFAULT_REQUEST_TIMEOUT  # 请求超时时间(秒)
    retry_count: int = DEFAULT_RETRY_COUNT  # 重试次数
    backoff_base: float = 0.5  # 指数退避基础秒数
    show_progress: bool = True  # 是否显示进度
    max_cache_size: int = 4 * 1024 * 1024  # 触发流式读取阈值(4MB)
    negotiated_chunk_size: Optional[int] = None  # P1-A协商的块大小，覆盖max_data_length
    max_retries: int = 5  # 最大重试次数

    def __post_init__(self):
        """参数验证"""
        if self.max_data_length <= 0:
            raise ValueError("max_data_length必须大于0")
        if self.request_timeout <= 0:
            raise ValueError("request_timeout必须大于0")
        if self.retry_count < 0:
            raise ValueError("retry_count不能为负数")
        if self.backoff_base <= 0:
            raise ValueError("backoff_base必须大于0")
        if self.max_cache_size <= 0:
            raise ValueError("max_cache_size必须大于0")

    def update_chunk_size(self, chunk_size: int) -> None:
        """
        更新协商的块大小 - P1-A功能

        Args:
            chunk_size: 协商得到的块大小
        """
        if chunk_size < MIN_CHUNK_SIZE or chunk_size > MAX_CHUNK_SIZE:
            raise ValueError(f"块大小必须在 {MIN_CHUNK_SIZE} 到 {MAX_CHUNK_SIZE} 之间")

        self.negotiated_chunk_size = chunk_size

    def get_effective_chunk_size(self) -> int:
        """
        获取有效的块大小 - P1-A功能

        Returns:
            如果协商过块大小则返回协商值，否则返回默认的max_data_length
        """
        return (
            self.negotiated_chunk_size
            if self.negotiated_chunk_size is not None
            else self.max_data_length
        )

    def reset_chunk_size(self) -> None:
        """
        重置块大小协商，回到默认值 - P1-A功能
        """
        self.negotiated_chunk_size = None
