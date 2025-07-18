"""
探测协议数据结构测试
==================

测试智能探测协商协议中各种数据结构的序列化和反序列化功能。
"""

import pytest
from src.serial_file_transfer.core.probe_structures import (
    ProbeRequestData,
    ProbeResponseData,
    CapabilityNegoData,
    CapabilityAckData,
    SwitchBaudrateData,
    SwitchAckData,
)
from src.serial_file_transfer.config.constants import PROBE_PROTOCOL_VERSION


class TestProbeRequestData:
    """测试探测请求数据结构"""

    def test_create_default(self):
        """测试创建默认探测请求"""
        request = ProbeRequestData.create()

        assert request.protocol_version == PROBE_PROTOCOL_VERSION
        assert 0x10000000 <= request.device_id <= 0xFFFFFFFF
        assert 0 <= request.random_seed <= 0xFFFFFFFF

    def test_create_with_device_id(self):
        """测试创建指定设备ID的探测请求"""
        device_id = 0x12345678
        request = ProbeRequestData.create(device_id)

        assert request.device_id == device_id
        assert request.protocol_version == PROBE_PROTOCOL_VERSION

    def test_pack_unpack(self):
        """测试打包和解包功能"""
        original = ProbeRequestData(
            device_id=0x12345678, protocol_version=1, random_seed=0x87654321
        )

        # 打包
        packed = original.pack()
        assert len(packed) == 9  # 4+1+4 = 9字节

        # 解包
        unpacked = ProbeRequestData.unpack(packed)
        assert unpacked is not None
        assert unpacked.device_id == original.device_id
        assert unpacked.protocol_version == original.protocol_version
        assert unpacked.random_seed == original.random_seed

    def test_unpack_invalid_data(self):
        """测试解包无效数据"""
        # 数据长度不足
        result = ProbeRequestData.unpack(b"\x01\x02\x03")
        assert result is None

        # 空数据
        result = ProbeRequestData.unpack(b"")
        assert result is None


class TestProbeResponseData:
    """测试探测响应数据结构"""

    def test_create_response(self):
        """测试基于请求创建响应"""
        request = ProbeRequestData.create()
        baudrates = [115200, 921600, 1728000]

        response = ProbeResponseData.create_response(request, baudrates)

        assert response.device_id == request.device_id
        assert response.protocol_version == request.protocol_version
        assert response.random_seed == request.random_seed
        assert response.supported_baudrates == baudrates

    def test_pack_unpack(self):
        """测试打包和解包功能"""
        original = ProbeResponseData(
            device_id=0x12345678,
            protocol_version=1,
            random_seed=0x87654321,
            supported_baudrates=[115200, 921600],
        )

        # 打包
        packed = original.pack()
        expected_len = 9 + 2 + 2 * 4  # 头部9字节 + 数量2字节 + 2个波特率8字节
        assert len(packed) == expected_len

        # 解包
        unpacked = ProbeResponseData.unpack(packed)
        assert unpacked is not None
        assert unpacked.device_id == original.device_id
        assert unpacked.protocol_version == original.protocol_version
        assert unpacked.random_seed == original.random_seed
        assert unpacked.supported_baudrates == original.supported_baudrates

    def test_pack_unpack_empty_baudrates(self):
        """测试空波特率列表的打包解包"""
        original = ProbeResponseData(
            device_id=0x12345678,
            protocol_version=1,
            random_seed=0x87654321,
            supported_baudrates=[],
        )

        packed = original.pack()
        unpacked = ProbeResponseData.unpack(packed)

        assert unpacked is not None
        assert unpacked.supported_baudrates == []

    def test_unpack_invalid_data(self):
        """测试解包无效数据"""
        # 数据长度不足
        result = ProbeResponseData.unpack(b"\x01\x02\x03")
        assert result is None


class TestCapabilityNegoData:
    """测试能力协商数据结构"""

    def test_pack_unpack(self):
        """测试打包和解包功能"""
        original = CapabilityNegoData(
            session_id=0x12345678,
            transfer_mode=1,
            file_count=5,
            total_size=1024 * 1024,
            selected_baudrate=921600,
            chunk_size=1024,  # P1-A新增必需参数
            root_path="test_folder",  # 新增根路径字段
        )

        # 打包
        packed = original.pack()
        # 新的长度：4+1+4+8+4+4+2+len("test_folder") = 27+11 = 38字节
        assert len(packed) == 38

        # 解包
        unpacked = CapabilityNegoData.unpack(packed)
        assert unpacked is not None
        assert unpacked.session_id == original.session_id
        assert unpacked.transfer_mode == original.transfer_mode
        assert unpacked.file_count == original.file_count
        assert unpacked.total_size == original.total_size
        assert unpacked.selected_baudrate == original.selected_baudrate
        assert unpacked.chunk_size == original.chunk_size  # P1-A验证新字段
        assert unpacked.root_path == original.root_path  # 验证根路径字段

    def test_unpack_invalid_data(self):
        """测试解包无效数据"""
        result = CapabilityNegoData.unpack(b"\x01\x02\x03")
        assert result is None

    def test_pack_unpack_empty_root_path(self):
        """测试空根路径的打包和解包"""
        original = CapabilityNegoData(
            session_id=0x12345678,
            transfer_mode=1,
            file_count=1,
            total_size=1024,
            selected_baudrate=115200,
            chunk_size=512,
            root_path="",  # 空根路径
        )

        # 打包
        packed = original.pack()
        # 长度：4+1+4+8+4+4+2+0 = 27字节
        assert len(packed) == 27

        # 解包
        unpacked = CapabilityNegoData.unpack(packed)
        assert unpacked is not None
        assert unpacked.root_path == ""


class TestCapabilityAckData:
    """测试能力确认数据结构"""

    def test_pack_unpack(self):
        """测试打包和解包功能"""
        original = CapabilityAckData(
            session_id=0x12345678,
            accept_status=1,
            negotiated_chunk_size=1024,  # P1-A新增必需参数
        )

        # 打包
        packed = original.pack()
        assert len(packed) == 9  # P1-A更新后: 4+1+4 = 9字节

        # 解包
        unpacked = CapabilityAckData.unpack(packed)
        assert unpacked is not None
        assert unpacked.session_id == original.session_id
        assert unpacked.accept_status == original.accept_status
        assert (
            unpacked.negotiated_chunk_size == original.negotiated_chunk_size
        )  # P1-A验证新字段


class TestSwitchBaudrateData:
    """测试波特率切换数据结构"""

    def test_pack_unpack(self):
        """测试打包和解包功能"""
        original = SwitchBaudrateData(
            session_id=0x12345678, new_baudrate=921600, switch_delay_ms=100
        )

        # 打包
        packed = original.pack()
        assert len(packed) == 10  # 4+4+2 = 10字节

        # 解包
        unpacked = SwitchBaudrateData.unpack(packed)
        assert unpacked is not None
        assert unpacked.session_id == original.session_id
        assert unpacked.new_baudrate == original.new_baudrate
        assert unpacked.switch_delay_ms == original.switch_delay_ms


class TestSwitchAckData:
    """测试切换确认数据结构"""

    def test_pack_unpack(self):
        """测试打包和解包功能"""
        original = SwitchAckData(session_id=0x12345678)

        # 打包
        packed = original.pack()
        assert len(packed) == 4  # 4字节

        # 解包
        unpacked = SwitchAckData.unpack(packed)
        assert unpacked is not None
        assert unpacked.session_id == original.session_id


class TestP1AChunkSizeNegotiation:
    """测试P1-A动态块大小协商功能"""

    def test_capability_nego_with_chunk_size(self):
        """测试能力协商数据包含块大小字段"""
        # 创建包含块大小的能力协商数据
        nego_data = CapabilityNegoData(
            session_id=12345,
            transfer_mode=1,
            file_count=1,
            total_size=1024 * 1024,
            selected_baudrate=460800,
            chunk_size=1024,  # P1-A新增字段
            root_path="test_root",  # 新增根路径字段
        )

        # 测试打包
        packed = nego_data.pack()
        # 新的数据长度: 4+1+4+8+4+4+2+len("test_root") = 27+9 = 36
        assert len(packed) == 36

        # 测试解包
        unpacked = CapabilityNegoData.unpack(packed)
        assert unpacked is not None
        assert unpacked.session_id == 12345
        assert unpacked.chunk_size == 1024
        assert unpacked.selected_baudrate == 460800
        assert unpacked.root_path == "test_root"

    def test_capability_ack_with_negotiated_chunk_size(self):
        """测试能力确认数据包含协商的块大小字段"""
        # 创建包含协商块大小的确认数据
        ack_data = CapabilityAckData(
            session_id=12345, accept_status=1, negotiated_chunk_size=1024  # P1-A新增字段
        )

        # 测试打包
        packed = ack_data.pack()
        assert len(packed) == 9  # 新的数据长度: 4+1+4 = 9

        # 测试解包
        unpacked = CapabilityAckData.unpack(packed)
        assert unpacked is not None
        assert unpacked.session_id == 12345
        assert unpacked.accept_status == 1
        assert unpacked.negotiated_chunk_size == 1024

    def test_capability_nego_pack_unpack_round_trip(self):
        """测试能力协商数据的完整往返序列化"""
        original = CapabilityNegoData(
            session_id=999999,
            transfer_mode=2,
            file_count=5,
            total_size=2**32 + 1000,  # 大文件
            selected_baudrate=1728000,
            chunk_size=8192,
            root_path="large_folder",  # 新增根路径字段
        )

        # 打包再解包
        packed = original.pack()
        unpacked = CapabilityNegoData.unpack(packed)

        assert unpacked is not None
        assert unpacked.session_id == original.session_id
        assert unpacked.transfer_mode == original.transfer_mode
        assert unpacked.file_count == original.file_count
        assert unpacked.total_size == original.total_size
        assert unpacked.selected_baudrate == original.selected_baudrate
        assert unpacked.chunk_size == original.chunk_size
        assert unpacked.root_path == original.root_path

    def test_capability_ack_pack_unpack_round_trip(self):
        """测试能力确认数据的完整往返序列化"""
        original = CapabilityAckData(
            session_id=888888, accept_status=0, negotiated_chunk_size=512  # 拒绝
        )

        # 打包再解包
        packed = original.pack()
        unpacked = CapabilityAckData.unpack(packed)

        assert unpacked is not None
        assert unpacked.session_id == original.session_id
        assert unpacked.accept_status == original.accept_status
        assert unpacked.negotiated_chunk_size == original.negotiated_chunk_size

    def test_capability_nego_invalid_data_length(self):
        """测试能力协商数据长度验证"""
        # 测试旧格式数据（21字节）应该解包失败
        old_data = b"\x00" * 21
        result = CapabilityNegoData.unpack(old_data)
        assert result is None

        # 测试错误长度数据
        wrong_data = b"\x00" * 20
        result = CapabilityNegoData.unpack(wrong_data)
        assert result is None

        # 测试过长数据
        long_data = b"\x00" * 30
        result = CapabilityNegoData.unpack(long_data)
        assert result is None

    def test_capability_ack_invalid_data_length(self):
        """测试能力确认数据长度验证"""
        # 测试旧格式数据（5字节）应该解包失败
        old_data = b"\x00" * 5
        result = CapabilityAckData.unpack(old_data)
        assert result is None

        # 测试错误长度数据
        wrong_data = b"\x00" * 8
        result = CapabilityAckData.unpack(wrong_data)
        assert result is None
