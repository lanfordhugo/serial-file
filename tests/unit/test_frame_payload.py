"""
FramePayload模块单元测试
"""

import struct
import pytest
from src.serial_file_transfer.core.frame_payload import FramePayload


class TestSendDataPayload:
    """SEND_DATA帧载荷测试"""
    
    def test_pack_send_data(self):
        """测试打包SEND_DATA载荷"""
        seq_id = 123
        offset = 4096
        payload = b'test_data_content'
        
        data = FramePayload.pack_send_data(seq_id, offset, payload)
        
        # 验证长度：2字节seq + 4字节offset + payload长度
        assert len(data) == 6 + len(payload)
        
        # 验证格式
        unpacked_seq = struct.unpack("<H", data[:2])[0]
        unpacked_offset = struct.unpack("<I", data[2:6])[0]
        unpacked_payload = data[6:]
        
        assert unpacked_seq == seq_id
        assert unpacked_offset == offset
        assert unpacked_payload == payload
    
    def test_unpack_send_data(self):
        """测试解包SEND_DATA载荷"""
        seq_id = 456
        offset = 8192
        payload = b'another_test_data'
        
        # 打包
        data = struct.pack("<HI", seq_id, offset) + payload
        
        # 解包
        result = FramePayload.unpack_send_data(data)
        
        assert result is not None
        unpacked_seq, unpacked_offset, unpacked_payload = result
        assert unpacked_seq == seq_id
        assert unpacked_offset == offset
        assert unpacked_payload == payload
    
    def test_unpack_send_data_invalid(self):
        """测试解包无效SEND_DATA载荷"""
        # 数据过短
        assert FramePayload.unpack_send_data(b'12345') is None
        assert FramePayload.unpack_send_data(b'') is None
    
    def test_pack_unpack_roundtrip(self):
        """测试打包解包往返"""
        seq_id = 789
        offset = 16384
        payload = b'roundtrip_test_payload_12345'
        
        packed = FramePayload.pack_send_data(seq_id, offset, payload)
        unpacked = FramePayload.unpack_send_data(packed)
        
        assert unpacked is not None
        assert unpacked[0] == seq_id
        assert unpacked[1] == offset
        assert unpacked[2] == payload


class TestAckNackPayload:
    """ACK/NACK帧载荷测试"""
    
    def test_pack_ack(self):
        """测试打包ACK载荷"""
        seq_id = 100
        offset = 2048
        
        data = FramePayload.pack_ack(seq_id, offset)
        
        # 验证长度：2字节seq + 4字节offset = 6字节
        assert len(data) == 6
        
        # 验证内容
        unpacked_seq = struct.unpack("<H", data[:2])[0]
        unpacked_offset = struct.unpack("<I", data[2:6])[0]
        
        assert unpacked_seq == seq_id
        assert unpacked_offset == offset
    
    def test_unpack_ack(self):
        """测试解包ACK载荷"""
        seq_id = 200
        offset = 4096
        
        data = struct.pack("<HI", seq_id, offset)
        result = FramePayload.unpack_ack(data)
        
        assert result is not None
        assert result[0] == seq_id
        assert result[1] == offset
    
    def test_unpack_ack_invalid(self):
        """测试解包无效ACK载荷"""
        assert FramePayload.unpack_ack(b'12345') is None  # 长度不足
        assert FramePayload.unpack_ack(b'') is None
    
    def test_pack_nack(self):
        """测试打包NACK载荷"""
        seq_id = 300
        offset = 8192
        
        data = FramePayload.pack_nack(seq_id, offset)
        
        # NACK与ACK格式相同
        assert len(data) == 6
        
        unpacked_seq = struct.unpack("<H", data[:2])[0]
        unpacked_offset = struct.unpack("<I", data[2:6])[0]
        
        assert unpacked_seq == seq_id
        assert unpacked_offset == offset
    
    def test_unpack_nack(self):
        """测试解包NACK载荷"""
        seq_id = 400
        offset = 12288
        
        data = struct.pack("<HI", seq_id, offset)
        result = FramePayload.unpack_nack(data)
        
        assert result is not None
        assert result[0] == seq_id
        assert result[1] == offset


class TestSyncPayload:
    """SYNC帧载荷测试"""
    
    def test_pack_sync_request(self):
        """测试打包SYNC_REQUEST载荷"""
        seq_id = 500
        offset = 16384
        
        data = FramePayload.pack_sync_request(seq_id, offset)
        
        assert len(data) == 6
        
        unpacked_seq = struct.unpack("<H", data[:2])[0]
        unpacked_offset = struct.unpack("<I", data[2:6])[0]
        
        assert unpacked_seq == seq_id
        assert unpacked_offset == offset
    
    def test_unpack_sync_request(self):
        """测试解包SYNC_REQUEST载荷"""
        seq_id = 600
        offset = 20480
        
        data = struct.pack("<HI", seq_id, offset)
        result = FramePayload.unpack_sync_request(data)
        
        assert result is not None
        assert result[0] == seq_id
        assert result[1] == offset
    
    def test_pack_sync_reply(self):
        """测试打包SYNC_REPLY载荷"""
        seq_id = 700
        offset = 24576
        ack_seq = 800
        
        data = FramePayload.pack_sync_reply(seq_id, offset, ack_seq)
        
        # 2字节seq + 4字节offset + 2字节ack_seq = 8字节
        assert len(data) == 8
        
        unpacked_seq = struct.unpack("<H", data[:2])[0]
        unpacked_offset = struct.unpack("<I", data[2:6])[0]
        unpacked_ack = struct.unpack("<H", data[6:8])[0]
        
        assert unpacked_seq == seq_id
        assert unpacked_offset == offset
        assert unpacked_ack == ack_seq
    
    def test_unpack_sync_reply(self):
        """测试解包SYNC_REPLY载荷"""
        seq_id = 900
        offset = 28672
        ack_seq = 1000
        
        data = struct.pack("<HIH", seq_id, offset, ack_seq)
        result = FramePayload.unpack_sync_reply(data)
        
        assert result is not None
        assert result[0] == seq_id
        assert result[1] == offset
        assert result[2] == ack_seq
    
    def test_unpack_sync_reply_invalid(self):
        """测试解包无效SYNC_REPLY载荷"""
        assert FramePayload.unpack_sync_reply(b'1234567') is None  # 长度不足
        assert FramePayload.unpack_sync_reply(b'') is None


class TestOtherPayloads:
    """其他载荷格式测试"""
    
    def test_pack_request_file(self):
        """测试打包文件请求"""
        data = FramePayload.pack_request_file()
        
        # 应该是2字节的特征值0x55AA
        assert len(data) == 2
        value = struct.unpack("<H", data)[0]
        assert value == 0x55AA
    
    def test_pack_file_size(self):
        """测试打包文件大小"""
        file_size = 1024 * 1024  # 1MB
        
        data = FramePayload.pack_file_size(file_size)
        
        assert len(data) == 4
        unpacked_size = struct.unpack("<I", data)[0]
        assert unpacked_size == file_size
    
    def test_unpack_file_size(self):
        """测试解包文件大小"""
        file_size = 5 * 1024 * 1024  # 5MB
        
        data = struct.pack("<I", file_size)
        result = FramePayload.unpack_file_size(data)
        
        assert result == file_size
    
    def test_unpack_file_size_invalid(self):
        """测试解包无效文件大小"""
        assert FramePayload.unpack_file_size(b'123') is None
        assert FramePayload.unpack_file_size(b'') is None
    
    def test_pack_filename(self):
        """测试打包文件名"""
        filename = "test_file.txt"
        
        data = FramePayload.pack_filename(filename)
        
        # 2字节长度 + UTF-8编码的文件名
        expected_len = 2 + len(filename.encode("utf-8"))
        assert len(data) == expected_len
        
        # 验证长度字段
        name_len = struct.unpack("<H", data[:2])[0]
        assert name_len == len(filename.encode("utf-8"))
    
    def test_unpack_filename(self):
        """测试解包文件名"""
        filename = "another_test.dat"
        
        encoded_name = filename.encode("utf-8")
        data = struct.pack("<H", len(encoded_name)) + encoded_name
        
        result = FramePayload.unpack_filename(data)
        
        assert result == filename
    
    def test_pack_filename_truncation(self):
        """测试文件名截断"""
        # 超长文件名
        long_filename = "a" * 600
        
        data = FramePayload.pack_filename(long_filename, max_length=512)
        
        # 应该被截断到512字节
        name_len = struct.unpack("<H", data[:2])[0]
        assert name_len == 512
    
    def test_unpack_filename_invalid(self):
        """测试解包无效文件名"""
        assert FramePayload.unpack_filename(b'1') is None  # 长度不足
        assert FramePayload.unpack_filename(b'') is None
        
        # 长度字段指示的长度超过实际数据
        invalid_data = struct.pack("<H", 100) + b'short'
        assert FramePayload.unpack_filename(invalid_data) is None
    
    def test_pack_data_request(self):
        """测试打包数据请求"""
        addr = 4096
        length = 1024
        
        data = FramePayload.pack_data_request(addr, length)
        
        # 4字节地址 + 2字节长度 = 6字节
        assert len(data) == 6
        
        unpacked_addr = struct.unpack("<I", data[:4])[0]
        unpacked_len = struct.unpack("<H", data[4:6])[0]
        
        assert unpacked_addr == addr
        assert unpacked_len == length
    
    def test_unpack_data_request(self):
        """测试解包数据请求"""
        addr = 8192
        length = 2048
        
        data = struct.pack("<IH", addr, length)
        result = FramePayload.unpack_data_request(data)
        
        assert result is not None
        assert result[0] == addr
        assert result[1] == length
    
    def test_unpack_data_request_invalid(self):
        """测试解包无效数据请求"""
        assert FramePayload.unpack_data_request(b'12345') is None
        assert FramePayload.unpack_data_request(b'') is None


class TestEdgeCases:
    """边界情况测试"""
    
    def test_seq_id_wrap_around(self):
        """测试序号回绕（0-65535）"""
        seq_id = 65535  # 最大值
        offset = 0
        
        data = FramePayload.pack_ack(seq_id, offset)
        result = FramePayload.unpack_ack(data)
        
        assert result is not None
        assert result[0] == 65535
    
    def test_large_offset(self):
        """测试大偏移量"""
        seq_id = 0
        offset = 0xFFFFFFFF  # 最大32位无符号整数
        
        data = FramePayload.pack_ack(seq_id, offset)
        result = FramePayload.unpack_ack(data)
        
        assert result is not None
        assert result[1] == offset
    
    def test_empty_payload(self):
        """测试空载荷"""
        seq_id = 1
        offset = 0
        payload = b''
        
        data = FramePayload.pack_send_data(seq_id, offset, payload)
        result = FramePayload.unpack_send_data(data)
        
        assert result is not None
        assert result[2] == b''
    
    def test_chinese_filename(self):
        """测试中文文件名"""
        filename = "测试文件.txt"
        
        data = FramePayload.pack_filename(filename)
        result = FramePayload.unpack_filename(data)
        
        assert result == filename

