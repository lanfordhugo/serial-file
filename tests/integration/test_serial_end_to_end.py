"""
串口端到端集成测试
==================

使用测试配置文件进行端到端串口传输测试。
支持虚拟串口和真实硬件串口，对程序来说没有区别。

配置文件：tests/integration/serial_config.yaml
"""

import threading
from pathlib import Path

import pytest

from serial_file_transfer.config.config_loader import ConfigLoader
from serial_file_transfer.core.serial_manager import SerialManager
from serial_file_transfer.transfer.sender import FileSender
from serial_file_transfer.transfer.receiver import FileReceiver


@pytest.mark.integration
def test_end_to_end_serial_transfer(temp_dir, test_file_large):
    """
    端到端串口传输测试
    
    设计要点：
    - 使用测试配置文件中的串口参数
    - 启动接收端线程，再在主线程发起发送
    - 验证文件内容一致性
    - 支持虚拟串口和真实硬件串口
    
    注意：需要配置文件中指定的串口对可用（如COM7<->COM8）
    """
    
    # 使用测试配置文件路径
    config_path = str(Path(__file__).parent / "serial_config.yaml")
    
    # 从测试配置文件加载串口端口信息
    config_data = ConfigLoader.load_config(config_path)
    port_config = config_data.get('serial_ports', {})
    sender_port = port_config.get('sender_port', 'COM7')
    receiver_port = port_config.get('receiver_port', 'COM8')
    
    # 使用配置加载器创建配置
    sender_config = ConfigLoader.create_serial_config(sender_port, config_path)
    receiver_config = ConfigLoader.create_serial_config(receiver_port, config_path)
    transfer_config = ConfigLoader.create_transfer_config(config_path)
    
    # 集成测试显示进度
    transfer_config.show_progress = True
    
    # 创建串口管理器
    sender_mgr = SerialManager(sender_config)
    receiver_mgr = SerialManager(receiver_config)
    
    # 构造收发器
    save_path = Path(temp_dir) / "received.txt"
    sender = FileSender(sender_mgr, test_file_large, transfer_config)
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
