"""
统一文件传输命令行接口
====================

提供统一的文件/文件夹发送和接收命令行接口，自动根据路径类型选择处理方式。
"""

from pathlib import Path
from typing import Optional
import time

from ..config.settings import SerialConfig, TransferConfig
from ..config.constants import PROBE_BAUDRATE, ProbeCommand
from ..core.serial_manager import SerialManager
from ..core.probe_manager import ProbeManager
from ..transfer.sender import FileSender
from ..transfer.receiver import FileReceiver
from ..transfer.file_manager import SenderFileManager, ReceiverFileManager
from ..utils.logger import get_logger
from ..utils.path_utils import get_relative_path_info

logger = get_logger(__name__)


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
        """获取波特率（智能模式下用于探测阶段）"""
        # 如果有临时参数，使用临时参数（非交互模式）
        if FileTransferCLI._temp_baudrate:
            print(f"✅ 使用指定波特率: {FileTransferCLI._temp_baudrate}")
            return FileTransferCLI._temp_baudrate

        # 智能模式下使用固定的探测波特率
        from ..config.constants import PROBE_BAUDRATE
        default_baudrate = PROBE_BAUDRATE  # 115200

        print(f"✅ 智能模式使用探测波特率: {default_baudrate}")
        print("   （实际传输波特率将通过协商确定）")
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

            # 创建探测阶段的串口配置（固定115200）
            probe_config = SerialConfig(port=port, baudrate=PROBE_BAUDRATE, timeout=0.5)

            with SerialManager(probe_config) as probe_serial:
                # 创建探测管理器
                probe_manager = ProbeManager(probe_serial)

                print("正在搜索接收设备(3s 周期探测，3 分钟超时)...")

                # 按 3 秒周期重复探测，最长 3 分钟
                PROBE_CYCLE = 3.0  # 单次探测周期 (秒)
                PROBE_TOTAL_TIMEOUT = 180.0  # 总超时 (秒)

                start_time = time.time()
                attempt = 0
                response = None

                max_attempts = int(PROBE_TOTAL_TIMEOUT // PROBE_CYCLE)

                while attempt < max_attempts:
                    attempt += 1
                    response = probe_manager.send_probe_request()
                    if response is not None:
                        break  # 找到设备

                    elapsed = time.time() - start_time
                    remaining = int(PROBE_TOTAL_TIMEOUT - elapsed)
                    if remaining <= 0:
                        break

                    print(f"⌛ 第 {attempt} 次探测未找到设备，剩余 {remaining}s，继续尝试...")
                    # send_probe_request 内部已阻塞约 3s，这里不再额外 sleep，以免单元测试耗时

                if response is None:
                    print("❌ 未找到接收设备，请检查:")
                    print("  1. 接收端是否已启动智能接收模式")
                    print("  2. 串口连接是否正常")
                    print("  3. 波特率是否匹配(115200)")
                    return False

                print(f"✅ 找到接收设备，支持波特率: {response.supported_baudrates}")

                # 能力协商，传递根路径信息
                root_path_name, is_folder = get_relative_path_info(Path(source_path))
                selected_baudrate = probe_manager.negotiate_capability(
                    file_count=file_count,
                    total_size=total_size,
                    supported_baudrates=response.supported_baudrates,
                    root_path=root_path_name,
                )

                if selected_baudrate is None:
                    print("❌ 能力协商失败")
                    return False

                negotiated_chunk = (
                    getattr(probe_manager, "negotiated_chunk_size", None) or 10 * 1024
                )

                # 执行波特率切换
                if not probe_manager.switch_baudrate():
                    print("❌ 波特率切换失败")
                    return False

                print(f"✅ 已切换到波特率: {selected_baudrate}")

            # 使用协商好的波特率进行文件传输
            transfer_config = TransferConfig(max_data_length=negotiated_chunk)
            final_config = SerialConfig(
                port=port, baudrate=selected_baudrate, timeout=0.5
            )

            with SerialManager(final_config) as transfer_serial:
                if path_type == "file":
                    # 单文件发送
                    print("开始传输文件...")
                    sender = FileSender(transfer_serial, source_path, transfer_config)

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

        except KeyboardInterrupt:
            print("\n用户取消操作")
            return False
        except Exception as e:
            logger.error(f"智能发送时发生异常: {e}")
            print(f"❌ 发送失败: {e}")
            return False
        finally:
            # 避免在测试环境中阻塞，检查是否在测试环境中运行
            import sys

            if "pytest" not in sys.modules:
                input("按回车键退出...")

    @staticmethod
    def smart_receive() -> bool:
        """智能接收模式 - 自动监听和响应"""
        try:
            print("=== 串口文件传输 - 智能接收 ===")

            # 获取用户输入
            port = FileTransferCLI.get_user_input_port()
            if port is None:
                return False

            # 自动使用当前目录作为接收根目录
            import os
            save_path = os.getcwd()
            print(f"✅ 自动接收目录: {save_path}")

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
            negotiated_chunk = (
                getattr(probe_manager, "negotiated_chunk_size", None) or 10 * 1024
            )
            transfer_config = TransferConfig(max_data_length=negotiated_chunk)

            final_baudrate = probe_manager.target_baudrate
            if final_baudrate is None:
                print("❌ 波特率信息丢失")
                return False

            final_config = SerialConfig(port=port, baudrate=final_baudrate, timeout=0.5)

            with SerialManager(final_config) as transfer_serial:
                print("开始接收文件...")

                # 获取协商信息
                negotiated_root_path = getattr(probe_manager, "negotiated_root_path", "")
                negotiated_transfer_mode = getattr(probe_manager, "negotiated_transfer_mode", 1)
                negotiated_file_count = getattr(probe_manager, "negotiated_file_count", 1)

                print(f"📋 传输信息: 模式={negotiated_transfer_mode}, 文件数={negotiated_file_count}")

                # 根据协商的根路径信息自动创建接收目录
                if negotiated_root_path:
                    # 如果有根路径信息，在接收目录下创建对应的子目录
                    final_save_path = Path(save_path) / negotiated_root_path
                    final_save_path.mkdir(parents=True, exist_ok=True)
                    print(f"✅ 自动创建接收目录: {final_save_path}")
                else:
                    final_save_path = Path(save_path)

                # 根据协商的传输模式智能选择接收方式
                if negotiated_transfer_mode == 1:  # 单文件模式
                    print("📄 单文件接收模式")

                    # 对于单文件，生成默认的文件路径
                    # 单文件传输协议中，文件名会在传输过程中自动处理
                    import time
                    timestamp = int(time.time())
                    default_filename = f"received_file_{timestamp}"
                    file_save_path = final_save_path / default_filename

                    # 确保父目录存在
                    file_save_path.parent.mkdir(parents=True, exist_ok=True)
                    print(f"📄 准备接收到: {file_save_path}")

                    # 初始化接收器并开始传输
                    receiver = FileReceiver(transfer_serial, str(file_save_path), transfer_config)

                    if receiver.start_transfer():
                        print("🎉 单文件接收成功！")
                        return True
                    else:
                        print("❌ 单文件接收失败！")
                        return False

                else:  # 批量文件模式 (transfer_mode == 2)
                    print("📁 批量文件接收模式")
                    file_manager = ReceiverFileManager(
                        str(final_save_path), transfer_serial, transfer_config
                    )

                    if file_manager.start_batch_receive():
                        print("🎉 批量文件接收成功！")
                        return True
                    else:
                        print("❌ 批量文件接收失败！")
                        return False

        except KeyboardInterrupt:
            print("\n用户取消操作")
            return False
        except Exception as e:
            logger.error(f"智能接收时发生异常: {e}")
            print(f"❌ 接收失败: {e}")
            return False
        finally:
            # 避免在测试环境中阻塞，检查是否在测试环境中运行
            import sys

            if "pytest" not in sys.modules:
                input("按回车键退出...")

