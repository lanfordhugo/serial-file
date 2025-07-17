"""
配置模块
=======

包含系统常量定义和配置管理功能。
"""

from .constants import *
from .settings import *

__all__ = [
    # 常量
    "SerialCommand",
    "DEFAULT_BAUDRATE",
    "DEFAULT_TIMEOUT",
    "MAX_FILE_NAME_LENGTH",
    "FRAME_HEADER_SIZE",
    "FRAME_CRC_SIZE",
    "FRAME_FORMAT_SIZE",
    # 配置
    "SerialConfig",
    "TransferConfig",
]
