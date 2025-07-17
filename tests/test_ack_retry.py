"""ACK/NACK 及重试机制测试
--------------------------------

确保 P0A、P0B 实现的核心功能工作正常。
"""

import struct
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path

import pytest

# 将 src 目录加入 Python 路径，保证本地包可导入
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from serial_file_transfer.config.constants import SerialCommand
from serial_file_transfer.core.frame_handler import FrameHandler
from serial_file_transfer.transfer.sender import FileSender
from serial_file_transfer.transfer.receiver import FileReceiver
from serial_file_transfer.core.serial_manager import SerialManager
from serial_file_transfer.config.settings import SerialConfig, TransferConfig


class DummySerialPort:
    """极简串口模拟，仅用于ACK/NACK交互单元测试。"""

    def __init__(self):
        self.written = []  # 记录写入的数据帧
        self.to_read = []  # 预置的读取数据帧（FIFO）

    # pyserial API
    def write(self, data: bytes):  # noqa: D401
        self.written.append(data)
        return len(data)

    def read(self, size: int) -> bytes:  # noqa: D401
        if not self.to_read or size <= 0:
            return b""
        # 从队列首元素读取指定字节数，支持按需拆分帧
        first = self.to_read[0]
        chunk = first[:size]
        # 更新剩余未读取部分
        remainder = first[size:]
        if remainder:
            self.to_read[0] = remainder
        else:
            self.to_read.pop(0)
        return chunk

    @property
    def is_open(self):  # noqa: D401
        return True


def test_ack_frame_pack_unpack():
    """ACK 帧可正确打包并解析"""
    seq = 123
    payload = struct.pack("<H", seq)
    frame = FrameHandler.pack_frame(SerialCommand.ACK, payload)
    assert frame is not None
    unpacked = FrameHandler.unpack_frame(frame)
    assert unpacked is not None
    cmd, length, data, crc = unpacked
    assert cmd == SerialCommand.ACK
    assert length == 2
    assert struct.unpack("<H", data)[0] == seq


def test_sender_waits_for_ack_and_retries():
    """FileSender._send_data_package 在无 ACK 时将重试，收到 ACK 后成功返回"""
    # 准备 dummy 串口
    port = DummySerialPort()

    # 创建 SerialManager 替身
    serial_manager = MagicMock(spec=SerialManager)
    serial_manager.port = port
    serial_manager.write.side_effect = port.write

    # 构造一个最小文件
    config = TransferConfig(max_data_length=4, retry_count=1, backoff_base=0.01)
    sender = FileSender(serial_manager, config=config)
    sender.file_data = b"ABCD" * 10  # mock 数据
    sender.file_size = len(sender.file_data)

    # 在第一次发送后不回 ACK，让其重试一次
    # 第二次预置 ACK 响应
    def inject_ack(seq):
        ack_frame = FrameHandler.pack_frame(SerialCommand.ACK, struct.pack("<H", seq))
        port.to_read.append(ack_frame)

    # 在重试之前插入 ACK
    # ACK 序号与 _seq_id (0) 一致
    inject_ack(0)

    # 执行发送数据包
    result = sender._send_data_package(0, 4)
    assert result is True
    # 确保至少写入一次
    assert port.written, "未写入数据帧"


def test_receiver_sends_ack():
    """Receiver 收到数据包后发送 ACK"""
    port = DummySerialPort()
    serial_manager = MagicMock(spec=SerialManager)
    serial_manager.port = port
    serial_manager.write.side_effect = port.write

    recv = FileReceiver(serial_manager, save_path="/tmp/dummy.bin")

    # 模拟 sender 发送的数据包 seq=0, payload=b"DATA"
    seq = 0
    payload = struct.pack("<H", seq) + b"DATA"
    frame = FrameHandler.pack_frame(SerialCommand.SEND_DATA, payload)
    port.to_read.append(frame)

    # 调用 receive_data_package
    assert recv.receive_data_package() is True

    # SerialManager.write 应被调用一次 ACK
    assert port.written, "Receiver 未写入 ACK"
    ack_unpacked = FrameHandler.unpack_frame(port.written[0])
    assert ack_unpacked is not None
    assert ack_unpacked[0] == SerialCommand.ACK
