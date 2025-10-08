# 项目架构文档

## 系统架构

### 整体架构

串口文件传输工具采用模块化分层设计，核心分为5个主要模块：

```
src/serial_file_transfer/
├── config/          # 配置管理层
├── core/            # 核心协议层
├── transfer/        # 传输逻辑层
├── utils/           # 工具函数层
├── gui/             # 图形界面层
└── cli/             # 命令行接口层
```

### 架构分层

```
┌─────────────────────────────────────┐
│     用户接口层 (GUI / CLI)           │
├─────────────────────────────────────┤
│     传输逻辑层 (Sender/Receiver)     │
├─────────────────────────────────────┤
│     核心协议层 (Frame/Serial)        │
├─────────────────────────────────────┤
│     配置管理层 (Config/Settings)     │
└─────────────────────────────────────┘
```

---

## 核心模块详解

### 1. 配置管理层 (`config/`)

**职责**: 管理系统配置和常量定义

| 模块 | 功能 |
|------|------|
| `constants.py` | 协议常量、命令字定义 |
| `settings.py` | 传输参数配置 |
| `config_loader.py` | YAML配置加载器 |

**核心配置**:

```python
# 传输配置
max_data_length: 4096        # 数据块大小
retry_count: 3               # 重试次数
timeout: 5                   # 超时时间（秒）

# 序号恢复
enable_sequence_recovery: true
sequence_mismatch_threshold: 3
```

---

### 2. 核心协议层 (`core/`)

**职责**: 实现串口通信和协议处理

| 模块 | 功能 |
|------|------|
| `serial_manager.py` | 串口管理、收发控制 |
| `frame_handler.py` | 帧打包/解包、CRC校验 |
| `frame_payload.py` | 载荷处理（支持offset字段）|
| `checksum.py` | CRC16 校验算法 |
| `sequence_recovery.py` | 序号同步恢复机制 |
| `serial_transport.py` | 串口抽象接口（测试用）|

**帧格式**:

```
+-----+-------+-------+--------+-----+-----+
| CMD | LEN_L | LEN_H |  DATA  | CRC | CRC |
| 1B  |  1B   |  1B   |   NB   | _L  | _H  |
+-----+-------+-------+--------+-----+-----+
```

**关键特性**:

- ✅ CRC16 校验保证数据完整性
- ✅ 序号同步机制处理序号漂移
- ✅ offset 字段支持重复帧识别

---

### 3. 传输逻辑层 (`transfer/`)

**职责**: 实现文件传输的高层逻辑

| 模块 | 功能 |
|------|------|
| `sender.py` | 发送端逻辑 |
| `receiver.py` | 接收端逻辑 |
| `file_manager.py` | 文件/文件夹管理 |

**发送流程**:

```
1. 等待文件名请求 → 发送文件名
2. 等待大小请求 → 发送文件大小
3. 等待数据请求 → 发送数据包
4. 等待ACK → 继续/重试
5. 传输完成
```

**接收流程**:

```
1. 请求文件名 → 接收文件名
2. 请求大小 → 接收文件大小
3. 请求数据 → 接收数据包
4. 验证并发送ACK
5. 传输完成
```

**关键特性**:

- ✅ 重复帧幂等处理（`offset < recv_size` 识别重复帧）
- ✅ 基于 offset 的数据确认
- ✅ 序号同步恢复机制

---

### 4. 工具函数层 (`utils/`)

**职责**: 提供通用工具函数

| 模块 | 功能 |
|------|------|
| `logger.py` | 日志管理 |
| `progress.py` | 进度跟踪 |
| `retry.py` | 重试机制 |
| `path_utils.py` | 路径处理 |
| `format_utils.py` | 格式化工具（大小、速度）|
| `error_handler.py` | 错误处理和友好提示 |
| `resource_path.py` | 资源路径解析 |

**重试策略**:

```python
# 统一重试流程
快速重试（3次，0.1秒间隔）
    ↓ 失败
序号同步（发送SYNC_REQUEST）
    ↓ 失败
硬件恢复（清理缓冲区）
    ↓ 失败
传输中止
```

---

### 5. 图形界面层 (`gui/`)

**职责**: 提供 GUI 交互界面

| 模块 | 功能 |
|------|------|
| `app.py` | 主应用类、视图切换 |
| `theme.py` | 主题管理 |
| `mode_selection_view.py` | 模式选择界面 |
| `send_panel.py` | 发送面板 |
| `receive_panel.py` | 接收面板 |
| `log_panel.py` | 可复用日志组件 |

**架构设计**:

```
gui_main.py (入口)
    ↓
SerialTransferApp (主应用)
    ├── ModeSelectionView (模式选择)
    ├── SendPanel (发送面板)
    │   └── LogPanel (日志组件)
    └── ReceivePanel (接收面板)
        └── LogPanel (日志组件)
```

**关键特性**:

- ✅ 模块化设计，单一职责
- ✅ LogPanel 组件复用
- ✅ 主题统一管理

详细说明见 [GUI 架构文档](GUI.md)

---

### 6. 命令行接口层 (`cli/`)

**职责**: 提供 CLI 交互接口

| 模块 | 功能 |
|------|------|
| `file_transfer.py` | CLI 主接口 |

**使用示例**:

```python
from serial_file_transfer.cli.file_transfer import FileTransferCLI

# 发送文件
FileTransferCLI.send()

# 接收文件
FileTransferCLI.receive()
```

---

## 核心设计原则

### 1. 模块化设计

- 每个模块职责单一、边界清晰
- 高内聚、低耦合
- 便于测试和维护

### 2. 分层架构

- 上层依赖下层，不反向依赖
- 接口清晰，易于扩展
- 配置层、协议层、逻辑层分离

### 3. 可测试性

- 使用抽象接口（如 `ISerialTransport`）
- 支持 Mock 测试
- 单元测试覆盖率 > 85%

### 4. 错误处理

- 统一的错误处理机制
- 友好的错误提示
- 完善的日志记录

### 5. 代码复用

- 提取通用工具函数
- 组件化设计（如 LogPanel）
- 避免代码重复

---

## 数据流向

### 发送端数据流

```
文件 → FileManager.read()
    ↓
FileSender._send_data_package()
    ↓
FrameHandler.pack_send_data_frame(seq, offset, payload)
    ↓
SerialManager.write(frame)
    ↓
串口发送
```

### 接收端数据流

```
串口接收
    ↓
FrameHandler.read_frame()
    ↓
FramePayload.unpack_send_data() → (seq, offset, payload)
    ↓
FileReceiver.receive_data_package()
    ↓
文件写入
```

---

## 扩展性

### 支持的扩展点

1. **新的传输协议**
   - 实现 `ISerialTransport` 接口
   - 继承 `FrameHandler` 自定义帧格式

2. **新的界面**
   - Web 界面（基于 Flask/FastAPI）
   - 移动端（React Native）

3. **新的功能**
   - 断点续传
   - 压缩传输
   - 加密传输

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 语言 | Python 3.7+ |
| 串口通信 | pyserial |
| GUI | tkinter |
| 配置 | PyYAML |
| 测试 | pytest, pytest-mock |
| 打包 | PyInstaller |

---

## 版本历史

### v1.4.1 (当前)

- ✅ GUI 模块化架构
- ✅ 工具函数层完善
- ✅ offset 字段支持

### v1.0.0 (基础)

- ✅ 基础传输功能
- ✅ CLI 接口
- ✅ 测试框架

---

**最后更新**: 2025-10-08
