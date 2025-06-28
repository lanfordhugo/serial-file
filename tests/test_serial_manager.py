#!/usr/bin/env python3
"""
串口管理器测试
==============

这个文件测试 serial_file_transfer.core.serial_manager 模块中的串口管理功能。

由于串口测试涉及硬件设备，我们使用mock对象来模拟串口行为。

Mock测试基础知识：
- Mock是模拟对象，用于替代真实的外部依赖
- 使用unittest.mock.patch装饰器可以替换模块中的对象
- MagicMock提供了灵活的模拟功能
- 可以设置mock对象的返回值、副作用等行为
- 可以验证mock对象是否被正确调用
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, PropertyMock
import serial

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from serial_file_transfer.core.serial_manager import SerialManager
from serial_file_transfer.config.settings import SerialConfig


class TestSerialManager:
    """
    测试SerialManager类的基本功能
    
    串口管理器是整个系统的核心组件，负责管理串口连接
    """
    
    def test_init(self):
        """
        测试SerialManager的初始化
        
        验证构造函数正确设置配置和初始状态
        """
        config = SerialConfig(port="COM1", baudrate=9600)
        manager = SerialManager(config)
        
        # 验证初始状态
        assert manager.config == config
        assert manager.port is None
        assert manager.is_open is False
    
    @patch('serial.Serial')  # 模拟serial.Serial类
    def test_open_success(self, mock_serial_class):
        """
        测试成功打开串口
        
        使用@patch装饰器模拟serial.Serial类
        这样可以避免依赖真实的串口硬件
        """
        # 设置mock对象的行为
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = True
        mock_serial_class.return_value = mock_serial_instance
        
        # 创建管理器并打开串口
        config = SerialConfig(port="COM1", baudrate=9600)
        manager = SerialManager(config)
        
        result = manager.open()
        
        # 验证结果
        assert result is True
        assert manager.is_open is True
        assert manager.port == mock_serial_instance
        
        # 验证Serial类被正确调用
        mock_serial_class.assert_called_once_with(**config.to_serial_kwargs())
    
    @patch('serial.Serial')
    def test_open_failure(self, mock_serial_class):
        """
        测试打开串口失败的情况
        
        模拟Serial构造函数抛出异常
        """
        # 设置mock抛出异常
        mock_serial_class.side_effect = serial.SerialException("无法打开串口")
        
        config = SerialConfig(port="COM1", baudrate=9600)
        manager = SerialManager(config)
        
        result = manager.open()
        
        # 验证失败结果
        assert result is False
        assert manager.is_open is False
        assert manager.port is None
    
    @patch('serial.Serial')
    def test_open_already_open(self, mock_serial_class):
        """
        测试重复打开已经打开的串口
        
        应该返回True但不重新创建串口对象
        """
        # 设置mock对象
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = True
        mock_serial_class.return_value = mock_serial_instance
        
        config = SerialConfig(port="COM1", baudrate=9600)
        manager = SerialManager(config)
        
        # 第一次打开
        result1 = manager.open()
        assert result1 is True
        
        # 第二次打开（应该检测到已经打开）
        result2 = manager.open()
        assert result2 is True
        
        # 验证Serial只被调用一次
        assert mock_serial_class.call_count == 1
    
    def test_close_when_not_open(self):
        """
        测试关闭未打开的串口
        
        应该安全地处理，不抛出异常
        """
        config = SerialConfig(port="COM1", baudrate=9600)
        manager = SerialManager(config)
        
        # 直接关闭未打开的串口
        manager.close()  # 不应该抛出异常
        
        assert manager.port is None
        assert manager.is_open is False
    
    @patch('serial.Serial')
    def test_close_success(self, mock_serial_class):
        """
        测试成功关闭串口
        """
        # 设置mock对象
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = True
        mock_serial_class.return_value = mock_serial_instance
        
        config = SerialConfig(port="COM1", baudrate=9600)
        manager = SerialManager(config)
        
        # 打开然后关闭
        manager.open()
        manager.close()
        
        # 验证关闭操作
        mock_serial_instance.close.assert_called_once()
        assert manager.port is None
        assert manager.is_open is False
    
    @patch('serial.Serial')
    def test_close_with_exception(self, mock_serial_class):
        """
        测试关闭串口时发生异常的情况
        
        即使关闭时出错，也应该清理内部状态
        """
        # 设置mock对象，关闭时抛出异常
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = True
        mock_serial_instance.close.side_effect = Exception("关闭失败")
        mock_serial_class.return_value = mock_serial_instance
        
        config = SerialConfig(port="COM1", baudrate=9600)
        manager = SerialManager(config)
        
        manager.open()
        manager.close()  # 不应该抛出异常
        
        # 验证状态被正确清理
        assert manager.port is None
        assert manager.is_open is False


class TestSerialManagerIO:
    """
    测试SerialManager的输入输出功能
    
    这些测试验证数据读写功能
    """
    
    @patch('serial.Serial')
    def test_write_success(self, mock_serial_class):
        """
        测试成功写入数据
        """
        # 设置mock对象
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = True
        mock_serial_instance.write.return_value = 5  # 模拟写入5字节
        mock_serial_class.return_value = mock_serial_instance
        
        config = SerialConfig(port="COM1", baudrate=9600)
        manager = SerialManager(config)
        manager.open()
        
        # 测试写入
        test_data = b'hello'
        result = manager.write(test_data)
        
        # 验证结果
        assert result is True
        mock_serial_instance.write.assert_called_once_with(test_data)
    
    @patch('serial.Serial')
    def test_write_partial(self, mock_serial_class):
        """
        测试部分写入的情况
        
        如果写入的字节数少于预期，应该返回False
        """
        # 设置mock对象，模拟只写入了3字节
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = True
        mock_serial_instance.write.return_value = 3  # 只写入3字节
        mock_serial_class.return_value = mock_serial_instance
        
        config = SerialConfig(port="COM1", baudrate=9600)
        manager = SerialManager(config)
        manager.open()
        
        # 测试写入5字节数据
        test_data = b'hello'  # 5字节
        result = manager.write(test_data)
        
        # 验证结果：期望5字节但只写入3字节，应该返回False
        assert result is False
    
    def test_write_when_not_open(self):
        """
        测试在串口未打开时写入数据
        
        应该返回False并记录错误
        """
        config = SerialConfig(port="COM1", baudrate=9600)
        manager = SerialManager(config)
        
        # 未打开串口就尝试写入
        result = manager.write(b'test')
        
        assert result is False
    
    @patch('serial.Serial')
    def test_write_exception(self, mock_serial_class):
        """
        测试写入时发生异常的情况
        """
        # 设置mock对象，写入时抛出异常
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = True
        mock_serial_instance.write.side_effect = Exception("写入失败")
        mock_serial_class.return_value = mock_serial_instance
        
        config = SerialConfig(port="COM1", baudrate=9600)
        manager = SerialManager(config)
        manager.open()
        
        result = manager.write(b'test')
        
        assert result is False
    
    @patch('serial.Serial')
    def test_read_success(self, mock_serial_class):
        """
        测试成功读取数据
        """
        # 设置mock对象
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = True
        mock_serial_instance.read.return_value = b'hello'
        mock_serial_class.return_value = mock_serial_instance
        
        config = SerialConfig(port="COM1", baudrate=9600)
        manager = SerialManager(config)
        manager.open()
        
        # 测试读取
        result = manager.read(5)
        
        # 验证结果
        assert result == b'hello'
        mock_serial_instance.read.assert_called_once_with(5)
    
    def test_read_when_not_open(self):
        """
        测试在串口未打开时读取数据
        
        应该返回空bytes
        """
        config = SerialConfig(port="COM1", baudrate=9600)
        manager = SerialManager(config)
        
        # 未打开串口就尝试读取
        result = manager.read(10)
        
        assert result == b''
    
    @patch('serial.Serial')
    def test_read_exception(self, mock_serial_class):
        """
        测试读取时发生异常的情况
        """
        # 设置mock对象，读取时抛出异常
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = True
        mock_serial_instance.read.side_effect = Exception("读取失败")
        mock_serial_class.return_value = mock_serial_instance
        
        config = SerialConfig(port="COM1", baudrate=9600)
        manager = SerialManager(config)
        manager.open()
        
        result = manager.read(10)
        
        assert result == b''


class TestSerialManagerContextManager:
    """
    测试SerialManager的上下文管理器功能
    
    上下文管理器允许使用with语句自动管理资源
    """
    
    @patch('serial.Serial')
    def test_context_manager_success(self, mock_serial_class):
        """
        测试上下文管理器的正常使用
        
        with语句应该自动打开和关闭串口
        """
        # 设置mock对象
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = True
        mock_serial_class.return_value = mock_serial_instance
        
        config = SerialConfig(port="COM1", baudrate=9600)
        manager = SerialManager(config)
        
        # 使用with语句
        with manager as ctx_manager:
            # 在with块内，串口应该是打开的
            assert ctx_manager is manager
            assert manager.is_open is True
        
        # 退出with块后，串口应该被关闭
        assert manager.port is None
    
    @patch('serial.Serial')
    def test_context_manager_open_failure(self, mock_serial_class):
        """
        测试上下文管理器打开失败的情况
        
        如果无法打开串口，应该抛出RuntimeError
        """
        # 设置mock抛出异常
        mock_serial_class.side_effect = serial.SerialException("无法打开串口")
        
        config = SerialConfig(port="COM1", baudrate=9600)
        manager = SerialManager(config)
        
        # 使用with语句，应该抛出RuntimeError
        with pytest.raises(RuntimeError, match="无法打开串口"):
            with manager:
                pass
    
    @patch('serial.Serial')
    def test_context_manager_exception_in_block(self, mock_serial_class):
        """
        测试在with块内发生异常的情况
        
        即使with块内发生异常，串口也应该被正确关闭
        """
        # 设置mock对象
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = True
        mock_serial_class.return_value = mock_serial_instance
        
        config = SerialConfig(port="COM1", baudrate=9600)
        manager = SerialManager(config)
        
        # 在with块内抛出异常
        with pytest.raises(ValueError, match="测试异常"):
            with manager:
                raise ValueError("测试异常")
        
        # 验证串口被正确关闭
        mock_serial_instance.close.assert_called_once()
        assert manager.port is None
    
    @patch('serial.Serial')
    def test_connection_context_manager(self, mock_serial_class):
        """
        测试connection()上下文管理器方法
        
        这是另一种使用上下文管理器的方式
        """
        # 设置mock对象
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = True
        mock_serial_class.return_value = mock_serial_instance
        
        config = SerialConfig(port="COM1", baudrate=9600)
        manager = SerialManager(config)
        
        # 使用connection()方法
        with manager.connection() as ctx_manager:
            assert ctx_manager is manager
            assert manager.is_open is True
        
        # 验证串口被关闭
        assert manager.port is None


class TestSerialManagerStatic:
    """
    测试SerialManager的静态方法
    
    这些方法不依赖实例状态，主要用于系统查询
    """
    
    @patch('serial.tools.list_ports.comports')
    def test_list_available_ports_success(self, mock_comports):
        """
        测试成功获取可用串口列表
        """
        # 创建mock串口信息对象
        mock_port1 = MagicMock()
        mock_port1.device = "COM1"
        mock_port1.description = "USB串口"
        mock_port1.hwid = "USB\\VID_1234&PID_5678"
        
        mock_port2 = MagicMock()
        mock_port2.device = "COM2"
        mock_port2.description = None  # 测试None描述
        mock_port2.hwid = None  # 测试None硬件ID
        
        mock_comports.return_value = [mock_port1, mock_port2]
        
        # 调用方法
        ports = SerialManager.list_available_ports()
        
        # 验证结果
        assert len(ports) == 2
        
        assert ports[0]['device'] == "COM1"
        assert ports[0]['description'] == "USB串口"
        assert ports[0]['hwid'] == "USB\\VID_1234&PID_5678"
        
        assert ports[1]['device'] == "COM2"
        assert ports[1]['description'] == "未知设备"  # None被替换为默认值
        assert ports[1]['hwid'] == "未知硬件ID"  # None被替换为默认值
    
    @patch('serial.tools.list_ports.comports')
    def test_list_available_ports_empty(self, mock_comports):
        """
        测试没有可用串口的情况
        """
        mock_comports.return_value = []
        
        ports = SerialManager.list_available_ports()
        
        assert ports == []
    
    @patch('serial.tools.list_ports.comports')
    def test_list_available_ports_exception(self, mock_comports):
        """
        测试获取串口列表时发生异常的情况
        """
        mock_comports.side_effect = Exception("系统错误")
        
        ports = SerialManager.list_available_ports()
        
        assert ports == []
    
    @patch('serial.tools.list_ports.comports')
    @patch('builtins.print')  # 模拟print函数
    def test_print_available_ports_with_ports(self, mock_print, mock_comports):
        """
        测试打印可用串口信息（有串口的情况）
        """
        # 设置mock串口
        mock_port = MagicMock()
        mock_port.device = "COM1"
        mock_port.description = "USB串口"
        mock_port.hwid = "USB\\VID_1234&PID_5678"
        
        mock_comports.return_value = [mock_port]
        
        # 调用方法
        SerialManager.print_available_ports()
        
        # 验证print被正确调用
        assert mock_print.call_count == 2  # 标题 + 1个串口
        mock_print.assert_any_call("可用的串口：")
        mock_print.assert_any_call("  COM1 - USB串口")
    
    @patch('serial.tools.list_ports.comports')
    @patch('builtins.print')
    def test_print_available_ports_no_ports(self, mock_print, mock_comports):
        """
        测试打印可用串口信息（无串口的情况）
        """
        mock_comports.return_value = []
        
        SerialManager.print_available_ports()
        
        # 验证打印了无串口消息
        mock_print.assert_called_once_with("没有找到可用的串口。")


class TestSerialManagerIntegration:
    """
    串口管理器集成测试
    
    测试多个功能组合使用的场景
    """
    
    @patch('serial.Serial')
    def test_typical_usage_workflow(self, mock_serial_class):
        """
        测试典型的使用流程
        
        模拟完整的打开->写入->读取->关闭流程
        """
        # 设置mock对象
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = True
        mock_serial_instance.write.return_value = 4  # 写入4字节
        mock_serial_instance.read.return_value = b'ok'  # 读取响应
        mock_serial_class.return_value = mock_serial_instance
        
        config = SerialConfig(port="COM1", baudrate=9600)
        manager = SerialManager(config)
        
        # 完整的使用流程
        assert manager.open() is True
        assert manager.write(b'test') is True
        response = manager.read(2)
        assert response == b'ok'
        manager.close()
        
        # 验证最终状态
        assert manager.is_open is False
        assert manager.port is None
    
    @pytest.mark.parametrize("port,baudrate,timeout", [
        ("COM1", 9600, 1.0),
        ("COM2", 115200, 2.0),
        ("/dev/ttyUSB0", 57600, 0.5),
        ("COM10", 1728000, 5.0),
    ])
    @patch('serial.Serial')
    def test_different_configurations(self, mock_serial_class, port, baudrate, timeout):
        """
        参数化测试：测试不同的串口配置
        
        验证SerialManager能正确处理各种配置组合
        """
        # 设置mock对象
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = True
        mock_serial_class.return_value = mock_serial_instance
        
        config = SerialConfig(port=port, baudrate=baudrate, timeout=timeout)
        manager = SerialManager(config)
        
        # 测试打开
        assert manager.open() is True
        
        # 验证Serial被正确调用
        expected_kwargs = config.to_serial_kwargs()
        mock_serial_class.assert_called_once_with(**expected_kwargs)
        
        manager.close()


# 如果直接运行这个文件，执行所有测试
if __name__ == "__main__":
    """
    运行测试的说明：
    
    1. 运行所有测试：pytest test_serial_manager.py -v
    2. 运行特定测试类：pytest test_serial_manager.py::TestSerialManagerIO -v
    3. 运行带覆盖率的测试：pytest test_serial_manager.py --cov=serial_file_transfer.core.serial_manager
    4. 只运行mock相关的测试：pytest test_serial_manager.py -k "mock" -v
    """
    pytest.main([__file__, "-v"]) 