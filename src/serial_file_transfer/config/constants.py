"""
系统常量定义
============

定义串口通信协议中使用的各种常量。
"""

from enum import IntEnum
import struct
from typing import Final, Dict


class SerialCommand(IntEnum):
    """串口通信命令字枚举"""

    # 文件大小相关命令
    REQUEST_FILE_SIZE = 0x61  # 请求文件大小 'a'
    REPLY_FILE_SIZE = 0x62  # 回复文件大小 'b'

    # 数据传输相关命令
    REQUEST_DATA = 0x63  # 请求数据包 'c'
    SEND_DATA = 0x64  # 发送数据包 'd'

    # 新增: 数据确认相关命令
    ACK = 0x65  # 数据包确认 'e'
    NACK = 0x66  # 数据包重传请求 'f'

    # 序号恢复机制命令 (中期改进)
    SYNC_REQUEST = 0x67  # 序号同步请求 'g'
    SYNC_REPLY = 0x68    # 序号同步回复 'h'

    # 协议状态同步命令 (跨设备稳定性改进)
    STATE_SYNC_REQUEST = 0x69   # 协议状态同步请求 'i'
    STATE_SYNC_REPLY = 0x6A     # 协议状态同步回复 'j'
    PROTOCOL_RESET = 0x6B       # 协议重置命令 'k'

    # 传输控制命令
    CANCEL_TRANSFER = 0x6C      # 取消当前传输

    # 文件名相关命令
    REQUEST_FILE_NAME = 0x51  # 请求文件名 'Q'
    REPLY_FILE_NAME = 0x52  # 回复文件名 'R'


# 数据帧格式定义
FRAME_HEADER_FORMAT: Final[str] = "<BH"  # 命令字(1字节) + 数据长度(2字节)
FRAME_CRC_FORMAT: Final[str] = "<H"  # 校验和(2字节)

# 帧大小计算
FRAME_HEADER_SIZE: Final[int] = struct.calcsize(FRAME_HEADER_FORMAT)
FRAME_CRC_SIZE: Final[int] = struct.calcsize(FRAME_CRC_FORMAT)
FRAME_FORMAT_SIZE: Final[int] = FRAME_HEADER_SIZE + FRAME_CRC_SIZE

# 其他常量
VAL_REQUEST_FILE: Final[int] = 0x55AA  # 请求文件的标识值 (2 字节特征值)
MAX_FILE_NAME_LENGTH: Final[int] = 512  # 最大文件路径长度（支持相对路径）

# 串口配置默认值
DEFAULT_BAUDRATE: Final[int] = 115200  # 默认波特率
DEFAULT_TIMEOUT: Final[float] = 0.1  # 默认超时时间(秒)
DEFAULT_MAX_DATA_LENGTH: Final[int] = 1024  # 默认单次传输最大数据长度

# 传输配置默认值
DEFAULT_REQUEST_TIMEOUT: Final[int] = 30  # 默认请求超时时间(秒) - 等待接收端启动时间
DEFAULT_CONNECTION_TIMEOUT: Final[int] = 30  # 连接建立超时时间(秒) - 等待接收端启动
DEFAULT_DATA_TIMEOUT: Final[int] = 5  # 数据传输超时时间(秒) - 传输过程中快速响应
DEFAULT_RETRY_COUNT: Final[int] = 3  # 默认重试次数

# 序号恢复机制配置 (中期改进)
DEFAULT_SEQUENCE_MISMATCH_THRESHOLD: Final[int] = 3  # 连续序号不匹配阈值，超过则触发同步
DEFAULT_SYNC_TIMEOUT: Final[int] = 2  # 序号同步超时时间(秒)

# CLI默认波特率
DEFAULT_CLI_BAUDRATE: Final[int] = 115200  # CLI默认波特率

# 批量传输状态机定义
class BatchTransferState(IntEnum):
    """批量传输状态枚举"""
    IDLE = 0          # 空闲状态
    REQUESTING_NAME = 1   # 请求文件名
    TRANSFERRING = 2      # 传输文件中
    COMPLETED = 3         # 传输完成
    FAILED = 4           # 传输失败
    TERMINATED = 5       # 传输终止

# 协议状态定义
class ProtocolState(IntEnum):
    """协议状态枚举 - 用于状态同步"""
    IDLE = 0                    # 空闲状态
    WAITING_FILENAME_REQUEST = 1    # 等待文件名请求
    WAITING_SIZE_REQUEST = 2        # 等待文件大小请求  
    WAITING_DATA_REQUEST = 3        # 等待数据请求
    SENDING_DATA = 4               # 发送数据中
    REQUESTING_FILENAME = 5        # 请求文件名
    REQUESTING_SIZE = 6            # 请求文件大小
    REQUESTING_DATA = 7            # 请求数据
    RECEIVING_DATA = 8             # 接收数据中
    ERROR_RECOVERY = 9             # 错误恢复中


# 块大小配置（固定配置，不再动态协商）
MIN_CHUNK_SIZE: Final[int] = 512  # 最小块大小
MAX_CHUNK_SIZE: Final[int] = 16384  # 最大块大小(16KB)

# 推荐块大小映射表（仅供参考，实际由配置文件指定）
BAUDRATE_CHUNK_SIZE_MAP: Final[Dict[int, int]] = {
    # 波特率 -> 推荐块大小映射
    9600: 512,
    19200: 512,
    38400: 512,
    57600: 512,
    115200: 1024,
    230400: 1024,
    460800: 1024,
    921600: 2048,
    1000000: 4096,
    1500000: 4096,
    1728000: 8192,  # 注意：调整为8192，原16384可能过大
}


def get_recommended_chunk_size(baudrate: int) -> int:
    """
    根据波特率获取推荐的块大小（仅供参考）
    
    注意：这只是推荐值，实际块大小由配置文件固定指定
    
    Args:
        baudrate: 波特率
    
    Returns:
        推荐的块大小（字节）
    """
    # 精确匹配
    if baudrate in BAUDRATE_CHUNK_SIZE_MAP:
        return BAUDRATE_CHUNK_SIZE_MAP[baudrate]
    
    # 找到最接近的波特率
    closest_baudrate = min(
        BAUDRATE_CHUNK_SIZE_MAP.keys(), key=lambda x: abs(x - baudrate)
    )
    
    return BAUDRATE_CHUNK_SIZE_MAP[closest_baudrate]
