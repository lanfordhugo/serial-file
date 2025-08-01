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
from ..config.constants import FRAME_FORMAT_SIZE

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

            # 获取基础配置
            serial_kwargs = self.config.to_serial_kwargs()

            # P1-B优化: 仅当用户使用默认超时时才应用自适应超时
            from ..config.constants import DEFAULT_TIMEOUT

            if abs(self.config.timeout - DEFAULT_TIMEOUT) < 0.001:  # 用户使用默认超时
                # 根据波特率计算自适应超时时间
                adaptive_timeout = max(
                    0.05, (FRAME_FORMAT_SIZE / self.config.baudrate) * 12
                )
                serial_kwargs["timeout"] = adaptive_timeout
                logger.debug(
                    f"应用P1-B自适应超时: {adaptive_timeout:.3f}s (波特率: {self.config.baudrate})"
                )
                used_timeout = adaptive_timeout
            else:  # 用户明确设置了超时值，尊重用户配置
                used_timeout = self.config.timeout
                logger.debug(f"使用用户配置的超时: {used_timeout:.3f}s")

            self._port = serial.Serial(**serial_kwargs)

            logger.info(f"成功打开串口 {self.config.port}，超时: {used_timeout:.3f}s")
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

            assert self._port is not None  # type: ignore[assert-type]
            bytes_written = self._port.write(data)

            # P1-B优化: write成功后立即flush，降低高波特率下的缓冲延迟
            if bytes_written == len(data):
                self._port.flush()
                return True
            else:
                return False

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
                return b""

            assert self._port is not None  # type: ignore[assert-type]
            return self._port.read(size)

        except Exception as e:
            logger.error(f"读取数据失败: {e}")
            return b""

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
                ports.append(
                    {
                        "device": port_info.device,
                        "description": port_info.description or "未知设备",
                        "hwid": port_info.hwid or "未知硬件ID",
                    }
                )
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

    # ----------------  动态波特率切换支持 ----------------
    def switch_baudrate(self, new_baudrate: int) -> bool:
        """动态切换当前已打开串口的波特率

        Args:
            new_baudrate: 目标波特率

        Returns:
            切换成功返回 True，否则 False
        """
        try:
            if not self.is_open:
                logger.error("串口未打开，无法切换波特率")
                return False

            # 此处 _port 一定不为 None，因为 is_open 已验证
            assert self._port is not None  # type: ignore[assert-type]

            # 若已是目标波特率则直接返回
            if self._port.baudrate == new_baudrate:  # type: ignore[attr-defined]
                logger.debug(f"波特率已是 {new_baudrate}，无需切换")
                return True

            logger.info(f"切换波特率: {self._port.baudrate} -> {new_baudrate}")  # type: ignore[attr-defined]
            self._port.baudrate = new_baudrate  # type: ignore[attr-defined]
            # 同步更新配置，避免后续 reopen 使用旧值
            self.config.baudrate = new_baudrate
            return True
        except Exception as e:
            logger.error(f"动态切换波特率失败: {e}")
            return False
