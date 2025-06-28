"""
单文件传输命令行接口
==================

提供单个文件发送和接收的命令行接口。
"""

from pathlib import Path
from typing import Optional

from ..config.settings import SerialConfig, TransferConfig
from ..core.serial_manager import SerialManager
from ..transfer.sender import FileSender
from ..transfer.receiver import FileReceiver
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SingleFileTransferCLI:
    """单文件传输命令行接口"""
    
    @staticmethod
    def show_available_ports() -> None:
        """显示可用的串口"""
        SerialManager.print_available_ports()
    
    @staticmethod
    def get_user_input_port() -> str:
        """获取用户输入的串口号"""
        SingleFileTransferCLI.show_available_ports()
        while True:
            port = input('请输入串口号（如COM1）: ').strip()
            if port:
                return port
            print("串口号不能为空，请重新输入。")
    
    @staticmethod
    def get_user_input_file_path() -> str:
        """获取用户输入的文件路径"""
        while True:
            file_path = input('请输入文件路径: ').strip()
            if file_path:
                path = Path(file_path)
                if path.exists() and path.is_file():
                    return str(path)
                else:
                    print("文件不存在或路径不是文件，请重新输入。")
            else:
                print("文件路径不能为空，请重新输入。")
    
    @staticmethod
    def get_user_input_save_path() -> str:
        """获取用户输入的保存路径"""
        while True:
            save_path = input('请输入保存路径（包含文件名）: ').strip()
            if save_path:
                return save_path
            print("保存路径不能为空，请重新输入。")
    
    @staticmethod
    def get_baudrate() -> int:
        """获取波特率"""
        default_baudrate = 1728000
        baudrate_input = input(f'请输入波特率（默认{default_baudrate}）: ').strip()
        
        if not baudrate_input:
            return default_baudrate
        
        try:
            return int(baudrate_input)
        except ValueError:
            print(f"波特率格式错误，使用默认值: {default_baudrate}")
            return default_baudrate
    
    @staticmethod
    def send_file() -> bool:
        """发送文件的CLI入口"""
        try:
            print("=== 串口文件发送 ===")
            
            # 获取用户输入
            port = SingleFileTransferCLI.get_user_input_port()
            file_path = SingleFileTransferCLI.get_user_input_file_path()
            baudrate = SingleFileTransferCLI.get_baudrate()
            
            # 创建配置
            serial_config = SerialConfig(port=port, baudrate=baudrate, timeout=0.5)
            transfer_config = TransferConfig(max_data_length=10*1024)  # 10KB
            
            # 创建串口管理器和发送器
            with SerialManager(serial_config) as serial_manager:
                sender = FileSender(serial_manager, file_path, transfer_config)
                
                print(f"开始发送文件: {file_path}")
                if sender.start_transfer():
                    print("文件发送成功！")
                    return True
                else:
                    print("文件发送失败！")
                    return False
                    
        except KeyboardInterrupt:
            print("\n用户取消操作")
            return False
        except Exception as e:
            logger.error(f"发送文件时发生异常: {e}")
            print(f"发送失败: {e}")
            return False
        finally:
            input('按回车键退出...')
    
    @staticmethod
    def receive_file() -> bool:
        """接收文件的CLI入口"""
        try:
            print("=== 串口文件接收 ===")
            
            # 获取用户输入
            port = SingleFileTransferCLI.get_user_input_port()
            save_path = SingleFileTransferCLI.get_user_input_save_path()
            baudrate = SingleFileTransferCLI.get_baudrate()
            
            # 创建配置
            serial_config = SerialConfig(port=port, baudrate=baudrate, timeout=0.05)
            transfer_config = TransferConfig(max_data_length=10*1024)  # 10KB
            
            # 创建串口管理器和接收器
            with SerialManager(serial_config) as serial_manager:
                receiver = FileReceiver(serial_manager, save_path, transfer_config)
                
                print(f"开始接收文件，保存到: {save_path}")
                if receiver.start_transfer():
                    print("文件接收成功！")
                    return True
                else:
                    print("文件接收失败！")
                    return False
                    
        except KeyboardInterrupt:
            print("\n用户取消操作")
            return False
        except Exception as e:
            logger.error(f"接收文件时发生异常: {e}")
            print(f"接收失败: {e}")
            return False
        finally:
            input('按回车键退出...') 