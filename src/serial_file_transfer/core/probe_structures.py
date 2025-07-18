"""
探测协议数据结构定义
==================

定义智能探测协商协议中使用的各种数据结构。
"""

import struct
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple
from ..config.constants import PROBE_PROTOCOL_VERSION


@dataclass
class ProbeRequestData:
    """探测请求数据结构"""

    device_id: int  # 4字节设备ID
    protocol_version: int  # 1字节协议版本
    random_seed: int  # 4字节随机数(防冲突)

    def pack(self) -> bytes:
        """打包成字节数据"""
        return struct.pack(
            "<IBI", self.device_id, self.protocol_version, self.random_seed
        )

    @classmethod
    def unpack(cls, data: bytes) -> Optional["ProbeRequestData"]:
        """从字节数据解包"""
        try:
            if len(data) != 9:  # 4+1+4 = 9字节
                return None
            device_id, protocol_version, random_seed = struct.unpack("<IBI", data)
            return cls(device_id, protocol_version, random_seed)
        except struct.error:
            return None

    @classmethod
    def create(cls, device_id: Optional[int] = None) -> "ProbeRequestData":
        """创建新的探测请求"""
        if device_id is None:
            device_id = random.randint(0x10000000, 0xFFFFFFFF)
        random_seed = random.randint(0, 0xFFFFFFFF)
        return cls(device_id, PROBE_PROTOCOL_VERSION, random_seed)


@dataclass
class ProbeResponseData:
    """探测响应数据结构"""

    device_id: int  # 4字节设备ID
    protocol_version: int  # 1字节协议版本
    random_seed: int  # 4字节随机数
    supported_baudrates: List[int]  # 支持的波特率列表

    def pack(self) -> bytes:
        """打包成字节数据"""
        # 头部：设备ID + 协议版本 + 随机数
        header = struct.pack(
            "<IBI", self.device_id, self.protocol_version, self.random_seed
        )

        # 波特率列表：数量 + 波特率值列表
        baudrates_count = len(self.supported_baudrates)
        baudrates_data = struct.pack("<H", baudrates_count)  # 2字节数量
        for baudrate in self.supported_baudrates:
            baudrates_data += struct.pack("<I", baudrate)  # 4字节波特率

        return header + baudrates_data

    @classmethod
    def unpack(cls, data: bytes) -> Optional["ProbeResponseData"]:
        """从字节数据解包"""
        try:
            if len(data) < 11:  # 最小长度：4+1+4+2 = 11字节
                return None

            # 解包头部
            device_id, protocol_version, random_seed = struct.unpack("<IBI", data[:9])

            # 解包波特率列表
            baudrates_count = struct.unpack("<H", data[9:11])[0]
            baudrates = []

            offset = 11
            for i in range(baudrates_count):
                if offset + 4 > len(data):
                    return None
                baudrate = struct.unpack("<I", data[offset : offset + 4])[0]
                baudrates.append(baudrate)
                offset += 4

            return cls(device_id, protocol_version, random_seed, baudrates)
        except struct.error:
            return None

    @classmethod
    def create_response(
        cls, request: ProbeRequestData, supported_baudrates: List[int]
    ) -> "ProbeResponseData":
        """基于探测请求创建响应"""
        return cls(
            device_id=request.device_id,
            protocol_version=request.protocol_version,
            random_seed=request.random_seed,
            supported_baudrates=supported_baudrates,
        )


@dataclass
class CapabilityNegoData:
    """能力协商数据结构"""

    session_id: int  # 4字节会话ID
    transfer_mode: int  # 1字节传输模式(1=单文件,2=批量)
    file_count: int  # 4字节文件数量
    total_size: int  # 8字节总大小
    selected_baudrate: int  # 4字节选择的波特率
    chunk_size: int  # 4字节推荐块大小 - P1-A新增
    root_path: str  # 变长字符串，发送端根路径信息（用于自动路径创建）

    def pack(self) -> bytes:
        """打包成字节数据"""
        # 编码根路径字符串
        root_path_bytes = self.root_path.encode("utf-8")
        root_path_length = len(root_path_bytes)

        # 固定部分：4+1+4+8+4+4+2 = 27字节（新增2字节路径长度）
        fixed_part = struct.pack(
            "<IBIQIIH",
            self.session_id,
            self.transfer_mode,
            self.file_count,
            self.total_size,
            self.selected_baudrate,
            self.chunk_size,
            root_path_length,
        )

        return fixed_part + root_path_bytes

    @classmethod
    def unpack(cls, data: bytes) -> Optional["CapabilityNegoData"]:
        """从字节数据解包"""
        try:
            if len(data) < 27:  # 至少需要固定部分的字节数
                return None

            # 解包固定部分
            fixed_values = struct.unpack("<IBIQIIH", data[:27])
            session_id, transfer_mode, file_count, total_size, selected_baudrate, chunk_size, root_path_length = fixed_values

            # 检查数据长度是否匹配
            if len(data) != 27 + root_path_length:
                return None

            # 解码根路径字符串
            root_path_bytes = data[27:27 + root_path_length]
            root_path = root_path_bytes.decode("utf-8")

            return cls(session_id, transfer_mode, file_count, total_size, selected_baudrate, chunk_size, root_path)
        except (struct.error, UnicodeDecodeError):
            return None


@dataclass
class CapabilityAckData:
    """能力确认数据结构"""

    session_id: int  # 4字节会话ID
    accept_status: int  # 1字节接受状态(0=拒绝,1=接受)
    negotiated_chunk_size: int  # 4字节最终协商的块大小 - P1-A新增

    def pack(self) -> bytes:
        """打包成字节数据"""
        return struct.pack(
            "<IBI", self.session_id, self.accept_status, self.negotiated_chunk_size
        )

    @classmethod
    def unpack(cls, data: bytes) -> Optional["CapabilityAckData"]:
        """从字节数据解包"""
        try:
            if len(data) != 9:  # 4+1+4 = 9字节
                return None
            session_id, accept_status, negotiated_chunk_size = struct.unpack(
                "<IBI", data
            )
            return cls(session_id, accept_status, negotiated_chunk_size)
        except struct.error:
            return None


@dataclass
class SwitchBaudrateData:
    """波特率切换数据结构"""

    session_id: int  # 4字节会话ID
    new_baudrate: int  # 4字节新波特率
    switch_delay_ms: int  # 2字节切换延时(毫秒)

    def pack(self) -> bytes:
        """打包成字节数据"""
        return struct.pack(
            "<IIH", self.session_id, self.new_baudrate, self.switch_delay_ms
        )

    @classmethod
    def unpack(cls, data: bytes) -> Optional["SwitchBaudrateData"]:
        """从字节数据解包"""
        try:
            if len(data) != 10:  # 4+4+2 = 10字节
                return None
            values = struct.unpack("<IIH", data)
            return cls(*values)
        except struct.error:
            return None


@dataclass
class SwitchAckData:
    """切换确认数据结构"""

    session_id: int  # 4字节会话ID

    def pack(self) -> bytes:
        """打包成字节数据"""
        return struct.pack("<I", self.session_id)

    @classmethod
    def unpack(cls, data: bytes) -> Optional["SwitchAckData"]:
        """从字节数据解包"""
        try:
            if len(data) != 4:  # 4字节
                return None
            session_id = struct.unpack("<I", data)[0]
            return cls(session_id)
        except struct.error:
            return None
