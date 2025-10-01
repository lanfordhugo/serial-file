"""
帧载荷处理模块
==============

提供不同命令类型的载荷打包和解包函数。
"""

import struct
from typing import Tuple, Optional
from ..config.constants import SerialCommand


class FramePayload:
    """帧载荷处理工具类"""
    
    # ==================== SEND_DATA 相关 ====================
    
    @staticmethod
    def pack_send_data(seq_id: int, offset: int, payload: bytes) -> bytes:
        """
        打包SEND_DATA帧载荷（vNext新格式）
        
        格式: seq(2) + offset(4) + payload(N)
        
        Args:
            seq_id: 序号（0-65535）
            offset: 文件偏移量
            payload: 文件数据
        
        Returns:
            打包后的载荷数据
        
        Examples:
            >>> data = FramePayload.pack_send_data(123, 4096, b'test')
            >>> len(data)
            10
        """
        return struct.pack("<HI", seq_id, offset) + payload
    
    @staticmethod
    def unpack_send_data(data: bytes) -> Optional[Tuple[int, int, bytes]]:
        """
        解包SEND_DATA帧载荷（vNext新格式）
        
        Args:
            data: 载荷数据
        
        Returns:
            元组(seq_id, offset, payload)，失败返回None
        
        Examples:
            >>> data = struct.pack("<HI", 123, 4096) + b'test'
            >>> seq, offset, payload = FramePayload.unpack_send_data(data)
            >>> seq, offset, payload
            (123, 4096, b'test')
        """
        if len(data) < 6:  # 至少需要2字节seq + 4字节offset
            return None
        
        try:
            seq_id = struct.unpack("<H", data[:2])[0]
            offset = struct.unpack("<I", data[2:6])[0]
            payload = data[6:]
            return seq_id, offset, payload
        except struct.error:
            return None
    
    # ==================== ACK/NACK 相关 ====================
    
    @staticmethod
    def pack_ack(seq_id: int, offset: int) -> bytes:
        """
        打包ACK帧载荷（vNext新格式）
        
        格式: seq(2) + offset(4)
        
        Args:
            seq_id: 确认的序号
            offset: 确认的偏移量
        
        Returns:
            打包后的载荷数据（6字节）
        """
        return struct.pack("<HI", seq_id, offset)
    
    @staticmethod
    def unpack_ack(data: bytes) -> Optional[Tuple[int, int]]:
        """
        解包ACK帧载荷（vNext新格式）
        
        Args:
            data: 载荷数据
        
        Returns:
            元组(seq_id, offset)，失败返回None
        """
        if len(data) < 6:
            return None
        
        try:
            seq_id = struct.unpack("<H", data[:2])[0]
            offset = struct.unpack("<I", data[2:6])[0]
            return seq_id, offset
        except struct.error:
            return None
    
    @staticmethod
    def pack_nack(seq_id: int, offset: int) -> bytes:
        """
        打包NACK帧载荷（vNext新格式）
        
        格式: seq(2) + offset(4)
        
        Args:
            seq_id: 请求重传的序号
            offset: 请求重传的偏移量
        
        Returns:
            打包后的载荷数据（6字节）
        """
        return struct.pack("<HI", seq_id, offset)
    
    @staticmethod
    def unpack_nack(data: bytes) -> Optional[Tuple[int, int]]:
        """
        解包NACK帧载荷（vNext新格式）
        
        Args:
            data: 载荷数据
        
        Returns:
            元组(seq_id, offset)，失败返回None
        """
        # NACK与ACK格式相同
        return FramePayload.unpack_ack(data)
    
    # ==================== SYNC 相关 ====================
    
    @staticmethod
    def pack_sync_request(seq_id: int, offset: int) -> bytes:
        """
        打包SYNC_REQUEST帧载荷（vNext新格式）
        
        格式: seq(2) + offset(4)
        
        Args:
            seq_id: 当前序号
            offset: 当前偏移量
        
        Returns:
            打包后的载荷数据（6字节）
        """
        return struct.pack("<HI", seq_id, offset)
    
    @staticmethod
    def unpack_sync_request(data: bytes) -> Optional[Tuple[int, int]]:
        """
        解包SYNC_REQUEST帧载荷
        
        Args:
            data: 载荷数据
        
        Returns:
            元组(seq_id, offset)，失败返回None
        """
        if len(data) < 6:
            return None
        
        try:
            seq_id = struct.unpack("<H", data[:2])[0]
            offset = struct.unpack("<I", data[2:6])[0]
            return seq_id, offset
        except struct.error:
            return None
    
    @staticmethod
    def pack_sync_reply(seq_id: int, offset: int, ack_seq: int) -> bytes:
        """
        打包SYNC_REPLY帧载荷（vNext新格式）
        
        格式: seq(2) + offset(4) + ack_seq(2)
        
        Args:
            seq_id: 回复的序号
            offset: 回复的偏移量
            ack_seq: 确认序号
        
        Returns:
            打包后的载荷数据（8字节）
        """
        return struct.pack("<HIH", seq_id, offset, ack_seq)
    
    @staticmethod
    def unpack_sync_reply(data: bytes) -> Optional[Tuple[int, int, int]]:
        """
        解包SYNC_REPLY帧载荷
        
        Args:
            data: 载荷数据
        
        Returns:
            元组(seq_id, offset, ack_seq)，失败返回None
        """
        if len(data) < 8:
            return None
        
        try:
            seq_id = struct.unpack("<H", data[:2])[0]
            offset = struct.unpack("<I", data[2:6])[0]
            ack_seq = struct.unpack("<H", data[6:8])[0]
            return seq_id, offset, ack_seq
        except struct.error:
            return None
    
    # ==================== 其他命令（格式不变） ====================
    
    @staticmethod
    def pack_request_file() -> bytes:
        """打包文件请求（REQUEST_FILE_NAME/REQUEST_FILE_SIZE）"""
        from ..config.constants import VAL_REQUEST_FILE
        return struct.pack("<H", VAL_REQUEST_FILE)
    
    @staticmethod
    def pack_file_size(file_size: int) -> bytes:
        """打包文件大小（REPLY_FILE_SIZE）"""
        return struct.pack("<I", file_size)
    
    @staticmethod
    def unpack_file_size(data: bytes) -> Optional[int]:
        """解包文件大小"""
        if len(data) < 4:
            return None
        try:
            return struct.unpack("<I", data)[0]
        except struct.error:
            return None
    
    @staticmethod
    def pack_filename(filename: str, max_length: int = 512) -> bytes:
        """
        打包文件名（REPLY_FILE_NAME）
        
        格式: length(2) + utf8_name(N)
        
        Args:
            filename: 文件名或相对路径
            max_length: 最大文件名长度
        
        Returns:
            打包后的载荷数据
        """
        encoded_name = filename.encode("utf-8")
        
        # 截断过长的文件名
        if len(encoded_name) > max_length:
            encoded_name = encoded_name[:max_length]
        
        # 变长编码：2字节长度 + 实际数据
        length_bytes = struct.pack("<H", len(encoded_name))
        return length_bytes + encoded_name
    
    @staticmethod
    def unpack_filename(data: bytes) -> Optional[str]:
        """
        解包文件名
        
        Args:
            data: 载荷数据
        
        Returns:
            文件名，失败返回None
        """
        if len(data) < 2:
            return None
        
        try:
            name_len = struct.unpack("<H", data[:2])[0]
            if len(data) < 2 + name_len:
                return None
            
            filename_bytes = data[2:2 + name_len]
            return filename_bytes.decode("utf-8")
        except (struct.error, UnicodeDecodeError):
            return None
    
    @staticmethod
    def pack_data_request(addr: int, length: int) -> bytes:
        """
        打包数据请求（REQUEST_DATA）
        
        格式: addr(4) + length(2)
        
        Args:
            addr: 请求的起始地址
            length: 请求的数据长度
        
        Returns:
            打包后的载荷数据（6字节）
        """
        return struct.pack("<IH", addr, length)
    
    @staticmethod
    def unpack_data_request(data: bytes) -> Optional[Tuple[int, int]]:
        """
        解包数据请求
        
        Args:
            data: 载荷数据
        
        Returns:
            元组(addr, length)，失败返回None
        """
        if len(data) < 6:
            return None
        
        try:
            addr = struct.unpack("<I", data[:4])[0]
            length = struct.unpack("<H", data[4:6])[0]
            return addr, length
        except struct.error:
            return None

