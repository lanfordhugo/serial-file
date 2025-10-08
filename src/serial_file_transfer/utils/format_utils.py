"""
文件名称: format_utils.py
内容摘要: 数据格式化工具函数集合
当前版本: v1.0.0
作者: AI Assistant
创建日期: 2025-10-08
"""

from typing import Tuple


def format_file_size(bytes_count: int, precision: int = 2) -> str:
    """
    格式化文件大小为人类可读格式
    
    Args:
        bytes_count: 字节数
        precision: 小数精度（默认2位）
        
    Returns:
        格式化后的字符串（如 "1.23 MB"）
        
    Examples:
        >>> format_file_size(1024)
        '1.00 KB'
        >>> format_file_size(1536, precision=1)
        '1.5 KB'
        >>> format_file_size(1048576)
        '1.00 MB'
    """
    if bytes_count < 1024:
        return f"{bytes_count} B"
    elif bytes_count < 1024 * 1024:
        kb = bytes_count / 1024
        return f"{kb:.{precision}f} KB"
    elif bytes_count < 1024 * 1024 * 1024:
        mb = bytes_count / (1024 * 1024)
        return f"{mb:.{precision}f} MB"
    else:
        gb = bytes_count / (1024 * 1024 * 1024)
        return f"{gb:.{precision}f} GB"


def format_transfer_speed(bytes_per_second: float, precision: int = 2) -> str:
    """
    格式化传输速度
    
    Args:
        bytes_per_second: 每秒字节数
        precision: 小数精度（默认2位）
        
    Returns:
        格式化后的速度字符串（如 "1.23 MB/s"）
        
    Examples:
        >>> format_transfer_speed(1024)
        '1.00 KB/s'
        >>> format_transfer_speed(1048576)
        '1.00 MB/s'
    """
    return format_file_size(int(bytes_per_second), precision=precision) + "/s"


def format_transfer_progress(
    current: int, total: int, precision: int = 2
) -> Tuple[str, str]:
    """
    格式化传输进度信息
    
    Args:
        current: 当前传输字节数
        total: 总字节数
        precision: 小数精度（默认2位）
        
    Returns:
        元组 (进度文本, 单位)
        
    Examples:
        >>> format_transfer_progress(512, 1024)
        ('0.50 / 1.00', 'KB')
        >>> format_transfer_progress(524288, 1048576)
        ('0.50 / 1.00', 'MB')
    """
    if total < 1024:
        # 字节
        return f"{current} / {total}", "B"
    elif total < 1024 * 1024:
        # KB
        current_kb = current / 1024
        total_kb = total / 1024
        return f"{current_kb:.{precision}f} / {total_kb:.{precision}f}", "KB"
    elif total < 1024 * 1024 * 1024:
        # MB
        current_mb = current / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        return f"{current_mb:.{precision}f} / {total_mb:.{precision}f}", "MB"
    else:
        # GB
        current_gb = current / (1024 * 1024 * 1024)
        total_gb = total / (1024 * 1024 * 1024)
        return f"{current_gb:.{precision}f} / {total_gb:.{precision}f}", "GB"


def format_progress_text(current: int, total: int) -> str:
    """
    格式化进度文本（自动选择合适单位）
    
    Args:
        current: 当前传输字节数
        total: 总字节数
        
    Returns:
        格式化后的进度文本
        
    Examples:
        >>> format_progress_text(512, 1024)
        '0.50 / 1.00 KB'
        >>> format_progress_text(524288, 1048576)
        '0.50 / 1.00 MB'
    """
    if total <= 0:
        return "0 / 0 B"
    
    # 根据总大小选择合适的单位
    if total < 1024:
        # 字节
        return f"{current} / {total} B"
    elif total < 1024 * 1024:
        # KB
        current_kb = current / 1024
        total_kb = total / 1024
        return f"{current_kb:.1f} / {total_kb:.1f} KB"
    elif total < 1024 * 1024 * 1024:
        # MB
        current_mb = current / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        return f"{current_mb:.2f} / {total_mb:.2f} MB"
    else:
        # GB
        current_gb = current / (1024 * 1024 * 1024)
        total_gb = total / (1024 * 1024 * 1024)
        return f"{current_gb:.2f} / {total_gb:.2f} GB"


def calculate_transfer_speed(
    current_bytes: int, previous_bytes: int, time_diff: float
) -> float:
    """
    计算传输速度（字节/秒）
    
    Args:
        current_bytes: 当前已传输字节数
        previous_bytes: 上次记录的字节数
        time_diff: 时间差（秒）
        
    Returns:
        传输速度（字节/秒）
        
    Examples:
        >>> calculate_transfer_speed(2048, 1024, 1.0)
        1024.0
    """
    if time_diff <= 0:
        return 0.0
    
    bytes_diff = current_bytes - previous_bytes
    if bytes_diff <= 0:
        return 0.0
    
    return bytes_diff / time_diff

