# vNext 实现指南

本文档提供阶段三及后续阶段的具体实现代码框架。

---

## 阶段三：发送端重构 - 代码框架

### 1. 创建发送端状态枚举

**文件**: `src/serial_file_transfer/core/sender_state.py`

```python
"""
发送端状态机定义
"""

from enum import IntEnum


class SenderState(IntEnum):
    """发送端状态枚举"""
    IDLE = 0                      # 空闲状态
    WAIT_FILENAME_REQUEST = 1     # 等待文件名请求
    SEND_FILENAME = 2             # 发送文件名
    WAIT_SIZE_REQUEST = 3         # 等待文件大小请求
    SEND_SIZE = 4                 # 发送文件大小
    WAIT_DATA_REQUEST = 5         # 等待数据请求
    SEND_DATA = 6                 # 发送数据包
    WAIT_ACK = 7                  # 等待ACK确认
    RETRY = 8                     # 快速重试阶段
    SYNC = 9                      # 序号同步
    HARDWARE_RECOVER = 10         # 硬件恢复
    COMPLETED = 11                # 传输完成
    ABORTED = 12                  # 传输中止
```

### 2. 修改sender.py关键部分

#### 删除自适应策略相关代码

**在 `__init__` 方法中删除**:
```python
# 删除这些导入
from ..core.adaptive_strategy import AdaptiveTransmissionStrategy, AdaptiveParameters

# 删除这段初始化代码
if self.config.enable_adaptive_strategy:
    adaptive_params = AdaptiveParameters(...)
    self.adaptive_strategy = AdaptiveTransmissionStrategy(...)
else:
    self.adaptive_strategy = None
```

#### 更新 `_send_data_package` 方法

**原有方法**（约328-451行）需要重写为：

```python
def _send_data_package(self, addr: int, length: int) -> bool:
    """
    发送数据包（vNext新格式：seq + offset + payload）
    
    Args:
        addr: 起始地址（即offset）
        length: 数据长度
    
    Returns:
        成功返回True，失败返回False
    """
    try:
        seq_id = self._seq_id & 0xFFFF
        offset = addr  # vNext: offset即请求地址
        start_time = time.time()
        
        # 获取文件数据
        payload = self.get_file_data(addr, length)
        
        # 使用新的帧打包函数（包含offset）
        frame = FrameHandler.pack_send_data_frame(seq_id, offset, payload)
        
        if not frame:
            logger.error(f"打包数据帧失败: seq={seq_id} offset={offset}")
            return False
        
        def _write_and_wait_ack() -> bool:
            # 发送数据
            if not self.serial_manager.write(frame):
                return False
            
            # 等待ACK
            ack_start = time.time()
            port = self.serial_manager.port
            if port is None:
                logger.error("串口未打开，无法等待ACK")
                return False
            
            while time.time() - ack_start < self.config.request_timeout:
                cmd, ack_data = FrameHandler.read_frame(port, 6 + 10)
                
                if cmd is None:
                    continue
                
                if cmd == SerialCommand.ACK:
                    # vNext: 解析ACK中的offset
                    result = FramePayload.unpack_ack(ack_data)
                    if result:
                        ack_seq, ack_offset = result
                        # 基于offset确认（关键改动）
                        if ack_offset == offset:
                            logger.debug(f"收到ACK确认: seq={ack_seq} offset={ack_offset}")
                            return True
                        else:
                            logger.warning(f"ACK偏移量不匹配: {ack_offset} != {offset}")
                
                elif cmd == SerialCommand.NACK:
                    result = FramePayload.unpack_nack(ack_data)
                    if result:
                        nack_seq, nack_offset = result
                        logger.warning(f"收到NACK: seq={nack_seq} offset={nack_offset}")
                    return False  # 触发重试
                
                elif cmd == SerialCommand.SYNC_REQUEST:
                    # 处理序号同步请求
                    logger.info("收到序号同步请求")
                    result = FramePayload.unpack_sync_request(ack_data)
                    if result:
                        sync_seq, sync_offset = result
                        # 发送同步回复
                        reply_data = FramePayload.pack_sync_reply(
                            self._seq_id, offset, sync_seq
                        )
                        reply_frame = FrameHandler.pack_frame(
                            SerialCommand.SYNC_REPLY, reply_data
                        )
                        if reply_frame:
                            self.serial_manager.write(reply_frame)
                    continue
            
            # ACK超时
            return False
        
        # 重试逻辑（保持简单，不使用自适应）
        result = retry_call(
            _write_and_wait_ack,
            max_retry=self.config.retry_count,
            base_delay=self.config.backoff_base,
            logger=logger,
        )
        
        if result:
            # 成功：更新序号和进度
            self._seq_id = (self._seq_id + 1) & 0xFFFF
            self.send_size = offset + length
            logger.debug(f"数据包发送成功: offset={offset} len={length} new_seq={self._seq_id}")
            return True
        else:
            logger.error(f"数据包多次发送失败: offset={offset}")
            return False
    
    except Exception as e:
        logger.error(f"发送数据包异常: {e}")
        return False
```

#### 删除 `_wait_for_data_request` 中的自适应逻辑

**原代码第492-508行**需要删除自适应块长检查：

```python
# 删除这段自适应块长获取代码
# 获取当前自适应的块大小
current_block_size = self.config.max_data_length
if self.adaptive_strategy:
    current_block_size = self.adaptive_strategy.get_current_block_size()

# 限制请求长度不超过当前块大小
if length > current_block_size:
    logger.warning(f"请求长度 {length} 超过当前块大小 {current_block_size}，发送NACK")
    # ... NACK处理
    return True

# 替换为简单的固定块长检查
if length > self.config.max_data_length:
    logger.warning(f"请求长度 {length} 超过配置块大小 {self.config.max_data_length}")
    # 调整为配置块长
    length = self.config.max_data_length
```

### 3. 添加必要的导入

**在sender.py顶部添加**:
```python
from ..core.frame_payload import FramePayload
```

**删除的导入**:
```python
# 删除
from ..core.adaptive_strategy import AdaptiveTransmissionStrategy, AdaptiveParameters
```

---

## 阶段四：接收端重构 - 代码框架

### 1. 更新 `receive_data_package` 方法

**文件**: `src/serial_file_transfer/transfer/receiver.py`

**原代码第246-349行**需要重写为：

```python
def receive_data_package(self) -> bool:
    """
    接收数据包（vNext新格式：seq + offset + payload）
    
    Returns:
        成功返回True，失败返回False
    """
    try:
        # 读取数据包
        cmd, data = FrameHandler.read_frame(
            self.serial_manager.port,
            6 + self.config.max_data_length,
        )
        
        # 解析失败，发送NACK
        if cmd is None or data is None:
            nack_data = FramePayload.pack_nack(self._expected_seq, self.recv_size)
            nack_frame = FrameHandler.pack_frame(SerialCommand.NACK, nack_data)
            if nack_frame:
                self.serial_manager.write(nack_frame)
                logger.debug(f"解析失败，发送NACK: seq={self._expected_seq} offset={self.recv_size}")
            return False
        
        if cmd != SerialCommand.SEND_DATA:
            logger.error(f"收到错误命令: {hex(cmd)}")
            return False
        
        # vNext: 解析新格式载荷（seq + offset + payload）
        result = FramePayload.unpack_send_data(data)
        if not result:
            logger.error("解析SEND_DATA载荷失败")
            return False
        
        seq_id, offset, payload = result
        logger.debug(f"收到数据包: seq={seq_id} offset={offset} len={len(payload)}")
        
        # === 关键：重复帧识别（vNext核心改进）===
        if offset < self.recv_size:
            # 重复帧：已接收过的数据
            logger.warning(f"检测到重复帧: offset={offset} < recv_size={self.recv_size}")
            
            # 重发ACK但丢弃数据（幂等处理）
            ack_data = FramePayload.pack_ack(seq_id, offset)
            ack_frame = FrameHandler.pack_frame(SerialCommand.ACK, ack_data)
            if ack_frame:
                self.serial_manager.write(ack_frame)
                logger.info(f"重发ACK（重复帧）: seq={seq_id} offset={offset}")
            
            return True  # 不算失败，继续接收
        
        # === 偏移量验证 ===
        if offset != self.recv_size:
            # 偏移量跳跃或倒退
            logger.error(f"偏移量不匹配: offset={offset} != recv_size={self.recv_size}")
            
            # 发送NACK
            nack_data = FramePayload.pack_nack(seq_id, self.recv_size)
            nack_frame = FrameHandler.pack_frame(SerialCommand.NACK, nack_data)
            if nack_frame:
                self.serial_manager.write(nack_frame)
            
            # 检查是否需要序号同步
            if self.sequence_recovery.record_sequence_mismatch():
                logger.info("触发序号同步...")
                synced_seq = self.sequence_recovery.perform_sequence_sync(
                    self.serial_manager,
                    self._expected_seq,
                    self.recv_size
                )
                if synced_seq is not None:
                    self._expected_seq = synced_seq & 0xFFFF
                    logger.info(f"序号同步成功: {synced_seq}")
            
            return False
        
        # === 序号验证 ===
        if seq_id != self._expected_seq:
            logger.warning(f"序号不匹配: seq={seq_id} != expected={self._expected_seq}")
            # 发送NACK
            nack_data = FramePayload.pack_nack(seq_id, offset)
            nack_frame = FrameHandler.pack_frame(SerialCommand.NACK, nack_data)
            if nack_frame:
                self.serial_manager.write(nack_frame)
            return False
        
        # === 数据有效：写入文件 ===
        self.recv_size += len(payload)
        if self._file_handle is not None:
            self._file_handle.write(payload)
        else:
            self.file_data += payload
        
        # 发送ACK（包含offset）
        ack_data = FramePayload.pack_ack(seq_id, offset)
        ack_frame = FrameHandler.pack_frame(SerialCommand.ACK, ack_data)
        if ack_frame:
            self.serial_manager.write(ack_frame)
            logger.debug(f"发送ACK: seq={seq_id} offset={offset}")
        
        # 更新期望序号
        self._expected_seq = (self._expected_seq + 1) & 0xFFFF
        
        # 重置序号不匹配计数器
        self.sequence_recovery.reset_mismatch_counter()
        
        return True
    
    except Exception as e:
        logger.error(f"接收数据包异常: {e}")
        return False
```

### 2. 删除动态块长调整

**在receiver.py中查找并删除**:
```python
# 删除这段处理NACK调整块长的代码（约273-277行）
if cmd == SerialCommand.NACK:
    seq, corr_len = struct.unpack("<HH", data[:4])
    logger.warning(f"收到 NACK，调整块长 {corr_len}")
    self.config.max_data_length = corr_len
    return False
```

---

## 测试验证步骤

### 1. 单元测试

```bash
# 测试帧载荷处理
pytest tests/unit/test_frame_payload.py -v

# 测试帧处理器
pytest tests/unit/test_frame_handler_vnext.py -v

# 测试发送端（待创建）
pytest tests/unit/test_sender_vnext.py -v

# 测试接收端（待创建）
pytest tests/unit/test_receiver_vnext.py -v
```

### 2. 集成测试

```bash
# 端到端测试
pytest tests/integration/test_end_to_end.py -v

# 异常恢复测试
pytest tests/integration/test_abnormal_recovery.py -v
```

### 3. 覆盖率检查

```bash
pytest --cov=src/serial_file_transfer --cov-report=html --cov-report=term-missing
```

---

## 关键改动清单

### 发送端改动
- [x] 删除 `AdaptiveTransmissionStrategy` 导入和初始化
- [x] 更新 `_send_data_package` 使用 `pack_send_data_frame`
- [x] ACK验证改为检查 `ack_offset == offset`
- [x] 删除所有 `adaptive_strategy.record_*` 调用
- [x] 删除 `_wait_for_data_request` 中的自适应块长检查

### 接收端改动
- [x] 更新 `receive_data_package` 使用 `unpack_send_data`
- [x] 添加重复帧识别逻辑（`offset < recv_size`）
- [x] 实现重复帧幂等ACK（重发ACK，丢弃数据）
- [x] 偏移量优先验证（`offset == recv_size`）
- [x] 删除动态块长调整逻辑

---

## 后续步骤建议

1. **先完成发送端重构**
   - 修改 `sender.py`
   - 编写单元测试
   - 验证通过

2. **再完成接收端重构**
   - 修改 `receiver.py`
   - 编写单元测试
   - 验证通过

3. **集成测试**
   - 端到端测试
   - 异常注入测试
   - 性能测试

4. **硬件验证**
   - 真实串口环境
   - 长时间稳定性
   - 干扰环境

5. **发布准备**
   - 文档更新
   - 迁移指南
   - 发布说明

---

**祝重构顺利！** 🚀

