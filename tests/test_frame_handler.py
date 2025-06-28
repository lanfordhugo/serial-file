"""
数据帧处理器测试
================

测试FrameHandler类的各种功能。
"""

import pytest
import struct

from serial_file_transfer.core.frame_handler import FrameHandler
from serial_file_transfer.config.constants import SerialCommand


class TestFrameHandler:
    """数据帧处理器测试类"""
    
    def test_pack_frame_success(self):
        """测试成功打包数据帧"""
        cmd = SerialCommand.REQUEST_FILE_SIZE
        data = b"test data"
        
        frame = FrameHandler.pack_frame(cmd, data)
        
        assert frame is not None
        assert len(frame) > len(data)  # 应该包含头部和校验和
    
    def test_pack_frame_with_none_data(self):
        """测试使用None数据打包"""
        cmd = SerialCommand.REQUEST_FILE_SIZE
        data = None
        
        frame = FrameHandler.pack_frame(cmd, data)
        
        assert frame is None
    
    def test_pack_frame_with_empty_data(self):
        """测试使用空数据打包"""
        cmd = SerialCommand.REQUEST_FILE_SIZE
        data = b""
        
        frame = FrameHandler.pack_frame(cmd, data)
        
        assert frame is not None
        assert len(frame) == 5  # 1字节命令 + 2字节长度 + 2字节校验和
    
    def test_unpack_frame_success(self):
        """测试成功解析数据帧"""
        # 先打包一个数据帧
        original_cmd = SerialCommand.SEND_DATA
        original_data = b"hello world"
        
        packed_frame = FrameHandler.pack_frame(original_cmd, original_data)
        assert packed_frame is not None
        
        # 再解析这个数据帧
        result = FrameHandler.unpack_frame(packed_frame)
        assert result is not None
        
        cmd, data_len, data, crc = result
        assert cmd == original_cmd
        assert data_len == len(original_data)
        assert data == original_data
        assert isinstance(crc, int)
    
    def test_unpack_frame_insufficient_data(self):
        """测试数据长度不足的情况"""
        short_data = b"123"  # 少于6字节的最小帧长度
        
        result = FrameHandler.unpack_frame(short_data)
        
        assert result is None
    
    def test_unpack_frame_corrupted_data(self):
        """测试数据损坏的情况"""
        # 创建一个有效的帧
        cmd = SerialCommand.REQUEST_DATA
        data = b"test"
        frame = FrameHandler.pack_frame(cmd, data)
        assert frame is not None
        
        # 损坏最后一个字节（校验和）
        corrupted_frame = frame[:-1] + b'\x00'
        
        result = FrameHandler.unpack_frame(corrupted_frame)
        
        assert result is None
    
    def test_pack_unpack_roundtrip(self):
        """测试打包-解包往返过程"""
        test_cases = [
            (SerialCommand.REQUEST_FILE_SIZE, b""),
            (SerialCommand.REPLY_FILE_SIZE, b"\x00\x10\x00\x00"),  # 4KB文件
            (SerialCommand.REQUEST_DATA, b"\x00\x00\x00\x00\xFF\x00"),  # 地址+长度
            (SerialCommand.SEND_DATA, b"A" * 100),  # 100字节数据
            (SerialCommand.REQUEST_FILE_NAME, b"\xAA"),
            (SerialCommand.REPLY_FILE_NAME, b"test.txt" + b"\x00" * 120),
        ]
        
        for original_cmd, original_data in test_cases:
            # 打包
            frame = FrameHandler.pack_frame(original_cmd, original_data)
            assert frame is not None, f"打包失败: cmd={original_cmd}, data={original_data}"
            
            # 解包
            result = FrameHandler.unpack_frame(frame)
            assert result is not None, f"解包失败: cmd={original_cmd}, data={original_data}"
            
            cmd, data_len, data, crc = result
            assert cmd == original_cmd, f"命令不匹配: 期望={original_cmd}, 实际={cmd}"
            assert data_len == len(original_data), f"数据长度不匹配: 期望={len(original_data)}, 实际={data_len}"
            assert data == original_data, f"数据内容不匹配: 期望={original_data}, 实际={data}"
    
    @pytest.mark.parametrize("cmd,data", [
        (0x61, b"request"),
        (0x62, struct.pack('<I', 1024)),
        (0x63, struct.pack('<IH', 0, 512)),
        (0x64, b"\x01\x02\x03\x04\x05"),
        (0x51, b"\xAA"),
        (0x52, b"filename.txt"),
    ])
    def test_parametrized_pack_unpack(self, cmd, data):
        """参数化测试不同的命令和数据组合"""
        frame = FrameHandler.pack_frame(cmd, data)
        assert frame is not None
        
        result = FrameHandler.unpack_frame(frame)
        assert result is not None
        
        unpacked_cmd, unpacked_len, unpacked_data, unpacked_crc = result
        assert unpacked_cmd == cmd
        assert unpacked_len == len(data)
        assert unpacked_data == data
        assert isinstance(unpacked_crc, int) 