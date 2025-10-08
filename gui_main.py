#!/usr/bin/env python3
"""
文件名称: gui_main.py
内容摘要: 串口文件传输工具 - GUI 入口（模块化架构）
当前版本: v1.4.1
作者: AI Assistant
创建日期: 2025-10-01
更新日期: 2025-10-08
说明: 采用模块化架构，将GUI逻辑拆分到独立模块中
"""

import sys
from pathlib import Path
import tkinter as tk

# 添加src路径到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from serial_file_transfer.gui.app import SerialTransferApp


def main() -> None:
    """主函数 - 创建并启动GUI应用"""
    root = tk.Tk()
    app = SerialTransferApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
