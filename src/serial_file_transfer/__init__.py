"""
串口文件传输工具
==============

这是一个基于串口通信的文件传输工具，支持单个文件和批量文件的可靠传输。

主要功能：
- 单文件传输
- 批量文件传输  
- 数据校验
- 进度显示
- 错误处理

作者: lanford
版本: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "lanford"
__email__ = ""
__description__ = "基于串口通信的文件传输工具"

# 导出主要类
from .transfer.sender import FileSender
from .transfer.receiver import FileReceiver
from .transfer.file_manager import SenderFileManager, ReceiverFileManager

__all__ = [
    "FileSender",
    "FileReceiver", 
    "SenderFileManager",
    "ReceiverFileManager"
] 