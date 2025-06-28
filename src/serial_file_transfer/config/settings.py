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
    DEFAULT_RETRY_COUNT
)


@dataclass
class SerialConfig:
    """串口配置类"""
    
    port: str                                    # 串口号
    baudrate: int = DEFAULT_BAUDRATE            # 波特率
    bytesize: int = serial.EIGHTBITS            # 数据位
    parity: str = serial.PARITY_NONE            # 校验位
    stopbits: float = serial.STOPBITS_ONE       # 停止位
    timeout: float = DEFAULT_TIMEOUT            # 超时时间
    
    def to_serial_kwargs(self) -> dict:
        """转换为serial.Serial的参数字典"""
        return {
            'port': self.port,
            'baudrate': self.baudrate,
            'bytesize': self.bytesize,
            'parity': self.parity,
            'stopbits': self.stopbits,
            'timeout': self.timeout
        }


@dataclass  
class TransferConfig:
    """传输配置类"""
    
    max_data_length: int = DEFAULT_MAX_DATA_LENGTH      # 单次传输最大数据长度
    request_timeout: int = DEFAULT_REQUEST_TIMEOUT      # 请求超时时间(秒)
    retry_count: int = DEFAULT_RETRY_COUNT              # 重试次数
    show_progress: bool = True                          # 是否显示进度
    
    def __post_init__(self):
        """参数验证"""
        if self.max_data_length <= 0:
            raise ValueError("max_data_length必须大于0")
        if self.request_timeout <= 0:
            raise ValueError("request_timeout必须大于0")
        if self.retry_count < 0:
            raise ValueError("retry_count不能为负数") 