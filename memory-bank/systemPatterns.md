# σ₂: System Patterns
*v1.0 | Created: 2025-09-24 | Updated: 2025-09-24*
*Π: INITIALIZING | Ω: RESEARCH*

## 🏛️ Architecture Overview
基于模块化设计的串口文件传输系统，采用分层架构模式：

```
src/serial_file_transfer/
├── cli/           # 命令行接口层
├── config/        # 配置管理层  
├── core/          # 核心传输层
├── transfer/      # 传输业务层
└── utils/         # 工具支持层
```

## 🔧 Core Components

### 传输层 (core/)
- **serial_manager.py**: 串口连接管理
- **frame_handler.py**: 数据帧处理
- **checksum.py**: 数据校验
- **probe_manager.py**: 设备探测
- **io_thread.py**: 异步I/O处理

### 业务层 (transfer/)
- **sender.py**: 文件发送逻辑
- **receiver.py**: 文件接收逻辑  
- **file_manager.py**: 文件管理

### 支持层 (utils/)
- **logger.py**: 日志系统
- **progress.py**: 进度监控
- **retry.py**: 重试机制
- **path_utils.py**: 路径处理

## 🎯 Design Patterns
- **分层架构**: 清晰的职责分离
- **工厂模式**: 传输对象创建
- **观察者模式**: 进度监控
- **重试模式**: 错误恢复
- **线程池模式**: 异步I/O处理

## 📈 Performance Characteristics
- 传输速度: 52-115 kbps (基于文件大小)
- 效率: 2.4%-5.3% (相对理论最大值)
- 支持文件大小: 100KB - 5MB+
- 默认配置: 1728000波特率, 16KB块大小

