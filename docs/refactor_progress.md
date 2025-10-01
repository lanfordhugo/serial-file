# vNext 重构进度跟踪

**当前版本**: v2.0 (vNext)  
**最后更新**: 2025-10-01  
**当前阶段**: 阶段三 - 发送端重构

---

## ✅ 已完成阶段

### 阶段一：协议规格敲定 ✅

**完成时间**: 2025-10-01  
**交付文档**:
- `docs/protocol_spec_vnext.md` - 完整协议规格
- `docs/state_machine_sender.md` - 发送端状态机设计
- `docs/state_machine_receiver.md` - 接收端状态机设计
- `docs/test_plan.md` - 详细测试计划

**核心设计**:
- ✅ 新帧格式：SEND_DATA = seq(2) + offset(4) + payload
- ✅ ACK/NACK格式：seq(2) + offset(4)
- ✅ 删除自适应块长策略
- ✅ 重复帧幂等处理
- ✅ 统一重试流程

### 阶段二：底层支撑模块改造 ✅

**完成时间**: 2025-10-01  
**交付代码**:
- `src/serial_file_transfer/config/constants.py` - 更新常量定义
- `src/serial_file_transfer/config/settings.py` - 删除自适应参数
- `config/transfer.yaml` - 更新配置文件
- `src/serial_file_transfer/core/serial_transport.py` - 抽象接口层
- `src/serial_file_transfer/core/frame_payload.py` - 载荷处理模块
- `src/serial_file_transfer/core/frame_handler.py` - 帧处理增强

**测试验证**:
- ✅ `tests/unit/test_frame_payload.py` - 29个用例通过
- ✅ `tests/unit/test_frame_handler_vnext.py` - 12个用例通过

---

## 🔄 当前阶段：阶段三 - 发送端重构

### 任务清单

- [x] 3.1 定义发送端状态枚举
- [ ] 3.2 创建SenderSessionController会话控制器
- [ ] 3.3 实现状态处理方法
- [ ] 3.4 重构FileSender使用新格式（offset）
- [ ] 3.5 删除自适应策略调用
- [ ] 3.6 编写发送端单元测试

### 详细执行步骤

#### 步骤 3.1：定义发送端状态枚举

**文件**: `src/serial_file_transfer/core/sender_state.py` (新建)

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

#### 步骤 3.2：创建会话控制器

**文件**: `src/serial_file_transfer/core/sender_session.py` (新建)

**主要类**:
- `SenderSessionController`: 状态机核心控制器
- 包含所有状态处理方法
- 统一重试策略

**关键方法**:
```python
def _handle_send_data(self) -> bool:
    """发送数据包（使用新格式 seq + offset）"""
    # 使用 FrameHandler.pack_send_data_frame()
    # 包含 offset 字段
    pass

def _handle_wait_ack(self) -> bool:
    """等待ACK（检查 offset 而非仅序号）"""
    # 解析 ACK 中的 offset
    # 基于 offset 确认传输进度
    pass

def _handle_retry(self) -> bool:
    """快速重试（3次，间隔0.1秒）"""
    pass

def _handle_sync(self) -> bool:
    """序号同步（发送 SYNC_REQUEST）"""
    pass

def _handle_hardware_recover(self) -> bool:
    """硬件恢复（清理缓冲区 + 保守重试）"""
    pass
```

#### 步骤 3.3：重构FileSender

**文件**: `src/serial_file_transfer/transfer/sender.py`

**主要修改**:
1. 删除 `AdaptiveTransmissionStrategy` 相关代码
2. 更新 `_send_data_package` 使用新格式
3. 集成 `SenderSessionController`
4. 简化重试逻辑

**关键代码片段**:
```python
# 旧版本（删除）
from ..core.adaptive_strategy import AdaptiveTransmissionStrategy

# 新版本（使用）
from ..core.sender_session import SenderSessionController
from ..core.frame_payload import FramePayload

def _send_data_package(self, addr: int, length: int) -> bool:
    """发送数据包（vNext新格式）"""
    seq_id = self._seq_id & 0xFFFF
    offset = addr  # 偏移量即请求地址
    
    # 获取数据
    payload = self.get_file_data(addr, length)
    
    # 使用新的帧处理函数
    frame = FrameHandler.pack_send_data_frame(seq_id, offset, payload)
    
    if not frame:
        logger.error("打包数据帧失败")
        return False
    
    # 发送并等待ACK
    if not self.serial_manager.write(frame):
        return False
    
    # 等待ACK（检查offset）
    cmd, data = FrameHandler.read_frame(self.serial_manager.port, ...)
    
    if cmd == SerialCommand.ACK:
        result = FramePayload.unpack_ack(data)
        if result:
            ack_seq, ack_offset = result
            # 基于offset确认
            if ack_offset == offset:
                self._seq_id = (self._seq_id + 1) & 0xFFFF
                self.send_size = offset + length
                return True
    
    return False
```

#### 步骤 3.4：删除自适应策略

**需要删除的代码**:
```python
# sender.py 中删除
from ..core.adaptive_strategy import AdaptiveTransmissionStrategy, AdaptiveParameters

# __init__ 中删除
if self.config.enable_adaptive_strategy:
    self.adaptive_strategy = AdaptiveTransmissionStrategy(...)
else:
    self.adaptive_strategy = None

# _send_data_package 中删除所有 adaptive_strategy 相关调用
if self.adaptive_strategy:
    self.adaptive_strategy.record_packet_result(...)
    adjustment = self.adaptive_strategy.adjust_parameters()
    ...
```

**保留的重试逻辑**:
- 快速重试（由配置决定次数）
- 序号同步（连续失败触发）
- 硬件恢复（同步失败后）

#### 步骤 3.5：编写单元测试

**文件**: `tests/unit/test_sender_vnext.py` (新建)

**测试用例**:
1. `test_send_data_with_offset` - 验证offset字段正确发送
2. `test_ack_with_offset` - 验证基于offset确认
3. `test_duplicate_ack_handling` - 验证重复ACK处理
4. `test_ack_loss_recovery` - 验证ACK丢失恢复
5. `test_nack_retry` - 验证NACK触发重试
6. `test_sequence_sync` - 验证序号同步流程
7. `test_hardware_recovery` - 验证硬件恢复流程
8. `test_no_adaptive_strategy` - 验证未使用自适应策略

**Mock策略**:
- 使用 `MockSerialTransport` 模拟串口
- 使用 `unittest.mock.patch` 模拟文件读取
- 注入ACK丢失、NACK等异常

#### 步骤 3.6：集成测试

**验证点**:
- 正常传输流程完整性
- ACK丢失后正确重试
- 重复帧不影响传输
- 序号同步能恢复
- 硬件恢复能成功

---

## 📋 待执行阶段

### 阶段四：接收端重构（状态机化）

**任务清单**:
- [ ] 4.1 定义接收端状态枚举
- [ ] 4.2 创建ReceiverSessionController
- [ ] 4.3 实现重复帧识别与幂等ACK
- [ ] 4.4 重构FileReceiver使用新格式
- [ ] 4.5 删除动态块长调整逻辑
- [ ] 4.6 编写接收端单元测试

**核心改造**:
- 接收端识别 `offset < recv_size` → 重复帧
- 重发ACK但丢弃数据（幂等性）
- 基于offset验证数据正确性

### 阶段五：集成与联调准备

**任务清单**:
- [ ] 5.1 搭建loopback测试环境
- [ ] 5.2 编写异常注入工具
- [ ] 5.3 执行端到端测试
- [ ] 5.4 编写集成测试脚本
- [ ] 5.5 生成测试报告

### 阶段六：硬件联调与验证

**任务清单**:
- [ ] 6.1 真实串口环境测试
- [ ] 6.2 干扰环境测试
- [ ] 6.3 长时间稳定性测试
- [ ] 6.4 性能指标验证
- [ ] 6.5 问题记录与修复

### 阶段七：回归、发布与交接

**任务清单**:
- [ ] 7.1 回归测试
- [ ] 7.2 编写迁移指南
- [ ] 7.3 更新README和文档
- [ ] 7.4 准备发布说明
- [ ] 7.5 代码评审与交接

---

## 🔍 关键设计要点提醒

### 发送端重构要点

1. **offset字段必须携带**
   - 每个SEND_DATA帧包含seq + offset + payload
   - offset = addr（请求的起始地址）
   
2. **基于offset确认**
   - ACK携带 seq + offset
   - 发送端检查 `ack_offset == current_offset`
   - 不再依赖序号推算进度

3. **重复ACK识别**
   - 收到旧offset的ACK时，判断是否已确认
   - 避免重复处理

4. **删除自适应逻辑**
   - 块长固定为 `config.max_data_length`
   - 不再动态调整
   - 简化代码复杂度

5. **统一重试流程**
   - 快速重试（3次，0.1秒间隔）
   - 序号同步（连续失败触发）
   - 硬件恢复（清理缓冲区 + 保守重试）
   - 中止（所有手段失败）

### 接收端重构要点

1. **重复帧幂等处理**
   ```python
   if offset < recv_size:
       # 重复帧：重发ACK，丢弃数据
       self._send_dup_ack(seq_id, offset)
       return True  # 继续接收下一包
   ```

2. **偏移量优先验证**
   ```python
   if offset == recv_size and seq_id == expected_seq:
       # 完全匹配：接受数据
   elif offset == recv_size:
       # 偏移量正确但序号不匹配：触发同步
   else:
       # 偏移量错误：发送NACK
   ```

3. **删除块长协商**
   - 不再根据NACK调整块长
   - 始终使用配置的固定块长

---

## 🛠️ 开发建议

1. **渐进式重构**
   - 先完成状态机框架
   - 再逐步替换旧逻辑
   - 保持向后兼容接口

2. **充分测试**
   - 每个步骤完成后运行单元测试
   - 使用Mock隔离外部依赖
   - 覆盖异常场景

3. **代码审查**
   - 状态机逻辑是否清晰
   - 错误处理是否完善
   - 日志输出是否充分

4. **文档同步**
   - 更新API文档
   - 更新配置说明
   - 更新故障排查指南

---

## 📞 问题与反馈

如遇到问题，参考：
- `docs/protocol_spec_vnext.md` - 协议规格
- `docs/state_machine_sender.md` - 发送端状态机设计
- `docs/test_plan.md` - 测试计划

---

**持续更新中...**

