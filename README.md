# 串口文件传输工具

## 项目简介

基于串口通信的可靠文件传输工具，支持单文件和批量文件的智能传输。采用自定义协议进行数据帧封装，具备校验和验证、进度显示、错误重传等功能。

**🚀 核心特性**：

- **双模式界面**: GUI 图形界面 + CLI 命令行接口
- **可靠传输协议**: CRC16 校验、offset 字段、重复帧幂等处理  
- **模块化架构**: 高内聚低耦合的分层设计
- **全面测试覆盖**: 完善的测试体系保障代码质量
- **代码复用**: 统一的工具函数层和错误处理机制

---

## 快速开始

### 环境安装

```bash
# 克隆项目
git clone <repository-url>
cd serial-file-transfer

# 安装依赖
pip install -r requirements.txt
```

### 使用方式

**GUI 模式**:

```bash
python gui_main.py
```

**CLI 模式**:

```bash
python main.py
```

### 代码集成

```python
from serial_file_transfer.transfer.sender import Sender
from serial_file_transfer.core.serial_manager import SerialManager

# 创建串口管理器
serial_mgr = SerialManager(port="COM3", baudrate=115200)
serial_mgr.open()

# 发送文件
sender = Sender(serial_mgr)
success = sender.send_file("test.txt")

serial_mgr.close()
```

---

## 项目架构

项目采用模块化分层设计，核心模块职责清晰：

```text
src/serial_file_transfer/
├── config/          # 配置管理（常量、设置）
├── core/            # 核心功能（串口、数据帧、校验）
├── transfer/        # 传输逻辑（发送、接收）
├── utils/           # 工具函数（日志、进度、格式化）
├── gui/             # 图形界面（模块化设计）
└── cli/             # 命令行接口
```

详细技术架构，请参考：[技术架构文档](docs/ARCHITECTURE.md)

---

## 文档导航

| 文档 | 内容 | 适合读者 |
|------|------|----------|
| 🏗️ **[技术架构](docs/ARCHITECTURE.md)** | 项目结构、核心模块、设计原则 | 开发者 |
| 📡 **[协议规范](docs/PROTOCOL.md)** | 传输协议、帧格式、核心机制 | 技术人员 |
| 🎨 **[GUI 架构](docs/GUI.md)** | 图形界面设计、模块化架构 | 前端开发者 |
| 🔧 **[开发指南](docs/DEVELOPMENT.md)** | 环境配置、代码规范、贡献流程 | 贡献者 |
| 📚 **[文档中心](docs/README.md)** | 完整文档索引、快速导航 | 所有用户 |

---

## 主要功能

### ✅ 双模式界面

- **GUI 模式**: 友好的图形界面（模块化设计，7个独立模块）
- **CLI 模式**: 灵活的命令行接口

### ✅ 可靠传输

- **自定义协议**: CRC16 校验、offset 字段、序号同步
- **错误恢复**: 重复帧幂等处理、统一重试流程
- **传输保障**: ACK确认机制、硬件恢复策略

### ✅ 文件管理

- 单文件传输
- 文件夹批量传输
- 大文件分块传输

### ✅ 质量保障

- 全面的测试覆盖
- Mock 测试技术
- 持续集成验证

---

## 测试与质量

项目采用全面的测试体系，确保代码质量。

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 查看测试覆盖率
pytest tests/ --cov=src/serial_file_transfer --cov-report=html

# 运行特定测试
pytest tests/unit/test_sender.py -v
```

详细测试规范，请参考：[开发指南 - 测试规范](docs/DEVELOPMENT.md#测试规范)

---

## 构建与打包

项目提供了Python构建脚本，用于生成独立的可执行文件。

### 构建可执行文件

```bash
# 运行构建脚本
python build.py

# 测试模式（跳过实际构建，用于调试）
python build.py --test
```

### 构建选项

构建脚本提供两种打包模式：

1. **单文件模式（推荐）**: 生成一个独立的.exe文件
   - 优点：便于分发，只有一个文件
   - 缺点：启动稍慢，文件较大

2. **目录模式**: 生成包含多个文件的目录
   - 优点：启动更快
   - 缺点：需要分发整个目录

### 构建特性

- ✅ **中文字符支持**: 完美处理中文路径和文件名
- ✅ **自动依赖检查**: 自动安装PyInstaller和项目依赖
- ✅ **智能清理**: 自动清理之前的构建文件
- ✅ **构建验证**: 自动测试生成的可执行文件
- ✅ **详细日志**: 完整的构建过程日志记录

### 构建输出

构建完成后，可执行文件将位于：

- 单文件模式：`dist/SerialFileTransfer.exe`
- 目录模式：`dist/SerialFileTransfer/SerialFileTransfer.exe`

---

## 版本信息

### 当前版本：v1.4.1

**核心特性**:

- ✅ **GUI 模块化架构**: 从单文件重构为 7 个独立模块
- ✅ **协议增强**: offset 字段支持、重复帧幂等处理
- ✅ **代码复用**: 工具函数层完善（error_handler、format_utils）
- ✅ **质量保障**: 完整的测试覆盖和代码规范

**技术栈**:

- Python 3.7+
- tkinter (GUI)
- pyserial (串口通信)
- pytest (测试框架)

---

## 贡献与支持

### 🤝 参与贡献

欢迎通过以下方式参与贡献：

- **Fork** 项目并提交 Pull Request
- **提交** Bug报告或功能建议

详细贡献指南请参考：[开发指南](docs/DEVELOPMENT.md)

### 📞 获取帮助

- 📖 **快速上手**: 查看本 README 的"快速开始"部分
- 🏗️ **技术架构**: 查看 [技术架构文档](docs/ARCHITECTURE.md)
- 📡 **协议细节**: 查看 [协议规范文档](docs/PROTOCOL.md)
- 🎨 **GUI 开发**: 查看 [GUI 架构文档](docs/GUI.md)
- 🔧 **开发贡献**: 查看 [开发指南](docs/DEVELOPMENT.md)
- 🐛 **Bug 报告**: 提交 GitHub Issues
- 💬 **功能建议**: 参与 GitHub Discussions

### 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 致谢

感谢所有贡献者和用户的支持，让这个项目变得更好！

**⭐ 如果这个项目对你有帮助，请给个Star支持一下！**
