#!/usr/bin/env python3
"""
配置类测试
==========

这个文件测试 serial_file_transfer.config.settings 模块中的配置类。

测试内容包括：
- SerialConfig类的功能测试
- TransferConfig类的功能测试
- 参数验证测试
- 默认值测试
"""

import pytest
import serial
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from serial_file_transfer.config.settings import SerialConfig, TransferConfig


class TestSerialConfig:
    """
    测试SerialConfig配置类
    
    SerialConfig用于管理串口连接的各种参数
    """
    
    def test_serial_config_default_values(self):
        """
        测试SerialConfig的默认值
        
        验证在只提供必需参数时，其他参数使用正确的默认值
        """
        # 只提供必需的port参数
        config = SerialConfig(port="COM1")
        
        # 验证默认值
        assert config.port == "COM1"
        assert config.baudrate == 115200  # 默认波特率
        assert config.bytesize == serial.EIGHTBITS  # 8数据位
        assert config.parity == serial.PARITY_NONE  # 无校验
        assert config.stopbits == serial.STOPBITS_ONE  # 1停止位
        assert config.timeout == 0.1  # 默认超时0.1秒
    
    def test_serial_config_custom_values(self):
        """
        测试SerialConfig的自定义值
        
        验证可以正确设置所有参数的自定义值
        """
        config = SerialConfig(
            port="COM3",
            baudrate=115200,
            bytesize=serial.SEVENBITS,
            parity=serial.PARITY_EVEN,
            stopbits=serial.STOPBITS_TWO,
            timeout=5.0
        )
        
        # 验证所有自定义值
        assert config.port == "COM3"
        assert config.baudrate == 115200
        assert config.bytesize == serial.SEVENBITS
        assert config.parity == serial.PARITY_EVEN
        assert config.stopbits == serial.STOPBITS_TWO
        assert config.timeout == 5.0
    
    def test_to_serial_kwargs(self):
        """
        测试to_serial_kwargs方法
        
        这个方法将配置对象转换为serial.Serial构造函数需要的参数字典
        """
        config = SerialConfig(
            port="COM1",
            baudrate=9600,
            timeout=1.0
        )
        
        # 调用方法获取参数字典
        kwargs = config.to_serial_kwargs()
        
        # 验证返回的字典包含所有必要的键
        expected_keys = {'port', 'baudrate', 'bytesize', 'parity', 'stopbits', 'timeout'}
        assert set(kwargs.keys()) == expected_keys, f"参数字典应该包含键: {expected_keys}"
        
        # 验证值的正确性
        assert kwargs['port'] == "COM1"
        assert kwargs['baudrate'] == 9600
        assert kwargs['timeout'] == 1.0
        assert kwargs['bytesize'] == serial.EIGHTBITS  # 默认值
        assert kwargs['parity'] == serial.PARITY_NONE  # 默认值
        assert kwargs['stopbits'] == serial.STOPBITS_ONE  # 默认值
    
    def test_to_serial_kwargs_with_all_custom_values(self):
        """
        测试to_serial_kwargs方法处理所有自定义值的情况
        """
        config = SerialConfig(
            port="/dev/ttyUSB0",  # Linux串口
            baudrate=57600,
            bytesize=serial.SEVENBITS,
            parity=serial.PARITY_ODD,
            stopbits=serial.STOPBITS_TWO,
            timeout=10.0
        )
        
        kwargs = config.to_serial_kwargs()
        
        # 验证所有自定义值都正确传递
        assert kwargs['port'] == "/dev/ttyUSB0"
        assert kwargs['baudrate'] == 57600
        assert kwargs['bytesize'] == serial.SEVENBITS
        assert kwargs['parity'] == serial.PARITY_ODD
        assert kwargs['stopbits'] == serial.STOPBITS_TWO
        assert kwargs['timeout'] == 10.0
    
    @pytest.mark.parametrize("port,baudrate,expected_port,expected_baudrate", [
        # 参数化测试：测试不同的端口和波特率组合
        ("COM1", 9600, "COM1", 9600),
        ("COM2", 115200, "COM2", 115200),
        ("/dev/ttyUSB0", 1728000, "/dev/ttyUSB0", 1728000),
        ("COM10", 57600, "COM10", 57600),
    ])
    def test_serial_config_parametrized(self, port, baudrate, expected_port, expected_baudrate):
        """
        参数化测试：测试不同的端口和波特率组合
        
        这种测试方式可以用相同的测试逻辑验证多组不同的输入
        """
        config = SerialConfig(port=port, baudrate=baudrate)
        
        assert config.port == expected_port
        assert config.baudrate == expected_baudrate


class TestTransferConfig:
    """
    测试TransferConfig配置类
    
    TransferConfig用于管理文件传输的各种参数
    """
    
    def test_transfer_config_default_values(self):
        """
        测试TransferConfig的默认值
        
        验证所有参数都有合理的默认值
        """
        config = TransferConfig()
        
        # 验证默认值（这些值在constants.py中定义）
        assert config.max_data_length == 1024  # 1KB
        assert config.request_timeout == 300  # 300秒
        assert config.retry_count == 3  # 重试3次
        assert config.show_progress is True  # 显示进度
    
    def test_transfer_config_custom_values(self):
        """
        测试TransferConfig的自定义值
        
        验证可以正确设置所有参数的自定义值
        """
        config = TransferConfig(
            max_data_length=5120,  # 5KB
            request_timeout=60,    # 60秒
            retry_count=5,         # 重试5次
            show_progress=False    # 不显示进度
        )
        
        assert config.max_data_length == 5120
        assert config.request_timeout == 60
        assert config.retry_count == 5
        assert config.show_progress is False
    
    def test_transfer_config_validation_max_data_length(self):
        """
        测试max_data_length参数验证
        
        max_data_length必须大于0，否则应该抛出ValueError
        """
        # 测试零值
        with pytest.raises(ValueError, match="max_data_length必须大于0"):
            TransferConfig(max_data_length=0)
        
        # 测试负值
        with pytest.raises(ValueError, match="max_data_length必须大于0"):
            TransferConfig(max_data_length=-1)
        
        # 测试正值应该正常工作
        config = TransferConfig(max_data_length=1024)
        assert config.max_data_length == 1024
    
    def test_transfer_config_validation_request_timeout(self):
        """
        测试request_timeout参数验证
        
        request_timeout必须大于0，否则应该抛出ValueError
        """
        # 测试零值
        with pytest.raises(ValueError, match="request_timeout必须大于0"):
            TransferConfig(request_timeout=0)
        
        # 测试负值
        with pytest.raises(ValueError, match="request_timeout必须大于0"):
            TransferConfig(request_timeout=-5)
        
        # 测试正值应该正常工作
        config = TransferConfig(request_timeout=120)
        assert config.request_timeout == 120
    
    def test_transfer_config_validation_retry_count(self):
        """
        测试retry_count参数验证
        
        retry_count不能为负数，但可以为0（表示不重试）
        """
        # 测试负值
        with pytest.raises(ValueError, match="retry_count不能为负数"):
            TransferConfig(retry_count=-1)
        
        # 测试零值应该正常工作（不重试）
        config = TransferConfig(retry_count=0)
        assert config.retry_count == 0
        
        # 测试正值应该正常工作
        config = TransferConfig(retry_count=10)
        assert config.retry_count == 10
    
    def test_transfer_config_validation_multiple_errors(self):
        """
        测试多个参数同时错误的情况
        
        __post_init__方法会按顺序检查参数，应该抛出第一个遇到的错误
        """
        # 同时传递多个无效参数，应该抛出第一个错误
        with pytest.raises(ValueError, match="max_data_length必须大于0"):
            TransferConfig(
                max_data_length=0,      # 第一个错误
                request_timeout=-1,     # 第二个错误
                retry_count=-1          # 第三个错误
            )
    
    @pytest.mark.parametrize("max_data_length,request_timeout,retry_count,show_progress", [
                 # 参数化测试：测试各种有效的参数组合
         (1024, 10, 0, True),      # 最小有效值
         (1024, 300, 3, True),     # 默认值
         (65536, 120, 10, False),  # 大值
         (512, 5, 1, True),        # 小值但有效
    ])
    def test_transfer_config_valid_combinations(self, max_data_length, request_timeout, 
                                              retry_count, show_progress):
        """
        参数化测试：验证各种有效的参数组合
        
        确保所有合理的参数组合都能正常工作
        """
        config = TransferConfig(
            max_data_length=max_data_length,
            request_timeout=request_timeout,
            retry_count=retry_count,
            show_progress=show_progress
        )
        
        assert config.max_data_length == max_data_length
        assert config.request_timeout == request_timeout
        assert config.retry_count == retry_count
        assert config.show_progress == show_progress
    
    def test_transfer_config_edge_cases(self):
        """
        测试边界情况
        
        验证在边界值附近的行为
        """
        # 测试最小有效值
        config = TransferConfig(
            max_data_length=1,      # 最小正整数
            request_timeout=1,      # 最小正整数
            retry_count=0           # 最小非负整数
        )
        
        assert config.max_data_length == 1
        assert config.request_timeout == 1
        assert config.retry_count == 0
        
        # 测试较大的值
        config = TransferConfig(
            max_data_length=1048576,  # 1MB
            request_timeout=3600,     # 1小时
            retry_count=100           # 大重试次数
        )
        
        assert config.max_data_length == 1048576
        assert config.request_timeout == 3600
        assert config.retry_count == 100


class TestConfigIntegration:
    """
    配置类集成测试
    
    测试两个配置类在一起使用时的行为
    """
    
    def test_configs_independence(self):
        """
        测试两个配置类的独立性
        
        确保修改一个配置不会影响另一个
        """
        serial_config = SerialConfig(port="COM1", baudrate=9600)
        transfer_config = TransferConfig(max_data_length=2048)
        
        # 修改一个配置
        serial_config.baudrate = 115200
        transfer_config.max_data_length = 4096
        
        # 验证修改只影响对应的配置
        assert serial_config.baudrate == 115200
        assert transfer_config.max_data_length == 4096
        
        # 创建新的配置实例，应该使用默认值
        new_serial_config = SerialConfig(port="COM2")
        new_transfer_config = TransferConfig()
        
        assert new_serial_config.baudrate == 115200  # 默认值
        assert new_transfer_config.max_data_length == 1024  # 默认值
    
    def test_configs_typical_usage(self):
        """
        测试配置类的典型使用场景
        
        模拟实际使用中的配置组合
        """
        # 高速传输配置
        high_speed_serial = SerialConfig(
            port="COM1",
            baudrate=1728000,  # 高波特率
            timeout=1.0        # 短超时
        )
        
        high_speed_transfer = TransferConfig(
            max_data_length=65536,  # 大数据块
            request_timeout=10,     # 短请求超时
            retry_count=1,          # 少重试
            show_progress=True
        )
        
        # 验证高速配置
        assert high_speed_serial.baudrate == 1728000
        assert high_speed_transfer.max_data_length == 65536
        
        # 可靠传输配置
        reliable_serial = SerialConfig(
            port="COM1",
            baudrate=115200,   # 稳定波特率
            timeout=5.0        # 长超时
        )
        
        reliable_transfer = TransferConfig(
            max_data_length=1024,   # 小数据块
            request_timeout=60,     # 长请求超时
            retry_count=10,         # 多重试
            show_progress=True
        )
        
        # 验证可靠配置
        assert reliable_serial.baudrate == 115200
        assert reliable_transfer.retry_count == 10


# 如果直接运行这个文件，执行所有测试
if __name__ == "__main__":
    """
    运行测试的说明：
    
    1. 直接运行文件：python test_settings.py
    2. 使用pytest运行：pytest test_settings.py -v
    3. 运行特定测试类：pytest test_settings.py::TestSerialConfig -v
    4. 运行特定测试方法：pytest test_settings.py::TestSerialConfig::test_serial_config_default_values -v
    """
    pytest.main([__file__, "-v"]) 