"""
文件名称: sequence_recovery.py
内容摘要: 序号恢复机制 - 解决发送端和接收端序号失同步问题
当前版本: v1.0.0
作者: AI Assistant
创建日期: 2025-09-29
"""

import struct
import time
from typing import Optional, Tuple, Protocol
from ..config.constants import SerialCommand
from ..core.frame_handler import FrameHandler
from ..utils.logger import get_console_logger

logger = get_console_logger(__name__)


class SerialPortProtocol(Protocol):
    """串口协议接口，用于类型提示"""
    
    def write(self, data: bytes) -> bool:
        """发送数据"""
        ...
    
    def read(self, size: int) -> bytes:
        """读取数据"""
        ...


class SequenceRecoveryManager:
    """序号恢复管理器 - 中期改进功能"""
    
    def __init__(self, enable_recovery: bool = True, mismatch_threshold: int = 3, sync_timeout: int = 2):
        """
        初始化序号恢复管理器
        
        Args:
            enable_recovery: 是否启用序号恢复机制
            mismatch_threshold: 连续序号不匹配阈值，超过则触发同步
            sync_timeout: 序号同步超时时间(秒)
        """
        self.enable_recovery = enable_recovery
        self.mismatch_threshold = mismatch_threshold
        self.sync_timeout = sync_timeout
        
        # 统计信息
        self.consecutive_mismatches = 0  # 连续序号不匹配次数
        self.total_sync_attempts = 0     # 总同步尝试次数
        self.successful_syncs = 0        # 成功同步次数
        
    def record_sequence_mismatch(self) -> bool:
        """
        记录序号不匹配事件
        
        Returns:
            是否应该触发序号同步
        """
        if not self.enable_recovery:
            return False
            
        self.consecutive_mismatches += 1
        logger.debug(f"序号不匹配计数: {self.consecutive_mismatches}/{self.mismatch_threshold}")
        
        if self.consecutive_mismatches >= self.mismatch_threshold:
            logger.warning(f"连续{self.consecutive_mismatches}次序号不匹配，触发序号同步")
            return True
        return False
    
    def reset_mismatch_counter(self) -> None:
        """重置序号不匹配计数器"""
        if self.consecutive_mismatches > 0:
            logger.debug("序号匹配成功，重置不匹配计数器")
            self.consecutive_mismatches = 0
    
    def send_sync_request(self, serial_port: SerialPortProtocol, expected_seq: int, current_seq: int) -> bool:
        """
        发送序号同步请求 (接收端调用)
        
        Args:
            serial_port: 串口对象  
            expected_seq: 接收端期望的序号
            current_seq: 接收端当前的序号位置
            
        Returns:
            发送成功返回True，失败返回False
        """
        if not self.enable_recovery:
            return False
            
        try:
            self.total_sync_attempts += 1
            
            # 构造同步请求数据：期望序号(2字节) + 当前位置(2字节)
            sync_data = struct.pack("<HH", expected_seq & 0xFFFF, current_seq & 0xFFFF)
            frame = FrameHandler.pack_frame(SerialCommand.SYNC_REQUEST, sync_data)
            
            if frame is None:
                logger.error("构造序号同步请求帧失败")
                return False
                
            success = serial_port.write(frame)
            if success:
                logger.info(f"已发送序号同步请求: 期望={expected_seq}, 当前={current_seq}")
            else:
                logger.error("发送序号同步请求失败")
                
            return success
            
        except Exception as e:
            logger.error(f"发送序号同步请求异常: {e}")
            return False
    
    def handle_sync_request(self, serial_port: SerialPortProtocol, request_data: bytes) -> Optional[Tuple[int, int]]:
        """
        处理序号同步请求 (发送端调用)
        
        Args:
            serial_port: 串口对象
            request_data: 同步请求数据
            
        Returns:
            成功返回(接收端期望序号, 接收端当前序号)，失败返回None
        """
        if not self.enable_recovery:
            return None
            
        try:
            if len(request_data) < 4:
                logger.error("序号同步请求数据长度不足")
                return None
                
            # 解析同步请求：期望序号 + 当前位置
            receiver_expected, receiver_current = struct.unpack("<HH", request_data[:4])
            
            logger.info(f"收到序号同步请求: 接收端期望={receiver_expected}, 当前={receiver_current}")
            
            # 发送同步回复，包含确认信息
            reply_data = struct.pack("<HH", receiver_expected & 0xFFFF, receiver_current & 0xFFFF)
            reply_frame = FrameHandler.pack_frame(SerialCommand.SYNC_REPLY, reply_data)
            
            if reply_frame is None:
                logger.error("构造序号同步回复帧失败")
                return None
                
            success = serial_port.write(reply_frame)
            if success:
                logger.info(f"已发送序号同步回复: 确认期望={receiver_expected}")
                return receiver_expected, receiver_current
            else:
                logger.error("发送序号同步回复失败")
                return None
                
        except Exception as e:
            logger.error(f"处理序号同步请求异常: {e}")
            return None
    
    def wait_for_sync_reply(self, serial_port: SerialPortProtocol) -> Optional[Tuple[int, int]]:
        """
        等待序号同步回复 (接收端调用)
        
        Args:
            serial_port: 串口对象
            
        Returns:
            成功返回(确认的期望序号, 确认的当前序号)，失败返回None
        """
        if not self.enable_recovery:
            return None
            
        try:
            start_time = time.time()
            
            while time.time() - start_time < self.sync_timeout:
                # 读取同步回复
                cmd, data = FrameHandler.read_frame(serial_port, 6 + 4)  # 帧头+CRC+数据(4字节)
                
                if cmd is None or data is None:
                    continue
                    
                if cmd == SerialCommand.SYNC_REPLY:
                    if len(data) < 4:
                        logger.error("序号同步回复数据长度不足")
                        continue
                        
                    # 解析同步回复
                    confirmed_expected, confirmed_current = struct.unpack("<HH", data[:4])
                    
                    logger.info(f"收到序号同步回复: 确认期望={confirmed_expected}, 确认当前={confirmed_current}")
                    self.successful_syncs += 1
                    self.reset_mismatch_counter()  # 同步成功，重置计数器
                    
                    return confirmed_expected, confirmed_current
                else:
                    logger.debug(f"等待同步回复时收到其他命令: {hex(cmd)}")
                    
            logger.warning(f"等待序号同步回复超时: {self.sync_timeout}秒")
            return None
            
        except Exception as e:
            logger.error(f"等待序号同步回复异常: {e}")
            return None
    
    def perform_sequence_sync(self, serial_port: SerialPortProtocol, expected_seq: int, current_seq: int) -> Optional[int]:
        """
        执行完整的序号同步流程 (接收端调用)
        
        Args:
            serial_port: 串口对象
            expected_seq: 接收端期望的序号
            current_seq: 接收端当前的序号位置
            
        Returns:
            成功返回同步后的序号，失败返回None
        """
        if not self.enable_recovery:
            return None
            
        logger.info("开始执行序号同步流程...")
        
        # 1. 发送同步请求
        if not self.send_sync_request(serial_port, expected_seq, current_seq):
            return None
        
        # 2. 等待同步回复
        reply = self.wait_for_sync_reply(serial_port)
        if reply is None:
            return None
            
        confirmed_expected, _ = reply
        
        # 3. 验证同步结果
        if confirmed_expected == expected_seq:
            logger.info(f"序号同步成功: 新序号={confirmed_expected}")
            return confirmed_expected
        else:
            logger.warning(f"序号同步不一致: 期望={expected_seq}, 确认={confirmed_expected}")
            return confirmed_expected  # 使用发送端确认的序号
    
    def get_recovery_stats(self) -> dict:
        """
        获取序号恢复统计信息
        
        Returns:
            包含统计信息的字典
        """
        success_rate = 0.0
        if self.total_sync_attempts > 0:
            success_rate = self.successful_syncs / self.total_sync_attempts
            
        return {
            "enable_recovery": self.enable_recovery,
            "mismatch_threshold": self.mismatch_threshold,
            "consecutive_mismatches": self.consecutive_mismatches,
            "total_sync_attempts": self.total_sync_attempts,
            "successful_syncs": self.successful_syncs,
            "sync_success_rate": success_rate,
        }
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        self.consecutive_mismatches = 0
        self.total_sync_attempts = 0
        self.successful_syncs = 0
        logger.debug("序号恢复统计信息已重置")
