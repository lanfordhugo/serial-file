# YMODEM 串口文件传输测试

这是一个简单的YMODEM协议文件传输测试程序，使用COM5和COM7串口进行通信。

## 功能说明

- **发送端**: 使用COM5串口发送文件
- **接收端**: 使用COM7串口接收文件
- **协议**: YMODEM 1K模式
- **波特率**: 115200

## 环境要求

- Python 3.7+
- Windows系统（使用COM端口）
- 虚拟串口工具（如com0com）或硬件串口连接

## 安装依赖

```bash
pip install -r requirements.txt
```

或者手动安装：

```bash
pip install ymodem pyserial
```

## 使用方法

### 1. 设置虚拟串口

如果没有物理串口，可以使用虚拟串口工具：
- 下载并安装 com0com
- 创建COM5和COM7的虚拟串口对

### 2. 运行测试

**方法一：分别运行发送端和接收端**

1. 在一个终端中运行接收端：
```bash
python ymodem_receiver.py
```

2. 在另一个终端中运行发送端：
```bash
python ymodem_sender.py
```

**方法二：使用测试脚本**

```bash
python test_ymodem.py
```

## 文件说明

- `ymodem_sender.py` - 发送端程序
- `ymodem_receiver.py` - 接收端程序
- `test_ymodem.py` - 自动化测试脚本
- `requirements.txt` - 依赖包列表
- `README.md` - 使用说明

## 测试流程

1. 发送端自动创建测试文件
2. 发送端连接COM5串口
3. 接收端连接COM7串口
4. 发送端使用YMODEM协议发送文件
5. 接收端接收文件并保存到received_files目录
6. 显示传输结果和文件内容

## 注意事项

- 确保COM5和COM7端口可用
- 如果使用虚拟串口，确保端口对已正确配置
- 传输过程中不要关闭程序
- 接收端需要先启动，然后再启动发送端

## 故障排除

1. **串口连接失败**：检查端口是否被占用或不存在
2. **传输失败**：检查串口配置是否正确
3. **导入错误**：确保已安装所需的Python包

## 扩展功能

可以根据需要修改以下参数：
- 串口号（COM5, COM7）
- 波特率（默认115200）
- 超时时间（默认5秒）
- 文件内容和大小 