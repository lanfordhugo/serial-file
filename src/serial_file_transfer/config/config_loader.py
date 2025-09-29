"""
配置加载器
==========

负责从 YAML 文件加载传输配置。
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import serial

from .settings import SerialConfig, TransferConfig
from ..utils.logger import get_console_logger

logger = get_console_logger(__name__)


class ConfigLoader:
    """配置加载器"""
    
    DEFAULT_CONFIG_PATHS = [
        "config/transfer.yaml",
        "config/transfer.yml", 
        "transfer.yaml",
        "transfer.yml"
    ]
    
    @classmethod
    def find_config_file(cls, config_path: Optional[str] = None) -> Optional[Path]:
        """
        查找配置文件
        
        Args:
            config_path: 指定的配置文件路径
            
        Returns:
            找到的配置文件路径，未找到返回None
        """
        # 如果指定了路径，直接检查
        if config_path:
            path = Path(config_path)
            if path.exists():
                return path
            logger.warning(f"指定的配置文件不存在: {config_path}")
            return None
        
        # 检查环境变量
        env_path = os.getenv("SERIAL_TRANSFER_CONFIG")
        if env_path:
            path = Path(env_path)
            if path.exists():
                return path
            logger.warning(f"环境变量指定的配置文件不存在: {env_path}")
        
        # 按默认路径查找
        project_root = Path(__file__).parent.parent.parent.parent
        for rel_path in cls.DEFAULT_CONFIG_PATHS:
            path = project_root / rel_path
            if path.exists():
                logger.debug(f"找到配置文件: {path}")
                return path
        
        logger.warning("未找到配置文件，将使用默认配置")
        return None
    
    @classmethod
    def load_config(cls, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
        """
        config_file = cls.find_config_file(config_path)
        
        if config_file is None:
            logger.info("使用默认配置")
            return cls._get_default_config()
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"成功加载配置文件: {config_file}")
            return config or {}
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            logger.info("使用默认配置")
            return cls._get_default_config()
    
    @classmethod
    def _get_default_config(cls) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "serial_config": {
                "baudrate": 1728000,  # 使用高速波特率作为默认值
                "bytesize": 8,
                "parity": "none",
                "stopbits": 1,
                "timeout": 0.05       # 优化的串口超时
            },
            "transfer_config": {
                "max_data_length": 16384,  # 高速传输块大小
                "request_timeout": 0.2,    # 优化的请求超时
                "retry_count": 3,
                "backoff_base": 0.5,
                "show_progress": True,
                "max_cache_size": 4194304,
                "max_retries": 5
            }
        }
    
    @classmethod
    def create_serial_config(cls, port: str, config_path: Optional[str] = None) -> SerialConfig:
        """
        创建串口配置
        
        Args:
            port: 串口号
            config_path: 配置文件路径
            
        Returns:
            SerialConfig 实例
        """
        config = cls.load_config(config_path)
        # 使用标准配置键名
        serial_cfg = config.get("serial_config", {})
        
        # 处理校验位字符串到pyserial常量的转换
        parity_map = {
            'none': serial.PARITY_NONE,
            'even': serial.PARITY_EVEN,
            'odd': serial.PARITY_ODD,
            'mark': serial.PARITY_MARK,
            'space': serial.PARITY_SPACE
        }
        
        parity_str = serial_cfg.get('parity', 'none').lower()
        parity = parity_map.get(parity_str, serial.PARITY_NONE)
        
        return SerialConfig(
            port=port,
            baudrate=serial_cfg.get('baudrate', 115200),
            bytesize=serial_cfg.get('bytesize', 8),
            parity=parity,
            stopbits=serial_cfg.get('stopbits', 1),
            timeout=serial_cfg.get('timeout', 0.5)
        )
    
    @classmethod
    def create_transfer_config(cls, config_path: Optional[str] = None) -> TransferConfig:
        """
        创建传输配置
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            TransferConfig 实例
        """
        config = cls.load_config(config_path)
        transfer_cfg = config.get("transfer_config", {})
        
        return TransferConfig(
            max_data_length=transfer_cfg.get('max_data_length', 1024),
            request_timeout=transfer_cfg.get('request_timeout', 5),
            retry_count=transfer_cfg.get('retry_count', 3),
            backoff_base=transfer_cfg.get('backoff_base', 0.5),
            show_progress=transfer_cfg.get('show_progress', True),
            max_cache_size=transfer_cfg.get('max_cache_size', 4194304),
            max_retries=transfer_cfg.get('max_retries', 5)
        )
    
    @classmethod
    def get_port_config(cls, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        获取端口配置
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            端口配置字典
        """
        config = cls.load_config(config_path)
        return config.get("port_config", {})
    
    @classmethod
    def get_test_config(cls, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        获取测试配置
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            测试配置字典
        """
        config = cls.load_config(config_path)
        return config.get("test_config", {})
