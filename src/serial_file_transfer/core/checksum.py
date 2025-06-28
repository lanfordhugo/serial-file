"""
校验算法模块
============

提供数据校验相关的算法实现。
"""

from typing import Union


def calculate_checksum(data: bytes) -> int:
    """
    计算数据的校验和
    
    采用简单的累加校验算法，将所有字节相加后取低16位。
    
    Args:
        data: 需要计算校验和的字节数据
        
    Returns:
        校验和值，16位无符号整数
        
    Raises:
        TypeError: 当输入不是bytes类型时抛出
        
    Examples:
        >>> calculate_checksum(b'hello')
        532
        >>> calculate_checksum(b'')
        0
    """
    if not isinstance(data, bytes):
        raise TypeError("输入数据必须是bytes类型")
    
    checksum = 0
    for byte in data:
        checksum += byte
    
    return checksum & 0xFFFF


def calculate_crc16_modbus(data: bytes) -> int:
    """
    计算CRC16校验码（Modbus格式）
    
    Args:
        data: 需要计算CRC的字节数据
        
    Returns:
        CRC16校验码
        
    Note:
        这是从原m_print.py中移植的函数，保持向后兼容
    """
    if not isinstance(data, bytes):
        raise TypeError("输入数据必须是bytes类型")
        
    crc = 0xFFFF
    polynomial = 0xA001

    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ polynomial
            else:
                crc >>= 1
                
    return crc 