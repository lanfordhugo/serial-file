"""
FrameHandler vNext版本单元测试
"""

import pytest
from src.serial_file_transfer.core.frame_handler import FrameHandler
from src.serial_file_transfer.core.frame_payload import FramePayload
from src.serial_file_transfer.config.constants import SerialCommand


class TestFrameHandlerVNext:
    """FrameHandler vNext新增功能测试"""
    
    def test_pack_send_data_frame(self):
        """测试打包SEND_DATA完整帧（包含offset）"""
        seq_id = 123
        offset = 4096
        payload = b'test_data_content'
        
        frame = FrameHandler.pack_send_data_frame(seq_id, offset, payload)
        
        assert frame is not None
        # 帧结构：cmd(1) + len(2) + seq(2) + offset(4) + payload + crc(2)
        expected_len = 1 + 2 + 2 + 4 + len(payload) + 2
        assert len(frame) == expected_len
        
        # 解包验证
        unpacked = FrameHandler.unpack_frame(frame)
        assert unpacked is not None
        cmd, data_len, data, crc = unpacked
        assert cmd == SerialCommand.SEND_DATA
        
        # 验证载荷
        result = FramePayload.unpack_send_data(data)
        assert result is not None
        assert result[0] == seq_id
        assert result[1] == offset
        assert result[2] == payload
    
    def test_pack_ack_frame(self):
        """测试打包ACK完整帧（包含offset）"""
        seq_id = 456
        offset = 8192
        
        frame = FrameHandler.pack_ack_frame(seq_id, offset)
        
        assert frame is not None
        # 帧结构：cmd(1) + len(2) + seq(2) + offset(4) + crc(2)
        assert len(frame) == 1 + 2 + 6 + 2
        
        # 解包验证
        unpacked = FrameHandler.unpack_frame(frame)
        assert unpacked is not None
        cmd, data_len, data, crc = unpacked
        assert cmd == SerialCommand.ACK
        
        # 验证载荷
        result = FramePayload.unpack_ack(data)
        assert result is not None
        assert result[0] == seq_id
        assert result[1] == offset
    
    def test_pack_nack_frame(self):
        """测试打包NACK完整帧（包含offset）"""
        seq_id = 789
        offset = 12288
        
        frame = FrameHandler.pack_nack_frame(seq_id, offset)
        
        assert frame is not None
        assert len(frame) == 1 + 2 + 6 + 2
        
        # 解包验证
        unpacked = FrameHandler.unpack_frame(frame)
        assert unpacked is not None
        cmd, data_len, data, crc = unpacked
        assert cmd == SerialCommand.NACK
        
        # 验证载荷
        result = FramePayload.unpack_nack(data)
        assert result is not None
        assert result[0] == seq_id
        assert result[1] == offset
    
    def test_send_data_frame_roundtrip(self):
        """测试SEND_DATA帧完整往返"""
        seq_id = 100
        offset = 2048
        payload = b'roundtrip_test_payload_12345'
        
        # 打包
        frame = FrameHandler.pack_send_data_frame(seq_id, offset, payload)
        assert frame is not None
        
        # 解包
        unpacked = FrameHandler.unpack_frame(frame)
        assert unpacked is not None
        cmd, _, data, _ = unpacked
        assert cmd == SerialCommand.SEND_DATA
        
        # 解析载荷
        result = FramePayload.unpack_send_data(data)
        assert result is not None
        unpacked_seq, unpacked_offset, unpacked_payload = result
        
        # 验证数据完整性
        assert unpacked_seq == seq_id
        assert unpacked_offset == offset
        assert unpacked_payload == payload
    
    def test_ack_frame_roundtrip(self):
        """测试ACK帧完整往返"""
        seq_id = 200
        offset = 4096
        
        # 打包
        frame = FrameHandler.pack_ack_frame(seq_id, offset)
        assert frame is not None
        
        # 解包
        unpacked = FrameHandler.unpack_frame(frame)
        assert unpacked is not None
        cmd, _, data, _ = unpacked
        assert cmd == SerialCommand.ACK
        
        # 解析载荷
        result = FramePayload.unpack_ack(data)
        assert result is not None
        
        assert result[0] == seq_id
        assert result[1] == offset
    
    def test_large_payload(self):
        """测试大载荷数据"""
        seq_id = 300
        offset = 0
        payload = b'x' * 8192  # 8KB payload
        
        frame = FrameHandler.pack_send_data_frame(seq_id, offset, payload)
        assert frame is not None
        
        # 解包验证
        unpacked = FrameHandler.unpack_frame(frame)
        assert unpacked is not None
        
        result = FramePayload.unpack_send_data(unpacked[2])
        assert result is not None
        assert len(result[2]) == 8192
    
    def test_seq_offset_boundary_values(self):
        """测试序号和偏移量边界值"""
        # 最大序号
        seq_id = 65535
        offset = 0
        frame = FrameHandler.pack_ack_frame(seq_id, offset)
        assert frame is not None
        
        unpacked = FrameHandler.unpack_frame(frame)
        assert unpacked is not None
        result = FramePayload.unpack_ack(unpacked[2])
        assert result[0] == 65535
        
        # 最大偏移量
        seq_id = 0
        offset = 0xFFFFFFFF
        frame = FrameHandler.pack_ack_frame(seq_id, offset)
        assert frame is not None
        
        unpacked = FrameHandler.unpack_frame(frame)
        assert unpacked is not None
        result = FramePayload.unpack_ack(unpacked[2])
        assert result[1] == 0xFFFFFFFF
    
    def test_backward_compatibility(self):
        """测试向后兼容性（旧格式帧仍能打包）"""
        # 测试REQUEST_FILE_NAME等旧命令
        request_data = FramePayload.pack_request_file()
        frame = FrameHandler.pack_frame(SerialCommand.REQUEST_FILE_NAME, request_data)
        
        assert frame is not None
        
        # 解包验证
        unpacked = FrameHandler.unpack_frame(frame)
        assert unpacked is not None
        assert unpacked[0] == SerialCommand.REQUEST_FILE_NAME


class TestFrameHandlerErrorHandling:
    """FrameHandler错误处理测试"""
    
    def test_empty_payload(self):
        """测试空载荷"""
        seq_id = 1
        offset = 0
        payload = b''
        
        frame = FrameHandler.pack_send_data_frame(seq_id, offset, payload)
        assert frame is not None
        
        unpacked = FrameHandler.unpack_frame(frame)
        assert unpacked is not None
        
        result = FramePayload.unpack_send_data(unpacked[2])
        assert result is not None
        assert result[2] == b''
    
    def test_corrupted_crc(self):
        """测试CRC校验错误"""
        seq_id = 100
        offset = 1024
        payload = b'test'
        
        frame = FrameHandler.pack_send_data_frame(seq_id, offset, payload)
        assert frame is not None
        
        # 破坏CRC
        corrupted_frame = frame[:-1] + bytes([frame[-1] ^ 0xFF])
        
        # 解包应该失败
        unpacked = FrameHandler.unpack_frame(corrupted_frame)
        assert unpacked is None
    
    def test_truncated_frame(self):
        """测试截断的帧"""
        seq_id = 200
        offset = 2048
        payload = b'test_data'
        
        frame = FrameHandler.pack_send_data_frame(seq_id, offset, payload)
        assert frame is not None
        
        # 截断帧
        truncated = frame[:-5]
        
        # 解包应该失败
        unpacked = FrameHandler.unpack_frame(truncated)
        assert unpacked is None
    
    def test_invalid_data_length(self):
        """测试无效的数据长度"""
        # 构造声明长度与实际长度不符的帧
        import struct
        from src.serial_file_transfer.core.checksum import calculate_checksum
        
        cmd = SerialCommand.SEND_DATA
        data = b'test'
        crc = calculate_checksum(data)
        
        # 声明长度100，但实际只有4字节
        header = struct.pack("<BH", cmd, 100)
        frame = header + data + struct.pack("<H", crc)
        
        # 解包应该失败
        unpacked = FrameHandler.unpack_frame(frame)
        assert unpacked is None

