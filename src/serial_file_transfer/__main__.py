#!/usr/bin/env python3
"""
串口文件传输工具 - 模块CLI入口
==============================

支持通过 python -m serial_file_transfer 调用
"""

import sys
import argparse
from pathlib import Path

from .cli.file_transfer import FileTransferCLI
from .utils.logger import get_logger

logger = get_logger(__name__)

# 版本信息
VERSION = "1.4.0"
PROGRAM_NAME = "串口文件传输工具"


def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description=f"{PROGRAM_NAME} v{VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  # 智能发送模式
  python -m serial_file_transfer send --port COM1 --path file.txt --baudrate 115200

  # 智能接收模式
  python -m serial_file_transfer receive --port COM2 --save ./received/ --baudrate 115200

更多信息请访问项目文档。
        """,
    )

    parser.add_argument(
        "--version", action="version", version=f"{PROGRAM_NAME} v{VERSION}"
    )

    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 发送命令（智能模式）
    send_parser = subparsers.add_parser("send", help="智能发送文件或文件夹")
    send_parser.add_argument("--port", required=True, help="串口号（如 COM1, /dev/ttyUSB0）")
    send_parser.add_argument("--path", required=True, help="要发送的文件或文件夹路径")
    send_parser.add_argument("--baudrate", type=int, default=115200, help="起始波特率（默认115200）")

    # 接收命令（智能模式）
    receive_parser = subparsers.add_parser("receive", help="智能接收文件")
    receive_parser.add_argument("--port", required=True, help="串口号（如 COM2, /dev/ttyUSB1）")
    receive_parser.add_argument("--save", required=True, help="文件保存路径")
    receive_parser.add_argument("--baudrate", type=int, default=115200, help="起始波特率（默认115200）")

    return parser


def main():
    """主函数"""
    try:
        parser = create_parser()
        args = parser.parse_args()

        if not args.command:
            parser.print_help()
            return

        # 根据命令执行相应操作（仅智能模式）
        if args.command == "send":
            try:
                # 临时设置参数到CLI类，供智能发送使用
                FileTransferCLI._temp_port = args.port
                FileTransferCLI._temp_path = args.path
                FileTransferCLI._temp_baudrate = args.baudrate

                success = FileTransferCLI.smart_send()

            finally:
                # 清理临时参数
                FileTransferCLI._clear_temp_params()

            sys.exit(0 if success else 1)

        elif args.command == "receive":
            try:
                # 临时设置参数到CLI类，供智能接收使用
                FileTransferCLI._temp_port = args.port
                FileTransferCLI._temp_save_path = args.save
                FileTransferCLI._temp_baudrate = args.baudrate

                success = FileTransferCLI.smart_receive()

            finally:
                # 清理临时参数
                FileTransferCLI._clear_temp_params()

            sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n👋 用户中断程序，退出")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序异常: {e}")
        print(f"\n💥 程序异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 