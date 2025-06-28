"""
串口管理模块
============

提供串口的统一管理和操作接口。
"""

import serial
from serial.tools import list_ports
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from ..config.settings import SerialConfig
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SerialManager:
    """串口管理器"""
    
    def __init__(self, config: SerialConfig):
        """
        初始化串口管理器
        
        Args:
            config: 串口配置对象
        """
        self.config = config
        self._port: Optional[serial.Serial] = None
        
    @property
    def port(self) -> Optional[serial.Serial]:
        """获取串口对象"""
        return self._port
    
    @property
    def is_open(self) -> bool:
        """检查串口是否已打开"""
        return self._port is not None and self._port.is_open
    
    def open(self) -> bool:
        """
        打开串口连接
        
        Returns:
            成功返回True，失败返回False
        """
        try:
            if self.is_open:
                logger.warning(f"串口 {self.config.port} 已经打开")
                return True
                
            # 创建串口对象
            self._port = serial.Serial(**self.config.to_serial_kwargs())
            
            logger.info(f"成功打开串口 {self.config.port}")
            return True
            
        except Exception as e:
            logger.error(f"打开串口失败: {e}")
            self._port = None
            return False
    
    def close(self) -> None:
        """关闭串口连接"""
        try:
            if self._port and self._port.is_open:
                self._port.close()
                logger.info(f"已关闭串口 {self.config.port}")
        except Exception as e:
            logger.error(f"关闭串口失败: {e}")
        finally:
            self._port = None
    
    def write(self, data: bytes) -> bool:
        """
        向串口写入数据
        
        Args:
            data: 要写入的字节数据
            
        Returns:
            成功返回True，失败返回False
        """
        try:
            if not self.is_open:
                logger.error("串口未打开，无法写入数据")
                return False
                
            bytes_written = self._port.write(data)
            return bytes_written == len(data)
            
        except Exception as e:
            logger.error(f"写入数据失败: {e}")
            return False
    
    def read(self, size: int) -> bytes:
        """
        从串口读取指定长度的数据
        
        Args:
            size: 要读取的字节数
            
        Returns:
            读取到的数据，失败时返回空bytes
        """
        try:
            if not self.is_open:
                logger.error("串口未打开，无法读取数据")
                return b''
                
            return self._port.read(size)
            
        except Exception as e:
            logger.error(f"读取数据失败: {e}")
            return b''
    
    @contextmanager
    def connection(self):
        """
        上下文管理器，自动管理串口连接
        
        Examples:
            >>> config = SerialConfig(port='COM1')
            >>> manager = SerialManager(config)
            >>> with manager.connection():
            ...     # 在这里使用串口
            ...     pass
        """
        try:
            if not self.open():
                raise RuntimeError(f"无法打开串口 {self.config.port}")
            yield self
        finally:
            self.close()
    
    @staticmethod
    def list_available_ports() -> List[Dict[str, str]]:
        """
        获取系统可用的串口列表
        
        Returns:
            串口信息列表，每个元素包含device、description等字段
        """
        try:
            ports = []
            for port_info in list_ports.comports():
                ports.append({
                    'device': port_info.device,
                    'description': port_info.description or '未知设备',
                    'hwid': port_info.hwid or '未知硬件ID'
                })
            return ports
        except Exception as e:
            logger.error(f"获取串口列表失败: {e}")
            return []
    
    @staticmethod
    def print_available_ports() -> None:
        """打印系统可用的串口信息"""
        ports = SerialManager.list_available_ports()
        
        if not ports:
            print("没有找到可用的串口。")
            return
            
        print("可用的串口：")
        for port in ports:
            print(f"  {port['device']} - {port['description']}")
    
    def __enter__(self):
        """支持with语句"""
        if not self.open():
            raise RuntimeError(f"无法打开串口 {self.config.port}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持with语句"""
        self.close()
    
    def __del__(self):
        """析构函数，确保串口被正确关闭"""
        self.close() 