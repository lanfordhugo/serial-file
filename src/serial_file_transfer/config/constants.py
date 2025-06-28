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
    REQUEST_FILE_SIZE = 0x61    # 请求文件大小 'a'
    REPLY_FILE_SIZE = 0x62      # 回复文件大小 'b'
    
    # 数据传输相关命令  
    REQUEST_DATA = 0x63         # 请求数据包 'c'
    SEND_DATA = 0x64           # 发送数据包 'd'
    
    # 新增: 数据确认相关命令
    ACK = 0x65                # 数据包确认 'e'
    NACK = 0x66               # 数据包重传请求 'f'
    
    # 文件名相关命令
    REQUEST_FILE_NAME = 0x51    # 请求文件名 'Q' 
    REPLY_FILE_NAME = 0x52      # 回复文件名 'R'


class ProbeCommand(IntEnum):
    """智能探测协议命令字枚举"""
    
    # 设备发现阶段
    PROBE_REQUEST = 0x41        # 探测请求
    PROBE_RESPONSE = 0x42       # 探测响应
    
    # 能力协商阶段  
    CAPABILITY_NEGO = 0x43      # 能力协商
    CAPABILITY_ACK = 0x44       # 能力确认
    
    # 连接建立阶段
    SWITCH_BAUDRATE = 0x45      # 切换波特率
    SWITCH_ACK = 0x46           # 切换确认
    CONNECTION_READY = 0x47     # 连接就绪


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

# 智能探测协议配置
PROBE_BAUDRATE: Final[int] = 115200        # 探测阶段固定波特率
PROBE_TIMEOUT: Final[float] = 3.0          # 探测超时时间(秒)
PROBE_RETRY_COUNT: Final[int] = 3          # 探测重试次数
CAPABILITY_TIMEOUT: Final[float] = 5.0     # 能力协商超时时间(秒)
SWITCH_TIMEOUT: Final[float] = 2.0         # 波特率切换超时时间(秒)
SWITCH_DELAY_MS: Final[int] = 100          # 波特率切换延时(毫秒)

# 探测协议版本
PROBE_PROTOCOL_VERSION: Final[int] = 1     # 当前探测协议版本 