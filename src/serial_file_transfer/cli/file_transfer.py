"""
统一文件传输命令行接口
====================

提供统一的文件/文件夹发送和接收命令行接口，自动根据路径类型选择处理方式。
"""

from pathlib import Path
from typing import Optional

from ..config.settings import SerialConfig, TransferConfig
from ..core.serial_manager import SerialManager
from ..transfer.sender import FileSender
from ..transfer.receiver import FileReceiver
from ..transfer.file_manager import SenderFileManager, ReceiverFileManager
from ..utils.logger import get_logger

logger = get_logger(__name__)


class FileTransferCLI:
    """统一文件传输命令行接口"""
    
    @staticmethod
    def show_available_ports() -> None:
        """显示可用的串口"""
        SerialManager.print_available_ports()
    
    @staticmethod
    def get_user_input_port() -> str:
        """获取用户输入的串口号"""
        FileTransferCLI.show_available_ports()
        while True:
            port = input('请输入串口号（如COM1）: ').strip()
            if port:
                return port
            print("串口号不能为空，请重新输入。")
    
    @staticmethod
    def get_user_input_source_path() -> str:
        """获取用户输入的源路径（文件或文件夹）"""
        while True:
            source_path = input('请输入要发送的文件或文件夹路径: ').strip()
            if source_path:
                path = Path(source_path)
                if path.exists():
                    return str(path)
                else:
                    print("路径不存在，请重新输入。")
            else:
                print("路径不能为空，请重新输入。")
    
    @staticmethod
    def get_user_input_save_path() -> str:
        """获取用户输入的保存路径"""
        while True:
            save_path = input('请输入保存路径（文件名或文件夹路径）: ').strip()
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
    def _detect_path_type(path: str) -> str:
        """
        检测路径类型
        
        Args:
            path: 文件或文件夹路径
            
        Returns:
            'file' 或 'folder'
        """
        path_obj = Path(path)
        if path_obj.is_file():
            return 'file'
        elif path_obj.is_dir():
            return 'folder'
        else:
            raise ValueError(f"无效的路径类型: {path}")
    
    @staticmethod
    def send() -> bool:
        """发送文件或文件夹的统一CLI入口"""
        try:
            print("=== 串口文件传输 - 发送 ===")
            
            # 获取用户输入
            port = FileTransferCLI.get_user_input_port()
            source_path = FileTransferCLI.get_user_input_source_path()
            baudrate = FileTransferCLI.get_baudrate()
            
            # 检测路径类型
            path_type = FileTransferCLI._detect_path_type(source_path)
            
            # 创建配置
            serial_config = SerialConfig(port=port, baudrate=baudrate, timeout=0.5)
            transfer_config = TransferConfig(max_data_length=10*1024)  # 10KB
            
            # 创建串口管理器
            with SerialManager(serial_config) as serial_manager:
                if path_type == 'file':
                    # 单文件发送
                    print(f"检测到文件，开始发送: {source_path}")
                    sender = FileSender(serial_manager, source_path, transfer_config)
                    
                    if sender.start_transfer():
                        print("文件发送成功！")
                        return True
                    else:
                        print("文件发送失败！")
                        return False
                        
                elif path_type == 'folder':
                    # 文件夹发送
                    print(f"检测到文件夹，开始批量发送: {source_path}")
                    file_manager = SenderFileManager(source_path, serial_manager, transfer_config)
                    
                    if file_manager.start_batch_send():
                        print("批量文件发送成功！")
                        return True
                    else:
                        print("批量文件发送失败！")
                        return False
                else:
                    print(f"未知路径类型: {path_type}")
                    return False
                        
        except KeyboardInterrupt:
            print("\n用户取消操作")
            return False
        except Exception as e:
            logger.error(f"发送时发生异常: {e}")
            print(f"发送失败: {e}")
            return False
        finally:
            input('按回车键退出...')
    
    @staticmethod
    def receive() -> bool:
        """接收文件或文件夹的统一CLI入口"""
        try:
            print("=== 串口文件传输 - 接收 ===")
            
            # 获取用户输入
            port = FileTransferCLI.get_user_input_port()
            save_path = FileTransferCLI.get_user_input_save_path()
            baudrate = FileTransferCLI.get_baudrate()
            
            # 询问接收模式
            print("\n请选择接收模式:")
            print("1. 单文件接收")
            print("2. 批量文件接收")
            
            while True:
                mode = input("请输入选择（1或2）: ").strip()
                if mode in ['1', '2']:
                    break
                print("请输入有效选择（1或2）")
            
            # 创建配置
            serial_config = SerialConfig(port=port, baudrate=baudrate, timeout=0.05)
            transfer_config = TransferConfig(max_data_length=10*1024)  # 10KB
            
            # 创建串口管理器
            with SerialManager(serial_config) as serial_manager:
                if mode == '1':
                    # 单文件接收
                    print(f"开始接收文件，保存到: {save_path}")
                    receiver = FileReceiver(serial_manager, save_path, transfer_config)
                    
                    if receiver.start_transfer():
                        print("文件接收成功！")
                        return True
                    else:
                        print("文件接收失败！")
                        return False
                        
                elif mode == '2':
                    # 批量文件接收
                    print(f"开始批量接收文件，保存到: {save_path}")
                    file_manager = ReceiverFileManager(save_path, serial_manager, transfer_config)
                    
                    if file_manager.start_batch_receive():
                        print("批量文件接收成功！")
                        return True
                    else:
                        print("批量文件接收失败！")
                        return False
                else:
                    print(f"未知接收模式: {mode}")
                    return False
                        
        except KeyboardInterrupt:
            print("\n用户取消操作")
            return False
        except Exception as e:
            logger.error(f"接收时发生异常: {e}")
            print(f"接收失败: {e}")
            return False
        finally:
            input('按回车键退出...') 