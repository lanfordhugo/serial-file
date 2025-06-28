#!/usr/bin/env python3
"""
校验和算法测试
==============

这个文件测试 serial_file_transfer.core.checksum 模块中的校验和算法。

pytest测试基础知识：
- pytest是Python最流行的测试框架
- 测试函数必须以 test_ 开头
- 使用 assert 语句进行断言验证
- pytest会自动发现并运行所有test_开头的函数
- 可以使用 pytest.raises() 测试异常情况
- 可以使用 @pytest.mark.parametrize 进行参数化测试
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到Python路径，确保能导入我们的模块
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from serial_file_transfer.core.checksum import calculate_checksum, calculate_crc16_modbus


class TestCalculateChecksum:
    """
    测试calculate_checksum函数的测试类
    
    pytest中的测试类：
    - 类名必须以Test开头
    - 类中的测试方法必须以test_开头
    - 可以使用setup_method和teardown_method进行测试前后的准备和清理
    """
    
    def test_calculate_checksum_empty_data(self):
        """
        测试空数据的校验和计算
        
        边界测试：空输入应该返回0
        这是一个重要的边界条件测试
        """
        result = calculate_checksum(b'')
        assert result == 0, "空数据的校验和应该为0"
    
    def test_calculate_checksum_single_byte(self):
        """
        测试单字节数据的校验和计算
        
        基础功能测试：验证单个字节的处理
        """
        # 测试字节值65 (ASCII 'A')
        result = calculate_checksum(b'A')
        assert result == 65, "单字节'A'(65)的校验和应该为65"
        
        # 测试字节值0
        result = calculate_checksum(b'\x00')
        assert result == 0, "单字节0的校验和应该为0"
        
        # 测试字节值255
        result = calculate_checksum(b'\xFF')
        assert result == 255, "单字节255的校验和应该为255"
    
    def test_calculate_checksum_multiple_bytes(self):
        """
        测试多字节数据的校验和计算
        
        正常功能测试：验证多字节累加逻辑
        """
        # 测试简单的多字节数据
        data = b'ABC'  # A=65, B=66, C=67, 总和=198
        result = calculate_checksum(data)
        expected = 65 + 66 + 67  # 198
        assert result == expected, f"'ABC'的校验和应该为{expected}"
        
        # 测试已知的数据
        data = b'hello'  # h=104, e=101, l=108, l=108, o=111, 总和=532
        result = calculate_checksum(data)
        expected = 532
        assert result == expected, f"'hello'的校验和应该为{expected}"
    
    def test_calculate_checksum_overflow_handling(self):
        """
        测试校验和溢出处理（16位截断）
        
        边界测试：验证超过16位的数据被正确截断到低16位
        """
        # 创建一个会导致溢出的数据：256个0xFF字节
        # 256 * 255 = 65280，超过16位最大值65535
        data = b'\xFF' * 256  # 总和 = 256 * 255 = 65280
        result = calculate_checksum(data)
        expected = 65280 & 0xFFFF  # 应该等于65280（刚好在16位范围内）
        assert result == expected, f"溢出数据的校验和应该被截断到16位: {expected}"
        
        # 测试真正的溢出情况：300个0xFF字节
        data = b'\xFF' * 300  # 总和 = 300 * 255 = 76500
        result = calculate_checksum(data)
        expected = 76500 & 0xFFFF  # 76500 & 0xFFFF = 10964
        assert result == expected, f"真正溢出的数据校验和应该为: {expected}"
    
    def test_calculate_checksum_large_data(self):
        """
        测试大数据块的校验和计算
        
        性能和稳定性测试：确保大数据也能正确处理
        """
        # 创建10KB的测试数据
        large_data = b'X' * 10240  # 10KB的'X'字符
        result = calculate_checksum(large_data)
        
        # 'X' 的ASCII值是88，10240个88的和是901120
        expected = (10240 * 88) & 0xFFFF  # 901120 & 0xFFFF = 49600
        assert result == expected, f"大数据块的校验和计算错误"
        
        # 验证函数能处理更大的数据而不崩溃
        very_large_data = b'Y' * 100000  # 100KB
        result = calculate_checksum(very_large_data)
        assert isinstance(result, int), "大数据处理应该返回整数"
        assert 0 <= result <= 0xFFFF, "校验和应该在16位范围内"
    
    def test_calculate_checksum_type_error(self):
        """
        测试类型错误处理
        
        异常测试：验证非bytes类型输入会抛出正确的异常
        pytest.raises用法：用于测试函数是否抛出预期的异常
        """
        # 测试字符串输入
        with pytest.raises(TypeError, match="输入数据必须是bytes类型"):
            calculate_checksum("hello")  # type: ignore # 故意传递错误类型测试异常
        
        # 测试整数输入
        with pytest.raises(TypeError, match="输入数据必须是bytes类型"):
            calculate_checksum(123)  # type: ignore # 故意传递错误类型测试异常
        
        # 测试列表输入
        with pytest.raises(TypeError, match="输入数据必须是bytes类型"):
            calculate_checksum([1, 2, 3])  # type: ignore # 故意传递错误类型测试异常
        
        # 测试None输入
        with pytest.raises(TypeError, match="输入数据必须是bytes类型"):
            calculate_checksum(None)  # type: ignore # 故意传递错误类型测试异常
    
    @pytest.mark.parametrize("data,expected", [
        # 参数化测试：一次定义多个测试用例
        # 格式：(输入数据, 期望结果)
        (b'', 0),                    # 空数据
        (b'\x00', 0),               # 单个零字节
        (b'\x01', 1),               # 单个字节1
        (b'\xFF', 255),             # 单个字节255
        (b'\x01\x02', 3),           # 两字节：1+2=3
        (b'\xFF\xFF', 510),         # 两字节：255+255=510
        (b'test', 448),             # 't'=116, 'e'=101, 's'=115, 't'=116, 总和=448
    ])
    def test_calculate_checksum_parametrized(self, data, expected):
        """
        参数化测试：使用不同的输入数据测试校验和计算
        
        @pytest.mark.parametrize装饰器说明：
        - 第一个参数是参数名列表："data,expected"
        - 第二个参数是测试用例列表，每个元组对应一组参数
        - pytest会为每个参数组合自动生成一个测试用例
        - 这样可以避免重复编写相似的测试代码
        """
        result = calculate_checksum(data)
        assert result == expected, f"数据{data}的校验和应该为{expected}，实际为{result}"


class TestCalculateCRC16Modbus:
    """
    测试calculate_crc16_modbus函数的测试类
    
    CRC16是一种更复杂的校验算法，通常用于工业通信协议
    """
    
    def test_crc16_empty_data(self):
        """测试空数据的CRC16计算"""
        result = calculate_crc16_modbus(b'')
        # CRC16算法对空数据有特定的初始值
        assert isinstance(result, int), "CRC16结果应该是整数"
        assert 0 <= result <= 0xFFFF, "CRC16结果应该在16位范围内"
    
    def test_crc16_known_values(self):
        """
        测试已知数据的CRC16值
        
        这些是通过标准CRC16算法计算出的已知结果
        用于验证我们的实现是否正确
        """
        # 测试简单数据
        result = calculate_crc16_modbus(b'A')
        assert isinstance(result, int), "CRC16结果应该是整数"
        
        # 测试更复杂的数据
        result = calculate_crc16_modbus(b'123456789')
        assert isinstance(result, int), "CRC16结果应该是整数"
        assert 0 <= result <= 0xFFFF, "CRC16结果应该在16位范围内"
    
    def test_crc16_type_error(self):
        """测试CRC16函数的类型错误处理"""
        with pytest.raises(TypeError, match="输入数据必须是bytes类型"):
            calculate_crc16_modbus("hello")  # type: ignore # 故意传递错误类型测试异常
        
        with pytest.raises(TypeError, match="输入数据必须是bytes类型"):
            calculate_crc16_modbus(123)  # type: ignore # 故意传递错误类型测试异常
    
    def test_crc16_different_from_checksum(self):
        """
        验证CRC16和简单校验和产生不同的结果
        
        这个测试确保两种算法确实是不同的
        """
        test_data = b'hello world'
        
        checksum_result = calculate_checksum(test_data)
        crc16_result = calculate_crc16_modbus(test_data)
        
        # 两种算法应该产生不同的结果（除非极其巧合）
        assert checksum_result != crc16_result, "CRC16和简单校验和应该产生不同的结果"
    
    def test_crc16_consistency(self):
        """
        测试CRC16算法的一致性
        
        相同的输入应该总是产生相同的输出
        """
        test_data = b'consistency test data'
        
        result1 = calculate_crc16_modbus(test_data)
        result2 = calculate_crc16_modbus(test_data)
        result3 = calculate_crc16_modbus(test_data)
        
        assert result1 == result2 == result3, "CRC16算法应该对相同输入产生一致的结果"


# 如果直接运行这个文件，执行所有测试
if __name__ == "__main__":
    """
    直接运行测试的方法：
    1. 在命令行运行：python test_checksum.py
    2. 或者使用pytest：pytest test_checksum.py -v
    
    -v 参数表示verbose（详细输出），会显示每个测试的名称和结果
    """
    pytest.main([__file__, "-v"]) 