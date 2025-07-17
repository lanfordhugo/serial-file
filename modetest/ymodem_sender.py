#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YMODEM 发送端测试程序
使用COM5串口发送文件
"""

import serial
import time
import os
import sys
from ymodem.Socket import ModemSocket


def create_test_file():
    """创建测试文件"""
    test_file = "test_send.txt"
    content = "这是一个YMODEM传输测试文件\n"
    content += "文件内容包含中文字符\n"
    content += "测试时间: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n"
    content += "传输协议: YMODEM\n"
    content += "发送端口: COM5\n"
    content += "接收端口: COM7\n"
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"已创建测试文件: {test_file}")
    return test_file


def ymodem_sender():
    """YMODEM发送端主函数"""
    try:
        # 创建测试文件
        test_file = create_test_file()
        
        # 配置串口
        port = 'COM5'
        baudrate = 115200
        timeout = 5
        
        print(f"正在连接串口 {port}，波特率 {baudrate}...")
        
        # 打开串口
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        
        print(f"串口 {port} 连接成功")
        
        # 定义读写函数
        def read_func(size: int, timeout: float | None = None) -> bytes | None:
            """读取数据函数，符合ModemSocket要求"""
            ser.timeout = float(timeout) if timeout is not None else None
            data = ser.read(size)
            return data if data else None

        def write_func(data: bytes | bytearray, timeout: float | None = None) -> int | None:
            """写入数据函数，符合ModemSocket要求"""
            ser.write_timeout = float(timeout) if timeout is not None else None
            return ser.write(data)
        
        # 创建YMODEM Socket
        modem = ModemSocket(read_func, write_func)
        
        # 发送进度回调函数
        def progress_callback(task_index, task_name, total_packets, success_packets):
            """发送进度回调函数"""
            progress = (success_packets / total_packets) * 100 if total_packets > 0 else 0
            print(f"发送进度: {progress:.1f}% ({success_packets}/{total_packets}) - {task_name}")
        
        print("开始发送文件...")
        print("请确保接收端已经准备好接收数据...")
        
        # 等待用户确认
        input("按Enter键开始发送...")
        
        # 发送文件
        file_path = os.path.abspath(test_file)
        success = modem.send([file_path], callback=progress_callback)
        
        if success:
            print("文件发送成功！")
        else:
            print("文件发送失败！")
        
        # 关闭串口
        ser.close()
        print("串口已关闭")
        
        # 清理测试文件
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"已删除测试文件: {test_file}")
        
        return success
        
    except serial.SerialException as e:
        print(f"串口错误: {e}")
        return False
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请先安装ymodem库: pip install ymodem")
        return False
    except Exception as e:
        print(f"发送过程中发生错误: {e}")
        return False


if __name__ == "__main__":
    print("YMODEM 发送端测试程序")
    print("=" * 50)
    
    success = ymodem_sender()
    
    if success:
        print("测试完成：发送成功")
        sys.exit(0)
    else:
        print("测试完成：发送失败")
        sys.exit(1) 