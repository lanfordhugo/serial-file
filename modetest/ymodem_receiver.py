#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YMODEM 接收端测试程序
使用COM7串口接收文件
"""

import serial
import time
import os
import sys
from ymodem.Socket import ModemSocket


def ymodem_receiver():
    """YMODEM接收端主函数"""
    try:
        # 配置串口
        port = 'COM7'
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
        def read_func(size, timeout=3):
            """读取数据函数"""
            ser.timeout = timeout
            data = ser.read(size)
            return data if data else None
        
        def write_func(data, timeout=3):
            """写入数据函数"""
            ser.write_timeout = timeout
            return ser.write(data)
        
        # 创建YMODEM Socket
        modem = ModemSocket(read_func, write_func)
        
        # 接收进度回调函数
        def progress_callback(task_index, task_name, total_packets, success_packets):
            """接收进度回调函数"""
            progress = (success_packets / total_packets) * 100 if total_packets > 0 else 0
            print(f"接收进度: {progress:.1f}% ({success_packets}/{total_packets}) - {task_name}")
        
        # 创建接收目录
        receive_dir = "received_files"
        if not os.path.exists(receive_dir):
            os.makedirs(receive_dir)
            print(f"已创建接收目录: {receive_dir}")
        
        print("准备接收文件...")
        print("等待发送端开始传输...")
        
        # 接收文件
        success = modem.recv(receive_dir, callback=progress_callback)
        
        if success:
            print("文件接收成功！")
            
            # 列出接收到的文件
            print("\n接收到的文件:")
            for file in os.listdir(receive_dir):
                file_path = os.path.join(receive_dir, file)
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    print(f"  - {file} ({file_size} 字节)")
                    
                    # 显示文件内容（如果是文本文件）
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            print(f"    内容预览:")
                            for line in content.split('\n')[:5]:  # 只显示前5行
                                print(f"      {line}")
                            if len(content.split('\n')) > 5:
                                print("      ...")
                    except:
                        print("    (二进制文件，无法显示内容)")
        else:
            print("文件接收失败！")
        
        # 关闭串口
        ser.close()
        print("串口已关闭")
        
        return success
        
    except serial.SerialException as e:
        print(f"串口错误: {e}")
        return False
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请先安装ymodem库: pip install ymodem")
        return False
    except Exception as e:
        print(f"接收过程中发生错误: {e}")
        return False


if __name__ == "__main__":
    print("YMODEM 接收端测试程序")
    print("=" * 50)
    
    success = ymodem_receiver()
    
    if success:
        print("测试完成：接收成功")
        sys.exit(0)
    else:
        print("测试完成：接收失败")
        sys.exit(1) 