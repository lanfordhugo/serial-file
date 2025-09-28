"""
串口端到端集成测试
==================

支持两种模式：
1. 虚拟串口模式（默认）：使用 pyserial 的 socket:// 虚拟串口对
2. 真实硬件模式：使用配置文件中的真实串口进行测试

配置文件：tests/integration/serial_config.yaml
"""

import threading
from pathlib import Path
import yaml

import pytest
import serial

from serial_file_transfer.config.settings import SerialConfig, TransferConfig
from serial_file_transfer.core.serial_manager import SerialManager
from serial_file_transfer.transfer.sender import FileSender
from serial_file_transfer.transfer.receiver import FileReceiver


def _load_serial_config():
    """加载串口配置文件。"""
    config_path = Path(__file__).parent / "serial_config.yaml"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        pytest.skip(f"配置文件不存在: {config_path}")
    except Exception as e:
        pytest.skip(f"加载配置文件失败: {e}")


def _create_serial_configs_from_yaml(config_data):
    """从YAML配置创建SerialConfig对象。"""
    serial_params = config_data.get('serial_params', {})
    
    # 处理校验位字符串到pyserial常量的转换
    parity_map = {
        'none': serial.PARITY_NONE,
        'even': serial.PARITY_EVEN,
        'odd': serial.PARITY_ODD
    }
    
    parity_str = serial_params.get('parity', 'none').lower()
    parity = parity_map.get(parity_str, serial.PARITY_NONE)
    
    sender_config = SerialConfig(
        port=config_data['serial_ports']['sender_port'],
        baudrate=serial_params.get('baudrate', 115200),
        bytesize=serial_params.get('bytesize', 8),
        parity=parity,
        stopbits=serial_params.get('stopbits', 1),
        timeout=serial_params.get('timeout', 0.5)
    )
    
    receiver_config = SerialConfig(
        port=config_data['serial_ports']['receiver_port'],
        baudrate=serial_params.get('baudrate', 115200),
        bytesize=serial_params.get('bytesize', 8),
        parity=parity,
        stopbits=serial_params.get('stopbits', 1),
        timeout=serial_params.get('timeout', 0.5)
    )
    
    return sender_config, receiver_config


def _create_transfer_config_from_yaml(config_data):
    """从YAML配置创建TransferConfig对象。"""
    transfer_params = config_data.get('transfer_config', {})
    
    return TransferConfig(
        max_data_length=transfer_params.get('max_data_length', 1024),
        request_timeout=transfer_params.get('request_timeout', 2.0),
        retry_count=transfer_params.get('retry_count', 3),
        show_progress=transfer_params.get('show_progress', False)
    )


@pytest.mark.integration
def test_end_to_end_virtual_serial_transfer(temp_dir, test_file_large):
    """
    端到端虚拟串口测试：使用外部虚拟串口软件创建的COM端口对进行真实协议交互。
    
    设计要点：
    - 使用外部虚拟串口（如COM7<->COM8）进行测试
    - 按照真实串口的方式使用SerialManager
    - 启动接收端线程，再在主线程发起发送，最终校验文件内容一致
    
    注意：需要外部虚拟串口软件创建COM端口对，或修改配置文件指定可用端口
    """
    
    # 加载配置获取虚拟串口号
    config_data = _load_serial_config()
    
    # 创建串口配置（使用配置文件中的端口，但允许测试失败时跳过）
    sender_config, receiver_config = _create_serial_configs_from_yaml(config_data)
    
    # 传输配置：适中块大小+合理超时，显示进度信息
    # 注意：max_data_length不能超过FrameHandler的硬编码限制1536字节
    transfer_cfg = TransferConfig(
        max_data_length=1024,  # 使用安全的块大小，避免超出FrameHandler限制
        request_timeout=2.0,   # 增加超时时间
        retry_count=3,
        show_progress=True,    # 集成测试显示进度
    )
    
    # 创建串口管理器
    sender_mgr = SerialManager(sender_config)
    receiver_mgr = SerialManager(receiver_config)
    
    # 构造收发器
    save_path = Path(temp_dir) / "received.txt"
    sender = FileSender(sender_mgr, test_file_large, transfer_cfg)
    receiver = FileReceiver(receiver_mgr, save_path, transfer_cfg)
    
    # 尝试打开虚拟串口
    try:
        if not sender_mgr.open():
            pytest.skip(f"无法打开发送端虚拟串口: {sender_config.port}")
        
        if not receiver_mgr.open():
            sender_mgr.close()
            pytest.skip(f"无法打开接收端虚拟串口: {receiver_config.port}")
        
        # Act - 并发执行：接收在子线程，发送在主线程
        recv_result = {"ok": False, "error": None}
        
        def _run_receiver():
            try:
                recv_result["ok"] = receiver.start_transfer()
            except Exception as e:
                recv_result["error"] = str(e)
        
        t_recv = threading.Thread(target=_run_receiver, daemon=True)
        t_recv.start()
        
        # 给接收端一点时间启动
        import time
        time.sleep(0.1)
        
        send_ok = sender.start_transfer()
        t_recv.join(timeout=15.0)  # 增加超时时间以适应1M文件传输
        
        # Assert - 验证结果与内容一致性
        if recv_result["error"]:
            pytest.fail(f"接收端出现异常: {recv_result['error']}")
        
        assert send_ok is True, "发送端应返回成功"
        assert recv_result["ok"] is True, "接收端应返回成功"
        assert save_path.exists(), "应生成接收文件"
        assert save_path.read_bytes() == Path(test_file_large).read_bytes(), "接收内容应与原文件一致"
        
    finally:
        # 确保串口被关闭
        try:
            sender_mgr.close()
        except:
            pass
        try:
            receiver_mgr.close()
        except:
            pass


@pytest.mark.integration
@pytest.mark.hardware
def test_end_to_end_hardware_serial_transfer(temp_dir, test_file_small):
    """
    端到端硬件串口测试：使用配置文件中的真实串口进行文件传输测试。
    
    注意：需要硬件连接 COM7 <-> COM8，且配置文件中 enable_hardware_test: true
    """
    
    # 加载配置
    config_data = _load_serial_config()
    
    # 检查是否启用硬件测试
    test_config = config_data.get('test_config', {})
    if not test_config.get('enable_hardware_test', False):
        pytest.skip("硬件测试已禁用，请在 serial_config.yaml 中设置 enable_hardware_test: true")
    
    # 检查测试文件大小限制
    max_file_size = test_config.get('max_test_file_size', 10240)
    if test_file_small.stat().st_size > max_file_size:
        pytest.skip(f"测试文件过大 ({test_file_small.stat().st_size} > {max_file_size} 字节)")
    
    # 创建串口配置
    sender_config, receiver_config = _create_serial_configs_from_yaml(config_data)
    transfer_config = _create_transfer_config_from_yaml(config_data)
    # 硬件测试强制显示进度
    transfer_config.show_progress = True
    
    # 创建串口管理器
    sender_mgr = SerialManager(sender_config)
    receiver_mgr = SerialManager(receiver_config)
    
    # 构造收发器
    save_path = Path(temp_dir) / "received_hardware.txt"
    sender = FileSender(sender_mgr, test_file_small, transfer_config)
    receiver = FileReceiver(receiver_mgr, save_path, transfer_config)
    
    # 尝试打开串口
    try:
        if not sender_mgr.open():
            pytest.skip(f"无法打开发送端串口: {sender_config.port}")
        
        if not receiver_mgr.open():
            sender_mgr.close()
            pytest.skip(f"无法打开接收端串口: {receiver_config.port}")
        
        # Act - 并发执行：接收在子线程，发送在主线程
        recv_result = {"ok": False, "error": None}
        
        def _run_receiver():
            try:
                recv_result["ok"] = receiver.start_transfer()
            except Exception as e:
                recv_result["error"] = str(e)
        
        t_recv = threading.Thread(target=_run_receiver, daemon=True)
        t_recv.start()
        
        # 给接收端一点时间启动
        import time
        time.sleep(0.1)
        
        send_ok = sender.start_transfer()
        
        # 等待接收端完成
        hardware_timeout = test_config.get('hardware_test_timeout', 10.0)
        t_recv.join(timeout=hardware_timeout)
        
        # Assert - 验证结果与内容一致性
        if recv_result["error"]:
            pytest.fail(f"接收端出现异常: {recv_result['error']}")
        
        assert send_ok is True, "发送端应返回成功"
        assert recv_result["ok"] is True, "接收端应返回成功"
        assert save_path.exists(), "应生成接收文件"
        assert save_path.read_bytes() == Path(test_file_small).read_bytes(), "接收内容应与原文件一致"
        
    finally:
        # 确保串口被关闭
        try:
            sender_mgr.close()
        except:
            pass
        try:
            receiver_mgr.close()
        except:
            pass


