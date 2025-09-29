"""
文件名称: test_folder_transfer_end_to_end.py
内容摘要: 文件夹传输端到端集成测试
当前版本: v1.0.0
作者: AI Assistant
创建日期: 2025-09-29
"""

import threading
import time
from pathlib import Path
import tempfile
import shutil

import pytest

from serial_file_transfer.config.config_loader import ConfigLoader
from serial_file_transfer.core.serial_manager import SerialManager
from serial_file_transfer.transfer.file_manager import SenderFileManager, ReceiverFileManager


@pytest.mark.integration
def test_end_to_end_folder_transfer():
    """
    端到端文件夹传输测试
    
    测试场景：
    - 创建包含多个文件的测试文件夹
    - 使用SenderFileManager发送文件夹
    - 使用ReceiverFileManager接收文件夹
    - 验证所有文件内容一致性和目录结构
    
    注意：需要配置文件中指定的串口对可用（如COM7<->COM8）
    """
    
    # 使用测试配置文件路径
    config_path = str(Path(__file__).parent / "serial_config.yaml")
    
    # 从测试配置文件加载串口端口信息
    config_data = ConfigLoader.load_config(config_path)
    port_config = config_data.get('serial_ports', {})
    sender_port = port_config.get('sender_port', 'COM7')
    receiver_port = port_config.get('receiver_port', 'COM8')
    
    # 创建测试文件夹结构
    with tempfile.TemporaryDirectory() as temp_base:
        # 发送端测试文件夹
        send_folder = Path(temp_base) / "send_folder"
        send_folder.mkdir()
        
        # 创建测试文件和子目录
        (send_folder / "file1.txt").write_text("测试文件1的内容", encoding='utf-8')
        (send_folder / "file2.txt").write_text("测试文件2的内容\n第二行内容", encoding='utf-8')
        
        # 创建子目录
        sub_dir = send_folder / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file3.txt").write_text("子目录文件内容", encoding='utf-8')
        
        # 创建二进制文件
        binary_data = bytes(range(256))  # 0-255的字节序列
        (send_folder / "binary.dat").write_bytes(binary_data)
        
        # 接收端目录
        recv_folder = Path(temp_base) / "recv_folder"
        recv_folder.mkdir()
        
        # 使用配置加载器创建配置
        sender_config = ConfigLoader.create_serial_config(sender_port, config_path)
        receiver_config = ConfigLoader.create_serial_config(receiver_port, config_path)
        transfer_config = ConfigLoader.create_transfer_config(config_path)
        
        # 集成测试显示进度
        transfer_config.show_progress = True
        
        # 创建串口管理器
        sender_mgr = SerialManager(sender_config)
        receiver_mgr = SerialManager(receiver_config)
        
        # 构造收发管理器
        sender_manager = SenderFileManager(send_folder, sender_mgr, transfer_config)
        receiver_manager = ReceiverFileManager(recv_folder, receiver_mgr, transfer_config)
        
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
                    recv_result["ok"] = receiver_manager.start_batch_receive()
                except Exception as e:
                    recv_result["error"] = str(e)
            
            t_recv = threading.Thread(target=_run_receiver, daemon=True)
            t_recv.start()
            
            # 给接收端一点时间启动
            time.sleep(0.2)
            
            send_ok = sender_manager.start_batch_send()
            t_recv.join(timeout=30.0)  # 增加超时时间以适应多文件传输
            
            # Assert - 验证结果
            if recv_result["error"]:
                pytest.fail(f"接收端出现异常: {recv_result['error']}")
            
            assert send_ok is True, "发送端应返回成功"
            assert recv_result["ok"] is True, "接收端应返回成功"
            
            # 验证文件结构和内容
            _verify_folder_structure_and_content(send_folder, recv_folder)
            
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


def _verify_folder_structure_and_content(original_folder: Path, received_folder: Path):
    """
    验证接收的文件夹结构和内容与原始文件夹一致
    
    Args:
        original_folder: 原始文件夹路径
        received_folder: 接收的文件夹路径
    """
    # 获取所有原始文件的相对路径
    original_files = []
    for file_path in original_folder.rglob("*"):
        if file_path.is_file():
            relative_path = file_path.relative_to(original_folder)
            original_files.append(relative_path)
    
    # 验证接收的文件数量
    received_files = []
    for file_path in received_folder.rglob("*"):
        if file_path.is_file():
            relative_path = file_path.relative_to(received_folder)
            received_files.append(relative_path)
    
    # 确保文件数量一致
    assert len(original_files) == len(received_files), f"文件数量不一致: 原始={len(original_files)}, 接收={len(received_files)}"
    
    # 验证每个文件的内容
    for relative_path in original_files:
        original_file = original_folder / relative_path
        received_file = received_folder / relative_path
        
        assert received_file.exists(), f"文件 {relative_path} 未被接收"
        
        # 比较文件内容
        original_content = original_file.read_bytes()
        received_content = received_file.read_bytes()
        
        assert original_content == received_content, f"文件 {relative_path} 内容不一致"
    
    print(f"✅ 验证通过：{len(original_files)} 个文件内容和结构完全一致")


@pytest.mark.integration
def test_folder_transfer_with_empty_files():
    """测试包含空文件的文件夹传输"""
    
    config_path = str(Path(__file__).parent / "serial_config.yaml")
    config_data = ConfigLoader.load_config(config_path)
    port_config = config_data.get('serial_ports', {})
    sender_port = port_config.get('sender_port', 'COM7')
    receiver_port = port_config.get('receiver_port', 'COM8')
    
    with tempfile.TemporaryDirectory() as temp_base:
        # 创建包含空文件的测试文件夹
        send_folder = Path(temp_base) / "send_folder"
        send_folder.mkdir()
        
        # 创建空文件
        (send_folder / "empty.txt").touch()
        # 创建正常文件
        (send_folder / "normal.txt").write_text("正常文件内容")
        
        recv_folder = Path(temp_base) / "recv_folder"
        recv_folder.mkdir()
        
        sender_config = ConfigLoader.create_serial_config(sender_port, config_path)
        receiver_config = ConfigLoader.create_serial_config(receiver_port, config_path)
        transfer_config = ConfigLoader.create_transfer_config(config_path)
        
        sender_mgr = SerialManager(sender_config)
        receiver_mgr = SerialManager(receiver_config)
        
        sender_manager = SenderFileManager(send_folder, sender_mgr, transfer_config)
        receiver_manager = ReceiverFileManager(recv_folder, receiver_mgr, transfer_config)
        
        try:
            if not sender_mgr.open():
                pytest.skip(f"无法打开发送端串口: {sender_config.port}")
            
            if not receiver_mgr.open():
                sender_mgr.close()
                pytest.skip(f"无法打开接收端串口: {receiver_config.port}")
            
            recv_result = {"ok": False, "error": None}
            
            def _run_receiver():
                try:
                    recv_result["ok"] = receiver_manager.start_batch_receive()
                except Exception as e:
                    recv_result["error"] = str(e)
            
            t_recv = threading.Thread(target=_run_receiver, daemon=True)
            t_recv.start()
            
            time.sleep(0.1)
            
            send_ok = sender_manager.start_batch_send()
            t_recv.join(timeout=15.0)
            
            if recv_result["error"]:
                pytest.fail(f"接收端出现异常: {recv_result['error']}")
            
            assert send_ok is True
            assert recv_result["ok"] is True
            
            # 验证空文件和正常文件都被正确传输
            empty_file = recv_folder / "empty.txt"
            normal_file = recv_folder / "normal.txt"
            
            assert empty_file.exists()
            assert empty_file.stat().st_size == 0
            assert normal_file.exists()
            assert normal_file.read_text() == "正常文件内容"
            
        finally:
            try:
                sender_mgr.close()
            except:
                pass
            try:
                receiver_mgr.close()
            except:
                pass


@pytest.mark.integration
def test_folder_transfer_large_files():
    """测试包含大文件的文件夹传输"""
    
    config_path = str(Path(__file__).parent / "serial_config.yaml")
    config_data = ConfigLoader.load_config(config_path)
    port_config = config_data.get('serial_ports', {})
    sender_port = port_config.get('sender_port', 'COM7')
    receiver_port = port_config.get('receiver_port', 'COM8')
    
    with tempfile.TemporaryDirectory() as temp_base:
        send_folder = Path(temp_base) / "send_folder"
        send_folder.mkdir()
        
        # 创建较大的文件 (100KB)
        large_content = "大文件内容测试\n" * 5000  # 约100KB
        (send_folder / "large.txt").write_text(large_content, encoding='utf-8')
        
        # 创建小文件
        (send_folder / "small.txt").write_text("小文件")
        
        recv_folder = Path(temp_base) / "recv_folder"
        recv_folder.mkdir()
        
        sender_config = ConfigLoader.create_serial_config(sender_port, config_path)
        receiver_config = ConfigLoader.create_serial_config(receiver_port, config_path)
        transfer_config = ConfigLoader.create_transfer_config(config_path)
        
        # 调整超时以适应大文件传输
        transfer_config.request_timeout = 60
        transfer_config.data_timeout = 30
        
        sender_mgr = SerialManager(sender_config)
        receiver_mgr = SerialManager(receiver_config)
        
        sender_manager = SenderFileManager(send_folder, sender_mgr, transfer_config)
        receiver_manager = ReceiverFileManager(recv_folder, receiver_mgr, transfer_config)
        
        try:
            if not sender_mgr.open():
                pytest.skip(f"无法打开发送端串口: {sender_config.port}")
            
            if not receiver_mgr.open():
                sender_mgr.close()
                pytest.skip(f"无法打开接收端串口: {receiver_config.port}")
            
            recv_result = {"ok": False, "error": None}
            
            def _run_receiver():
                try:
                    recv_result["ok"] = receiver_manager.start_batch_receive()
                except Exception as e:
                    recv_result["error"] = str(e)
            
            t_recv = threading.Thread(target=_run_receiver, daemon=True)
            t_recv.start()
            
            time.sleep(0.1)
            
            send_ok = sender_manager.start_batch_send()
            t_recv.join(timeout=90.0)  # 增加超时时间适应大文件传输
            
            if recv_result["error"]:
                pytest.fail(f"接收端出现异常: {recv_result['error']}")
            
            assert send_ok is True
            assert recv_result["ok"] is True
            
            # 验证大文件和小文件内容
            _verify_folder_structure_and_content(send_folder, recv_folder)
            
        finally:
            try:
                sender_mgr.close()
            except:
                pass
            try:
                receiver_mgr.close()
            except:
                pass
