"""
数据帧处理模块
==============

负责串口通信中数据帧的封装和解析。
"""

import struct
import serial
from typing import Optional, Tuple, Union

from ..config.constants import (
    SerialCommand,
    FRAME_HEADER_FORMAT,
    FRAME_CRC_FORMAT, 
    FRAME_HEADER_SIZE,
    FRAME_CRC_SIZE,
    FRAME_FORMAT_SIZE
)
from .checksum import calculate_checksum
from ..utils.logger import get_logger

logger = get_logger(__name__)


class FrameHandler:
    """数据帧处理器"""
    
    @staticmethod
    def pack_frame(cmd: Union[SerialCommand, int], data: bytes) -> Optional[bytes]:
        """
        将命令和数据打包成数据帧
        
        数据帧格式：| 命令字(1B) | 数据长度(2B) | 数据内容(NB) | 校验和(2B) |
        
        Args:
            cmd: 命令字，可以是SerialCommand枚举或整数
            data: 要发送的数据，bytes类型
            
        Returns:
            打包后的数据帧，失败时返回None
            
        Examples:
            >>> handler = FrameHandler()
            >>> frame = handler.pack_frame(SerialCommand.REQUEST_FILE_SIZE, b'test')
            >>> isinstance(frame, bytes)
            True
        """
        if data is None:
            logger.error("数据为空，无法计算校验和")
            return None
            
        try:
            # 计算校验和
            crc = calculate_checksum(data)
            
            # 获取数据长度
            data_len = len(data)
            
            # 打包数据帧：头部 + 数据 + 校验和
            packed_frame = (
                struct.pack(FRAME_HEADER_FORMAT, int(cmd), data_len) + 
                data + 
                struct.pack(FRAME_CRC_FORMAT, crc)
            )
            
            return packed_frame
            
        except Exception as e:
            logger.error(f"打包数据帧失败: {e}")
            return None
    
    @staticmethod 
    def unpack_frame(frame_data: bytes) -> Optional[Tuple[int, int, bytes, int]]:
        """
        解析数据帧
        
        Args:
            frame_data: 接收到的数据帧
            
        Returns:
            元组(命令字, 数据长度, 数据内容, 校验和)，失败时返回None
            
        Examples:
            >>> handler = FrameHandler()
            >>> result = handler.unpack_frame(packed_frame)
            >>> result is not None
            True
        """
        try:
            # 检查数据帧最小长度
            if len(frame_data) < FRAME_FORMAT_SIZE:
                logger.debug(f'数据长度不足一帧: {len(frame_data)}')
                return None
            
            # 解析头部：命令字和数据长度
            header = frame_data[:FRAME_HEADER_SIZE]
            cmd, data_len = struct.unpack(FRAME_HEADER_FORMAT, header)
            
            # 检查数据长度是否匹配
            actual_data_len = len(frame_data) - FRAME_HEADER_SIZE - FRAME_CRC_SIZE
            if data_len != actual_data_len:
                logger.error(
                    f'数据长度不匹配: 声明长度={data_len}, 实际长度={actual_data_len}'
                )
                return None
            
            # 提取数据部分
            data_start = FRAME_HEADER_SIZE
            data_end = data_start + data_len
            data = frame_data[data_start:data_end]
            
            # 解析校验和
            crc_start = data_end
            crc_end = crc_start + FRAME_CRC_SIZE
            received_crc = struct.unpack(FRAME_CRC_FORMAT, frame_data[crc_start:crc_end])[0]
            
            # 验证校验和
            calculated_crc = calculate_checksum(data)
            if received_crc != calculated_crc:
                logger.error(
                    f'校验和错误: 接收={hex(received_crc)}, 计算={hex(calculated_crc)}'
                )
                return None
            
            return cmd, data_len, data, received_crc
            
        except Exception as e:
            logger.error(f"解析数据帧失败: {e}")
            return None
    
    @staticmethod
    def read_frame(port: serial.Serial, size: int) -> Tuple[Optional[int], Optional[bytes]]:
        """
        从串口读取指定长度的数据帧并解析
        
        Args:
            port: 串口对象
            size: 要读取的字节数
            
        Returns:
            元组(命令字, 数据内容)，失败时返回(None, None)
        """
        try:
            # 从串口读取数据
            read_data = port.read(size)
            if len(read_data) == 0:
                return None, None
            
            # 解析数据帧
            unpacked = FrameHandler.unpack_frame(read_data)
            if unpacked is None:
                return None, None
            
            cmd, _, data, _ = unpacked
            return cmd, data
            
        except Exception as e:
            logger.error(f"读取数据帧失败: {e}")
            return None, None


# 为了保持向后兼容，提供原函数名的别名
def make_pack(cmd: Union[SerialCommand, int], data: bytes) -> Optional[bytes]:
    """向后兼容的函数别名"""
    return FrameHandler.pack_frame(cmd, data)


def unpack_data(packed_data: bytes) -> Optional[Tuple[int, int, bytes, int]]:
    """向后兼容的函数别名"""
    return FrameHandler.unpack_frame(packed_data)


def read_frame(port: serial.Serial, size: int) -> Tuple[Optional[int], Optional[bytes]]:
    """向后兼容的函数别名"""
    return FrameHandler.read_frame(port, size) 