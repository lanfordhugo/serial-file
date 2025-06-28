"""
文件发送模块
============

负责单个文件的发送逻辑。
"""

import os
import struct
import time
from pathlib import Path
from typing import Optional, Union

from ..config.constants import SerialCommand, VAL_REQUEST_FILE, MAX_FILE_NAME_LENGTH
from ..config.settings import TransferConfig
from ..core.frame_handler import FrameHandler
from ..core.serial_manager import SerialManager
from ..utils.logger import get_logger
from ..utils.progress import TransferProgressTracker, progress_bar

logger = get_logger(__name__)


class FileSender:
    """文件发送器"""
    
    def __init__(
        self, 
        serial_manager: SerialManager, 
        file_path: Optional[Union[str, Path]] = None,
        config: Optional[TransferConfig] = None
    ):
        """
        初始化文件发送器
        
        Args:
            serial_manager: 串口管理器
            file_path: 要发送的文件路径（可选）
            config: 传输配置（可选）
        """
        self.serial_manager = serial_manager
        self.config = config or TransferConfig()
        
        # 传输状态
        self.send_size = 0
        self.file_size = 0
        self.file_data = b''
        
        # 如果提供了文件路径，立即初始化
        if file_path:
            self.init_file(file_path)
    
    def init_file(self, file_path: Union[str, Path]) -> bool:
        """
        初始化要发送的文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            成功返回True，失败返回False
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                logger.error(f"文件不存在: {file_path}")
                return False
                
            if not file_path.is_file():
                logger.error(f"路径不是文件: {file_path}")
                return False
            
            # 重置状态
            self.send_size = 0
            self.file_size = file_path.stat().st_size
            
            # 读取文件内容
            with file_path.open('rb') as f:
                self.file_data = f.read()
            
            logger.info(f"已加载文件: {file_path.name}, 大小: {self.file_size / 1024:.2f} KB")
            return True
            
        except Exception as e:
            logger.error(f"初始化文件失败: {e}")
            return False
    
    def get_file_data(self, addr: int, length: int) -> bytes:
        """
        根据地址和长度获取文件数据
        
        Args:
            addr: 起始地址
            length: 数据长度
            
        Returns:
            指定区间的文件数据
        """
        return self.file_data[addr:addr + length]
    
    def wait_for_file_size_request(self) -> bool:
        """
        等待接收端请求文件大小
        
        Returns:
            成功返回True，超时返回False
        """
        logger.info("等待接收端请求文件大小...")
        
        start_time = time.time()
        while True:
            # 检查超时
            if time.time() - start_time > self.config.request_timeout:
                logger.error(f"等待文件大小请求超时: {self.config.request_timeout}秒")
                return False
            
            # 读取命令
            cmd, data = FrameHandler.read_frame(
                self.serial_manager.port, 
                6 + 1  # 帧头+CRC+数据
            )
            
            if cmd is None or data is None:
                continue
                
            if cmd != SerialCommand.REQUEST_FILE_SIZE:
                logger.warning(f"收到错误命令: {hex(cmd)}")
                continue
            
            # 验证请求数据
            if int.from_bytes(data, byteorder='little') == VAL_REQUEST_FILE:
                logger.info("收到文件大小请求")
                self._send_file_size()
                return True
    
    def wait_for_filename_request(self) -> bool:
        """
        等待接收端请求文件名
        
        Returns:
            成功返回True，超时返回False
        """
        logger.info("等待接收端请求文件名...")
        
        start_time = time.time()
        while True:
            # 检查超时
            if time.time() - start_time > self.config.request_timeout:
                logger.error(f"等待文件名请求超时: {self.config.request_timeout}秒")
                return False
            
            # 读取命令
            cmd, data = FrameHandler.read_frame(
                self.serial_manager.port,
                6 + 1  # 帧头+CRC+数据
            )
            
            if cmd is None or data is None:
                continue
                
            if cmd != SerialCommand.REQUEST_FILE_NAME:
                logger.warning(f"收到错误命令: {hex(cmd)}")
                continue
            
            logger.info("收到文件名请求")
            return True
    
    def send_filename(self, filename: str) -> bool:
        """
        发送文件名
        
        Args:
            filename: 文件名
            
        Returns:
            成功返回True，失败返回False
        """
        try:
            # 编码文件名
            encoded_name = filename.encode('utf-8')
            
            # 填充到最大长度
            padded_name = encoded_name + b'\x00' * (MAX_FILE_NAME_LENGTH - len(encoded_name))
            
            # 打包并发送
            frame = FrameHandler.pack_frame(SerialCommand.REPLY_FILE_NAME, padded_name)
            if frame and self.serial_manager.write(frame):
                logger.info(f"已发送文件名: {filename}")
                return True
            else:
                logger.error("发送文件名失败")
                return False
                
        except Exception as e:
            logger.error(f"发送文件名异常: {e}")
            return False
    
    def _send_file_size(self) -> bool:
        """
        发送文件大小
        
        Returns:
            成功返回True，失败返回False
        """
        try:
            # 打包文件大小（4字节）
            size_data = struct.pack('<I', self.file_size)
            frame = FrameHandler.pack_frame(SerialCommand.REPLY_FILE_SIZE, size_data)
            
            if frame and self.serial_manager.write(frame):
                logger.info(f"已发送文件大小: {self.file_size / 1024:.2f} KB")
                return True
            else:
                logger.error("发送文件大小失败")
                return False
                
        except Exception as e:
            logger.error(f"发送文件大小异常: {e}")
            return False
    
    def _send_data_package(self, addr: int, length: int) -> bool:
        """
        发送数据包
        
        Args:
            addr: 起始地址
            length: 数据长度
            
        Returns:
            成功返回True，失败返回False
        """
        try:
            # 获取数据
            data = self.get_file_data(addr, length)
            
            # 打包并发送
            frame = FrameHandler.pack_frame(SerialCommand.SEND_DATA, data)
            if frame and self.serial_manager.write(frame):
                return True
            else:
                logger.error("发送数据包失败")
                return False
                
        except Exception as e:
            logger.error(f"发送数据包异常: {e}")
            return False
    
    def _wait_for_data_request(self) -> bool:
        """
        等待并处理数据请求
        
        Returns:
            成功返回True，传输完成或失败返回False
        """
        try:
            # 读取数据请求
            cmd, data = FrameHandler.read_frame(
                self.serial_manager.port,
                6 + 4 + 2  # 帧头+CRC+地址(4字节)+长度(2字节)
            )
            
            if cmd is None or data is None:
                return True  # 继续等待
                
            if cmd != SerialCommand.REQUEST_DATA:
                logger.warning(f"收到错误命令: {hex(cmd)}")
                return True  # 继续等待
            
            # 解析请求地址和长度
            addr, length = struct.unpack('<IH', data)
            
            # 验证请求有效性
            if addr + length > self.file_size:
                if addr > self.file_size:
                    logger.error(f"请求地址超出文件范围: {addr} > {self.file_size}")
                    return False
                else:
                    logger.warning(f"请求长度超出文件范围，调整为: {self.file_size - addr}")
                    length = self.file_size - addr
            
            # 发送数据包
            if self._send_data_package(addr, length):
                self.send_size = addr + length
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"处理数据请求异常: {e}")
            return False
    
    def start_transfer(self) -> bool:
        """
        开始文件传输
        
        Returns:
            成功返回True，失败返回False
        """
        if self.file_size == 0:
            logger.error("没有要发送的文件")
            return False
        
        try:
            # 等待文件大小请求
            if not self.wait_for_file_size_request():
                return False
            
            # 开始传输进度跟踪
            start_time = time.time()
            
            logger.info("开始文件传输...")
            
            while self.send_size < self.file_size:
                # 等待并处理数据请求
                if not self._wait_for_data_request():
                    break
                
                # 显示进度
                if self.config.show_progress:
                    progress_percent = (self.send_size / self.file_size) * 100
                    elapsed_time = time.time() - start_time
                    send_rate = (self.send_size / elapsed_time / 1024) if elapsed_time > 0 else 0
                    progress_bar(progress_percent, send_rate)
            
            # 检查是否传输完成
            if self.send_size >= self.file_size:
                if self.config.show_progress:
                    print()  # 换行
                    
                elapsed_time = time.time() - start_time
                logger.info(f"文件发送完成！用时: {elapsed_time:.2f}秒")
                return True
            else:
                logger.error("文件传输未完成")
                return False
                
        except Exception as e:
            logger.error(f"文件传输异常: {e}")
            return False


# 为了保持向后兼容，提供原类名的别名
Sender = FileSender 