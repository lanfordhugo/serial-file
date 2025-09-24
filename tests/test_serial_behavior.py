"""
串口行为测试 (重构版)
===================

专注串口管理器的对外行为，使用FakeSerial隔离硬件依赖。
避免验证内部实现细节，专注行为结果。
"""

import pytest
from unittest.mock import patch
from serial_file_transfer.core.serial_manager import SerialManager


class TestSerialManagerBehavior:
    """串口管理器行为测试 - 专注对外行为契约"""

    @pytest.mark.parametrize(
        "port,baudrate,timeout,expected_success", [
            ("COM1", 115200, 0.1, True),
            ("COM2", 1728000, 0.2, True),
            ("/dev/ttyUSB0", 9600, 1.0, True),
        ]
    )
    @patch("serial.Serial")
    def test_open_close_lifecycle(self, mock_serial_class, serial_config_default, 
                                 port, baudrate, timeout, expected_success):
        """测试串口打开关闭生命周期 - 行为驱动"""
        # Arrange - 配置Mock串口行为
        mock_serial_instance = mock_serial_class.return_value
        mock_serial_instance.is_open = True
        
        config = serial_config_default
        config.port = port
        config.baudrate = baudrate  
        config.timeout = timeout
        manager = SerialManager(config)
        
        # Act & Assert - 验证行为结果而非内部调用
        # 1. 打开行为
        assert manager.open() == expected_success
        assert manager.is_open == expected_success
        
        # 2. 重复打开应该成功（幂等性）
        assert manager.open() == expected_success
        
        # 3. 关闭行为  
        manager.close()
        mock_serial_instance.is_open = False
        assert manager.is_open == False
        
        # 4. 重复关闭应该安全（幂等性）
        manager.close()  # 不应该抛出异常

    @patch("serial.Serial")
    def test_read_write_operations(self, mock_serial_class, serial_config_default, fake_serial):
        """测试读写操作行为"""
        # Arrange
        mock_serial_instance = mock_serial_class.return_value
        mock_serial_instance.is_open = True
        mock_serial_instance.write.return_value = 5
        mock_serial_instance.read.return_value = b"hello"
        
        manager = SerialManager(serial_config_default)
        manager.open()
        
        # Act & Assert - 写入行为
        write_result = manager.write(b"hello")
        assert write_result == True  # 关注行为结果：成功/失败
        
        # Act & Assert - 读取行为  
        read_result = manager.read(5)
        assert read_result == b"hello"  # 关注行为结果：数据内容

    @pytest.mark.parametrize(
        "operation,exception_type,should_recover", [
            ("open", Exception, False),
            ("write", Exception, True),  # 写入失败后串口仍可用
            ("read", Exception, True),   # 读取失败后串口仍可用
        ]
    )
    @patch("serial.Serial")
    def test_error_handling_behavior(self, mock_serial_class, serial_config_default,
                                   operation, exception_type, should_recover):
        """测试错误处理行为 - 关注错误后的系统状态"""
        # Arrange
        mock_serial_instance = mock_serial_class.return_value
        if operation == "open":
            mock_serial_class.side_effect = exception_type("模拟错误")
        else:
            mock_serial_instance.is_open = True
            getattr(mock_serial_instance, operation).side_effect = exception_type("模拟错误")
        
        manager = SerialManager(serial_config_default)
        
        # Act & Assert
        if operation == "open":
            assert manager.open() == False  # 关注行为结果
            assert manager.is_open == False
        else:
            manager.open()  # 先正常打开
            mock_serial_instance.is_open = True
            
            if operation == "write":
                result = manager.write(b"test")
                assert result == False  # 写入失败
            elif operation == "read":
                result = manager.read(5)
                assert result == b""  # 读取失败返回空
            
            # 验证恢复能力
            if should_recover:
                assert manager.is_open == True  # 串口仍然可用

    @patch("serial.tools.list_ports.comports")
    def test_port_discovery_behavior(self, mock_comports):
        """测试端口发现行为"""
        # Arrange - 模拟不同的端口发现场景
        test_scenarios = [
            ([], []),  # 无端口
            ([("COM1", "USB Serial"), ("COM2", "Bluetooth")], 
             [{"device": "COM1", "description": "USB Serial", "hwid": "USB\\VID_1234&PID_5678\\COM1"},
              {"device": "COM2", "description": "Bluetooth", "hwid": "USB\\VID_1234&PID_5678\\COM2"}]),  # 有端口
        ]
        
        for mock_ports_data, expected_ports in test_scenarios:
            # 设置Mock行为
            mock_ports = []
            for port_name, desc in mock_ports_data:
                mock_port = type('MockPort', (), {})()
                mock_port.device = port_name
                mock_port.description = desc
                mock_port.hwid = f"USB\\VID_1234&PID_5678\\{port_name}"  # 添加hwid属性
                mock_ports.append(mock_port)
            mock_comports.return_value = mock_ports
            
            # Act
            available_ports = SerialManager.list_available_ports()
            
            # Assert - 验证行为结果
            assert available_ports == expected_ports

    @patch("serial.Serial") 
    def test_context_manager_behavior(self, mock_serial_class, serial_config_default):
        """测试上下文管理器行为 - 资源自动清理"""
        # Arrange
        mock_serial_instance = mock_serial_class.return_value
        mock_serial_instance.is_open = True
        
        manager = SerialManager(serial_config_default)
        
        # Act & Assert - 正常流程
        with manager:
            assert manager.is_open == True
        
        # 验证资源清理行为
        mock_serial_instance.close.assert_called()
        
        # Act & Assert - 异常流程  
        mock_serial_instance.reset_mock()
        try:
            with manager:
                raise ValueError("测试异常")
        except ValueError:
            pass
        
        # 即使有异常，资源也应该被清理
        mock_serial_instance.close.assert_called()


class TestSerialManagerIntegration:
    """串口管理器集成行为测试"""
    
    @patch("serial.Serial")
    def test_typical_usage_workflow(self, mock_serial_class, serial_config_default):
        """测试典型使用工作流 - 端到端行为验证"""
        # Arrange
        mock_serial_instance = mock_serial_class.return_value
        mock_serial_instance.is_open = True
        mock_serial_instance.write.return_value = 10
        mock_serial_instance.read.return_value = b"response"
        
        manager = SerialManager(serial_config_default)
        
        # Act - 模拟完整的使用流程
        # 1. 打开串口
        assert manager.open() == True
        
        # 2. 发送数据
        send_success = manager.write(b"command123")
        assert send_success == True
        
        # 3. 读取响应
        response = manager.read(8)
        assert response == b"response"
        
        # 4. 关闭串口
        manager.close()
        assert manager.is_open == False
        
        # 验证整个流程的一致性 - 这里关注的是行为序列，而非具体调用
