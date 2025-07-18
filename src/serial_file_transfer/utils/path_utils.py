"""
路径处理工具模块
================

提供跨平台路径处理和文件名冲突解决功能。
"""

import os
import re
from pathlib import Path
from typing import Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除或替换不安全的字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的安全文件名
    """
    # 定义不安全的字符
    unsafe_chars = r'[<>:"/\\|?*]'
    
    # 替换不安全字符为下划线
    safe_filename = re.sub(unsafe_chars, '_', filename)
    
    # 移除开头和结尾的空格和点
    safe_filename = safe_filename.strip(' .')
    
    # 确保文件名不为空
    if not safe_filename:
        safe_filename = "unnamed_file"
    
    # 限制文件名长度（Windows限制为255字符）
    if len(safe_filename) > 255:
        name, ext = os.path.splitext(safe_filename)
        max_name_len = 255 - len(ext)
        safe_filename = name[:max_name_len] + ext
    
    return safe_filename


def normalize_path(path_str: str) -> str:
    """
    标准化路径，确保跨平台兼容性
    
    Args:
        path_str: 原始路径字符串
        
    Returns:
        标准化后的路径字符串
    """
    # 将所有路径分隔符统一为正斜杠
    normalized = path_str.replace('\\', '/')
    
    # 移除多余的斜杠
    normalized = re.sub(r'/+', '/', normalized)
    
    # 移除开头的斜杠（相对路径）
    normalized = normalized.lstrip('/')
    
    return normalized


def resolve_file_conflict(file_path: Path) -> Path:
    """
    解决文件名冲突，如果文件已存在则生成新的文件名
    
    Args:
        file_path: 目标文件路径
        
    Returns:
        解决冲突后的文件路径
    """
    if not file_path.exists():
        return file_path
    
    # 分离文件名和扩展名
    stem = file_path.stem
    suffix = file_path.suffix
    parent = file_path.parent
    
    # 尝试添加数字后缀
    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_path = parent / new_name
        
        if not new_path.exists():
            logger.info(f"文件冲突解决: {file_path.name} -> {new_name}")
            return new_path
        
        counter += 1
        
        # 防止无限循环
        if counter > 9999:
            logger.error(f"无法解决文件冲突: {file_path}")
            return file_path


def create_safe_path(base_path: Path, relative_path: str) -> Path:
    """
    创建安全的文件路径，处理跨平台兼容性和文件名冲突
    
    Args:
        base_path: 基础路径
        relative_path: 相对路径
        
    Returns:
        安全的完整文件路径
    """
    # 标准化相对路径
    normalized_path = normalize_path(relative_path)
    
    # 分割路径组件并清理每个部分
    path_parts = []
    for part in normalized_path.split('/'):
        if part and part != '.':  # 忽略空部分和当前目录标记
            safe_part = sanitize_filename(part)
            path_parts.append(safe_part)
    
    # 构建完整路径
    if path_parts:
        full_path = base_path
        for part in path_parts:
            full_path = full_path / part
    else:
        full_path = base_path / "unnamed_file"
    
    # 解决文件名冲突
    return resolve_file_conflict(full_path)


def ensure_directory_exists(dir_path: Path) -> bool:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        dir_path: 目录路径
        
    Returns:
        成功返回True，失败返回False
    """
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"创建目录失败: {dir_path}, 错误: {e}")
        return False


def get_relative_path_info(source_path: Path) -> tuple[str, bool]:
    """
    获取源路径的相对路径信息
    
    Args:
        source_path: 源路径
        
    Returns:
        (根目录名称, 是否为文件夹) 的元组
    """
    if source_path.is_file():
        return "", False
    elif source_path.is_dir():
        return source_path.name, True
    else:
        return "", False
