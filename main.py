#!/usr/bin/env python3
"""
串口文件传输工具 - 主程序入口
============================

这是一个基于串口通信的文件传输工具的主入口程序。
支持单个文件和批量文件的可靠传输。

使用方法：
    python main.py              # 交互式菜单
    python main.py --send       # 直接进入发送模式
    python main.py --receive    # 直接进入接收模式
    python main.py --help       # 显示帮助信息
"""

import sys
import argparse
from pathlib import Path

# 添加src路径到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

# 导入资源路径处理器并初始化打包环境
from serial_file_transfer.utils.resource_path import setup_packaged_environment
setup_packaged_environment()

from serial_file_transfer.cli.file_transfer import FileTransferCLI
from serial_file_transfer.utils.logger import get_console_logger, setup_logger
import logging

# 临时启用DEBUG日志来分析问题
logger = setup_logger(__name__, level=logging.DEBUG, file_output=False)

# 版本信息
VERSION = "1.4.0"
PROGRAM_NAME = "串口文件传输工具"


class SerialFileTransferApp:
    """串口文件传输工具主应用类"""

    def __init__(self):
        """初始化应用"""
        self.running = True

    def show_banner(self):
        """显示程序横幅"""
        print("=" * 50)
        print(f"{PROGRAM_NAME} v{VERSION}")
        print("=" * 50)
        print("基于串口通信的可靠文件传输工具")
        print("支持智能路径检测，自动选择传输方式")
        print("=" * 50)
        print()

    def show_menu(self):
        """显示主菜单"""
        print("请选择操作：")
        print("1. 🚀 智能发送文件/文件夹")
        print("2. 📡 智能接收文件")
        print("3. ⚙️  设置波特率")
        print("4. 查看帮助")
        print("5. 退出程序")
        print()

    def show_help(self):
        """显示帮助信息"""
        print("\n" + "=" * 50)
        print("帮助信息")
        print("=" * 50)
        print()
        print("📡 文件传输模式：")
        print("   - 使用配置文件管理传输参数")
        print("   - 自动检测文件/文件夹类型")
        print("   - 固定波特率，稳定可靠")
        print("   - 一键完成传输过程")
        print()
        print("📁 文件发送：")
        print("   - 输入文件路径：自动单文件传输")
        print("   - 输入文件夹路径：自动批量传输")
        print("   - 使用配置文件的传输参数")
        print()
        print("📥 文件接收：")
        print("   - 自动监听发送端连接")
        print("   - 使用配置文件的传输参数")
        print("   - 自动处理文件传输")
        print()
        print("🔧 使用步骤：")
        print("   1. 连接两台设备的串口")
        print("   2. 先启动接收端程序（文件接收）")
        print("   3. 再启动发送端程序（文件发送）")
        print("   4. 系统自动完成文件传输")
        print()
        print("⚙️  配置文件：config/transfer.yaml")
        print("📋 传输协议：自定义帧格式，带校验和验证")
        print("🔍 支持波特率：115200 到 1728000（可配置）")
        print()
        print("=" * 50)
        input("按回车键返回主菜单...")
        print()

    def get_user_choice(self) -> str:
        """获取用户选择"""
        while True:
            try:
                choice = input("请输入选择 (1-5): ").strip()
                if choice in ["1", "2", "3", "4", "5"]:
                    return choice
                else:
                    print("❌ 无效选择，请输入 1-5 之间的数字")
            except KeyboardInterrupt:
                print("\n\n👋 用户取消操作，程序退出")
                return "5"
            except EOFError:
                return "5"

    def handle_smart_send(self):
        """处理智能发送操作"""
        try:
            print("\n" + "=" * 30)
            print("🚀 智能发送文件/文件夹")
            print("=" * 30)
            success = FileTransferCLI.smart_send()
            if success:
                print("\n✅ 智能发送操作完成！")
            else:
                print("\n❌ 智能发送操作失败！")
        except Exception as e:
            logger.error(f"智能发送操作异常: {e}")
            print(f"\n💥 智能发送操作异常: {e}")
        finally:
            print()

    def handle_smart_receive(self):
        """处理智能接收操作"""
        try:
            print("\n" + "=" * 30)
            print("📡 智能接收文件")
            print("=" * 30)
            success = FileTransferCLI.smart_receive()
            if success:
                print("\n✅ 智能接收操作完成！")
            else:
                print("\n❌ 智能接收操作失败！")
        except Exception as e:
            logger.error(f"智能接收操作异常: {e}")
            print(f"\n💥 智能接收操作异常: {e}")
        finally:
            print()

    def handle_baudrate_setting(self):
        """处理波特率设置"""
        print("\n" + "=" * 50)
        print("⚙️  波特率设置")
        print("=" * 50)
        print()
        print("请选择波特率（推荐从低到高测试稳定性）：")
        print()
        print("1. 460800  (推荐 ⭐⭐⭐⭐⭐) - 稳定可靠，适合长距离传输")
        print("2. 921600  (推荐 ⭐⭐⭐)     - 速度较快，可能在部分硬件上不稳定")
        print("3. 1728000 (推荐 ⭐⭐)       - 高速传输，需要优质硬件支持")
        print()
        print("💡 提示：")
        print("   - 如遇传输失败，建议降低波特率")
        print("   - 默认推荐使用 460800（选项1）")
        print("   - 921600 及以上需要硬件流控支持（如不支持易失败）")
        print()
        
        baudrate_map = {
            "1": 460800,
            "2": 921600,
            "3": 1728000
        }
        
        while True:
            try:
                choice = input("请选择波特率 (1-3, 默认1): ").strip()
                if not choice:
                    choice = "1"  # 默认选项
                
                if choice in baudrate_map:
                    baudrate = baudrate_map[choice]
                    print(f"\n✅ 已选择波特率: {baudrate} bps")
                    
                    # 更新配置文件
                    import yaml
                    config_file = Path("config/transfer.yaml")
                    
                    try:
                        with open(config_file, "r", encoding="utf-8") as f:
                            config = yaml.safe_load(f)
                        
                        # 更新波特率
                        if "serial" not in config:
                            config["serial"] = {}
                        config["serial"]["baudrate"] = baudrate
                        
                        # 写回配置文件
                        with open(config_file, "w", encoding="utf-8") as f:
                            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
                        
                        print(f"✅ 配置已更新: config/transfer.yaml")
                        print(f"   波特率设置为: {baudrate} bps")
                        
                        # 根据波特率给出块长建议
                        if baudrate == 460800:
                            recommended_block = 2048
                            print(f"\n💡 建议块长: {recommended_block} 字节（已自动设置）")
                            if "transfer" not in config:
                                config["transfer"] = {}
                            config["transfer"]["max_data_length"] = recommended_block
                        elif baudrate == 921600:
                            recommended_block = 512
                            print(f"\n💡 建议块长: {recommended_block} 字节（已自动设置）")
                            print("   ⚠️  此波特率可能不稳定，如遇失败请降至 460800")
                            if "transfer" not in config:
                                config["transfer"] = {}
                            config["transfer"]["max_data_length"] = recommended_block
                        else:  # 1728000
                            recommended_block = 8192
                            print(f"\n💡 建议块长: {recommended_block} 字节（已自动设置）")
                            print("   ⚠️  高速传输需要优质硬件，如遇失败请降至 460800")
                            if "transfer" not in config:
                                config["transfer"] = {}
                            config["transfer"]["max_data_length"] = recommended_block
                        
                        # 再次写回配置文件（包含块长更新）
                        with open(config_file, "w", encoding="utf-8") as f:
                            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
                        
                    except Exception as e:
                        logger.error(f"更新配置文件失败: {e}")
                        print(f"\n❌ 更新配置文件失败: {e}")
                        print("   请手动编辑 config/transfer.yaml")
                    
                    print()
                    input("按回车键返回主菜单...")
                    print()
                    break
                else:
                    print("❌ 无效选择，请输入 1-3")
                    
            except KeyboardInterrupt:
                print("\n\n👋 取消设置，返回主菜单")
                print()
                break
            except EOFError:
                break



    def run_interactive(self):
        """运行交互式界面"""
        self.show_banner()

        while self.running:
            self.show_menu()
            choice = self.get_user_choice()

            if choice == "1":
                self.handle_smart_send()
            elif choice == "2":
                self.handle_smart_receive()
            elif choice == "3":
                self.handle_baudrate_setting()
            elif choice == "4":
                self.show_help()
            elif choice == "5":
                print("\n👋 感谢使用，程序退出！")
                self.running = False

        print()




def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description=f"{PROGRAM_NAME} v{VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  python main.py              # 启动交互式界面（智能模式）

更多信息请访问项目文档。
        """,
    )

    parser.add_argument(
        "--version", action="version", version=f"{PROGRAM_NAME} v{VERSION}"
    )

    return parser


def main():
    """主函数"""
    try:
        # 解析命令行参数（保留版本信息支持）
        parser = create_parser()
        parser.parse_args()

        # 创建应用实例并运行交互式界面
        app = SerialFileTransferApp()
        app.run_interactive()

    except KeyboardInterrupt:
        print("\n\n👋 用户中断程序，退出")
    except Exception as e:
        logger.error(f"程序异常: {e}")
        print(f"\n💥 程序异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
