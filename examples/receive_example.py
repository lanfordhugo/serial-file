#!/usr/bin/env python3
"""
文件接收示例
============

演示如何使用串口文件传输工具接收文件或文件夹。
支持两种接收模式：
- 单文件接收：接收一个文件
- 批量文件接收：接收多个文件到指定文件夹
"""

import sys
from pathlib import Path

# 添加src路径到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from serial_file_transfer.cli.file_transfer import FileTransferCLI


def main():
    """主函数"""
    print("串口文件传输工具 - 接收")
    print("=" * 40)
    print("支持单文件接收或批量文件接收")
    print("程序会询问您选择接收模式")
    print()

    try:
        success = FileTransferCLI.receive()
        if success:
            print("\n✅ 文件接收完成！")
        else:
            print("\n❌ 文件接收失败！")
    except Exception as e:
        print(f"\n💥 程序异常: {e}")


if __name__ == "__main__":
    main()
