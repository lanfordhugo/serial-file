"""
文件名称: resource_path.py
内容摘要: 打包后资源路径处理工具
当前版本: v1.0.0
作者: AI Assistant
创建日期: 2025-09-29

功能说明:
- 处理PyInstaller打包后的资源文件路径
- 支持开发环境和打包环境的路径兼容
- 遵循PyInstaller最佳实践
"""

import sys
import os
from pathlib import Path
from typing import Union


def get_resource_path(relative_path: Union[str, Path]) -> Path:
    """
    获取资源文件的绝对路径
    
    在开发环境中返回相对于项目根目录的路径
    在打包环境中返回相对于临时目录的路径
    
    Args:
        relative_path: 相对路径（相对于项目根目录）
        
    Returns:
        资源文件的绝对路径
        
    Example:
        >>> get_resource_path("config/transfer.yaml")
        Path("/path/to/project/config/transfer.yaml")  # 开发环境
        Path("/tmp/_MEI12345/config/transfer.yaml")    # 打包环境
    """
    relative_path = Path(relative_path)
    
    try:
        # PyInstaller打包后的临时目录
        if hasattr(sys, '_MEIPASS'):
            # 打包环境：使用临时目录
            base_path = Path(sys._MEIPASS)
            resource_path = base_path / relative_path
            
            # 验证文件是否存在
            if resource_path.exists():
                return resource_path
            else:
                # 如果临时目录中没有找到，尝试当前工作目录
                fallback_path = Path.cwd() / relative_path
                if fallback_path.exists():
                    return fallback_path
                # 如果都找不到，返回临时目录路径（让调用者处理文件不存在的情况）
                return resource_path
        else:
            # 开发环境：相对于项目根目录
            # 通过当前文件位置推断项目根目录
            current_file = Path(__file__)
            # 从 src/serial_file_transfer/utils/resource_path.py 回到项目根目录
            project_root = current_file.parent.parent.parent.parent
            resource_path = project_root / relative_path
            
            # 验证路径是否存在
            if resource_path.exists():
                return resource_path
            else:
                # 尝试当前工作目录
                fallback_path = Path.cwd() / relative_path
                if fallback_path.exists():
                    return fallback_path
                # 返回推断的路径（让调用者处理文件不存在的情况）
                return resource_path
                
    except Exception:
        # 异常情况：返回相对于当前工作目录的路径
        return Path.cwd() / relative_path


def get_config_path(config_filename: str = "transfer.yaml") -> Path:
    """
    获取配置文件路径
    
    Args:
        config_filename: 配置文件名
        
    Returns:
        配置文件的绝对路径
    """
    return get_resource_path(f"config/{config_filename}")


def is_packaged() -> bool:
    """
    检查当前是否运行在PyInstaller打包环境中
    
    Returns:
        True if 打包环境, False if 开发环境
    """
    return hasattr(sys, '_MEIPASS')


def get_bundle_dir() -> Path:
    """
    获取程序包目录
    
    在开发环境中返回项目根目录
    在打包环境中返回临时解压目录
    
    Returns:
        程序包目录路径
    """
    if is_packaged():
        return Path(sys._MEIPASS)
    else:
        # 开发环境：返回项目根目录
        current_file = Path(__file__)
        return current_file.parent.parent.parent.parent


def setup_packaged_environment():
    """
    设置打包环境的Python路径
    
    确保在打包环境中能正确导入模块
    应在程序启动时调用
    """
    if is_packaged():
        bundle_dir = get_bundle_dir()
        src_dir = bundle_dir / "src"
        
        # 将源码目录添加到Python路径的最前面
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))
            
        # 确保bundle目录也在路径中
        if str(bundle_dir) not in sys.path:
            sys.path.insert(0, str(bundle_dir))


def debug_paths():
    """
    调试函数：打印路径信息
    用于排查打包后的路径问题
    """
    print(f"是否打包环境: {is_packaged()}")
    print(f"程序包目录: {get_bundle_dir()}")
    print(f"当前工作目录: {Path.cwd()}")
    print(f"Python路径: {sys.path[:3]}...")  # 只显示前3个路径
    
    # 测试配置文件路径
    config_path = get_config_path()
    print(f"配置文件路径: {config_path}")
    print(f"配置文件存在: {config_path.exists()}")
    
    if is_packaged():
        print(f"临时目录: {sys._MEIPASS}")
        temp_config = Path(sys._MEIPASS) / "config" / "transfer.yaml"
        print(f"临时配置文件: {temp_config}")
        print(f"临时配置存在: {temp_config.exists()}")
