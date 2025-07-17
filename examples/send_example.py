#!/usr/bin/env python3
"""
文件发送示例
============

演示如何使用串口文件传输工具发送文件或文件夹。
支持自动检测路径类型：
- 如果是文件，则发送单个文件
- 如果是文件夹，则批量发送文件夹中的所有文件
"""

import sys
from pathlib import Path

# 添加src路径到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from serial_file_transfer.cli.file_transfer import FileTransferCLI


def main():
    """主函数"""
    print("串口文件传输工具 - 发送")
    print("=" * 40)
    print("支持发送单个文件或整个文件夹")
    print("程序会自动检测路径类型并选择相应的传输方式")
    print()

    try:
        success = FileTransferCLI.send()
        if success:
            print("\n✅ 文件发送完成！")
        else:
            print("\n❌ 文件发送失败！")
    except Exception as e:
        print(f"\n💥 程序异常: {e}")


if __name__ == "__main__":
    main()
