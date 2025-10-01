# 串口文件传输 vNext 测试计划

**版本**: v2.0  
**创建日期**: 2025-10-01  
**状态**: 待执行

## 一、测试目标

1. **协议正确性**: 验证新协议（offset字段、幂等ACK）正确性
2. **可靠性**: 验证ACK丢失、重复帧、序号漂移等异常场景恢复能力
3. **性能**: 验证固定块长配置下的传输速度和稳定性
4. **兼容性**: 确保配置升级路径正确

## 二、测试范围

### 2.1 协议层测试
- ✅ 帧打包/解包（包含offset字段）
- ✅ ACK/NACK/SYNC负载格式
- ✅ CRC校验
- ✅ 边界值测试

### 2.2 状态机测试
- ✅ 发送端状态转移
- ✅ 接收端状态转移
- ✅ 异常状态处理
- ✅ 超时与重试

### 2.3 可靠性测试
- ✅ ACK丢失恢复
- ✅ 重复帧处理
- ✅ 序号同步
- ✅ 硬件恢复流程
- ✅ 长时间传输稳定性

### 2.4 性能测试
- ✅ 不同块长下的传输速度
- ✅ 重试率统计
- ✅ CPU/内存占用

---

## 三、测试环境

### 3.1 单元测试环境
- Python 3.9+
- pytest
- pytest-mock
- coverage

### 3.2 集成测试环境
- loopback串口模拟器（虚拟串口对）
- 或双进程测试框架

### 3.3 硬件联调环境
- 真实串口连接（USB转串口）
- 不同波特率配置
- 不同干扰环境

---

## 四、测试用例设计

### 4.1 单元测试用例

#### 4.1.1 帧处理测试

**测试类**: `TestFrameHandler`

| 用例ID | 用例名称 | 测试目标 | 输入 | 预期输出 |
|--------|---------|---------|------|---------|
| UT-FH-001 | 打包SEND_DATA帧（新格式） | 验证offset字段正确打包 | seq=123, offset=4096, payload=b'test' | 帧格式正确，包含6字节头部 |
| UT-FH-002 | 解包SEND_DATA帧（新格式） | 验证offset字段正确解析 | 完整帧数据 | seq=123, offset=4096, payload=b'test' |
| UT-FH-003 | 打包ACK帧（新格式） | 验证ACK包含offset | seq=123, offset=4096 | 6字节ACK数据 |
| UT-FH-004 | 解包ACK帧（新格式） | 验证ACK offset解析 | 6字节ACK数据 | seq=123, offset=4096 |
| UT-FH-005 | CRC校验错误 | 验证CRC错误检测 | 错误CRC帧 | 返回None，记录错误 |
| UT-FH-006 | 数据长度过大 | 验证长度上限检查 | data_len > MAX_CHUNK_SIZE | 返回None，记录错误 |

**测试代码示例**:
```python
def test_pack_send_data_with_offset():
    """测试打包SEND_DATA帧（包含offset）"""
    seq_id = 123
    offset = 4096
    payload = b'test_data'
    
    # 构造数据: seq(2) + offset(4) + payload
    data = struct.pack("<HI", seq_id, offset) + payload
    frame = FrameHandler.pack_frame(SerialCommand.SEND_DATA, data)
    
    assert frame is not None
    assert len(frame) == 3 + len(data) + 2  # header(3) + data + crc(2)
    
    # 解包验证
    cmd, unpacked_data = FrameHandler.unpack_frame(frame)
    assert cmd == SerialCommand.SEND_DATA
    
    unpacked_seq = struct.unpack("<H", unpacked_data[:2])[0]
    unpacked_offset = struct.unpack("<I", unpacked_data[2:6])[0]
    unpacked_payload = unpacked_data[6:]
    
    assert unpacked_seq == seq_id
    assert unpacked_offset == offset
    assert unpacked_payload == payload
```

#### 4.1.2 发送端状态机测试

**测试类**: `TestSenderStateMachine`

| 用例ID | 用例名称 | 测试目标 | Mock设置 | 预期状态转移 |
|--------|---------|---------|---------|------------|
| UT-SM-001 | 正常流程 | 验证完整传输流程 | 所有帧正确响应 | IDLE → ... → COMPLETED |
| UT-SM-002 | ACK丢失恢复 | 验证ACK超时后重试 | 首次ACK丢失，重试成功 | WAIT_ACK → RETRY → WAIT_ACK → WAIT_DATA_REQUEST |
| UT-SM-003 | NACK重传 | 验证NACK触发重传 | 返回NACK | WAIT_ACK → RETRY → SEND_DATA |
| UT-SM-004 | 序号同步 | 验证同步流程 | 快速重试失败 | RETRY → SYNC → WAIT_DATA_REQUEST |
| UT-SM-005 | 硬件恢复 | 验证硬件恢复流程 | 同步失败 | SYNC → HARDWARE_RECOVER → WAIT_DATA_REQUEST |
| UT-SM-006 | 传输中止 | 验证失败中止 | 硬件恢复失败 | HARDWARE_RECOVER → ABORTED |

**测试代码示例**:
```python
@patch('serial.Serial')
def test_sender_ack_lost_recovery(mock_serial):
    """测试ACK丢失后的恢复"""
    # 设置Mock
    mock_port = MagicMock()
    mock_serial.return_value = mock_port
    
    # 模拟ACK丢失（首次返回None，重试后返回ACK）
    ack_responses = [None, None, create_ack_frame(seq=0, offset=0)]
    mock_port.read.side_effect = lambda n: ack_responses.pop(0) if ack_responses else b''
    
    # 创建发送端
    sender = FileSender(mock_serial, 'test.txt', config)
    sender.init_file('test.txt')
    
    # 执行发送
    result = sender._send_data_package(addr=0, length=1024)
    
    # 验证
    assert result is True
    assert sender._retry_count > 0  # 发生了重试
    assert sender._seq_id == 1  # 序号正确增加
```

#### 4.1.3 接收端状态机测试

**测试类**: `TestReceiverStateMachine`

| 用例ID | 用例名称 | 测试目标 | Mock设置 | 预期状态转移 |
|--------|---------|---------|---------|------------|
| UT-RM-001 | 正常流程 | 验证完整接收流程 | 所有帧正确 | IDLE → ... → COMPLETED |
| UT-RM-002 | 重复帧识别 | 验证重复帧幂等ACK | offset < recv_size | VALIDATE_DATA → SEND_DUP_ACK → REQUEST_DATA |
| UT-RM-003 | 序号不匹配 | 验证序号错误处理 | seq != expected_seq | VALIDATE_DATA → SEND_NACK → RETRY |
| UT-RM-004 | 偏移量跳跃 | 验证偏移量错误 | offset > recv_size | VALIDATE_DATA → SEND_NACK → RETRY |
| UT-RM-005 | 数据验证成功 | 验证正确数据处理 | offset==recv_size, seq匹配 | VALIDATE_DATA → WRITE_DATA → SEND_ACK |

**测试代码示例**:
```python
def test_receiver_duplicate_frame_handling():
    """测试重复帧的幂等ACK处理"""
    receiver = FileReceiver(mock_serial, 'output.txt', config)
    receiver.recv_size = 4096  # 已接收4096字节
    receiver._expected_seq = 2
    
    # 构造重复帧（offset=0, seq=0, 已接收过）
    duplicate_data = struct.pack("<HI", 0, 0) + b'old_data'
    receiver._received_data = duplicate_data
    
    # 执行验证
    receiver._handle_validate_data()
    
    # 验证状态转移到SEND_DUP_ACK
    assert receiver.state == ReceiverState.SEND_DUP_ACK
    
    # 执行发送重复ACK
    receiver._handle_send_dup_ack()
    
    # 验证
    assert receiver.recv_size == 4096  # 进度未变
    assert receiver._expected_seq == 2  # 序号未变
    assert receiver.state == ReceiverState.REQUEST_DATA  # 继续请求
```

#### 4.1.4 配置加载测试

**测试类**: `TestConfigLoader`

| 用例ID | 用例名称 | 测试目标 | 输入 | 预期输出 |
|--------|---------|---------|------|---------|
| UT-CF-001 | 加载有效配置 | 验证配置正确加载 | 标准transfer.yaml | 配置对象正确 |
| UT-CF-002 | 固定块长验证 | 验证块长范围 | max_data_length=4096 | 加载成功 |
| UT-CF-003 | 块长过大 | 验证上限检查 | max_data_length=20000 | 抛出异常 |
| UT-CF-004 | 块长过小 | 验证下限检查 | max_data_length=256 | 抛出异常 |
| UT-CF-005 | 删除自适应配置 | 验证不再支持 | enable_adaptive_strategy | 忽略或警告 |

---

### 4.2 集成测试用例

#### 4.2.1 正常传输测试

**测试类**: `TestEndToEndTransfer`

| 用例ID | 用例名称 | 文件大小 | 块长 | 波特率 | 预期结果 |
|--------|---------|---------|------|--------|---------|
| IT-E2E-001 | 小文件传输 | 100KB | 1024 | 115200 | 成功，校验和一致 |
| IT-E2E-002 | 中等文件传输 | 1MB | 4096 | 921600 | 成功，校验和一致 |
| IT-E2E-003 | 大文件传输 | 10MB | 8192 | 1728000 | 成功，校验和一致 |
| IT-E2E-004 | 超大文件传输 | 100MB | 8192 | 1728000 | 成功，校验和一致 |

**验证点**:
- 文件大小一致
- 文件内容一致（MD5校验）
- 传输时间合理
- 无重试或重试率 < 1%

#### 4.2.2 异常恢复测试

**测试类**: `TestAbnormalRecovery`

| 用例ID | 用例名称 | 异常注入方式 | 预期恢复行为 |
|--------|---------|------------|------------|
| IT-RCV-001 | ACK丢失恢复 | 随机丢弃20% ACK帧 | 快速重试成功，传输完成 |
| IT-RCV-002 | NACK重传 | 随机注入CRC错误 | 接收端发NACK，发送端重传 |
| IT-RCV-003 | 重复帧处理 | 模拟ACK丢失导致重复发送 | 接收端重发ACK，不重复写入 |
| IT-RCV-004 | 序号同步 | 人为篡改序号 | 触发SYNC，双方序号重新对齐 |
| IT-RCV-005 | 硬件恢复 | 连续失败触发 | 清理缓冲区，延迟重试成功 |

**测试代码示例**:
```python
def test_ack_loss_recovery():
    """测试ACK丢失恢复（集成测试）"""
    # 创建测试文件
    test_file = create_test_file(size=1024*1024)  # 1MB
    
    # 配置ACK丢失率20%
    mock_transport = MockSerialTransport(ack_loss_rate=0.2)
    
    # 创建发送端和接收端
    sender = FileSender(mock_transport, test_file, config)
    receiver = FileReceiver(mock_transport, 'output.txt', config)
    
    # 执行传输
    result = run_transfer(sender, receiver)
    
    # 验证
    assert result is True
    assert os.path.getsize('output.txt') == 1024*1024
    assert calculate_md5(test_file) == calculate_md5('output.txt')
    
    # 统计
    stats = mock_transport.get_stats()
    assert stats['retry_count'] > 0  # 发生了重试
    assert stats['retry_rate'] < 0.3  # 重试率合理
```

#### 4.2.3 块长配置测试

**测试类**: `TestBlockSizeConfig`

| 用例ID | 用例名称 | 块长配置 | 波特率 | 预期结果 |
|--------|---------|---------|--------|---------|
| IT-BLK-001 | 最小块长 | 512 | 115200 | 传输成功，速度较慢 |
| IT-BLK-002 | 默认块长 | 1024 | 115200 | 传输成功 |
| IT-BLK-003 | 大块长 | 8192 | 1728000 | 传输成功，速度较快 |
| IT-BLK-004 | 块长与波特率不匹配 | 8192 | 9600 | 重试率高，但能完成 |

---

### 4.3 硬件联调测试

#### 4.3.1 真实串口传输

**测试环境**:
- USB转串口设备
- 两台PC或一台PC的两个串口
- 不同波特率配置

| 用例ID | 用例名称 | 波特率 | 块长 | 文件大小 | 预期结果 |
|--------|---------|--------|------|---------|---------|
| HW-E2E-001 | 低速传输 | 115200 | 1024 | 1MB | 成功 |
| HW-E2E-002 | 中速传输 | 921600 | 4096 | 10MB | 成功 |
| HW-E2E-003 | 高速传输 | 1728000 | 8192 | 100MB | 成功 |

**监控指标**:
- 传输时间
- 平均速率（KB/s）
- 重试次数
- 重试率
- CPU占用率
- 内存占用

#### 4.3.2 干扰环境测试

**干扰方式**:
- 串口线缆晃动
- 电磁干扰（靠近电源线）
- 长距离传输（延长线）

| 用例ID | 用例名称 | 干扰类型 | 预期结果 |
|--------|---------|---------|---------|
| HW-INT-001 | 线缆晃动 | 传输中晃动线缆 | 触发重试，最终成功 |
| HW-INT-002 | 电磁干扰 | 靠近干扰源 | CRC错误增多，NACK重传 |
| HW-INT-003 | 长距离传输 | 10米延长线 | 重试率提高，但能完成 |

#### 4.3.3 长时间稳定性测试

**测试条件**:
- 连续传输1小时
- 文件大小10-100MB
- 循环传输

**监控指标**:
- 累计传输文件数
- 成功率
- 平均重试率
- 内存泄漏检测
- 串口异常检测

---

### 4.4 回归测试

#### 4.4.1 旧功能验证

| 用例ID | 功能点 | 验证内容 |
|--------|--------|---------|
| RG-001 | 文件名传输 | 支持长文件名和相对路径 |
| RG-002 | 文件夹传输 | 批量文件传输 |
| RG-003 | 进度显示 | 进度条正确显示 |
| RG-004 | 日志记录 | 日志输出完整 |

#### 4.4.2 配置升级测试

| 用例ID | 测试场景 | 验证内容 |
|--------|---------|---------|
| RG-CFG-001 | 旧配置迁移 | 删除自适应参数后仍能加载 |
| RG-CFG-002 | 新配置验证 | 固定块长配置生效 |
| RG-CFG-003 | 默认值验证 | 未配置项使用默认值 |

---

## 五、测试执行计划

### 5.1 第1周：单元测试

**目标**: 完成所有单元测试，覆盖率 ≥ 90%

| 日期 | 任务 | 负责模块 |
|------|------|---------|
| Day 1-2 | 帧处理测试 | FrameHandler |
| Day 3-4 | 发送端状态机测试 | Sender |
| Day 4-5 | 接收端状态机测试 | Receiver |
| Day 5 | 配置加载测试 | Config |

**交付物**:
- 单元测试代码
- 覆盖率报告
- 测试报告

### 5.2 第2周：集成测试

**目标**: 完成loopback模拟测试

| 日期 | 任务 | 测试类型 |
|------|------|---------|
| Day 1-2 | 正常传输测试 | E2E |
| Day 3-4 | 异常恢复测试 | Recovery |
| Day 5 | 块长配置测试 | Config |

**交付物**:
- 集成测试代码
- 异常注入工具
- 测试报告

### 5.3 第3周：硬件联调

**目标**: 完成真实串口环境验证

| 日期 | 任务 | 测试环境 |
|------|------|---------|
| Day 1-2 | 真实串口传输 | 不同波特率 |
| Day 3 | 干扰环境测试 | 干扰注入 |
| Day 4-5 | 长时间稳定性测试 | 1小时连续传输 |

**交付物**:
- 硬件测试报告
- 性能数据
- 问题清单

### 5.4 第4周：回归与修复

**目标**: 修复问题，完成回归测试

| 日期 | 任务 |
|------|------|
| Day 1-3 | 问题修复 |
| Day 4 | 回归测试 |
| Day 5 | 测试报告汇总 |

**交付物**:
- 最终测试报告
- 问题修复记录
- 发布说明

---

## 六、测试工具与脚本

### 6.1 Mock串口工具

```python
class MockSerialTransport:
    """模拟串口传输（支持异常注入）"""
    
    def __init__(self, ack_loss_rate=0.0, crc_error_rate=0.0):
        self.ack_loss_rate = ack_loss_rate
        self.crc_error_rate = crc_error_rate
        self.send_count = 0
        self.retry_count = 0
    
    def write(self, data):
        """模拟发送"""
        self.send_count += 1
        
        # 模拟CRC错误
        if random.random() < self.crc_error_rate:
            data = self._corrupt_crc(data)
        
        return True
    
    def read(self, size):
        """模拟接收"""
        # 模拟ACK丢失
        if random.random() < self.ack_loss_rate:
            self.retry_count += 1
            return None
        
        return self._generate_response(size)
    
    def get_stats(self):
        """获取统计信息"""
        return {
            'send_count': self.send_count,
            'retry_count': self.retry_count,
            'retry_rate': self.retry_count / self.send_count if self.send_count > 0 else 0
        }
```

### 6.2 测试文件生成工具

```python
def create_test_file(size: int, pattern: str = 'random') -> str:
    """创建测试文件
    
    Args:
        size: 文件大小（字节）
        pattern: 数据模式（'random', 'zeros', 'sequential'）
    
    Returns:
        文件路径
    """
    filename = f"test_{size}_{pattern}.bin"
    
    with open(filename, 'wb') as f:
        if pattern == 'random':
            f.write(os.urandom(size))
        elif pattern == 'zeros':
            f.write(b'\x00' * size)
        elif pattern == 'sequential':
            data = bytes(range(256)) * (size // 256 + 1)
            f.write(data[:size])
    
    return filename
```

### 6.3 性能统计工具

```python
class TransferStats:
    """传输统计"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.total_bytes = 0
        self.retry_count = 0
        self.packet_count = 0
    
    def start(self):
        self.start_time = time.time()
    
    def finish(self):
        self.end_time = time.time()
    
    def record_packet(self, size: int, retried: bool = False):
        self.total_bytes += size
        self.packet_count += 1
        if retried:
            self.retry_count += 1
    
    def get_report(self) -> dict:
        elapsed = self.end_time - self.start_time
        speed = self.total_bytes / elapsed if elapsed > 0 else 0
        retry_rate = self.retry_count / self.packet_count if self.packet_count > 0 else 0
        
        return {
            'elapsed_time': elapsed,
            'total_bytes': self.total_bytes,
            'speed_kbps': speed / 1024,
            'packet_count': self.packet_count,
            'retry_count': self.retry_count,
            'retry_rate': retry_rate * 100,  # 百分比
        }
```

---

## 七、测试通过标准

### 7.1 单元测试
- ✅ 所有用例通过
- ✅ 代码覆盖率 ≥ 90%
- ✅ 核心模块覆盖率 = 100%（FrameHandler, Sender, Receiver）

### 7.2 集成测试
- ✅ 所有正常传输用例成功
- ✅ 异常恢复用例成功率 ≥ 95%
- ✅ 重试率 < 5%

### 7.3 硬件联调
- ✅ 真实串口传输成功率 = 100%
- ✅ 干扰环境成功率 ≥ 95%
- ✅ 长时间稳定性测试无崩溃、无内存泄漏

### 7.4 性能指标
- ✅ 115200波特率: ≥ 10 KB/s
- ✅ 921600波特率: ≥ 80 KB/s
- ✅ 1728000波特率: ≥ 150 KB/s

---

## 八、风险与应对

### 8.1 风险识别

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|---------|
| 硬件串口不稳定 | 高 | 中 | 准备多套设备，更换测试环境 |
| loopback模拟器不完善 | 中 | 中 | 补充真实串口测试 |
| 异常场景覆盖不足 | 高 | 高 | 参考日志分析，补充测试用例 |
| 性能达不到目标 | 中 | 低 | 优化代码，调整块长配置 |

### 8.2 测试资源

**人力**:
- 测试工程师 x 1
- 开发工程师 x 1（协助调试）

**设备**:
- PC x 2
- USB转串口 x 2
- 串口线缆 x 2

**工具**:
- pytest
- coverage
- loopback串口模拟器

---

## 九、测试报告模板

### 9.1 单元测试报告

```markdown
# 单元测试报告

## 测试概况
- 测试日期: YYYY-MM-DD
- 测试人员: XXX
- 测试环境: Python 3.9, pytest 7.x

## 测试结果
- 总用例数: 50
- 通过: 48
- 失败: 2
- 跳过: 0
- 覆盖率: 92%

## 失败用例分析
1. UT-FH-006: 数据长度过大检查失败
   - 原因: 边界值判断错误
   - 修复: 已修复并回归通过

## 覆盖率分析
| 模块 | 覆盖率 |
|------|--------|
| FrameHandler | 100% |
| Sender | 95% |
| Receiver | 94% |
| Config | 85% |
```

### 9.2 集成测试报告

```markdown
# 集成测试报告

## 测试概况
- 测试日期: YYYY-MM-DD
- 测试环境: loopback模拟器

## 正常传输测试
| 用例 | 文件大小 | 块长 | 结果 | 耗时 | 速率 |
|------|---------|------|------|------|------|
| IT-E2E-001 | 100KB | 1024 | ✅ | 2.5s | 40 KB/s |
| IT-E2E-002 | 1MB | 4096 | ✅ | 15s | 68 KB/s |

## 异常恢复测试
| 用例 | 异常类型 | 结果 | 重试率 |
|------|---------|------|--------|
| IT-RCV-001 | ACK丢失20% | ✅ | 22% |
| IT-RCV-002 | CRC错误10% | ✅ | 12% |
| IT-RCV-003 | 重复帧 | ✅ | 0% |
```

### 9.3 硬件联调报告

```markdown
# 硬件联调测试报告

## 测试环境
- 设备: USB转串口 (FT232)
- PC: Windows 10 / Ubuntu 20.04
- 线缆长度: 1.5米

## 真实串口传输
| 波特率 | 文件大小 | 结果 | 平均速率 | 重试率 |
|--------|---------|------|----------|--------|
| 115200 | 1MB | ✅ | 11.2 KB/s | 1.2% |
| 921600 | 10MB | ✅ | 85.3 KB/s | 2.5% |
| 1728000 | 100MB | ✅ | 155.7 KB/s | 3.8% |

## 干扰环境测试
| 干扰类型 | 结果 | 重试率 | 备注 |
|---------|------|--------|------|
| 线缆晃动 | ✅ | 15% | 触发硬件恢复2次 |
| 电磁干扰 | ✅ | 25% | CRC错误增多 |

## 长时间稳定性
- 测试时长: 1小时
- 累计传输: 50个文件（共500MB）
- 成功率: 100%
- 平均重试率: 3.2%
- 内存占用: 稳定在50MB左右
- CPU占用: < 10%
```

---

**文档结束**

