"""
文件名称: protocol_state_sync.py
内容摘要: 协议状态强同步机制，解决跨设备传输中的状态不一致问题
当前版本: v1.0.0
作者: Assistant
创建日期: 2025-09-29
"""

import struct
import time
from typing import Optional, Tuple, Any
from enum import IntEnum

from ..config.constants import SerialCommand, ProtocolState
from ..core.frame_handler import FrameHandler
from ..core.serial_manager import SerialManager
from ..utils.logger import get_console_logger

logger = get_console_logger(__name__)


class ProtocolStateSynchronizer:
    """
    协议状态强同步器
    
    解决跨设备传输中的核心问题：
    1. 传输失败后双方状态机不一致
    2. 错误命令（如0x64 SEND_DATA出现在错误位置）
    3. 协议状态混乱导致传输彻底失败
    
    核心策略：
    - 定期状态同步检查
    - 检测到错误命令时强制重置
    - 提供协议状态恢复机制
    """

    def __init__(
        self,
        enable_sync: bool = True,
        sync_interval: float = 15.0,
        force_sync_on_error: bool = True
    ):
        """
        初始化协议状态同步器
        
        Args:
            enable_sync: 是否启用状态同步
            sync_interval: 状态同步检查间隔（秒）
            force_sync_on_error: 检测到错误命令时是否强制同步
        """
        self.enable_sync = enable_sync
        self.sync_interval = sync_interval
        self.force_sync_on_error = force_sync_on_error
        
        # 状态跟踪
        self.local_state = ProtocolState.IDLE
        self.remote_state = ProtocolState.IDLE
        self.last_sync_time = 0.0
        
        # 统计信息
        self.total_sync_attempts = 0
        self.successful_syncs = 0
        self.forced_resets = 0
        self.error_command_detections = 0

    def set_local_state(self, state: ProtocolState, reason: str = "") -> None:
        """设置本地协议状态"""
        if self.local_state != state:
            logger.debug(f"协议状态切换: {self.local_state.name} -> {state.name} {reason}")
            self.local_state = state

    def should_sync_state(self) -> bool:
        """判断是否需要进行状态同步"""
        if not self.enable_sync:
            return False
            
        return (time.time() - self.last_sync_time) > self.sync_interval

    def detect_error_command(self, expected_commands: list, received_command: int) -> bool:
        """
        检测错误命令
        
        Args:
            expected_commands: 当前状态下期望的命令列表
            received_command: 实际收到的命令
            
        Returns:
            True表示检测到错误命令，需要强制同步
        """
        if received_command not in expected_commands:
            self.error_command_detections += 1
            logger.warning(f"检测到错误命令: 收到 0x{received_command:02x}, 期望 {[hex(cmd) for cmd in expected_commands]}")
            
            # 特别关注0x64 (SEND_DATA)出现在错误位置的情况
            if received_command == SerialCommand.SEND_DATA:
                logger.error(f"检测到SEND_DATA命令出现在错误位置，发送端和接收端状态不同步")
                return True
                
            return self.force_sync_on_error
            
        return False

    def request_state_sync(self, serial_manager: SerialManager) -> bool:
        """
        请求协议状态同步
        
        Args:
            serial_manager: 串口管理器
            
        Returns:
            成功返回True，失败返回False
        """
        if not self.enable_sync:
            return False
            
        try:
            # 协议：本地状态(1字节) + 时间戳(4字节)
            timestamp = int(time.time()) & 0xFFFFFFFF
            payload = struct.pack("<BI", self.local_state, timestamp)
            frame = FrameHandler.pack_frame(SerialCommand.STATE_SYNC_REQUEST, payload)
            
            if frame and serial_manager.write(frame):
                logger.info(f"已发送协议状态同步请求: 本地状态={self.local_state.name}")
                self.total_sync_attempts += 1
                self.last_sync_time = time.time()
                return True
            else:
                logger.error("发送协议状态同步请求失败")
                return False
                
        except Exception as e:
            logger.error(f"发送协议状态同步请求异常: {e}")
            return False

    def handle_state_sync_request(self, serial_manager: SerialManager, data: bytes) -> Optional[Tuple[ProtocolState, int]]:
        """
        处理收到的协议状态同步请求
        
        Args:
            serial_manager: 串口管理器
            data: STATE_SYNC_REQUEST帧的数据部分
            
        Returns:
            成功返回(远程状态, 时间戳)，失败返回None
        """
        if not self.enable_sync:
            return None
            
        try:
            if len(data) < 5:
                logger.error("协议状态同步请求数据长度不足")
                return None
                
            remote_state_value, timestamp = struct.unpack("<BI", data[:5])
            remote_state = ProtocolState(remote_state_value)
            
            logger.info(f"收到协议状态同步请求: 远程状态={remote_state.name}, 本地状态={self.local_state.name}")
            
            # 发送同步回复
            reply_payload = struct.pack("<BBI", self.local_state, remote_state_value, timestamp)
            reply_frame = FrameHandler.pack_frame(SerialCommand.STATE_SYNC_REPLY, reply_payload)
            
            if reply_frame and serial_manager.write(reply_frame):
                logger.info(f"已发送协议状态同步回复")
                self.remote_state = remote_state
                return remote_state, timestamp
            else:
                logger.error("发送协议状态同步回复失败")
                return None
                
        except Exception as e:
            logger.error(f"处理协议状态同步请求异常: {e}")
            return None

    def wait_for_state_sync_reply(self, serial_port: Any, timeout: float = 5.0) -> Optional[Tuple[ProtocolState, ProtocolState]]:
        """
        等待协议状态同步回复
        
        Args:
            serial_port: 串口对象
            timeout: 等待超时时间（秒）
            
        Returns:
            成功返回(确认的本地状态, 确认的远程状态)，失败返回None
        """
        if not self.enable_sync:
            return None
            
        try:
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                cmd, data = FrameHandler.read_frame(serial_port, 6 + 7)  # 帧头+CRC+数据(7字节)
                
                if cmd is None or data is None:
                    continue
                    
                if cmd == SerialCommand.STATE_SYNC_REPLY:
                    if len(data) < 7:
                        logger.error("协议状态同步回复数据长度不足")
                        continue
                        
                    local_state_value, remote_state_value, timestamp = struct.unpack("<BBI", data[:7])
                    confirmed_local = ProtocolState(local_state_value)
                    confirmed_remote = ProtocolState(remote_state_value)
                    
                    logger.info(f"收到协议状态同步回复: 确认本地={confirmed_local.name}, 确认远程={confirmed_remote.name}")
                    
                    self.remote_state = confirmed_remote
                    self.successful_syncs += 1
                    
                    return confirmed_local, confirmed_remote
                else:
                    logger.debug(f"等待状态同步回复时收到其他命令: {hex(cmd)}")
                    
            logger.warning(f"等待协议状态同步回复超时: {timeout}秒")
            return None
            
        except Exception as e:
            logger.error(f"等待协议状态同步回复异常: {e}")
            return None

    def force_protocol_reset(self, serial_manager: SerialManager) -> bool:
        """
        强制协议重置
        
        当检测到严重的状态不一致时，强制双方回到IDLE状态
        
        Args:
            serial_manager: 串口管理器
            
        Returns:
            成功返回True，失败返回False
        """
        try:
            # 发送协议重置命令
            reset_payload = struct.pack("<B", ProtocolState.IDLE)
            reset_frame = FrameHandler.pack_frame(SerialCommand.PROTOCOL_RESET, reset_payload)
            
            if reset_frame and serial_manager.write(reset_frame):
                logger.warning("已发送协议重置命令，强制双方回到IDLE状态")
                self.local_state = ProtocolState.IDLE
                self.remote_state = ProtocolState.IDLE
                self.forced_resets += 1
                return True
            else:
                logger.error("发送协议重置命令失败")
                return False
                
        except Exception as e:
            logger.error(f"强制协议重置异常: {e}")
            return False

    def handle_protocol_reset(self, data: bytes) -> bool:
        """
        处理收到的协议重置命令
        
        Args:
            data: PROTOCOL_RESET帧的数据部分
            
        Returns:
            成功返回True，失败返回False
        """
        try:
            if len(data) < 1:
                logger.error("协议重置命令数据长度不足")
                return False
                
            reset_state_value = struct.unpack("<B", data[:1])[0]
            reset_state = ProtocolState(reset_state_value)
            
            logger.warning(f"收到协议重置命令，强制状态重置为: {reset_state.name}")
            
            self.local_state = reset_state
            self.remote_state = reset_state
            
            return True
            
        except Exception as e:
            logger.error(f"处理协议重置命令异常: {e}")
            return False

    def check_state_consistency(self) -> bool:
        """
        检查协议状态一致性
        
        Returns:
            True表示状态一致，False表示状态不一致
        """
        # 定义兼容的状态对
        compatible_states = {
            (ProtocolState.WAITING_FILENAME_REQUEST, ProtocolState.REQUESTING_FILENAME),
            (ProtocolState.WAITING_SIZE_REQUEST, ProtocolState.REQUESTING_SIZE),
            (ProtocolState.WAITING_DATA_REQUEST, ProtocolState.REQUESTING_DATA),
            (ProtocolState.SENDING_DATA, ProtocolState.RECEIVING_DATA),
            (ProtocolState.IDLE, ProtocolState.IDLE),
        }
        
        state_pair = (self.local_state, self.remote_state)
        reverse_pair = (self.remote_state, self.local_state)
        
        is_consistent = state_pair in compatible_states or reverse_pair in compatible_states
        
        if not is_consistent:
            logger.warning(f"协议状态不一致: 本地={self.local_state.name}, 远程={self.remote_state.name}")
            
        return is_consistent

    def get_sync_stats(self) -> dict:
        """获取同步统计信息"""
        return {
            "enable_sync": self.enable_sync,
            "sync_interval": self.sync_interval,
            "local_state": self.local_state.name,
            "remote_state": self.remote_state.name,
            "last_sync_time": self.last_sync_time,
            "total_sync_attempts": self.total_sync_attempts,
            "successful_syncs": self.successful_syncs,
            "forced_resets": self.forced_resets,
            "error_command_detections": self.error_command_detections,
        }

    def reset_stats(self) -> None:
        """重置统计信息"""
        self.total_sync_attempts = 0
        self.successful_syncs = 0
        self.forced_resets = 0
        self.error_command_detections = 0
        self.last_sync_time = 0.0
