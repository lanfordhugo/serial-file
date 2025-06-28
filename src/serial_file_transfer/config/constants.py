"""
系统常量定义
============

定义串口通信协议中使用的各种常量。
"""

from enum import IntEnum
import struct
from typing import Final


class SerialCommand(IntEnum):
    """串口通信命令字枚举"""
    
    # 文件大小相关命令
    REQUEST_FILE_SIZE: int = 0x61    # 请求文件大小 'a'
    REPLY_FILE_SIZE: int = 0x62      # 回复文件大小 'b'
    
    # 数据传输相关命令  
    REQUEST_DATA: int = 0x63         # 请求数据包 'c'
    SEND_DATA: int = 0x64           # 发送数据包 'd'
    
    # 文件名相关命令
    REQUEST_FILE_NAME: int = 0x51    # 请求文件名 'Q' 
    REPLY_FILE_NAME: int = 0x52      # 回复文件名 'R'


# 数据帧格式定义
FRAME_HEADER_FORMAT: Final[str] = "<BH"  # 命令字(1字节) + 数据长度(2字节)
FRAME_CRC_FORMAT: Final[str] = "<H"      # 校验和(2字节)

# 帧大小计算
FRAME_HEADER_SIZE: Final[int] = struct.calcsize(FRAME_HEADER_FORMAT)
FRAME_CRC_SIZE: Final[int] = struct.calcsize(FRAME_CRC_FORMAT) 
FRAME_FORMAT_SIZE: Final[int] = FRAME_HEADER_SIZE + FRAME_CRC_SIZE

# 其他常量
VAL_REQUEST_FILE: Final[int] = 0xAA      # 请求文件的标识值
MAX_FILE_NAME_LENGTH: Final[int] = 128   # 最大文件名长度

# 串口配置默认值
DEFAULT_BAUDRATE: Final[int] = 115200    # 默认波特率
DEFAULT_TIMEOUT: Final[float] = 0.1      # 默认超时时间(秒)
DEFAULT_MAX_DATA_LENGTH: Final[int] = 1024  # 默认单次传输最大数据长度

# 传输配置默认值
DEFAULT_REQUEST_TIMEOUT: Final[int] = 300  # 默认请求超时时间(秒)
DEFAULT_RETRY_COUNT: Final[int] = 3        # 默认重试次数 