# σ₃: Technical Context
*v1.0 | Created: 2025-09-24 | Updated: 2025-09-24*
*Π: INITIALIZING | Ω: RESEARCH*

## 🛠️ Technology Stack
- 🐍 **Backend**: Python 3.x
- 📡 **Serial Communication**: pyserial
- 🧪 **Testing**: pytest, coverage
- 📦 **Packaging**: PyInstaller
- 📝 **Documentation**: Markdown
- 🔧 **Build**: Custom build.py script

## 📚 Key Dependencies
```
pyserial>=3.5
pytest>=7.0
coverage>=6.0
```

## 🏗️ Development Environment
- **OS**: Windows 10/11 (主要), Linux (支持)
- **Python**: 3.8+
- **IDE**: 支持多种IDE
- **版本控制**: Git

## 🔧 Build & Deployment
- **构建脚本**: build.py
- **输出**: SerialFileTransfer.exe
- **分发**: dist/ 目录包含可执行文件和依赖
- **日志**: 运行时日志存储在 logs/ 目录

## 📊 Performance Metrics
基于 performance_results.json 的测试数据：
- **100KB文件**: 3.1s传输时间, 52.2kbps
- **1MB文件**: 14.6s传输时间, 103.3kbps  
- **5MB文件**: 58.2s传输时间, 114.9kbps

## 🔍 Testing Infrastructure
- **单元测试**: tests/ 目录下完整测试套件
- **集成测试**: integration/ 子目录
- **性能测试**: performance_test.py
- **覆盖率**: htmlcov/ 目录包含详细报告
- **配置**: pytest.ini

