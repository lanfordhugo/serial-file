"""
核心模块
========

包含数据帧处理、串口管理和校验算法等核心功能。
"""

from .frame_handler import FrameHandler
from .checksum import calculate_checksum
from .serial_manager import SerialManager

__all__ = [
    "FrameHandler",
    "calculate_checksum", 
    "SerialManager"
] 