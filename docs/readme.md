# 串口文件传输工具 - 文档索引

**当前版本**: v2.0 (重构版)  
**最后更新**: 2025-10-01

---

## 📚 文档目录

### 协议与设计文档

| 文档 | 说明 | 状态 |
|------|------|------|
| [protocol_spec_vnext.md](protocol_spec_vnext.md) | 串口文件传输协议规格 vNext（核心文档） | ✅ 已完成 |
| [state_machine_sender.md](state_machine_sender.md) | 发送端状态机详细设计 | ✅ 已完成 |
| [state_machine_receiver.md](state_machine_receiver.md) | 接收端状态机详细设计 | ✅ 已完成 |

### 测试与质量文档

| 文档 | 说明 | 状态 |
|------|------|------|
| [test_plan.md](test_plan.md) | 详细测试计划（单元/集成/硬件联调） | ✅ 已完成 |

### 用户文档

| 文档 | 说明 | 状态 |
|------|------|------|
| [user_guide.md](user_guide.md) | 用户使用指南 | ⚠️ 待更新 |
| [readme.md](readme.md) | 项目说明文档 | ⚠️ 待更新 |

---

## 🎯 vNext 核心变更

### 协议变更
- ✅ 数据帧增加 `offset` 字段（4字节）
- ✅ ACK/NACK 携带 `seq_id + offset`（6字节）
- ✅ 支持重复帧幂等确认
- ✅ 基于偏移量的可靠传输

### 架构变更
- ✅ 发送端/接收端状态机化
- ✅ 统一重试与恢复策略（快速→同步→硬件恢复）
- ✅ 删除自适应块长策略，改为配置固定
- ✅ 删除智能探测协商机制

### 配置变更
- ✅ 固定块长配置：`max_data_length`
- ❌ 删除自适应策略配置
- ❌ 删除探测协商配置

---

## 📖 阅读指南

### 开发者必读
1. **[protocol_spec_vnext.md](protocol_spec_vnext.md)** - 了解协议变更和新帧格式
2. **[state_machine_sender.md](state_machine_sender.md)** - 发送端实现细节
3. **[state_machine_receiver.md](state_machine_receiver.md)** - 接收端实现细节（重点：重复帧处理）
4. **[test_plan.md](test_plan.md)** - 测试要求和用例设计

### 测试工程师必读
1. **[test_plan.md](test_plan.md)** - 完整测试计划
2. **[protocol_spec_vnext.md](protocol_spec_vnext.md)** - 第七节：测试要求

### 用户必读
1. **[user_guide.md](user_guide.md)** - 使用说明（待更新）
2. **[readme.md](readme.md)** - 快速开始（待更新）

---

## 🗂️ 已删除文档

以下旧版文档已被删除，避免与 vNext 协议冲突：

| 文档 | 删除原因 | 替代文档 |
|------|---------|---------|
| `protocol.md` | 旧版协议规范 | `protocol_spec_vnext.md` |
| `architecture.md` | 包含已废弃的智能探测设计 | `state_machine_*.md` |
| `testing.md` | 旧版测试框架 | `test_plan.md` |
| `todo.md` | 包含已废弃的优化方向 | 无（重构已确定方向） |

---

## 🚀 重构进度

### ✅ 已完成
- [x] 阶段一：协议规格敲定
  - [x] 梳理现有协议
  - [x] 设计新帧结构
  - [x] 状态机设计
  - [x] 错误码与日志规范
  - [x] 测试计划

### 🚧 进行中
- [ ] 阶段二：底层支撑模块改造
- [ ] 阶段三：发送端重构
- [ ] 阶段四：接收端重构
- [ ] 阶段五：集成与联调准备
- [ ] 阶段六：硬件联调与验证
- [ ] 阶段七：回归、发布与交接

---

## 📝 文档维护规范

### 文档更新流程
1. 先更新对应的 Markdown 文档
2. 更新本 README 的状态标记
3. 如有协议变更，同步更新测试计划

### 版本标记说明
- ✅ 已完成：文档已完成并经过评审
- 🚧 进行中：文档正在编写或更新
- ⚠️ 待更新：文档需要更新以匹配新协议
- ❌ 已废弃：文档不再使用

---

## 📧 联系方式

如有问题或建议，请：
1. 提交 Issue
2. 查看项目 README
3. 联系项目维护者

---

**最后更新**: 2025-10-01  
**适用版本**: v2.0 (vNext)
