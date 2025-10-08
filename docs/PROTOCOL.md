# 串口文件传输协议规范

## 协议概述

### 设计目标
- **可靠性**: CRC校验、ACK确认、错误重传
- **简洁性**: 固定块长配置、清晰的状态转移
- **可扩展**: 支持offset字段、序号同步机制

### 传输流程
```
发送端                           接收端
  │                               │
  │◄─────── REQUEST_FILE_NAME ────│
  │                               │
  │─────── REPLY_FILE_NAME ──────►│
  │                               │
  │◄─────── REQUEST_FILE_SIZE ────│
  │                               │
  │─────── REPLY_FILE_SIZE ──────►│
  │                               │
  │◄─────── REQUEST_DATA ─────────│
  │                               │
  │─────── SEND_DATA ────────────►│
  │                               │
  │◄─────── ACK/NACK ─────────────│
  │                               │
  └───── (循环直到传输完成) ──────┘
```

---

## 命令字定义

| 命令字 | 十六进制 | ASCII | 用途 | 数据载荷 |
|--------|----------|-------|------|----------|
| REQUEST_FILE_NAME | 0x51 | 'Q' | 请求文件名 | 2字节特征值 0x55AA |
| REPLY_FILE_NAME | 0x52 | 'R' | 回复文件名 | 2字节长度 + UTF-8文件名 |
| REQUEST_FILE_SIZE | 0x61 | 'a' | 请求文件大小 | 2字节特征值 0x55AA |
| REPLY_FILE_SIZE | 0x62 | 'b' | 回复文件大小 | 4字节文件大小 |
| REQUEST_DATA | 0x63 | 'c' | 请求数据包 | 4字节地址 + 2字节长度 |
| SEND_DATA | 0x64 | 'd' | 发送数据包 | seq(2) + offset(4) + payload |
| ACK | 0x65 | 'e' | 数据包确认 | seq(2) + offset(4) |
| NACK | 0x66 | 'f' | 重传请求 | seq(2) + offset(4) |
| SYNC_REQUEST | 0x67 | 'g' | 序号同步请求 | seq(2) + offset(4) |
| SYNC_REPLY | 0x68 | 'h' | 序号同步回复 | seq(2) + offset(4) + ack(2) |

---

## 帧格式定义

### 通用帧结构
```
+-----+-------+-------+--------+-------+-------+
| CMD | LEN_L | LEN_H |  DATA  | CRC_L | CRC_H |
| 1B  |  1B   |  1B   |  N B   |  1B   |  1B   |
+-----+-------+-------+--------+-------+-------+
```

**字段说明**:
- **CMD**: 命令字（1字节）
- **LEN**: 数据长度（2字节，小端序）
- **DATA**: 数据载荷（N字节）
- **CRC**: CRC16校验和（2字节，小端序）

---

### SEND_DATA 载荷格式（核心）

```
+-------+-------+----------+----------+----------+----------+----------+
| SEQ_L | SEQ_H | OFFSET_0 | OFFSET_1 | OFFSET_2 | OFFSET_3 | PAYLOAD  |
|  1B   |  1B   |   1B     |   1B     |   1B     |   1B     |   N B    |
+-------+-------+----------+----------+----------+----------+----------+
```

**字段说明**:
- **SEQ**: 序号（2字节，小端序，0-65535循环）
- **OFFSET**: 文件偏移量（4字节，小端序，绝对字节位置）
- **PAYLOAD**: 文件数据（N字节）

**关键特性**:
- ✅ offset 明确指示数据在文件中的位置
- ✅ 接收端可基于 offset 判断是否重复帧
- ✅ 序号用于防重与窗口控制，不参与进度计算

---

### ACK/NACK 载荷格式

```
+-------+-------+----------+----------+----------+----------+
| SEQ_L | SEQ_H | OFFSET_0 | OFFSET_1 | OFFSET_2 | OFFSET_3 |
|  1B   |  1B   |   1B     |   1B     |   1B     |   1B     |
+-------+-------+----------+----------+----------+----------+
```

**字段说明**:
- **SEQ**: 确认的序号（2字节）
- **OFFSET**: 确认的偏移量（4字节，小端序）

**关键特性**:
- ✅ 发送端根据 offset 判断是否已确认
- ✅ 接收端可重发历史 ACK（幂等），不影响传输进度

---

### SYNC 同步帧载荷格式

**SYNC_REQUEST**:
```
+-------+-------+----------+----------+----------+----------+
| SEQ_L | SEQ_H | OFFSET_0 | OFFSET_1 | OFFSET_2 | OFFSET_3 |
+-------+-------+----------+----------+----------+----------+
```

**SYNC_REPLY**:
```
+-------+-------+----------+----------+----------+----------+-------+-------+
| SEQ_L | SEQ_H | OFFSET_0 | OFFSET_1 | OFFSET_2 | OFFSET_3 | ACK_L | ACK_H |
+-------+-------+----------+----------+----------+----------+-------+-------+
```

**特性**:
- ✅ 基于 offset 同步，不依赖块长推算
- ✅ 发送端可根据 offset 调整序号和发送位置

---

## 核心机制

### 1. 重复帧幂等处理

**接收端逻辑**:
```python
if offset < recv_size:
    # 重复帧：重发ACK但丢弃数据
    send_ack(seq_id, offset)
    return True  # 不算失败，继续接收

elif offset == recv_size:
    if seq_id == expected_seq:
        # 新包：写入数据
        write_data(payload)
        send_ack(seq_id, offset)
        expected_seq = (expected_seq + 1) & 0xFFFF
    else:
        # 序号不匹配：发送NACK
        send_nack(seq_id, recv_size)
else:
    # 偏移量跳跃：发送NACK
    send_nack(seq_id, recv_size)
```

**关键优化**:
- ✅ `offset < recv_size` 识别重复帧
- ✅ 重发 ACK 打破 ACK 丢失死锁
- ✅ 数据不重复写入，保证完整性

---

### 2. 基于 offset 的数据确认

**发送端逻辑**:
```python
# 发送数据包
frame = pack_send_data_frame(seq_id, offset, payload)
serial.write(frame)

# 等待ACK
cmd, data = read_frame()
if cmd == ACK:
    ack_seq, ack_offset = unpack_ack(data)
    if ack_offset == offset:  # 基于offset确认
        seq_id = (seq_id + 1) & 0xFFFF
        return True
```

**优势**:
- ✅ 不依赖序号推算进度
- ✅ ACK丢失后重传时能正确识别
- ✅ 避免块长变化导致的不一致

---

### 3. 序号同步机制

**触发条件**: 连续3次序号不匹配

**同步流程**:
```
接收端                     发送端
  │                         │
  │─── SYNC_REQUEST(seq, offset) ──►│
  │                         │
  │◄─── SYNC_REPLY(seq, offset, ack) ──│
  │                         │
  └── 调整期望序号 ─────────┘
```

**特性**:
- ✅ 自动恢复序号漂移
- ✅ 基于 offset 确定同步点
- ✅ 不中断传输流程

---

### 4. 统一重试流程

```
快速重试（3次，0.1秒间隔）
    ↓ 失败
序号同步（发送SYNC_REQUEST）
    ↓ 失败
硬件恢复（清理缓冲区，延迟1秒）
    ↓ 失败
传输中止
```

**配置参数**:
```yaml
transfer:
  retry_count: 3              # 快速重试次数
  backoff_base: 0.5           # 重试间隔基数
  max_retries: 5              # 最大重试次数
  sequence_mismatch_threshold: 3  # 序号不匹配阈值
```

---

## 配置规范

### 推荐配置

**波特率与块长对应**:
| 波特率 | 推荐块长 | 说明 |
|--------|----------|------|
| 9600-57600 | 512 | 低速链路 |
| 115200-460800 | 1024 | 中速链路（默认）|
| 921600-1000000 | 2048 | 高速链路 |
| 1500000-1728000 | 4096-8192 | 超高速链路 |

### 配置示例

```yaml
serial:
  baudrate: 115200
  timeout: 0.2

transfer:
  max_data_length: 1024      # 固定块长
  request_timeout: 30
  data_timeout: 5
  retry_count: 3
  backoff_base: 0.5
  max_retries: 5
  
  # 序号恢复
  enable_sequence_recovery: true
  sequence_mismatch_threshold: 3
  sync_timeout: 2
```

---

## 错误处理

### 错误类型

| 错误码 | 名称 | 说明 | 恢复策略 |
|--------|------|------|----------|
| E001 | FRAME_PACK_ERROR | 帧打包失败 | 记录日志，返回失败 |
| E002 | FRAME_UNPACK_ERROR | 帧解包失败 | 发送 NACK，重试 |
| E003 | CRC_ERROR | CRC 校验错误 | 发送 NACK，重试 |
| E004 | SEQ_MISMATCH | 序号不匹配 | 发送 NACK，触发同步 |
| E005 | OFFSET_MISMATCH | 偏移量不匹配 | 发送 NACK，触发同步 |
| E006 | ACK_TIMEOUT | ACK 超时 | 快速重试 → 同步 → 硬件恢复 |
| E007 | DUPLICATE_FRAME | 重复帧 | 重发 ACK，丢弃数据 |

### 日志规范

**传输事件日志**:
```
[时间] [级别] [模块] 事件: cmd=0x64 seq=123 offset=1234567 len=4096
```

**示例**:
```
[2025-10-08 14:46:34.885] INFO [sender] send_data: cmd=0x64 seq=123 offset=1234567 len=4096
[2025-10-08 14:46:34.900] WARNING [receiver] nack: seq=123 offset=1234567 error=E004
[2025-10-08 14:46:35.000] INFO [sender] retry: stage=fast count=1
```

---

## 协议扩展

### 未来可能的扩展

1. **滑动窗口**: 支持多包同时发送
2. **压缩传输**: 支持数据压缩
3. **断点续传**: 支持中断后继续
4. **加密传输**: 支持数据加密

### 扩展约束

- offset 字段为4字节（32位），最大支持 4GB 文件
- 如需支持更大文件，可扩展 offset 为8字节

---

## 兼容性说明

### 当前实现状态

**✅ 已实现**:
- offset 字段支持（SEND_DATA、ACK/NACK）
- 重复帧幂等处理
- 基于 offset 的数据确认
- 序号同步机制

**⚠️ 部分实现**:
- 状态机架构（设计完成，未实现）
- 自适应策略删除（计划中）

**📐 设计文档**:
- 完整状态机设计见 `design/vnext/state_machine_*.md`
- 协议详细规格见 `design/vnext/protocol_spec_vnext.md`

---

**协议版本**: v1.0  
**最后更新**: 2025-10-08

