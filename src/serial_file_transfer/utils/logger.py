"""
日志记录模块
============

提供统一的日志记录功能，支持彩色输出和函数调用追踪。
"""

import datetime
import inspect
import logging
import sys
from typing import Any, Optional
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[0m',      # 默认色
        'WARNING': '\033[33m',  # 黄色 
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
        'RESET': '\033[0m'      # 重置
    }
    
    def format(self, record):
        """格式化日志记录"""
        # 获取调用信息
        frame = inspect.currentframe()
        try:
            # 寻找调用日志函数的栈帧
            while frame:
                if frame.f_code.co_filename != __file__:
                    caller_filename = Path(frame.f_code.co_filename).name
                    caller_function = frame.f_code.co_name
                    caller_line = frame.f_lineno
                    break
                frame = frame.f_back
            else:
                caller_filename = "unknown"
                caller_function = "unknown"
                caller_line = 0
        finally:
            del frame
        
        # 添加毫秒精度的时间戳
        now = datetime.datetime.now()
        milliseconds = now.microsecond // 1000
        timestamp = now.strftime(f"%Y-%m-%d %H:%M:%S.{milliseconds:03d}")
        
        # 构建日志消息
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        formatted_message = (
            f"{color}[{timestamp}] {record.getMessage()} "
            f"[{caller_filename}.{caller_function}():{caller_line}]{reset}"
        )
        
        return formatted_message


# 全局日志器字典
_loggers = {}


def setup_logger(
    name: str = "serial_file_transfer",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    console_output: bool = True
) -> logging.Logger:
    """
    设置日志器
    
    Args:
        name: 日志器名称
        level: 日志级别
        log_file: 日志文件路径，None表示不写入文件
        console_output: 是否输出到控制台
        
    Returns:
        配置好的日志器
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 清除已有的处理器
    logger.handlers.clear()
    
    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColoredFormatter())
        logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # 防止重复输出
    logger.propagate = False
    
    return logger


def get_logger(name: str = "serial_file_transfer") -> logging.Logger:
    """
    获取日志器实例
    
    Args:
        name: 日志器名称
        
    Returns:
        日志器实例
    """
    if name not in _loggers:
        _loggers[name] = setup_logger(name)
    return _loggers[name]


# 兼容原有的打印函数
def d_print(*args: Any, **kwargs: Any) -> None:
    """
    常规信息打印（兼容原有函数）
    
    Args:
        *args: 要打印的参数
        **kwargs: 关键字参数
    """
    logger = get_logger()
    message = ' '.join(map(str, args))
    logger.info(message)


def e_print(*args: Any, **kwargs: Any) -> None:
    """
    错误信息打印（兼容原有函数）
    
    Args:
        *args: 要打印的参数  
        **kwargs: 关键字参数
    """
    logger = get_logger()
    message = ' '.join(map(str, args))
    logger.error(message)


# 默认设置根日志器
_default_logger = setup_logger() 