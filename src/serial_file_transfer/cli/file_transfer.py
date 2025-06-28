"""
统一文件传输命令行接口
====================

提供统一的文件/文件夹发送和接收命令行接口，自动根据路径类型选择处理方式。
"""

from pathlib import Path
from typing import Optional

from ..config.settings import SerialConfig, TransferConfig
from ..config.constants import PROBE_BAUDRATE, ProbeCommand
from ..core.serial_manager import SerialManager
from ..core.probe_manager import ProbeManager
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
    def get_user_input_port() -> Optional[str]:
        """获取用户选择的串口号"""
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
                    selected_port = ports[index]['device']
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
            if port is None:
                return False
                
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
    def smart_send() -> bool:
        """智能发送模式 - 自动探测和协商"""
        try:
            print("=== 串口文件传输 - 智能发送 ===")
            
            # 获取用户输入
            port = FileTransferCLI.get_user_input_port()
            if port is None:
                return False
                
            source_path = FileTransferCLI.get_user_input_source_path()
            
            # 检测路径类型和统计信息
            path_type = FileTransferCLI._detect_path_type(source_path)
            
            # 统计文件信息
            if path_type == 'file':
                file_count = 1
                total_size = Path(source_path).stat().st_size
                print(f"准备发送文件: {source_path} ({total_size} 字节)")
            else:
                # 简单统计文件夹信息
                path_obj = Path(source_path)
                files = list(path_obj.rglob('*'))
                file_count = len([f for f in files if f.is_file()])
                total_size = sum(f.stat().st_size for f in files if f.is_file())
                print(f"准备发送文件夹: {source_path} ({file_count}个文件, {total_size} 字节)")
            
            # 创建探测阶段的串口配置（固定115200）
            probe_config = SerialConfig(port=port, baudrate=PROBE_BAUDRATE, timeout=0.5)
            
            with SerialManager(probe_config) as probe_serial:
                # 创建探测管理器
                probe_manager = ProbeManager(probe_serial)
                
                print("正在搜索接收设备...")
                
                # 发送探测请求
                response = probe_manager.send_probe_request()
                if response is None:
                    print("❌ 未找到接收设备，请检查:")
                    print("  1. 接收端是否已启动智能接收模式")
                    print("  2. 串口连接是否正常")
                    print("  3. 波特率是否匹配(115200)")
                    return False
                
                print(f"✅ 找到接收设备，支持波特率: {response.supported_baudrates}")
                
                # 进行能力协商
                selected_baudrate = probe_manager.negotiate_capability(
                    file_count=file_count,
                    total_size=total_size,
                    supported_baudrates=response.supported_baudrates
                )
                
                if selected_baudrate is None:
                    print("❌ 能力协商失败")
                    return False
                
                print(f"✅ 协商成功，使用波特率: {selected_baudrate}")
                
                # 执行波特率切换
                if not probe_manager.switch_baudrate():
                    print("❌ 波特率切换失败")
                    return False
                
                print(f"✅ 已切换到波特率: {selected_baudrate}")
                
            # 使用协商好的波特率进行文件传输
            transfer_config = TransferConfig(max_data_length=10*1024)
            final_config = SerialConfig(port=port, baudrate=selected_baudrate, timeout=0.5)
            
            with SerialManager(final_config) as transfer_serial:
                if path_type == 'file':
                    # 单文件发送
                    print("开始传输文件...")
                    sender = FileSender(transfer_serial, source_path, transfer_config)
                    
                    if sender.start_transfer():
                        print("🎉 文件发送成功！")
                        return True
                    else:
                        print("❌ 文件发送失败！")
                        return False
                        
                elif path_type == 'folder':
                    # 文件夹发送
                    print("开始批量传输文件...")
                    file_manager = SenderFileManager(source_path, transfer_serial, transfer_config)
                    
                    if file_manager.start_batch_send():
                        print("🎉 批量文件发送成功！")
                        return True
                    else:
                        print("❌ 批量文件发送失败！")
                        return False
                        
        except KeyboardInterrupt:
            print("\n用户取消操作")
            return False
        except Exception as e:
            logger.error(f"智能发送时发生异常: {e}")
            print(f"❌ 发送失败: {e}")
            return False
        finally:
            input('按回车键退出...')
    
    @staticmethod
    def smart_receive() -> bool:
        """智能接收模式 - 自动监听和响应"""
        try:
            print("=== 串口文件传输 - 智能接收 ===")
            
            # 获取用户输入
            port = FileTransferCLI.get_user_input_port()
            if port is None:
                return False
                
            save_path = FileTransferCLI.get_user_input_save_path()
            
            print("正在等待发送端连接...")
            print("提示: 请在发送端启动智能发送模式")
            
            # 创建探测阶段的串口配置（固定115200）
            probe_config = SerialConfig(port=port, baudrate=PROBE_BAUDRATE, timeout=0.1)
            
            with SerialManager(probe_config) as probe_serial:
                # 创建探测管理器
                probe_manager = ProbeManager(probe_serial)
                
                # 等待探测请求
                request = probe_manager.wait_for_probe_request(timeout=30.0)  # 30秒超时
                if request is None:
                    print("❌ 等待连接超时，请检查:")
                    print("  1. 发送端是否已启动智能发送模式")
                    print("  2. 串口连接是否正常")
                    return False
                
                print(f"✅ 收到连接请求，设备ID: {hex(request.device_id)}")
                
                # 发送探测响应
                if not probe_manager.send_probe_response(request):
                    print("❌ 发送响应失败")
                    return False
                
                print("✅ 已发送设备响应")
                
                # 等待和处理能力协商
                print("等待能力协商...")
                capability_data = probe_manager._receive_probe_frame(
                    ProbeCommand.CAPABILITY_NEGO, 10.0
                )
                
                if capability_data is None:
                    print("❌ 未收到能力协商")
                    return False
                
                if not probe_manager.handle_capability_nego(capability_data):
                    print("❌ 能力协商失败")
                    return False
                
                print(f"✅ 能力协商成功，波特率: {probe_manager.target_baudrate}")
                
                # 等待和处理波特率切换
                print("等待波特率切换...")
                switch_data = probe_manager._receive_probe_frame(
                    ProbeCommand.SWITCH_BAUDRATE, 5.0
                )
                
                if switch_data is None:
                    print("❌ 未收到切换指令")
                    return False
                
                if not probe_manager.handle_baudrate_switch(switch_data):
                    print("❌ 波特率切换失败")
                    return False
                
                print(f"✅ 已切换到波特率: {probe_manager.target_baudrate}")
                
            # 使用协商好的波特率进行文件传输
            transfer_config = TransferConfig(max_data_length=10*1024)
            
            # 确保target_baudrate不为None
            final_baudrate = probe_manager.target_baudrate
            if final_baudrate is None:
                print("❌ 波特率信息丢失")
                return False
                
            final_config = SerialConfig(
                port=port, 
                baudrate=final_baudrate, 
                timeout=0.05
            )
            
            with SerialManager(final_config) as transfer_serial:
                print("开始接收文件...")
                
                # 尝试单文件接收，如果失败再尝试批量接收
                # 这里可以根据协商时的传输模式来决定
                receiver = FileReceiver(transfer_serial, save_path, transfer_config)
                
                if receiver.start_transfer():
                    print("🎉 文件接收成功！")
                    return True
                else:
                    # 尝试批量接收
                    print("尝试批量接收模式...")
                    file_manager = ReceiverFileManager(save_path, transfer_serial, transfer_config)
                    
                    if file_manager.start_batch_receive():
                        print("🎉 批量文件接收成功！")
                        return True
                    else:
                        print("❌ 文件接收失败！")
                        return False
                        
        except KeyboardInterrupt:
            print("\n用户取消操作")
            return False
        except Exception as e:
            logger.error(f"智能接收时发生异常: {e}")
            print(f"❌ 接收失败: {e}")
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
            if port is None:
                return False
                
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