"""
串口传输抽象接口层
==================

提供串口传输的抽象接口，便于测试和模拟。
"""

from abc import ABC, abstractmethod
from typing import Optional
import serial


class SerialTransport(ABC):
    """串口传输抽象接口"""
    
    @abstractmethod
    def open(self) -> bool:
        """
        打开串口
        
        Returns:
            成功返回True，失败返回False
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """关闭串口"""
        pass
    
    @abstractmethod
    def write(self, data: bytes) -> bool:
        """
        写入数据
        
        Args:
            data: 要写入的数据
        
        Returns:
            成功返回True，失败返回False
        """
        pass
    
    @abstractmethod
    def read(self, size: int) -> bytes:
        """
        读取指定字节数的数据
        
        Args:
            size: 要读取的字节数
        
        Returns:
            读取到的数据
        """
        pass
    
    @abstractmethod
    def reset_input_buffer(self) -> None:
        """清空输入缓冲区"""
        pass
    
    @abstractmethod
    def reset_output_buffer(self) -> None:
        """清空输出缓冲区"""
        pass
    
    @property
    @abstractmethod
    def is_open(self) -> bool:
        """
        串口是否打开
        
        Returns:
            打开返回True，关闭返回False
        """
        pass


class RealSerialTransport(SerialTransport):
    """真实串口传输实现"""
    
    def __init__(self, port: str, baudrate: int, timeout: float = 0.1, **kwargs):
        """
        初始化真实串口传输
        
        Args:
            port: 串口号
            baudrate: 波特率
            timeout: 超时时间（秒）
            **kwargs: 其他串口参数
        """
        self._port: Optional[serial.Serial] = None
        self._port_name = port
        self._baudrate = baudrate
        self._timeout = timeout
        self._kwargs = kwargs
    
    def open(self) -> bool:
        """打开串口"""
        try:
            self._port = serial.Serial(
                port=self._port_name,
                baudrate=self._baudrate,
                timeout=self._timeout,
                **self._kwargs
            )
            return True
        except Exception:
            return False
    
    def close(self) -> None:
        """关闭串口"""
        if self._port and self._port.is_open:
            self._port.close()
    
    def write(self, data: bytes) -> bool:
        """写入数据"""
        try:
            if self._port and self._port.is_open:
                self._port.write(data)
                return True
            return False
        except Exception:
            return False
    
    def read(self, size: int) -> bytes:
        """读取数据"""
        try:
            if self._port and self._port.is_open:
                return self._port.read(size)
            return b''
        except Exception:
            return b''
    
    def reset_input_buffer(self) -> None:
        """清空输入缓冲区"""
        if self._port and self._port.is_open:
            self._port.reset_input_buffer()
    
    def reset_output_buffer(self) -> None:
        """清空输出缓冲区"""
        if self._port and self._port.is_open:
            self._port.reset_output_buffer()
    
    @property
    def is_open(self) -> bool:
        """串口是否打开"""
        return self._port is not None and self._port.is_open
    
    @property
    def port(self) -> Optional[serial.Serial]:
        """获取底层串口对象（用于兼容旧代码）"""
        return self._port


class MockSerialTransport(SerialTransport):
    """模拟串口传输（用于测试）"""
    
    def __init__(self, ack_loss_rate: float = 0.0, crc_error_rate: float = 0.0):
        """
        初始化模拟串口传输
        
        Args:
            ack_loss_rate: ACK丢失率（0.0-1.0）
            crc_error_rate: CRC错误率（0.0-1.0）
        """
        import random
        
        self._is_open = False
        self._ack_loss_rate = ack_loss_rate
        self._crc_error_rate = crc_error_rate
        self._send_buffer = b''
        self._recv_buffer = b''
        self._send_count = 0
        self._retry_count = 0
        self._random = random
    
    def open(self) -> bool:
        """打开串口"""
        self._is_open = True
        return True
    
    def close(self) -> None:
        """关闭串口"""
        self._is_open = False
    
    def write(self, data: bytes) -> bool:
        """写入数据"""
        if not self._is_open:
            return False
        
        self._send_count += 1
        
        # 模拟CRC错误
        if self._random.random() < self._crc_error_rate:
            # 破坏CRC
            data = self._corrupt_crc(data)
        
        self._send_buffer += data
        return True
    
    def read(self, size: int) -> bytes:
        """读取数据"""
        if not self._is_open:
            return b''
        
        # 模拟ACK丢失
        if self._random.random() < self._ack_loss_rate:
            self._retry_count += 1
            return b''  # 模拟超时
        
        # 从接收缓冲区读取
        if len(self._recv_buffer) >= size:
            data = self._recv_buffer[:size]
            self._recv_buffer = self._recv_buffer[size:]
            return data
        else:
            # 不足时返回全部
            data = self._recv_buffer
            self._recv_buffer = b''
            return data
    
    def reset_input_buffer(self) -> None:
        """清空输入缓冲区"""
        self._recv_buffer = b''
    
    def reset_output_buffer(self) -> None:
        """清空输出缓冲区"""
        self._send_buffer = b''
    
    @property
    def is_open(self) -> bool:
        """串口是否打开"""
        return self._is_open
    
    def set_recv_data(self, data: bytes) -> None:
        """设置接收缓冲区数据（用于测试）"""
        self._recv_buffer += data
    
    def get_send_data(self) -> bytes:
        """获取发送缓冲区数据（用于测试）"""
        data = self._send_buffer
        self._send_buffer = b''
        return data
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'send_count': self._send_count,
            'retry_count': self._retry_count,
            'retry_rate': self._retry_count / self._send_count if self._send_count > 0 else 0
        }
    
    def _corrupt_crc(self, data: bytes) -> bytes:
        """破坏CRC校验（用于测试）"""
        if len(data) < 2:
            return data
        # 翻转最后一个字节（CRC的一部分）
        return data[:-1] + bytes([data[-1] ^ 0xFF])

