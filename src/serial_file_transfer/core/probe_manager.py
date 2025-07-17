"""
智能探测协商管理器
================

负责处理设备发现、能力协商、波特率切换等智能探测协议功能。
"""

import time
import random
from typing import Optional, List, Tuple
from ..config.constants import (
    ProbeCommand,
    PROBE_BAUDRATE,
    PROBE_TIMEOUT,
    PROBE_RETRY_COUNT,
    CAPABILITY_TIMEOUT,
    SWITCH_TIMEOUT,
    SWITCH_DELAY_MS,
    PROBE_PROTOCOL_VERSION,
)
from ..config.constants import FRAME_HEADER_SIZE, FRAME_CRC_SIZE
from ..config.settings import SerialConfig
from ..core.serial_manager import SerialManager
from ..core.frame_handler import FrameHandler
from ..core.probe_structures import (
    ProbeRequestData,
    ProbeResponseData,
    CapabilityNegoData,
    CapabilityAckData,
    SwitchBaudrateData,
    SwitchAckData,
)
from ..utils.logger import get_logger
from ..config.constants import calculate_recommended_chunk_size

logger = get_logger(__name__)


class ProbeTimeoutError(Exception):
    """探测超时异常"""

    pass


class ProbeManager:
    """智能探测协商管理器"""

    def __init__(self, serial_manager: SerialManager):
        """
        初始化探测管理器

        Args:
            serial_manager: 串口管理器实例
        """
        self.serial_manager = serial_manager
        self.session_id: Optional[int] = None
        self.target_baudrate: Optional[int] = None
        self.device_id: Optional[int] = None
        self.negotiated_chunk_size: Optional[int] = None

        # 支持的波特率列表（按优先级排序）
        # 现代整数波特率 + 传统兼容波特率
        self.supported_baudrates = [
            6000000,  # 6 Mbps - 极高速
            4000000,  # 4 Mbps - 超高速  
            3000000,  # 3 Mbps - 高速
            2000000,  # 2 Mbps - 现代整数波特率
            1728000,  # 1.728 Mbps - 高性能兼容
            921600,   # 921.6 kbps - 标准高速
            460800,   # 460.8 kbps - 中等速度
            230400,   # 230.4 kbps - 稳定选择
            115200    # 115.2 kbps - 最大兼容(传统基准)
        ]

    def _generate_session_id(self) -> int:
        """生成新的会话ID"""
        return random.randint(0x10000000, 0xFFFFFFFF)

    def _send_probe_frame(self, cmd: ProbeCommand, data: bytes) -> bool:
        """
        发送探测协议数据帧

        Args:
            cmd: 探测命令字
            data: 数据内容

        Returns:
            发送成功返回True，失败返回False
        """
        try:
            frame = FrameHandler.pack_frame(cmd, data)
            if frame is None:
                logger.error(f"打包探测帧失败: cmd={cmd}")
                return False

            return self.serial_manager.write(frame)
        except Exception as e:
            logger.error(f"发送探测帧异常: {e}")
            return False

    def _receive_probe_frame(
        self, expected_cmd: ProbeCommand, timeout: float
    ) -> Optional[bytes]:
        """
        接收指定命令的探测协议数据帧

        Args:
            expected_cmd: 期望的命令字
            timeout: 超时时间(秒)

        Returns:
            接收到的数据内容，超时或错误返回None
        """
        try:
            start_time = time.time()
            buffer = b""

            HEADER_SIZE = FRAME_HEADER_SIZE  # 3 字节

            while time.time() - start_time < timeout:
                # 读取新数据并追加到缓冲区
                new_data = self.serial_manager.read(1024)
                if new_data:
                    buffer += new_data

                # 解析缓冲区中所有完整帧
                while True:
                    if len(buffer) < HEADER_SIZE + FRAME_CRC_SIZE:
                        break  # 数据不足

                    # 取头部，读取声明数据长度
                    try:
                        cmd = buffer[0]
                        data_len = int.from_bytes(buffer[1:3], "little")
                    except Exception:
                        # 头部异常，丢弃 1 字节
                        buffer = buffer[1:]
                        continue

                    frame_len = HEADER_SIZE + data_len + FRAME_CRC_SIZE

                    if len(buffer) < frame_len:
                        # 不够一个完整帧，继续读取
                        break

                    frame_bytes = buffer[:frame_len]
                    buffer = buffer[frame_len:]

                    unpacked = FrameHandler.unpack_frame(frame_bytes)
                    if unpacked is None:
                        # 解析失败，继续下一个帧
                        continue

                    cmd_parsed, _, data_parsed, _ = unpacked
                    if cmd_parsed == expected_cmd:
                        return data_parsed
                    # 若不是期望命令，忽略继续循环

                time.sleep(0.005)  # 避免忙循环

            logger.warning(f"接收探测帧超时: cmd={expected_cmd}, timeout={timeout}s")
            return None

        except Exception as e:
            logger.error(f"接收探测帧异常: {e}")
            return None

    def send_probe_request(self) -> Optional[ProbeResponseData]:
        """
        发送探测请求并等待响应

        Returns:
            成功返回探测响应数据，失败返回None
        """
        try:
            # 创建探测请求
            request = ProbeRequestData.create()
            self.device_id = request.device_id

            logger.info(f"发送探测请求: device_id={hex(request.device_id)}")

            # 发送探测请求
            if not self._send_probe_frame(ProbeCommand.PROBE_REQUEST, request.pack()):
                logger.error("发送探测请求失败")
                return None

            # 等待探测响应
            response_data = self._receive_probe_frame(
                ProbeCommand.PROBE_RESPONSE, PROBE_TIMEOUT
            )

            if response_data is None:
                logger.warning("未收到探测响应")
                return None

            # 解析响应数据
            response = ProbeResponseData.unpack(response_data)
            if response is None:
                logger.error("解析探测响应失败")
                return None

            # 验证响应
            if (
                response.device_id != request.device_id
                or response.protocol_version != request.protocol_version
                or response.random_seed != request.random_seed
            ):
                logger.error("探测响应验证失败")
                return None

            logger.info(f"收到探测响应: 支持波特率={response.supported_baudrates}")
            return response

        except Exception as e:
            logger.error(f"探测请求异常: {e}")
            return None

    def wait_for_probe_request(
        self, timeout: float = PROBE_TIMEOUT
    ) -> Optional[ProbeRequestData]:
        """
        等待接收探测请求

        Args:
            timeout: 超时时间(秒)

        Returns:
            成功返回探测请求数据，超时返回None
        """
        try:
            logger.info("等待探测请求...")

            request_data = self._receive_probe_frame(
                ProbeCommand.PROBE_REQUEST, timeout
            )

            if request_data is None:
                logger.info("等待探测请求超时")
                return None

            # 解析请求数据
            request = ProbeRequestData.unpack(request_data)
            if request is None:
                logger.error("解析探测请求失败")
                return None

            logger.info(f"收到探测请求: device_id={hex(request.device_id)}")
            return request

        except Exception as e:
            logger.error(f"等待探测请求异常: {e}")
            return None

    def send_probe_response(self, request: ProbeRequestData) -> bool:
        """
        发送探测响应

        Args:
            request: 收到的探测请求

        Returns:
            发送成功返回True，失败返回False
        """
        try:
            # 创建响应
            response = ProbeResponseData.create_response(
                request, self.supported_baudrates
            )

            logger.info(f"发送探测响应: 支持波特率={response.supported_baudrates}")

            # 发送响应
            return self._send_probe_frame(ProbeCommand.PROBE_RESPONSE, response.pack())

        except Exception as e:
            logger.error(f"发送探测响应异常: {e}")
            return False

    def negotiate_capability(
        self, file_count: int, total_size: int, supported_baudrates: List[int]
    ) -> Optional[int]:
        """
        返回 selected_baudrate
        """
        try:
            # 选择最高的公共波特率
            selected_baudrate = None
            for baudrate in self.supported_baudrates:
                if baudrate in supported_baudrates:
                    selected_baudrate = baudrate
                    break

            if selected_baudrate is None:
                logger.error("没有找到公共支持的波特率")
                return None

            # 生成会话ID
            self.session_id = self._generate_session_id()
            self.target_baudrate = selected_baudrate

            # 确定传输模式
            transfer_mode = 2 if file_count > 1 else 1

            # P1-A优化: 根据波特率计算推荐块大小
            recommended_chunk_size = calculate_recommended_chunk_size(selected_baudrate)

            # 创建能力协商数据
            capability_data = CapabilityNegoData(
                session_id=self.session_id,
                transfer_mode=transfer_mode,
                file_count=file_count,
                total_size=total_size,
                selected_baudrate=selected_baudrate,
                chunk_size=recommended_chunk_size,  # P1-A新增参数
            )

            logger.info(
                f"发送能力协商: 波特率={selected_baudrate}, 文件数={file_count}, 推荐块大小={recommended_chunk_size}"
            )

            # 发送能力协商
            if not self._send_probe_frame(
                ProbeCommand.CAPABILITY_NEGO, capability_data.pack()
            ):
                logger.error("发送能力协商失败")
                return None

            # 等待能力确认
            ack_data = self._receive_probe_frame(
                ProbeCommand.CAPABILITY_ACK, CAPABILITY_TIMEOUT
            )

            if ack_data is None:
                logger.warning("未收到能力确认")
                return None

            # 解析确认数据
            ack = CapabilityAckData.unpack(ack_data)
            if ack is None:
                logger.error("解析能力确认失败")
                return None

            # 验证会话ID和接受状态
            if ack.session_id != self.session_id or ack.accept_status != 1:
                logger.error(
                    f"能力协商被拒绝: session_id={hex(ack.session_id) if ack.session_id else 'None'}, status={ack.accept_status}"
                )
                return None

            logger.info(
                f"能力协商成功: 波特率={selected_baudrate}, 协商块大小={ack.negotiated_chunk_size}"
            )
            # 保存
            self.negotiated_chunk_size = ack.negotiated_chunk_size
            return selected_baudrate

        except Exception as e:
            logger.error(f"能力协商异常: {e}")
            return None

    def handle_capability_nego(self, nego_data: bytes) -> bool:
        """
        接收端处理能力协商

        Args:
            nego_data: 能力协商数据

        Returns:
            处理成功返回True，失败返回False
        """
        try:
            # 解析协商数据
            capability = CapabilityNegoData.unpack(nego_data)
            if capability is None:
                logger.error("解析能力协商失败")
                return False

            # 保存会话信息
            self.session_id = capability.session_id
            self.target_baudrate = capability.selected_baudrate

            # 检查波特率是否支持
            if capability.selected_baudrate not in self.supported_baudrates:
                logger.error(f"不支持的波特率: {capability.selected_baudrate}")
                # 发送拒绝
                if self.session_id is not None:
                    # P1-A优化: 协商块大小，拒绝时使用最小值
                    from ..config.constants import MIN_CHUNK_SIZE

                    ack = CapabilityAckData(self.session_id, 0, MIN_CHUNK_SIZE)
                    self._send_probe_frame(ProbeCommand.CAPABILITY_ACK, ack.pack())
                return False

            # P1-A优化: 协商块大小
            from ..config.constants import negotiate_chunk_size, MAX_CHUNK_SIZE

            negotiated_chunk = negotiate_chunk_size(
                capability.chunk_size, MAX_CHUNK_SIZE
            )

            logger.info(
                f"接受能力协商: 波特率={capability.selected_baudrate}, 文件数={capability.file_count}, 协商块大小={negotiated_chunk}"
            )

            # 发送接受确认
            if self.session_id is not None:
                ack = CapabilityAckData(self.session_id, 1, negotiated_chunk)
                self.negotiated_chunk_size = negotiated_chunk
                return self._send_probe_frame(ProbeCommand.CAPABILITY_ACK, ack.pack())
            else:
                logger.error("会话ID为None，无法发送确认")
                return False

        except Exception as e:
            logger.error(f"处理能力协商异常: {e}")
            return False

    def switch_baudrate(self) -> bool:
        """
        发送端执行波特率切换

        Returns:
            切换成功返回True，失败返回False
        """
        try:
            if self.session_id is None or self.target_baudrate is None:
                logger.error("会话信息不完整，无法切换波特率")
                return False

            # 创建切换数据
            switch_data = SwitchBaudrateData(
                session_id=self.session_id,
                new_baudrate=self.target_baudrate,
                switch_delay_ms=SWITCH_DELAY_MS,
            )

            logger.info(f"发送波特率切换指令: {self.target_baudrate}")

            # 发送切换指令
            if not self._send_probe_frame(
                ProbeCommand.SWITCH_BAUDRATE, switch_data.pack()
            ):
                logger.error("发送波特率切换指令失败")
                return False

            # 等待切换确认
            ack_data = self._receive_probe_frame(
                ProbeCommand.SWITCH_ACK, SWITCH_TIMEOUT
            )

            if ack_data is None:
                logger.warning("未收到波特率切换确认")
                return False

            # 解析确认数据
            ack = SwitchAckData.unpack(ack_data)
            if ack is None or ack.session_id != self.session_id:
                logger.error("波特率切换确认验证失败")
                return False

            # 执行同步切换
            return self._execute_baudrate_switch(self.target_baudrate, SWITCH_DELAY_MS)

        except Exception as e:
            logger.error(f"波特率切换异常: {e}")
            return False

    def handle_baudrate_switch(self, switch_data: bytes) -> bool:
        """
        接收端处理波特率切换

        Args:
            switch_data: 切换数据

        Returns:
            处理成功返回True，失败返回False
        """
        try:
            # 解析切换数据
            switch = SwitchBaudrateData.unpack(switch_data)
            if switch is None:
                logger.error("解析波特率切换数据失败")
                return False

            # 验证会话ID
            if switch.session_id != self.session_id:
                logger.error(
                    "波特率切换会话ID不匹配: %s != %s",
                    hex(switch.session_id),
                    hex(self.session_id) if self.session_id is not None else "None",
                )
                return False

            # 验证波特率
            if switch.new_baudrate != self.target_baudrate:
                logger.error(f"波特率不匹配: {switch.new_baudrate} != {self.target_baudrate}")
                return False

            logger.info(f"收到波特率切换指令: {switch.new_baudrate}")

            # 发送切换确认
            assert self.session_id is not None  # type: ignore[assert-type]
            ack = SwitchAckData(self.session_id)
            if not self._send_probe_frame(ProbeCommand.SWITCH_ACK, ack.pack()):
                logger.error("发送波特率切换确认失败")
                return False

            # 执行同步切换
            return self._execute_baudrate_switch(
                switch.new_baudrate, switch.switch_delay_ms
            )

        except Exception as e:
            logger.error(f"处理波特率切换异常: {e}")
            return False

    def _execute_baudrate_switch(self, new_baudrate: int, delay_ms: int) -> bool:
        """
        执行精确的波特率切换

        Args:
            new_baudrate: 新波特率
            delay_ms: 切换延时(毫秒)

        Returns:
            切换成功返回True，失败返回False
        """
        try:
            logger.info(f"执行波特率切换: {new_baudrate}, 延时={delay_ms}ms")

            # 精确延时
            time.sleep(delay_ms / 1000.0)

            # 切换波特率
            # 注意：这里需要SerialManager支持动态波特率切换
            if hasattr(self.serial_manager, "switch_baudrate"):
                # 保证返回布尔值，兼容测试中的Mock对象
                try:
                    result = self.serial_manager.switch_baudrate(new_baudrate)
                except Exception as e:
                    logger.error(f"串口动态切换波特率异常: {e}")
                    return False

                return bool(result)
            else:
                # 如果不支持动态切换，需要重新配置串口
                logger.warning("串口管理器不支持动态波特率切换")
                # 这里可以添加重新配置串口的逻辑
                return True

        except Exception as e:
            logger.error(f"执行波特率切换异常: {e}")
            return False
