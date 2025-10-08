"""
文件名称: error_handler.py
内容摘要: 统一的错误处理和错误消息格式化工具
当前版本: v1.0.0
作者: AI Assistant
创建日期: 2025-10-08
"""

from typing import Tuple


def format_serial_error(error: Exception) -> str:
    """
    将串口异常转换为用户友好的错误消息
    
    Args:
        error: 原始异常对象
        
    Returns:
        用户友好的错误消息字符串
    """
    error_str = str(error)
    
    # 权限错误
    if "Permission denied" in error_str or "Access is denied" in error_str:
        return "串口权限不足，可能被其他程序占用"
    
    # 资源忙碌
    elif "Device or resource busy" in error_str or "busy" in error_str:
        return "串口被其他程序占用"
    
    # 设备不存在
    elif "No such file or directory" in error_str:
        return "串口设备不存在，请检查设备连接"
    
    # 超时错误
    elif "timeout" in error_str.lower():
        return "串口连接超时"
    
    # 其他未知错误
    else:
        return f"串口不可用: {error_str}"


def parse_serial_error(error: Exception) -> Tuple[str, str]:
    """
    解析串口异常，返回错误类型和详细消息
    
    Args:
        error: 原始异常对象
        
    Returns:
        元组 (错误类型, 错误消息)
    """
    error_str = str(error)
    
    if "Permission denied" in error_str or "Access is denied" in error_str:
        return "permission_error", "串口权限不足，可能被其他程序占用"
    
    elif "Device or resource busy" in error_str or "busy" in error_str:
        return "busy_error", "串口被其他程序占用"
    
    elif "No such file or directory" in error_str:
        return "not_found_error", "串口设备不存在，请检查设备连接"
    
    elif "timeout" in error_str.lower():
        return "timeout_error", "串口连接超时"
    
    else:
        return "unknown_error", f"串口不可用: {error_str}"

