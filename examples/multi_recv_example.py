#!/usr/bin/env python3
"""
多文件接收示例
==============

演示如何使用串口文件传输工具批量接收多个文件。
"""

import sys
from pathlib import Path

# 添加src路径到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from serial_file_transfer.cli.multi_file import MultiFileTransferCLI


def main():
    """主函数"""
    print("串口文件传输工具 - 批量文件接收")
    print("=" * 40)
    
    try:
        success = MultiFileTransferCLI.receive_files()
        if success:
            print("\n✅ 批量文件接收完成！")
        else:
            print("\n❌ 批量文件接收失败！")
    except Exception as e:
        print(f"\n💥 程序异常: {e}")


if __name__ == "__main__":
    main() 