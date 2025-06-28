# 代码集成示例

## 说明

这个文件夹包含的是**代码集成示例**，展示如何在其他Python项目中集成串口文件传输功能。

**⚠️ 注意**：如果你只是想使用串口文件传输工具，请直接运行项目根目录的 `main.py`：

```bash
# 直接使用产品
python main.py
```

## 示例文件说明

### send_example.py

展示如何在代码中集成发送功能，适用于：

- 需要在自己的Python项目中添加文件发送功能
- 自动化脚本中的文件传输
- 批处理程序中的文件分发

### receive_example.py  

展示如何在代码中集成接收功能，适用于：

- 需要在自己的Python项目中添加文件接收功能
- 服务端程序中的文件收集
- 自动化测试中的文件验证

## 集成方式

如果你想在自己的项目中集成串口文件传输功能，可以参考这些示例：

```python
# 集成发送功能
from serial_file_transfer.cli.file_transfer import FileTransferCLI

def my_send_function():
    success = FileTransferCLI.send()
    return success

# 集成接收功能  
def my_receive_function():
    success = FileTransferCLI.receive()
    return success
```

## 直接使用 vs 代码集成

| 使用方式 | 适用场景 | 入口文件 |
|---------|---------|---------|
| **直接使用** | 日常文件传输需求 | `python main.py` |
| **代码集成** | 在其他项目中集成传输功能 | 参考 `examples/` |

## 更多信息

详细的API文档和使用说明请参考项目根目录的 `README.md` 文件。
