"""
命令行接口模块
==============

提供统一的文件传输命令行接口，支持自动路径检测。
"""

from .file_transfer import FileTransferCLI

__all__ = [
    "FileTransferCLI"
] 