import struct
from serial_file_transfer.core.frame_handler import FrameHandler
from serial_file_transfer.config.constants import SerialCommand


class FakeSerial:
    """模拟 serial.Serial, 每次 read 返回预定义分段数据"""

    def __init__(self, data: bytes, chunk_size: int = 50):
        self._buffer = bytearray(data)
        self.chunk_size = chunk_size
        # 模拟串口 timeout 行为: 一旦缓冲为空, read 返回空 bytes

    def read(self, size: int) -> bytes:  # noqa: D401
        if not self._buffer:
            return b""
        n = min(size, self.chunk_size, len(self._buffer))
        chunk = self._buffer[:n]
        del self._buffer[:n]
        return bytes(chunk)


def test_read_frame_large_payload():
    """FrameHandler.read_frame 能够在多次分段读取下组装完整帧"""
    seq_id = 0
    data_bytes = b"a" * 8192  # 大块数据
    payload = struct.pack("<H", seq_id) + data_bytes

    frame = FrameHandler.pack_frame(SerialCommand.SEND_DATA, payload)
    assert frame is not None

    fake_port = FakeSerial(frame, chunk_size=100)  # 每次最多100字节, 需要>3次才能读完

    cmd, data = FrameHandler.read_frame(fake_port, size=len(frame))  # type: ignore[arg-type]
    assert cmd == SerialCommand.SEND_DATA
    assert data == payload
