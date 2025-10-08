# 开发指南

## 环境配置

### 系统要求

- **Python**: 3.7 或更高版本
- **操作系统**: Windows / Linux / macOS
- **编辑器**: VS Code（推荐）/ PyCharm

### 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd serial-file-transfer

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖
pip install pytest pytest-cov pytest-mock
```

### 开发工具配置

**VS Code 配置** (`.vscode/settings.json`):
```json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "editor.formatOnSave": true
}
```

---

## 代码规范

### Python 编码规范

本项目严格遵循 **PEP 8** 和项目自定义规范。

#### 命名约定

```python
# 类名：PascalCase
class SerialManager:
    pass

# 函数名/变量名：snake_case
def send_data_package():
    user_name = "test"

# 常量：UPPER_SNAKE_CASE
MAX_DATA_LENGTH = 4096

# 私有属性/方法：单下划线前缀
def _internal_method():
    pass
```

#### 类型提示（强制）

```python
from typing import Optional, List, Dict, Tuple

def send_file(
    file_path: str,
    port: str,
    baudrate: int = 115200
) -> bool:
    """发送文件"""
    pass

class FileManager:
    files: List[str]
    config: Dict[str, Any]
    
    def get_file_size(self, path: str) -> int:
        pass
```

#### 文档字符串（强制）

```python
def send_data_package(addr: int, length: int) -> bool:
    """
    发送数据包
    
    Args:
        addr: 起始地址（文件偏移量）
        length: 数据长度
    
    Returns:
        成功返回 True，失败返回 False
    
    Raises:
        IOError: 串口写入失败
    """
    pass
```

#### 文件头注释（强制）

```python
"""
文件名称: serial_manager.py
内容摘要: 串口管理模块，负责串口的打开、关闭和数据收发
当前版本: v1.0.0
作者: Your Name
创建日期: 2025-10-08
"""
```

---

## 项目结构

### 模块组织

```
src/serial_file_transfer/
├── __init__.py          # 包初始化
├── __main__.py          # 命令行入口
├── config/              # 配置管理
│   ├── constants.py     # 协议常量
│   ├── settings.py      # 参数配置
│   └── config_loader.py # 配置加载
├── core/                # 核心协议
│   ├── serial_manager.py    # 串口管理
│   ├── frame_handler.py     # 帧处理
│   ├── frame_payload.py     # 载荷处理
│   ├── checksum.py          # CRC校验
│   └── sequence_recovery.py # 序号恢复
├── transfer/            # 传输逻辑
│   ├── sender.py        # 发送端
│   ├── receiver.py      # 接收端
│   └── file_manager.py  # 文件管理
├── gui/                 # 图形界面
│   ├── app.py           # 主应用
│   ├── theme.py         # 主题管理
│   ├── send_panel.py    # 发送面板
│   ├── receive_panel.py # 接收面板
│   └── log_panel.py     # 日志组件
├── utils/               # 工具函数
│   ├── logger.py        # 日志系统
│   ├── progress.py      # 进度跟踪
│   ├── retry.py         # 重试机制
│   ├── format_utils.py  # 格式化工具
│   └── error_handler.py # 错误处理
└── cli/                 # 命令行接口
    └── file_transfer.py # CLI 主接口
```

### 新增模块指南

1. **确定模块职责**: 单一职责原则
2. **选择合适的包**: config/core/transfer/utils/gui/cli
3. **创建模块文件**: 使用 snake_case 命名
4. **添加文件头注释**: 包含摘要、版本、作者
5. **编写测试**: 在 `tests/` 对应目录创建测试文件

---

## 测试规范

### 测试框架

使用 **pytest** 作为主要测试框架。

### 测试目录结构

```
tests/
├── unit/               # 单元测试
│   ├── test_frame_handler.py
│   ├── test_sender.py
│   └── test_receiver.py
├── integration/        # 集成测试
│   ├── test_end_to_end.py
│   └── test_abnormal_recovery.py
└── functional/         # 功能测试
    └── test_cli.py
```

### 测试命名规范

```python
# 测试文件：test_<module>.py
# 测试类：Test<Module>
# 测试方法：test_<功能>_<场景>

class TestSender:
    def test_send_data_with_offset(self):
        """测试发送数据包含offset字段"""
        pass
    
    def test_send_data_when_ack_lost_then_retry(self):
        """测试ACK丢失时重试"""
        pass
```

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/unit/test_sender.py -v

# 运行特定测试方法
pytest tests/unit/test_sender.py::TestSender::test_send_data_with_offset -v

# 查看测试覆盖率
pytest tests/ --cov=src/serial_file_transfer --cov-report=html

# 生成覆盖率报告
pytest tests/ --cov=src --cov-report=term-missing
```

### Mock 使用规范

```python
from unittest.mock import Mock, patch, MagicMock

# Mock 串口对象
@pytest.fixture
def mock_serial():
    serial = Mock()
    serial.is_open = True
    serial.read = Mock(return_value=b'\x00\x00')
    serial.write = Mock(return_value=True)
    return serial

# 使用 patch
@patch('serial.Serial')
def test_serial_manager(mock_serial_class):
    mock_serial_class.return_value = mock_serial
    # 测试逻辑
```

---

## Git 工作流

### 分支管理

```
main          # 主分支（稳定版本）
  ├── develop # 开发分支
  │   ├── feature/xxx  # 功能分支
  │   ├── bugfix/xxx   # 修复分支
  │   └── refactor/xxx # 重构分支
  └── hotfix/xxx       # 紧急修复
```

### 提交规范

```bash
# 功能开发
git commit -m "feat: 添加offset字段支持"

# Bug修复
git commit -m "fix: 修复ACK丢失死锁问题"

# 重构
git commit -m "refactor: 重构GUI模块化架构"

# 文档
git commit -m "docs: 更新协议规范文档"

# 测试
git commit -m "test: 添加重复帧测试用例"

# 构建
git commit -m "build: 更新依赖版本"
```

### Pull Request 流程

1. 创建功能分支
2. 开发并提交代码
3. 运行测试确保通过
4. 提交 Pull Request
5. 代码审查
6. 合并到 develop

---

## 调试技巧

### 日志调试

```python
import logging

logger = logging.getLogger(__name__)

# 设置日志级别
logger.setLevel(logging.DEBUG)

# 关键位置添加日志
logger.debug(f"发送数据: seq={seq_id} offset={offset} len={len(payload)}")
logger.info(f"传输完成: {file_size} 字节")
logger.warning(f"收到NACK: seq={seq_id}")
logger.error(f"传输失败: {error}")
```

### 断点调试

使用 VS Code 调试配置 (`.vscode/launch.json`):
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: GUI",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/gui_main.py",
            "console": "integratedTerminal"
        },
        {
            "name": "Python: 测试",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["tests/", "-v"]
        }
    ]
}
```

### 串口调试

使用虚拟串口工具：
- Windows: com0com
- Linux: socat

```bash
# Linux 创建虚拟串口对
socat -d -d pty,raw,echo=0 pty,raw,echo=0
```

---

## 性能优化

### 性能分析

```bash
# 使用 cProfile
python -m cProfile -o profile.stats main.py

# 分析结果
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"
```

### 优化建议

1. **避免频繁的字符串拼接**
   ```python
   # 不推荐
   result = ""
   for item in items:
       result += str(item)
   
   # 推荐
   result = "".join(str(item) for item in items)
   ```

2. **使用生成器减少内存占用**
   ```python
   # 不推荐
   data = [read_chunk(i) for i in range(1000)]
   
   # 推荐
   data = (read_chunk(i) for i in range(1000))
   ```

3. **缓存重复计算**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=128)
   def calculate_crc(data: bytes) -> int:
       pass
   ```

---

## 构建与打包

### 开发版本运行

```bash
# GUI 模式
python gui_main.py

# CLI 模式
python main.py

# 模块方式
python -m serial_file_transfer
```

### 打包为可执行文件

```bash
# 使用 build.py 脚本
python build.py

# 测试模式（不实际构建）
python build.py --test

# 输出位置
# 单文件模式: dist/SerialFileTransfer.exe
# 目录模式: dist/SerialFileTransfer/SerialFileTransfer.exe
```

---

## 贡献流程

### 贡献步骤

1. **Fork 项目**
2. **创建功能分支** (`git checkout -b feature/amazing-feature`)
3. **提交更改** (`git commit -m 'feat: 添加新功能'`)
4. **推送分支** (`git push origin feature/amazing-feature`)
5. **创建 Pull Request**

### Pull Request 要求

- ✅ 代码符合 PEP 8 规范
- ✅ 添加完整的类型提示和文档字符串
- ✅ 编写对应的测试用例
- ✅ 所有测试通过
- ✅ 更新相关文档
- ✅ commit 信息清晰

### 代码审查标准

1. **功能正确性**: 实现符合需求
2. **代码质量**: 遵循编码规范
3. **测试覆盖**: 关键逻辑有测试
4. **文档完整**: 代码和文档同步
5. **性能合理**: 无明显性能问题

---

## 常见问题

### 环境问题

**Q: 如何解决依赖冲突？**

```bash
# 创建新的虚拟环境
python -m venv venv_new
source venv_new/bin/activate  # Linux/macOS
venv_new\Scripts\activate     # Windows

# 重新安装依赖
pip install -r requirements.txt
```

**Q: 如何升级依赖版本？**

```bash
# 升级所有依赖
pip install --upgrade -r requirements.txt

# 生成新的 requirements.txt
pip freeze > requirements.txt
```

### 开发问题

**Q: 如何添加新的协议命令？**

1. 在 `config/constants.py` 添加命令字定义
2. 在 `core/frame_handler.py` 添加帧处理逻辑
3. 在 `transfer/sender.py` 或 `receiver.py` 使用
4. 添加测试用例

**Q: 如何扩展 GUI？**

参考 [GUI 架构文档](GUI.md) 的"添加新视图"部分。

---

## 学习资源

### 项目文档

- [架构文档](ARCHITECTURE.md) - 了解系统架构
- [协议规范](PROTOCOL.md) - 了解通信协议
- [GUI 架构](GUI.md) - 了解界面设计

### Python 学习

- [PEP 8](https://pep8.org/) - Python 代码风格指南
- [Python Type Hints](https://docs.python.org/3/library/typing.html) - 类型提示
- [pytest 文档](https://docs.pytest.org/) - 测试框架

### 工具文档

- [pyserial 文档](https://pythonhosted.org/pyserial/) - 串口通信
- [tkinter 教程](https://docs.python.org/3/library/tkinter.html) - GUI 开发

---

**最后更新**: 2025-10-08

