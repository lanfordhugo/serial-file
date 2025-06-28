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
    SwitchAckData
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
            device_id=0x12345678,
            protocol_version=1,
            random_seed=0x87654321
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
        result = ProbeRequestData.unpack(b'\x01\x02\x03')
        assert result is None
        
        # 空数据
        result = ProbeRequestData.unpack(b'')
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
            supported_baudrates=[115200, 921600]
        )
        
        # 打包
        packed = original.pack()
        expected_len = 9 + 2 + 2*4  # 头部9字节 + 数量2字节 + 2个波特率8字节
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
            supported_baudrates=[]
        )
        
        packed = original.pack()
        unpacked = ProbeResponseData.unpack(packed)
        
        assert unpacked is not None
        assert unpacked.supported_baudrates == []
    
    def test_unpack_invalid_data(self):
        """测试解包无效数据"""
        # 数据长度不足
        result = ProbeResponseData.unpack(b'\x01\x02\x03')
        assert result is None


class TestCapabilityNegoData:
    """测试能力协商数据结构"""
    
    def test_pack_unpack(self):
        """测试打包和解包功能"""
        original = CapabilityNegoData(
            session_id=0x12345678,
            transfer_mode=1,
            file_count=5,
            total_size=1024*1024,
            selected_baudrate=921600
        )
        
        # 打包
        packed = original.pack()
        assert len(packed) == 21  # 4+1+4+8+4 = 21字节
        
        # 解包
        unpacked = CapabilityNegoData.unpack(packed)
        assert unpacked is not None
        assert unpacked.session_id == original.session_id
        assert unpacked.transfer_mode == original.transfer_mode
        assert unpacked.file_count == original.file_count
        assert unpacked.total_size == original.total_size
        assert unpacked.selected_baudrate == original.selected_baudrate
    
    def test_unpack_invalid_data(self):
        """测试解包无效数据"""
        result = CapabilityNegoData.unpack(b'\x01\x02\x03')
        assert result is None


class TestCapabilityAckData:
    """测试能力确认数据结构"""
    
    def test_pack_unpack(self):
        """测试打包和解包功能"""
        original = CapabilityAckData(
            session_id=0x12345678,
            accept_status=1
        )
        
        # 打包
        packed = original.pack()
        assert len(packed) == 5  # 4+1 = 5字节
        
        # 解包
        unpacked = CapabilityAckData.unpack(packed)
        assert unpacked is not None
        assert unpacked.session_id == original.session_id
        assert unpacked.accept_status == original.accept_status


class TestSwitchBaudrateData:
    """测试波特率切换数据结构"""
    
    def test_pack_unpack(self):
        """测试打包和解包功能"""
        original = SwitchBaudrateData(
            session_id=0x12345678,
            new_baudrate=921600,
            switch_delay_ms=100
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