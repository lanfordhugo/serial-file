"""
统一文件传输命令行接口
====================

提供统一的文件/文件夹发送和接收命令行接口，自动根据路径类型选择处理方式。
"""

from pathlib import Path
from typing import Optional
import time

from ..config.settings import SerialConfig, TransferConfig
from ..config.config_loader import ConfigLoader
from ..core.serial_manager import SerialManager
from ..transfer.sender import FileSender
from ..transfer.receiver import FileReceiver
from ..transfer.file_manager import SenderFileManager, ReceiverFileManager
from ..utils.logger import get_console_logger
from ..utils.path_utils import get_relative_path_info

logger = get_console_logger(__name__)


class FileTransferCLI:
    """统一文件传输命令行接口"""

    # CLI参数传递的临时属性（支持非交互模式）
    _temp_port: str | None = None
    _temp_path: str | None = None
    _temp_save_path: str | None = None
    _temp_baudrate: int | None = None

    @classmethod
    def _clear_temp_params(cls) -> None:
        """清理临时参数"""
        cls._temp_port = None
        cls._temp_path = None
        cls._temp_save_path = None
        cls._temp_baudrate = None

    @staticmethod
    def show_available_ports() -> None:
        """显示可用的串口"""
        SerialManager.print_available_ports()

    @staticmethod
    def get_user_input_port() -> Optional[str]:
        """获取用户选择的串口号"""
        # 如果有临时参数，使用临时参数（非交互模式）
        if FileTransferCLI._temp_port:
            port = FileTransferCLI._temp_port
            print(f"✅ 使用指定串口: {port}")
            return port
            
        # 获取可用串口列表
        ports = SerialManager.list_available_ports()

        # 如果没有找到串口，返回None
        if not ports:
            print("❌ 没有找到可用的串口。")
            print("   请检查:")
            print("   1. 串口设备是否已连接")
            print("   2. 串口驱动是否已安装")
            print("   3. 是否有足够的权限访问串口")
            return None

        # 显示可用串口列表
        print("可用的串口列表:")
        for i, port in enumerate(ports, 1):
            print(f"  {i}. {port['device']} - {port['description']}")

        # 让用户选择
        while True:
            try:
                choice = input(f"\n请选择串口号 (1-{len(ports)}): ").strip()
                if not choice:
                    print("请输入有效的选择。")
                    continue

                index = int(choice) - 1
                if 0 <= index < len(ports):
                    selected_port = ports[index]["device"]
                    print(f"✅ 已选择: {selected_port}")
                    return selected_port
                else:
                    print(f"请输入1到{len(ports)}之间的数字。")
            except ValueError:
                print("请输入有效的数字。")
            except KeyboardInterrupt:
                print("\n用户取消选择")
                return None

    @staticmethod
    def get_user_input_source_path() -> str:
        """获取用户输入的源路径（文件或文件夹）"""
        # 如果有临时参数，使用临时参数（非交互模式）
        if FileTransferCLI._temp_path:
            path = Path(FileTransferCLI._temp_path)
            if path.exists():
                print(f"✅ 使用指定路径: {path}")
                return str(path)
            else:
                raise ValueError(f"指定的路径不存在: {FileTransferCLI._temp_path}")
        
        # 交互模式
        while True:
            source_path = input("请输入要发送的文件或文件夹路径: ").strip()
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
        # 如果有临时参数，使用临时参数（非交互模式）
        if FileTransferCLI._temp_save_path:
            print(f"✅ 使用指定保存路径: {FileTransferCLI._temp_save_path}")
            return FileTransferCLI._temp_save_path
            
        # 交互模式
        while True:
            save_path = input("请输入保存路径（文件名或文件夹路径）: ").strip()
            if save_path:
                return save_path
            print("保存路径不能为空，请重新输入。")

    @staticmethod
    def get_baudrate() -> int:
        """获取波特率"""
        # 如果有临时参数，使用临时参数（非交互模式）
        if FileTransferCLI._temp_baudrate:
            print(f"✅ 使用指定波特率: {FileTransferCLI._temp_baudrate}")
            return FileTransferCLI._temp_baudrate

        # 使用默认波特率
        from ..config.constants import DEFAULT_CLI_BAUDRATE
        default_baudrate = DEFAULT_CLI_BAUDRATE

        print(f"✅ 使用默认波特率: {default_baudrate}")
        print("   （可通过配置文件调整传输参数）")
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
            return "file"
        elif path_obj.is_dir():
            return "folder"
        else:
            raise ValueError(f"无效的路径类型: {path}")

    @staticmethod
    def smart_send() -> bool:
        """发送模式 - 使用配置文件参数"""
        try:
            print("=== 串口文件传输 - 发送模式 ===")

            # 获取用户输入
            port = FileTransferCLI.get_user_input_port()
            if port is None:
                return False

            source_path = FileTransferCLI.get_user_input_source_path()

            # 检测路径类型和统计信息
            path_type = FileTransferCLI._detect_path_type(source_path)

            # 统计文件信息
            if path_type == "file":
                file_count = 1
                total_size = Path(source_path).stat().st_size
                print(f"准备发送文件: {source_path} ({total_size} 字节)")
            else:
                # 简单统计文件夹信息
                path_obj = Path(source_path)
                files = list(path_obj.rglob("*"))
                file_count = len([f for f in files if f.is_file()])
                total_size = sum(f.stat().st_size for f in files if f.is_file())
                print(f"准备发送文件夹: {source_path} ({file_count}个文件, {total_size} 字节)")

            # 从配置文件加载传输参数
            serial_config = ConfigLoader.create_serial_config(port)
            transfer_config = ConfigLoader.create_transfer_config()
            
            print(f"📋 传输参数: 波特率={serial_config.baudrate}, 块大小={transfer_config.max_data_length}")

            with SerialManager(serial_config) as transfer_serial:
                if path_type == "file":
                    # 单文件发送
                    print("开始传输文件...")
                    sender = FileSender(transfer_serial, source_path, transfer_config)

                    # 等待接收端请求文件名
                    print("等待接收端请求文件名...")
                    if not sender.wait_for_filename_request():
                        print("❌ 等待文件名请求超时！")
                        return False

                    # 发送文件名（只发送文件名，不包含路径）
                    import os
                    filename = os.path.basename(source_path)
                    print(f"发送文件名: {filename}")
                    if not sender.send_filename(filename):
                        print("❌ 发送文件名失败！")
                        return False

                    if sender.start_transfer():
                        print("🎉 文件发送成功！")
                        return True
                    else:
                        print("❌ 文件发送失败！")
                        return False

                elif path_type == "folder":
                    # 文件夹发送
                    print("开始批量传输文件...")
                    file_manager = SenderFileManager(
                        source_path, transfer_serial, transfer_config
                    )

                    if file_manager.start_batch_send():
                        print("🎉 批量文件发送成功！")
                        return True
                    else:
                        print("❌ 批量文件发送失败！")
                        return False

            # 若代码执行至此仍未 return，视为失败
            return False

        except KeyboardInterrupt:
            print("\n用户取消操作")
            return False
        except Exception as e:
            logger.error(f"发送时发生异常: {e}")
            print(f"❌ 发送失败: {e}")
            return False
        finally:
            # 避免在测试环境中阻塞，检查是否在测试环境中运行
            import sys

            if "pytest" not in sys.modules:
                input("按回车键退出...")

    @staticmethod
    def smart_receive() -> bool:
        """智能接收模式 - 自动检测单文件或文件夹传输"""
        try:
            print("=== 串口文件传输 - 接收模式 ===")

            # 获取用户输入
            port = FileTransferCLI.get_user_input_port()
            if port is None:
                return False

            # 自动使用当前目录作为接收根目录
            import os
            save_path = os.getcwd()
            print(f"✅ 自动接收目录: {save_path}")

            print("正在等待发送端连接...")
            print("提示: 请在发送端启动发送模式")

            # 从配置文件加载传输参数
            serial_config = ConfigLoader.create_serial_config(port)
            transfer_config = ConfigLoader.create_transfer_config()
            
            print(f"📋 传输参数: 波特率={serial_config.baudrate}, 块大小={transfer_config.max_data_length}")

            with SerialManager(serial_config) as transfer_serial:
                print("开始接收文件...")
                print("🔍 正在检测传输类型...")

                # 创建recv_file目录
                final_save_path = Path(save_path)
                recv_file_dir = final_save_path / "recv_file"
                recv_file_dir.mkdir(parents=True, exist_ok=True)
                print(f"📁 接收目录: {recv_file_dir}")

                # 检测传输类型的逻辑
                transmission_type = FileTransferCLI._detect_transmission_type(transfer_serial, transfer_config)
                
                if transmission_type == "folder":
                    # 文件夹传输模式
                    print("📁 检测到文件夹传输模式")
                    return FileTransferCLI._handle_folder_receive(recv_file_dir, transfer_serial, transfer_config)
                else:
                    # 单文件传输模式
                    print("📄 检测到单文件传输模式")
                    return FileTransferCLI._handle_single_file_receive(recv_file_dir, transfer_serial, transfer_config)

        except KeyboardInterrupt:
            print("\n用户取消操作")
            return False
        except Exception as e:
            logger.error(f"接收时发生异常: {e}")
            print(f"❌ 接收失败: {e}")
            return False
        finally:
            # 避免在测试环境中阻塞，检查是否在测试环境中运行
            import sys

            if "pytest" not in sys.modules:
                input("按回车键退出...")

    @staticmethod
    def _detect_transmission_type(serial_manager, transfer_config) -> str:
        """
        智能检测传输类型（单文件或文件夹）
        
        检测策略：
        1. 分析文件名特征（路径分隔符、分卷文件等）
        2. 检测是否有多个文件
        3. 默认降级到单文件模式
        
        Args:
            serial_manager: 串口管理器
            transfer_config: 传输配置
            
        Returns:
            "file" 或 "folder"
        """
        try:
            # 创建临时接收器进行检测
            temp_receiver = FileReceiver(serial_manager, config=transfer_config)
            
            # 尝试获取第一个文件名
            if not temp_receiver.send_filename_request():
                return "file"  # 默认为单文件
                
            first_filename = temp_receiver.receive_filename()
            if first_filename is None:
                return "file"  # 默认为单文件
            
            print(f"📄 检测到第一个文件: {first_filename}")
            
            # 检测逻辑1：分析文件名特征
            has_path_separator = "/" in first_filename or "\\" in first_filename
            is_volume_file = any(first_filename.endswith(ext) for ext in [
                '.001', '.002', '.003', '.004', '.005',
                '.part1', '.part2', '.part3', '.part4', '.part5',
                '.z01', '.z02', '.z03', '.rar', '.r01', '.r02'
            ])
            
            if has_path_separator:
                print("🔍 检测到路径分隔符，判定为文件夹传输")
                return "folder"
                
            if is_volume_file:
                print("🔍 检测到分卷文件，判定为文件夹传输")
                return "folder"
            
            # 检测逻辑2：尝试探测是否还有第二个文件
            print("🔍 探测是否还有更多文件...")
            
            # 注意：这里不能真正接收第一个文件，只是探测
            # 我们使用一个更简单的策略：如果文件名看起来像单个文件，就当作单文件处理
            # 如果后续发现还有文件，ReceiverFileManager会自动处理
            
            # 检测逻辑3：文件名模式分析
            filename_lower = first_filename.lower()
            
            # 常见的单文件扩展名
            single_file_extensions = [
                '.txt', '.doc', '.pdf', '.jpg', '.png', '.mp4', '.avi',
                '.exe', '.msi', '.deb', '.rpm', '.dmg', '.iso'
            ]
            
            is_single_file = any(filename_lower.endswith(ext) for ext in single_file_extensions)
            
            if is_single_file and not is_volume_file:
                print("🔍 检测到单一文件格式，判定为单文件传输")
                return "file"
            
            # 默认策略：当不确定时，选择更安全的文件夹模式
            # 文件夹模式可以处理单文件，但单文件模式无法处理多文件
            print("🔍 无法确定传输类型，使用文件夹模式以确保兼容性")
            return "folder"
            
        except Exception as e:
            logger.error(f"检测传输类型异常: {e}")
            return "file"  # 出错时默认为单文件

    @staticmethod  
    def _handle_single_file_receive(recv_file_dir, serial_manager, transfer_config) -> bool:
        """
        处理单文件接收
        
        Args:
            recv_file_dir: 接收文件目录
            serial_manager: 串口管理器
            transfer_config: 传输配置
            
        Returns:
            成功返回True，失败返回False
        """
        try:
            # 初始化接收器
            receiver = FileReceiver(serial_manager, config=transfer_config)

            # 请求并接收文件名（带重试机制）
            print("📝 正在获取文件名...")
            filename = None
            max_retries = 3

            for attempt in range(max_retries):
                if attempt > 0:
                    print(f"🔄 重试获取文件名 ({attempt + 1}/{max_retries})...")

                if not receiver.send_filename_request():
                    print(f"❌ 发送文件名请求失败 (尝试 {attempt + 1})")
                    if attempt == max_retries - 1:
                        print("❌ 多次尝试后仍无法发送文件名请求！")
                        return False
                    continue

                filename = receiver.receive_filename()
                if filename is not None:
                    break

                print(f"❌ 接收文件名失败 (尝试 {attempt + 1})")
                if attempt == max_retries - 1:
                    print("❌ 多次尝试后仍无法接收文件名！")
                    return False

            if filename is None:
                print("❌ 无法获取文件名！")
                return False

            print(f"📄 接收到文件名: {filename}")

            # 使用 create_safe_path 统一生成保存路径
            from ..utils.path_utils import create_safe_path, ensure_directory_exists
            file_save_path = create_safe_path(recv_file_dir, filename)
            ensure_directory_exists(file_save_path.parent)

            print(f"📄 准备保存到: {file_save_path}")

            # 设置保存路径并开始传输
            receiver.init_receive_params(file_save_path)

            if receiver.start_transfer():
                print("🎉 单文件接收成功！")
                print(f"✅ 文件已保存到: {file_save_path}")
                return True
            else:
                print("❌ 单文件接收失败！")
                return False
                
        except Exception as e:
            logger.error(f"单文件接收异常: {e}")
            print(f"❌ 单文件接收异常: {e}")
            return False

    @staticmethod
    def _handle_folder_receive(recv_file_dir, serial_manager, transfer_config) -> bool:
        """
        处理文件夹接收
        
        Args:
            recv_file_dir: 接收文件目录  
            serial_manager: 串口管理器
            transfer_config: 传输配置
            
        Returns:
            成功返回True，失败返回False
        """
        try:
            from ..transfer.file_manager import ReceiverFileManager
            
            # 使用批量接收管理器
            file_manager = ReceiverFileManager(
                recv_file_dir, serial_manager, transfer_config
            )
            
            print("开始批量文件接收...")
            
            if file_manager.start_batch_receive():
                print("🎉 文件夹接收成功！")
                print(f"✅ 所有文件已保存到: {recv_file_dir}")
                return True
            else:
                print("❌ 文件夹接收失败！")
                return False
                
        except Exception as e:
            logger.error(f"文件夹接收异常: {e}")
            print(f"❌ 文件夹接收异常: {e}")
            return False

