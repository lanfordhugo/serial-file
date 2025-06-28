"""
多文件传输命令行接口
==================

提供批量文件发送和接收的命令行接口。
"""

from pathlib import Path

from ..config.settings import SerialConfig, TransferConfig
from ..core.serial_manager import SerialManager
from ..transfer.file_manager import SenderFileManager, ReceiverFileManager
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MultiFileTransferCLI:
    """多文件传输命令行接口"""
    
    @staticmethod
    def show_available_ports() -> None:
        """显示可用的串口"""
        SerialManager.print_available_ports()
    
    @staticmethod
    def get_user_input_port() -> str:
        """获取用户输入的串口号"""
        MultiFileTransferCLI.show_available_ports()
        while True:
            port = input('请输入串口号（如COM1）: ').strip()
            if port:
                return port
            print("串口号不能为空，请重新输入。")
    
    @staticmethod
    def get_user_input_folder_path() -> str:
        """获取用户输入的文件夹路径"""
        while True:
            folder_path = input('请输入文件夹路径: ').strip()
            if folder_path:
                path = Path(folder_path)
                if path.exists() and path.is_dir():
                    return str(path)
                else:
                    print("文件夹不存在或路径不是文件夹，请重新输入。")
            else:
                print("文件夹路径不能为空，请重新输入。")
    
    @staticmethod
    def get_user_input_save_folder() -> str:
        """获取用户输入的保存文件夹路径"""
        while True:
            save_folder = input('请输入保存文件夹路径: ').strip()
            if save_folder:
                return save_folder
            print("保存文件夹路径不能为空，请重新输入。")
    
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
    def send_files() -> bool:
        """发送多个文件的CLI入口"""
        try:
            print("=== 串口批量文件发送 ===")
            
            # 获取用户输入
            port = MultiFileTransferCLI.get_user_input_port()
            folder_path = MultiFileTransferCLI.get_user_input_folder_path()
            baudrate = MultiFileTransferCLI.get_baudrate()
            
            # 创建配置
            serial_config = SerialConfig(port=port, baudrate=baudrate, timeout=0.5)
            transfer_config = TransferConfig(max_data_length=10*1024)  # 10KB
            
            # 创建串口管理器和文件管理器
            with SerialManager(serial_config) as serial_manager:
                file_manager = SenderFileManager(folder_path, serial_manager, transfer_config)
                
                print(f"开始发送文件夹: {folder_path}")
                if file_manager.start_batch_send():
                    print("批量文件发送成功！")
                    return True
                else:
                    print("批量文件发送失败！")
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
    def receive_files() -> bool:
        """接收多个文件的CLI入口"""
        try:
            print("=== 串口批量文件接收 ===")
            
            # 获取用户输入
            port = MultiFileTransferCLI.get_user_input_port()
            save_folder = MultiFileTransferCLI.get_user_input_save_folder()
            baudrate = MultiFileTransferCLI.get_baudrate()
            
            # 创建配置
            serial_config = SerialConfig(port=port, baudrate=baudrate, timeout=0.05)
            transfer_config = TransferConfig(max_data_length=10*1024)  # 10KB
            
            # 创建串口管理器和文件管理器
            with SerialManager(serial_config) as serial_manager:
                file_manager = ReceiverFileManager(save_folder, serial_manager, transfer_config)
                
                print(f"开始接收文件，保存到: {save_folder}")
                if file_manager.start_batch_receive():
                    print("批量文件接收成功！")
                    return True
                else:
                    print("批量文件接收失败！")
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