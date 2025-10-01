"""
文件名称: test_end_to_end.py
内容摘要: 串口文件传输端到端集成测试（合并版）
当前版本: v1.0.0
作者: AI Assistant
创建日期: 2025-10-01

集成测试说明：
- 测试单文件传输和文件夹批量传输
- 支持虚拟串口和真实硬件串口
- 使用测试配置文件：tests/integration/serial_config.yaml
- 所有测试都标记为 @pytest.mark.integration

注意事项：
- 需要配置文件中指定的串口对可用（如COM11<->COM12）
- 集成测试默认不在常规测试中执行
- 运行方式：pytest -m integration tests/integration/test_end_to_end.py
"""

import threading
import time
from pathlib import Path
import tempfile

import pytest

from serial_file_transfer.config.config_loader import ConfigLoader
from serial_file_transfer.core.serial_manager import SerialManager
from serial_file_transfer.transfer.sender import FileSender
from serial_file_transfer.transfer.receiver import FileReceiver
from serial_file_transfer.transfer.file_manager import (
    SenderFileManager,
    ReceiverFileManager,
)


# ==================== 测试辅助函数 ====================


def _get_test_serial_configs(config_path: str) -> tuple[str, str]:
    """
    从测试配置文件获取串口端口配置
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        (sender_port, receiver_port) 元组
    """
    config_data = ConfigLoader.load_config(config_path)
    port_config = config_data.get("serial_ports", {})
    sender_port = port_config.get("sender_port", "COM7")
    receiver_port = port_config.get("receiver_port", "COM8")
    return sender_port, receiver_port


def _execute_transfer_with_threading(
    sender_manager,
    receiver_manager,
    sender_method: str = "start_transfer",
    receiver_method: str = "start_transfer",
    timeout: float = 30.0,
    startup_delay: float = 0.1,
) -> tuple[bool, bool, str | None]:
    """
    在多线程环境中执行传输操作
    
    Args:
        sender_manager: 发送端管理器
        receiver_manager: 接收端管理器
        sender_method: 发送端方法名（默认 start_transfer）
        receiver_method: 接收端方法名（默认 start_transfer）
        timeout: 超时时间（秒）
        startup_delay: 接收端启动延迟（秒）
        
    Returns:
        (send_ok, recv_ok, error_msg) 元组
    """
    recv_result = {"ok": False, "error": None}

    def _run_receiver():
        try:
            method = getattr(receiver_manager, receiver_method)
            recv_result["ok"] = method()
        except Exception as e:
            recv_result["error"] = str(e)

    # 启动接收端线程
    t_recv = threading.Thread(target=_run_receiver, daemon=True)
    t_recv.start()

    # 给接收端启动时间
    time.sleep(startup_delay)

    # 在主线程执行发送
    send_method = getattr(sender_manager, sender_method)
    send_ok = send_method()

    # 等待接收端完成
    t_recv.join(timeout=timeout)

    return send_ok, recv_result["ok"], recv_result["error"]


def _verify_folder_structure_and_content(
    original_folder: Path, received_folder: Path
):
    """
    验证接收的文件夹结构和内容与原始文件夹一致
    
    Args:
        original_folder: 原始文件夹路径
        received_folder: 接收的文件夹路径
        
    Raises:
        AssertionError: 当文件数量或内容不一致时
    """
    # 获取所有原始文件的相对路径
    original_files = []
    for file_path in original_folder.rglob("*"):
        if file_path.is_file():
            relative_path = file_path.relative_to(original_folder)
            original_files.append(relative_path)

    # 获取所有接收文件的相对路径
    received_files = []
    for file_path in received_folder.rglob("*"):
        if file_path.is_file():
            relative_path = file_path.relative_to(received_folder)
            received_files.append(relative_path)

    # 验证文件数量一致
    assert len(original_files) == len(received_files), (
        f"文件数量不一致: 原始={len(original_files)}, "
        f"接收={len(received_files)}"
    )

    # 验证每个文件的内容
    for relative_path in original_files:
        original_file = original_folder / relative_path
        received_file = received_folder / relative_path

        assert received_file.exists(), f"文件 {relative_path} 未被接收"

        # 比较文件内容
        original_content = original_file.read_bytes()
        received_content = received_file.read_bytes()

        assert original_content == received_content, (
            f"文件 {relative_path} 内容不一致"
        )

    print(f"✅ 验证通过：{len(original_files)} 个文件内容和结构完全一致")


class SerialManagerContextManager:
    """串口管理器上下文管理器，确保串口正确关闭"""

    def __init__(self, sender_mgr: SerialManager, receiver_mgr: SerialManager):
        self.sender_mgr = sender_mgr
        self.receiver_mgr = receiver_mgr
        self.sender_opened = False
        self.receiver_opened = False

    def __enter__(self):
        """打开串口"""
        if not self.sender_mgr.open():
            pytest.skip(f"无法打开发送端串口: {self.sender_mgr.config.port}")
        self.sender_opened = True

        if not self.receiver_mgr.open():
            pytest.skip(f"无法打开接收端串口: {self.receiver_mgr.config.port}")
        self.receiver_opened = True

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """关闭串口"""
        if self.sender_opened:
            try:
                self.sender_mgr.close()
            except Exception:
                pass

        if self.receiver_opened:
            try:
                self.receiver_mgr.close()
            except Exception:
                pass


# ==================== 单文件传输测试 ====================


@pytest.mark.integration
def test_single_file_transfer(temp_dir, test_file_large):
    """
    端到端单文件串口传输测试
    
    测试场景：
    - 使用测试配置文件中的串口参数
    - 传输1MB大小的测试文件
    - 验证文件内容一致性
    - 支持虚拟串口和真实硬件串口
    
    注意：需要配置文件中指定的串口对可用
    """
    # 获取配置文件路径
    config_path = str(Path(__file__).parent / "serial_config.yaml")

    # 获取串口端口配置
    sender_port, receiver_port = _get_test_serial_configs(config_path)

    # 创建配置
    sender_config = ConfigLoader.create_serial_config(sender_port, config_path)
    receiver_config = ConfigLoader.create_serial_config(receiver_port, config_path)
    transfer_config = ConfigLoader.create_transfer_config(config_path)

    # 集成测试显示进度
    transfer_config.show_progress = True

    # 创建串口管理器
    sender_mgr = SerialManager(sender_config)
    receiver_mgr = SerialManager(receiver_config)

    # 创建收发器
    save_path = Path(temp_dir) / "received.txt"
    sender = FileSender(sender_mgr, test_file_large, transfer_config)
    receiver = FileReceiver(receiver_mgr, save_path, transfer_config)

    # 执行传输
    with SerialManagerContextManager(sender_mgr, receiver_mgr):
        send_ok, recv_ok, error = _execute_transfer_with_threading(
            sender, receiver, timeout=15.0
        )

        # 验证结果
        if error:
            pytest.fail(f"接收端出现异常: {error}")

        assert send_ok is True, "发送端应返回成功"
        assert recv_ok is True, "接收端应返回成功"
        assert save_path.exists(), "应生成接收文件"
        assert save_path.read_bytes() == Path(test_file_large).read_bytes(), (
            "接收内容应与原文件一致"
        )


# ==================== 文件夹传输测试 ====================


@pytest.mark.integration
def test_folder_transfer_multi_files():
    """
    端到端文件夹传输测试（多文件）
    
    测试场景：
    - 创建包含多个文件和子目录的测试文件夹
    - 包含文本文件、二进制文件和子目录
    - 验证所有文件内容一致性和目录结构
    """
    config_path = str(Path(__file__).parent / "serial_config.yaml")
    sender_port, receiver_port = _get_test_serial_configs(config_path)

    with tempfile.TemporaryDirectory() as temp_base:
        # 创建发送端测试文件夹
        send_folder = Path(temp_base) / "send_folder"
        send_folder.mkdir()

        # 创建测试文件和子目录
        (send_folder / "file1.txt").write_text(
            "测试文件1的内容", encoding="utf-8"
        )
        (send_folder / "file2.txt").write_text(
            "测试文件2的内容\n第二行内容", encoding="utf-8"
        )

        # 创建子目录
        sub_dir = send_folder / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file3.txt").write_text("子目录文件内容", encoding="utf-8")

        # 创建二进制文件
        binary_data = bytes(range(256))  # 0-255的字节序列
        (send_folder / "binary.dat").write_bytes(binary_data)

        # 创建接收端目录
        recv_folder = Path(temp_base) / "recv_folder"
        recv_folder.mkdir()

        # 创建配置
        sender_config = ConfigLoader.create_serial_config(sender_port, config_path)
        receiver_config = ConfigLoader.create_serial_config(
            receiver_port, config_path
        )
        transfer_config = ConfigLoader.create_transfer_config(config_path)
        transfer_config.show_progress = True

        # 创建串口管理器和文件管理器
        sender_mgr = SerialManager(sender_config)
        receiver_mgr = SerialManager(receiver_config)

        sender_manager = SenderFileManager(
            send_folder, sender_mgr, transfer_config
        )
        receiver_manager = ReceiverFileManager(
            recv_folder, receiver_mgr, transfer_config
        )

        # 执行传输
        with SerialManagerContextManager(sender_mgr, receiver_mgr):
            send_ok, recv_ok, error = _execute_transfer_with_threading(
                sender_manager,
                receiver_manager,
                sender_method="start_batch_send",
                receiver_method="start_batch_receive",
                timeout=30.0,
                startup_delay=0.2,
            )

            # 验证结果
            if error:
                pytest.fail(f"接收端出现异常: {error}")

            assert send_ok is True, "发送端应返回成功"
            assert recv_ok is True, "接收端应返回成功"

            # 验证文件结构和内容
            _verify_folder_structure_and_content(send_folder, recv_folder)


@pytest.mark.integration
@pytest.mark.xfail(reason="空文件传输存在已知bug: 发送端拒绝发送空文件")
def test_folder_transfer_empty_files():
    """
    文件夹传输测试（包含空文件）
    
    测试场景：
    - 测试空文件的正确处理
    - 混合空文件和正常文件
    - 验证空文件也能正确传输
    
    注意：当前版本存在已知bug，空文件传输失败
    """
    config_path = str(Path(__file__).parent / "serial_config.yaml")
    sender_port, receiver_port = _get_test_serial_configs(config_path)

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

        # 创建配置和管理器
        sender_config = ConfigLoader.create_serial_config(sender_port, config_path)
        receiver_config = ConfigLoader.create_serial_config(
            receiver_port, config_path
        )
        transfer_config = ConfigLoader.create_transfer_config(config_path)

        sender_mgr = SerialManager(sender_config)
        receiver_mgr = SerialManager(receiver_config)

        sender_manager = SenderFileManager(
            send_folder, sender_mgr, transfer_config
        )
        receiver_manager = ReceiverFileManager(
            recv_folder, receiver_mgr, transfer_config
        )

        # 执行传输
        with SerialManagerContextManager(sender_mgr, receiver_mgr):
            send_ok, recv_ok, error = _execute_transfer_with_threading(
                sender_manager,
                receiver_manager,
                sender_method="start_batch_send",
                receiver_method="start_batch_receive",
                timeout=15.0,
            )

            # 验证结果
            if error:
                pytest.fail(f"接收端出现异常: {error}")

            assert send_ok is True, "发送端应返回成功"
            assert recv_ok is True, "接收端应返回成功"

            # 验证空文件和正常文件都被正确传输
            empty_file = recv_folder / "empty.txt"
            normal_file = recv_folder / "normal.txt"

            assert empty_file.exists(), "空文件应被正确接收"
            assert empty_file.stat().st_size == 0, "空文件大小应为0"
            assert normal_file.exists(), "正常文件应被正确接收"
            assert normal_file.read_text() == "正常文件内容", (
                "正常文件内容应一致"
            )


@pytest.mark.integration
@pytest.mark.slow
def test_folder_transfer_large_files():
    """
    文件夹传输测试（包含大文件）
    
    测试场景：
    - 测试包含大文件（100KB）的文件夹传输
    - 混合大文件和小文件
    - 验证大文件传输的稳定性
    
    注意：此测试标记为 @pytest.mark.slow，因为传输时间较长
    """
    config_path = str(Path(__file__).parent / "serial_config.yaml")
    sender_port, receiver_port = _get_test_serial_configs(config_path)

    with tempfile.TemporaryDirectory() as temp_base:
        send_folder = Path(temp_base) / "send_folder"
        send_folder.mkdir()

        # 创建较大的文件 (100KB)
        large_content = "大文件内容测试\n" * 5000  # 约100KB
        (send_folder / "large.txt").write_text(large_content, encoding="utf-8")

        # 创建小文件
        (send_folder / "small.txt").write_text("小文件")

        recv_folder = Path(temp_base) / "recv_folder"
        recv_folder.mkdir()

        # 创建配置和管理器
        sender_config = ConfigLoader.create_serial_config(sender_port, config_path)
        receiver_config = ConfigLoader.create_serial_config(
            receiver_port, config_path
        )
        transfer_config = ConfigLoader.create_transfer_config(config_path)

        # 调整超时以适应大文件传输
        transfer_config.request_timeout = 60
        transfer_config.data_timeout = 30

        sender_mgr = SerialManager(sender_config)
        receiver_mgr = SerialManager(receiver_config)

        sender_manager = SenderFileManager(
            send_folder, sender_mgr, transfer_config
        )
        receiver_manager = ReceiverFileManager(
            recv_folder, receiver_mgr, transfer_config
        )

        # 执行传输
        with SerialManagerContextManager(sender_mgr, receiver_mgr):
            send_ok, recv_ok, error = _execute_transfer_with_threading(
                sender_manager,
                receiver_manager,
                sender_method="start_batch_send",
                receiver_method="start_batch_receive",
                timeout=90.0,  # 增加超时时间适应大文件传输
            )

            # 验证结果
            if error:
                pytest.fail(f"接收端出现异常: {error}")

            assert send_ok is True, "发送端应返回成功"
            assert recv_ok is True, "接收端应返回成功"

            # 验证大文件和小文件内容
            _verify_folder_structure_and_content(send_folder, recv_folder)

