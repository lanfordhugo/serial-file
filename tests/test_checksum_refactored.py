"""
校验和算法测试 (重构版)
=====================

精简的校验和算法契约测试，专注核心功能与边界条件。
"""

import pytest
from serial_file_transfer.core.checksum import calculate_checksum, calculate_crc16_modbus


class TestChecksumAlgorithms:
    """校验和算法契约测试"""

    @pytest.mark.parametrize(
        "data,expected,description", [
            # 边界条件
            (b"", 0, "空数据"),
            (b"\x00", 0, "单字节零值"),
            (b"\xFF", 255, "单字节最大值"),
            
            # 正常数据
            (b"A", 65, "单字节ASCII"),
            (b"ABC", 65+66+67, "多字节ASCII"),
            (b"hello", 532, "常见字符串"),
            
            # 溢出处理 (16位截断)
            (b"\xFF" * 256, 65280, "边界溢出"),
            (b"\xFF" * 300, 76500 & 0xFFFF, "真实溢出截断"),
        ]
    )
    def test_calculate_checksum(self, data, expected, description):
        """参数化测试校验和计算的核心场景"""
        result = calculate_checksum(data)
        assert result == expected, f"{description}: 期望 {expected}, 实际 {result}"

    @pytest.mark.parametrize(
        "invalid_data,expected_error", [
            ("hello", "输入数据必须是bytes类型"),      # 字符串
            (123, "输入数据必须是bytes类型"),          # 整数
            ([1, 2, 3], "输入数据必须是bytes类型"),    # 列表
            (None, "输入数据必须是bytes类型"),         # None
        ]
    )
    def test_calculate_checksum_type_errors(self, invalid_data, expected_error):
        """参数化测试类型错误处理"""
        with pytest.raises(TypeError, match=expected_error):
            calculate_checksum(invalid_data)  # type: ignore

    @pytest.mark.parametrize(
        "data,expected,description", [
            # CRC16-Modbus关键场景  
            (b"", 0xFFFF, "空数据CRC"),
            (b"\x00", 0x40BF, "单字节零值CRC"),
            (b"123456789", 0x4B37, "标准测试向量"),
            (b"hello world", 0xDDC7, "常见字符串CRC"),
        ]
    )
    def test_calculate_crc16_modbus(self, data, expected, description):
        """参数化测试CRC16-Modbus计算"""
        result = calculate_crc16_modbus(data)
        assert result == expected, f"{description}: 期望 0x{expected:04X}, 实际 0x{result:04X}"

    def test_crc16_type_errors(self):
        """CRC16类型错误测试 - 保持简单"""
        with pytest.raises(TypeError, match="输入数据必须是bytes类型"):
            calculate_crc16_modbus("hello")  # type: ignore
        
        with pytest.raises(TypeError, match="输入数据必须是bytes类型"):
            calculate_crc16_modbus(123)  # type: ignore
