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
import os


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器 - 性能优化版本"""

    # ANSI颜色代码
    COLORS = {
        "DEBUG": "\033[36m",  # 青色
        "INFO": "\033[0m",  # 默认色
        "WARNING": "\033[33m",  # 黄色
        "ERROR": "\033[31m",  # 红色
        "CRITICAL": "\033[35m",  # 紫色
        "RESET": "\033[0m",  # 重置
    }

    def __init__(self):
        """初始化格式化器，启用性能优化缓存"""
        super().__init__()
        # 缓存颜色格式，避免重复查找
        self._color_cache = {}
        for level, color_code in self.COLORS.items():
            self._color_cache[level] = (color_code, self.COLORS["RESET"])

    def _get_caller_info(self):
        """获取调用者信息，使用缓存优化"""
        frame = inspect.currentframe()
        try:
            # 寻找调用日志函数的栈帧（优化：直接跳过已知的日志模块栈帧）
            skip_count = 0
            while frame and skip_count < 10:  # 限制搜索深度，防止无限循环
                if frame.f_code.co_filename != __file__:
                    caller_filename = Path(frame.f_code.co_filename).name
                    caller_function = frame.f_code.co_name
                    caller_line = frame.f_lineno
                    return caller_filename, caller_function, caller_line
                frame = frame.f_back
                skip_count += 1
            
            # 兜底返回
            return "unknown", "unknown", 0
        finally:
            del frame

    def format(self, record):
        """格式化日志记录 - 性能优化版本"""
        # 使用缓存的颜色信息
        color, reset = self._color_cache.get(
            record.levelname, 
            self._color_cache.get("INFO", ("", ""))
        )

        # 获取调用信息
        caller_filename, caller_function, caller_line = self._get_caller_info()

        # 使用更高效的时间戳生成
        now = datetime.datetime.now()
        milliseconds = now.microsecond // 1000
        
        # 性能优化：减少字符串格式化次数，使用单次格式化
        formatted_message = (
            f"{color}[{now.strftime('%Y-%m-%d %H:%M:%S')}.{milliseconds:03d}] "
            f"{record.getMessage()} [{caller_filename}.{caller_function}():{caller_line}]{reset}"
        )

        return formatted_message


# 全局日志器字典
_loggers = {}

# 全局额外handler列表（用于GUI等场景注册额外的日志处理器）
_extra_handlers = []


def register_extra_handler(handler: logging.Handler) -> None:
    """
    注册额外的日志处理器到所有日志器
    
    主要用于GUI等场景，需要将底层模块的日志同时输出到UI界面。
    调用此函数后，所有已创建和未来创建的日志器都会添加此handler。
    
    Args:
        handler: 要注册的日志处理器
    """
    if handler not in _extra_handlers:
        _extra_handlers.append(handler)
        
        # 为所有已创建的日志器添加此handler
        for logger in _loggers.values():
            if handler not in logger.handlers:
                logger.addHandler(handler)


def unregister_extra_handler(handler: logging.Handler) -> None:
    """
    移除已注册的额外日志处理器
    
    Args:
        handler: 要移除的日志处理器
    """
    if handler in _extra_handlers:
        _extra_handlers.remove(handler)
        
        # 从所有日志器中移除此handler
        for logger in _loggers.values():
            if handler in logger.handlers:
                logger.removeHandler(handler)


def setup_logger(
    name: str = "serial_file_transfer",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    console_output: bool = True,
    file_output: bool = True,
    enable_propagate: bool = False,
) -> logging.Logger:
    """
    设置日志器

    Args:
        name: 日志器名称
        level: 日志级别
        log_file: 日志文件路径，None表示使用默认路径
        console_output: 是否输出到控制台
        file_output: 是否输出到文件
        enable_propagate: 是否允许日志传播到父日志器（默认False以避免重复输出）

    Returns:
        配置好的日志器
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 清除已有的处理器
    logger.handlers.clear()

    # 控制台处理器
    if console_output:
        # 将日志输出到 stderr，防止与进度条 (stdout) 冲突
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(ColoredFormatter())
        logger.addHandler(console_handler)

    # 文件处理器
    if file_output:
        if log_file is None:
            # 默认 logs 目录
            logs_dir = Path.cwd() / "logs"
            logs_dir.mkdir(exist_ok=True)

            # 根据模块名称区分
            if ".transfer.sender" in name:
                file_name = "sender.log"
            elif ".transfer.receiver" in name:
                file_name = "receiver.log"
            else:
                file_name = "serial_file_transfer.log"

            log_file = str(logs_dir / file_name)

        # 显式指定 UTF-8 编码
        file_handler = logging.FileHandler(log_file, "a", "utf-8")
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(filename)s.%(funcName)s():%(lineno)d]"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # 添加全局注册的额外处理器
    for extra_handler in _extra_handlers:
        if extra_handler not in logger.handlers:
            logger.addHandler(extra_handler)

    # 防止重复输出（可配置）
    logger.propagate = enable_propagate

    return logger


def get_logger(name: str = "serial_file_transfer", console_only: bool = False) -> logging.Logger:
    """
    获取日志器实例

    Args:
        name: 日志器名称
        console_only: 是否仅输出到控制台（不创建日志文件）

    Returns:
        日志器实例
    """
    # 为了支持不同的配置，使用不同的键值
    logger_key = f"{name}_console_only" if console_only else name
    
    if logger_key not in _loggers:
        if console_only:
            _loggers[logger_key] = setup_logger(name, file_output=False)
        else:
            _loggers[logger_key] = setup_logger(name)
    return _loggers[logger_key]


def get_console_logger(name: str = "serial_file_transfer") -> logging.Logger:
    """
    获取仅输出到控制台的日志器（不创建文件）

    Args:
        name: 日志器名称

    Returns:
        仅输出到控制台的日志器实例
    """
    return get_logger(name, console_only=True)


# 兼容原有的打印函数
def d_print(*args: Any, **kwargs: Any) -> None:
    """
    常规信息打印（兼容原有函数）

    Args:
        *args: 要打印的参数
        **kwargs: 关键字参数
    """
    logger = get_console_logger()  # 修改：使用console_logger避免创建文件
    message = " ".join(map(str, args))
    logger.info(message)


def e_print(*args: Any, **kwargs: Any) -> None:
    """
    错误信息打印（兼容原有函数）

    Args:
        *args: 要打印的参数
        **kwargs: 关键字参数
    """
    logger = get_console_logger()  # 修改：使用console_logger避免创建文件
    message = " ".join(map(str, args))
    logger.error(message)


# 注释掉默认根日志器设置，避免创建不必要的日志文件
# _default_logger = setup_logger()
