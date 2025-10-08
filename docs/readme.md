# 文档中心

> **串口文件传输工具** - 完整文档索引

---

## 📚 核心文档

### 1. [项目架构](ARCHITECTURE.md)
**适合**: 开发者、架构师

了解系统整体架构、模块设计和数据流向。

**内容**:
- 整体架构和分层设计
- 核心模块详解（config/core/transfer/utils/gui/cli）
- 数据流向和扩展性
- 设计原则和技术栈

---

### 2. [协议规范](PROTOCOL.md)
**适合**: 技术人员、开发者

了解串口通信协议的详细定义和核心机制。

**内容**:
- 协议概述和传输流程
- 命令字和帧格式定义
- 核心机制（重复帧处理、offset确认、序号同步）
- 配置规范和错误处理

---

### 3. [GUI 架构](GUI.md)
**适合**: 前端开发者、UI设计师

了解图形界面的模块化设计和组件结构。

**内容**:
- GUI 模块结构（7个独立模块）
- 核心模块详解（app/theme/panels/log_panel）
- 视图切换流程和线程管理
- 日志系统和进度回调

---

### 4. [开发指南](DEVELOPMENT.md)
**适合**: 贡献者、新开发者

了解开发环境配置、编码规范和贡献流程。

**内容**:
- 环境配置和依赖安装
- 代码规范（PEP 8、类型提示、文档字符串）
- 测试规范和 Git 工作流
- 调试技巧和性能优化
- 贡献流程和代码审查标准

---

## 🎯 快速导航

### 我想...

- **了解项目整体架构** → [ARCHITECTURE.md](ARCHITECTURE.md)
- **了解通信协议** → [PROTOCOL.md](PROTOCOL.md)
- **了解 GUI 设计** → [GUI.md](GUI.md)
- **开始开发贡献** → [DEVELOPMENT.md](DEVELOPMENT.md)
- **查看协议设计细节** → [design/vnext/](design/vnext/)

---

## 📁 文档结构

```
docs/
├── README.md              # 📖 文档索引（本文件）
├── ARCHITECTURE.md        # 🏗️ 项目架构
├── PROTOCOL.md            # 📡 协议规范
├── GUI.md                 # 🎨 GUI 架构
├── DEVELOPMENT.md         # 🔧 开发指南
└── design/                # 📐 设计文档
    └── vnext/             # vNext 协议设计（部分实现）
        ├── protocol_spec_vnext.md     # 完整协议规格
        ├── state_machine_sender.md    # 发送端状态机
        └── state_machine_receiver.md  # 接收端状态机
```

---

## 🔍 设计文档说明

### vNext 协议设计 (`design/vnext/`)

**状态**: ⚠️ 设计文档，部分已实现

这些文档包含 vNext v2.0 协议的详细设计，但仅有部分功能已实现：

**✅ 已实现**:
- offset 字段支持（SEND_DATA、ACK/NACK）
- 重复帧幂等处理
- 基于 offset 的数据确认
- 序号同步机制

**❌ 未实现**:
- 完整的状态机架构（SenderSessionController、ReceiverSessionController）
- 自适应策略删除（adaptive_strategy.py 仍存在）
- 完整的 vNext 测试验证

**文档列表**:
- [protocol_spec_vnext.md](design/vnext/protocol_spec_vnext.md) - 完整协议规格（519行）
- [state_machine_sender.md](design/vnext/state_machine_sender.md) - 发送端状态机设计（558行）
- [state_machine_receiver.md](design/vnext/state_machine_receiver.md) - 接收端状态机设计（826行）

> **注意**: 这些是设计文档，实际实现以核心文档和源代码为准。

---

## 📖 阅读建议

### 新用户
1. 先阅读项目根目录的 [README.md](../README.md)
2. 了解基本功能和使用方法
3. 如需深入，再查看核心文档

### 开发者
1. [ARCHITECTURE.md](ARCHITECTURE.md) - 理解整体架构
2. [PROTOCOL.md](PROTOCOL.md) - 了解通信协议
3. [DEVELOPMENT.md](DEVELOPMENT.md) - 开始贡献代码

### 前端开发
1. [GUI.md](GUI.md) - 了解 GUI 设计
2. [DEVELOPMENT.md](DEVELOPMENT.md) - 环境配置和规范

### 协议研究
1. [PROTOCOL.md](PROTOCOL.md) - 核心协议
2. [design/vnext/protocol_spec_vnext.md](design/vnext/protocol_spec_vnext.md) - 详细设计

---

## 🆕 文档更新日志

### 2025-10-08
- ✅ 整合核心文档（架构、协议、GUI、开发）
- ✅ 删除所有报告类一次性文档
- ✅ 精简 vNext 设计文档
- ✅ 创建清晰的文档结构

---

## 📝 文档维护

### 文档原则
- ✅ 保留核心、关键、重要信息
- ✅ 删除报告类一次性文档
- ✅ 文档与代码保持同步
- ✅ 使用中文编写

### 更新流程
1. **新功能开发**: 先更新设计文档（`design/`）
2. **功能完成**: 更新核心文档
3. **功能废弃**: 删除或归档相关文档

---

## 💡 获取帮助

### 文档问题
- 文档不清楚或错误 → 提交 Issue
- 需要补充文档 → 提交 Pull Request

### 技术问题
- 使用问题 → 查看 [README.md](../README.md)
- 开发问题 → 查看 [DEVELOPMENT.md](DEVELOPMENT.md)
- Bug 报告 → 提交 GitHub Issue

---

**最后更新**: 2025-10-08  
**文档版本**: v1.0
