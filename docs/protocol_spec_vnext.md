# 串口文件传输协议规格 vNext

**版本**: v2.0 (重构版)  
**创建日期**: 2025-10-01  
**状态**: 设计阶段

## 一、协议概述

### 1.1 设计目标
- **可靠性**: 解决 ACK 丢失、重复帧死锁、序号漂移等问题
- **清晰性**: 基于明确状态机，消除隐式协商和推断
- **简单性**: 固定块长配置，移除自适应策略
- **可测试性**: 支持单元测试、集成测试和硬件联调

### 1.2 主要变更
- ✅ 数据帧增加 `offset` 字段，以偏移量为主确认点
- ✅ ACK/NACK 帧携带 `{seq_id, offset}` 支持幂等确认
- ✅ 删除自适应块长协商，改为配置文件固定
- ✅ 统一重试与恢复策略
- ✅ 建立明确的双端状态机模型

---

## 二、现有协议对照表

### 2.1 命令字定义（保持不变）

| 命令字 | 十六进制 | ASCII | 用途 | 数据载荷 |
|--------|----------|-------|------|----------|
| REQUEST_FILE_NAME | 0x51 | 'Q' | 请求文件名 | 2字节特征值 0x55AA |
| REPLY_FILE_NAME | 0x52 | 'R' | 回复文件名 | 2字节长度 + UTF-8文件名 |
| REQUEST_FILE_SIZE | 0x61 | 'a' | 请求文件大小 | 2字节特征值 0x55AA |
| REPLY_FILE_SIZE | 0x62 | 'b' | 回复文件大小 | 4字节文件大小 |
| REQUEST_DATA | 0x63 | 'c' | 请求数据包 | 4字节地址 + 2字节长度 |
| SEND_DATA | 0x64 | 'd' | 发送数据包 | **见2.2节（有变更）** |
| ACK | 0x65 | 'e' | 数据包确认 | **见2.3节（有变更）** |
| NACK | 0x66 | 'f' | 重传请求 | **见2.3节（有变更）** |
| SYNC_REQUEST | 0x67 | 'g' | 序号同步请求 | **见2.4节（有变更）** |
| SYNC_REPLY | 0x68 | 'h' | 序号同步回复 | **见2.4节（有变更）** |

### 2.2 帧格式定义

#### 2.2.1 通用帧结构（不变）
```
+--------+--------+--------+----------+--------+--------+
|  CMD   | LEN_L  | LEN_H  |   DATA   | CRC_L  | CRC_H  |
| (1B)   | (1B)   | (1B)   |  (N B)   | (1B)   | (1B)   |
+--------+--------+--------+----------+--------+--------+
```

- **CMD**: 命令字（1字节）
- **LEN**: 数据长度（2字节，小端序）
- **DATA**: 数据载荷（N字节）
- **CRC**: CRC16校验和（2字节，小端序）

#### 2.2.2 旧版 SEND_DATA 载荷格式
```
+--------+--------+----------+
| SEQ_L  | SEQ_H  | PAYLOAD  |
| (1B)   | (1B)   |  (N B)   |
+--------+--------+----------+
```
- **SEQ**: 序号（2字节，小端序，0-65535循环）
- **PAYLOAD**: 文件数据（N字节）

**问题**: 
- ❌ ACK 丢失后序号与偏移量解耦，导致死锁
- ❌ 自适应块长变化时，序号推算 `recv_size // max_data_length` 不准确
- ❌ 重复帧无法识别，接收端总是发送 NACK

#### 2.2.3 新版 SEND_DATA 载荷格式（✨重点变更）
```
+--------+--------+----------+----------+----------+----------+----------+
| SEQ_L  | SEQ_H  | OFFSET_0 | OFFSET_1 | OFFSET_2 | OFFSET_3 | PAYLOAD  |
| (1B)   | (1B)   |  (1B)    |  (1B)    |  (1B)    |  (1B)    |  (N B)   |
+--------+--------+----------+----------+----------+----------+----------+
```
- **SEQ**: 序号（2字节，小端序，用于窗口控制与防重）
- **OFFSET**: 文件偏移量（4字节，小端序，绝对字节位置）
- **PAYLOAD**: 文件数据（N字节）

**改进**:
- ✅ 偏移量明确指示数据在文件中的位置
- ✅ 接收端可基于 offset 判断是否重复帧
- ✅ 序号仅用于防重与窗口控制，不参与进度计算

### 2.3 ACK/NACK 载荷格式（✨重点变更）

#### 2.3.1 旧版格式
```
ACK/NACK: SEQ_L | SEQ_H (2字节)
```

**问题**:
- ❌ 只有序号，无法确认具体偏移量
- ❌ ACK 丢失后重发时，接收端已推进序号，导致永久不匹配

#### 2.3.2 新版格式
```
+--------+--------+----------+----------+----------+----------+
| SEQ_L  | SEQ_H  | OFFSET_0 | OFFSET_1 | OFFSET_2 | OFFSET_3 |
| (1B)   | (1B)   |  (1B)    |  (1B)    |  (1B)    |  (1B)    |
+--------+--------+----------+----------+----------+----------+
```
- **SEQ**: 确认的序号（2字节）
- **OFFSET**: 确认的偏移量（4字节，小端序）

**改进**:
- ✅ 发送端根据 offset 判断是否已确认，避免序号推算错误
- ✅ 接收端可重发历史 ACK（幂等），不影响传输进度

### 2.4 SYNC 同步帧载荷格式（✨优化）

#### 2.4.1 旧版格式
```
SYNC_REQUEST: EXPECTED_SEQ_L | EXPECTED_SEQ_H (2字节)
SYNC_REPLY:   EXPECTED_SEQ_L | EXPECTED_SEQ_H | CURRENT_SEQ_L | CURRENT_SEQ_H (4字节)
```

#### 2.4.2 新版格式
```
SYNC_REQUEST:
+--------+--------+----------+----------+----------+----------+
| SEQ_L  | SEQ_H  | OFFSET_0 | OFFSET_1 | OFFSET_2 | OFFSET_3 |
+--------+--------+----------+----------+----------+----------+

SYNC_REPLY:
+--------+--------+----------+----------+----------+----------+--------+--------+
| SEQ_L  | SEQ_H  | OFFSET_0 | OFFSET_1 | OFFSET_2 | OFFSET_3 | ACK_L  | ACK_H  |
+--------+--------+----------+----------+----------+----------+--------+--------+
```

**改进**:
- ✅ 基于 offset 同步，不依赖块长推算
- ✅ 发送端可根据 offset 调整序号和发送位置

---

## 三、状态机设计

### 3.1 发送端状态机

```
┌─────────────┐
│    IDLE     │
└──────┬──────┘
       │ init_file()
       ▼
┌─────────────────┐
│ WAIT_FILENAME   │◄─────────┐
│   _REQUEST      │          │ timeout retry
└──────┬──────────┘          │
       │ REQUEST_FILE_NAME   │
       ▼                     │
┌─────────────────┐          │
│  SEND_FILENAME  ├──────────┘
└──────┬──────────┘
       │ send_filename()
       ▼
┌─────────────────┐
│  WAIT_SIZE      │◄─────────┐
│   _REQUEST      │          │
└──────┬──────────┘          │
       │ REQUEST_FILE_SIZE   │
       ▼                     │
┌─────────────────┐          │
│  SEND_SIZE      ├──────────┘
└──────┬──────────┘
       │ send_file_size()
       ▼
┌─────────────────┐
│  WAIT_DATA      │◄────────────────┐
│   _REQUEST      │                 │
└──────┬──────────┘                 │
       │ REQUEST_DATA               │
       ▼                            │
┌─────────────────┐                 │
│  SEND_DATA      │                 │
└──────┬──────────┘                 │
       │ _send_data_package()       │
       ▼                            │
┌─────────────────┐                 │
│   WAIT_ACK      │                 │
└──────┬──────┬───┘                 │
       │ ACK  │ NACK/Timeout        │
       │      ├─────────────────────┤
       │      │                     │
       │      ▼                     │
       │ ┌─────────────────┐        │
       │ │ RETRY/RECOVER   │        │
       │ │  (快速→同步→   │        │
       │ │   硬件恢复)     │        │
       │ └─────────┬───────┘        │
       │           │ continue       │
       │           └────────────────┘
       ▼
┌─────────────────┐
│   COMPLETED     │
└─────────────────┘
```

**状态说明**:
- `IDLE`: 初始状态
- `WAIT_FILENAME_REQUEST`: 等待接收端请求文件名
- `SEND_FILENAME`: 发送文件名
- `WAIT_SIZE_REQUEST`: 等待接收端请求文件大小
- `SEND_SIZE`: 发送文件大小
- `WAIT_DATA_REQUEST`: 等待接收端请求数据
- `SEND_DATA`: 发送数据包（携带 seq + offset）
- `WAIT_ACK`: 等待 ACK/NACK
- `RETRY/RECOVER`: 重试与恢复（快速重试→协议同步→硬件恢复）
- `COMPLETED`: 传输完成
- `ABORTED`: 传输中止

### 3.2 接收端状态机

```
┌─────────────┐
│    IDLE     │
└──────┬──────┘
       │ start_transfer()
       ▼
┌─────────────────┐
│ REQUEST_FILENAME│
└──────┬──────────┘
       │ send_filename_request()
       ▼
┌─────────────────┐
│ WAIT_FILENAME   │◄─────────┐
│   _REPLY        │          │ timeout retry
└──────┬──────────┘          │
       │ REPLY_FILE_NAME     │
       ▼                     │
┌─────────────────┐          │
│ VALIDATE_NAME   ├──────────┘
└──────┬──────────┘
       │ receive_filename()
       ▼
┌─────────────────┐
│ REQUEST_SIZE    │
└──────┬──────────┘
       │ send_file_size_request()
       ▼
┌─────────────────┐
│ WAIT_SIZE_REPLY │◄─────────┐
└──────┬──────────┘          │
       │ REPLY_FILE_SIZE     │
       ▼                     │
┌─────────────────┐          │
│ VALIDATE_SIZE   ├──────────┘
└──────┬──────────┘
       │ receive_file_size()
       ▼
┌─────────────────┐
│ REQUEST_DATA    │◄────────────────┐
└──────┬──────────┘                 │
       │ send_data_request()        │
       ▼                            │
┌─────────────────┐                 │
│ WAIT_DATA_REPLY │                 │
└──────┬──────────┘                 │
       │ SEND_DATA                  │
       ▼                            │
┌─────────────────┐                 │
│ VALIDATE_DATA   │                 │
│  (检查seq/     │                 │
│   offset重复)   │                 │
└──────┬──────┬───┘                 │
       │ 新包 │ 重复包              │
       │      │                     │
       │      ▼                     │
       │ ┌─────────────────┐        │
       │ │ SEND_DUP_ACK    │        │
       │ │ (重发ACK丢弃)   ├────────┘
       │ └─────────────────┘        │
       │                            │
       ▼                            │
┌─────────────────┐                 │
│  WRITE_DATA     │                 │
└──────┬──────────┘                 │
       │ write to file              │
       ▼                            │
┌─────────────────┐                 │
│   SEND_ACK      ├─────────────────┘
└──────┬──────────┘
       │ all data received
       ▼
┌─────────────────┐
│   COMPLETED     │
└─────────────────┘
```

**关键逻辑**:
- `VALIDATE_DATA`: 检查 `seq_id` 和 `offset`
  - 若 `offset < recv_size`: 重复帧 → 发送 ACK 但丢弃数据
  - 若 `offset == recv_size && seq_id == expected_seq`: 新包 → 写入数据
  - 若序号不匹配: 发送 NACK，触发序号同步或重试

---

## 四、错误码与日志规范

### 4.1 错误码定义

| 错误码 | 名称 | 说明 | 恢复策略 |
|--------|------|------|----------|
| E001 | FRAME_PACK_ERROR | 帧打包失败 | 记录日志，返回失败 |
| E002 | FRAME_UNPACK_ERROR | 帧解包失败 | 发送 NACK，重试 |
| E003 | CRC_ERROR | CRC 校验错误 | 发送 NACK，重试 |
| E004 | SEQ_MISMATCH | 序号不匹配 | 发送 NACK，触发同步 |
| E005 | OFFSET_MISMATCH | 偏移量不匹配 | 发送 NACK，触发同步 |
| E006 | ACK_TIMEOUT | ACK 超时 | 快速重试 → 同步 → 硬件恢复 |
| E007 | DUPLICATE_FRAME | 重复帧 | 重发 ACK，丢弃数据 |
| E008 | SYNC_FAILED | 序号同步失败 | 硬件恢复 → 中止 |
| E009 | HARDWARE_RECOVERY | 硬件恢复 | 清理缓冲区，延迟重试 |
| E010 | TRANSFER_ABORTED | 传输中止 | 删除不完整文件，记录日志 |

### 4.2 日志字段规范

**通用字段**:
```json
{
  "timestamp": "2025-10-01 14:46:22.851",
  "level": "INFO|WARNING|ERROR",
  "module": "sender|receiver|frame_handler",
  "message": "描述信息"
}
```

**传输事件字段**:
```json
{
  "event": "send_data|receive_data|ack|nack|sync|retry|abort",
  "cmd": "0x64",
  "seq_id": 123,
  "offset": 1234567,
  "length": 4096,
  "retry_stage": "fast|sync|hardware|none",
  "retry_count": 2,
  "error_code": "E006"
}
```

**示例**:
```
[2025-10-01 14:46:34.885] INFO [sender] send_data: cmd=0x64 seq=123 offset=1234567 len=4096
[2025-10-01 14:46:34.900] WARNING [receiver] nack: seq=123 offset=1234567 error=E004
[2025-10-01 14:46:35.000] INFO [sender] retry: stage=fast count=1
```

---

## 五、配置规范

### 5.1 配置文件示例（transfer.yaml）

```yaml
serial:
  baudrate: 1728000
  timeout: 0.2

transfer:
  # 固定块长配置（移除自适应）
  max_data_length: 4096
  
  # 超时配置
  request_timeout: 30
  connection_timeout: 30
  data_timeout: 5
  
  # 重试配置
  retry_count: 3
  backoff_base: 0.5
  max_retries: 5
  
  # 序号恢复配置
  sequence_mismatch_threshold: 3
  sync_timeout: 2
  enable_sequence_recovery: true
  
  # 移除的配置项（已删除）
  # enable_adaptive_strategy: false
  # adaptive_good_threshold: 0.95
  # adaptive_poor_threshold: 0.80
  # adaptive_bad_threshold: 0.60
  # adaptive_window_size: 20
  # adaptive_adjustment_interval: 10.0
```

### 5.2 块长配置指南

**推荐值**（根据波特率）:

| 波特率 | 推荐块长 | 说明 |
|--------|----------|------|
| 9600-57600 | 512 | 低速链路，保守配置 |
| 115200-460800 | 1024 | 中速链路，默认配置 |
| 921600-1000000 | 2048 | 高速链路 |
| 1500000-1728000 | 4096-8192 | 超高速链路，需硬件支持 |

**调优建议**:
1. 初次使用推荐值
2. 观察日志中的重试率
3. 若重试率 > 5%，降低块长
4. 若重试率 < 1% 且速率未饱和，可尝试增大

---

## 六、兼容性说明

### 6.1 不兼容变更
- ❌ `SEND_DATA` 载荷格式变更（增加 offset 字段）
- ❌ `ACK/NACK` 载荷格式变更（增加 offset 字段）
- ❌ `SYNC` 载荷格式变更（增加 offset 字段）
- ❌ 删除自适应策略配置项

### 6.2 升级路径
- 发送端和接收端**必须同时升级**到 v2.0
- 旧版本客户端无法与新版本服务端通信
- 建议在升级前备份旧版本可执行文件

### 6.3 回滚方案
- 保留旧版本可执行文件和配置文件
- 若新版本出现问题，可快速回退

---

## 七、测试要求

### 7.1 单元测试覆盖
- [ ] 帧打包/解包（包含 offset 字段）
- [ ] ACK/NACK 处理（幂等逻辑）
- [ ] 重复帧识别
- [ ] 序号与偏移量同步
- [ ] 状态机转移

### 7.2 集成测试场景
- [ ] 正常传输（小文件 < 1MB）
- [ ] 正常传输（大文件 > 10MB）
- [ ] ACK 丢失恢复
- [ ] 重复帧处理
- [ ] NACK 重试
- [ ] 序号同步
- [ ] 硬件恢复流程

### 7.3 硬件联调验证
- [ ] 真实串口传输
- [ ] 长时间稳定性测试（> 1小时）
- [ ] 干扰注入测试
- [ ] 速率与重试率统计

---

## 八、未来优化方向

1. **滑动窗口机制**: 支持多包同时发送，提高吞吐量
2. **压缩传输**: 支持数据压缩，减少传输时间
3. **断点续传**: 支持中断后从上次位置继续
4. **多文件并发**: 支持多个文件同时传输

---

## 附录A：状态机转移表

### 发送端状态转移表

| 当前状态 | 输入事件 | 下一状态 | 动作 |
|---------|---------|---------|------|
| IDLE | init_file() | WAIT_FILENAME_REQUEST | - |
| WAIT_FILENAME_REQUEST | REQUEST_FILE_NAME | SEND_FILENAME | send_filename() |
| WAIT_FILENAME_REQUEST | timeout | WAIT_FILENAME_REQUEST | 记录日志，继续等待 |
| SEND_FILENAME | success | WAIT_SIZE_REQUEST | - |
| WAIT_SIZE_REQUEST | REQUEST_FILE_SIZE | SEND_SIZE | send_file_size() |
| SEND_SIZE | success | WAIT_DATA_REQUEST | - |
| WAIT_DATA_REQUEST | REQUEST_DATA | SEND_DATA | _send_data_package() |
| SEND_DATA | success | WAIT_ACK | - |
| WAIT_ACK | ACK(offset匹配) | WAIT_DATA_REQUEST | seq++, 继续 |
| WAIT_ACK | NACK | RETRY | 记录错误，重试 |
| WAIT_ACK | timeout | RETRY | 记录超时，重试 |
| RETRY | 快速重试成功 | WAIT_ACK | - |
| RETRY | 快速重试失败 | SYNC | 触发同步 |
| SYNC | 同步成功 | WAIT_DATA_REQUEST | 调整序号 |
| SYNC | 同步失败 | HARDWARE_RECOVER | 硬件恢复 |
| HARDWARE_RECOVER | 恢复成功 | WAIT_DATA_REQUEST | - |
| HARDWARE_RECOVER | 恢复失败 | ABORTED | 删除文件，中止 |
| WAIT_DATA_REQUEST | 所有数据已确认 | COMPLETED | - |

### 接收端状态转移表

| 当前状态 | 输入事件 | 下一状态 | 动作 |
|---------|---------|---------|------|
| IDLE | start_transfer() | REQUEST_FILENAME | - |
| REQUEST_FILENAME | success | WAIT_FILENAME_REPLY | send_filename_request() |
| WAIT_FILENAME_REPLY | REPLY_FILE_NAME | VALIDATE_NAME | receive_filename() |
| WAIT_FILENAME_REPLY | timeout | REQUEST_FILENAME | 重试 |
| VALIDATE_NAME | valid | REQUEST_SIZE | - |
| REQUEST_SIZE | success | WAIT_SIZE_REPLY | send_file_size_request() |
| WAIT_SIZE_REPLY | REPLY_FILE_SIZE | VALIDATE_SIZE | receive_file_size() |
| VALIDATE_SIZE | valid | REQUEST_DATA | 打开文件句柄 |
| REQUEST_DATA | success | WAIT_DATA_REPLY | send_data_request() |
| WAIT_DATA_REPLY | SEND_DATA | VALIDATE_DATA | 检查 seq/offset |
| VALIDATE_DATA | 新包(offset==recv_size) | WRITE_DATA | 写入文件 |
| VALIDATE_DATA | 重复包(offset<recv_size) | SEND_DUP_ACK | 重发ACK，丢弃 |
| VALIDATE_DATA | 序号不匹配 | SEND_NACK | 发送NACK |
| WRITE_DATA | success | SEND_ACK | 更新进度 |
| SEND_ACK | success | REQUEST_DATA | 继续请求 |
| SEND_ACK | recv_size==file_size | COMPLETED | 传输完成 |
| SEND_NACK | success | RETRY | 触发重试流程 |
| RETRY | 失败次数 < 阈值 | REQUEST_DATA | 快速重试 |
| RETRY | 失败次数 ≥ 阈值 | SYNC | 触发同步 |
| SYNC | 同步成功 | REQUEST_DATA | 调整序号 |
| SYNC | 同步失败 | HARDWARE_RECOVER | 硬件恢复 |
| HARDWARE_RECOVER | 恢复失败 | ABORTED | 删除文件，中止 |

---

**文档结束**

