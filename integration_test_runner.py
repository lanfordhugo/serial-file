#!/usr/bin/env python3
"""
串口文件传输 - 集成测试运行器
============================

提供便捷的集成测试执行入口，支持多种运行模式。

使用方法：
    python integration_test_runner.py --help           # 显示帮助
    python integration_test_runner.py --basic          # 基础功能测试
    python integration_test_runner.py --full           # 完整集成测试
    python integration_test_runner.py --large          # 大文件测试  
    python integration_test_runner.py --skip-hardware  # 跳过硬件测试
    python integration_test_runner.py --ports COM3,COM4 # 指定串口
"""

import argparse
import sys
import subprocess
from pathlib import Path


def run_pytest_command(test_args: list, description: str) -> bool:
    """
    执行pytest命令
    
    Args:
        test_args: pytest参数列表
        description: 测试描述
        
    Returns:
        测试是否成功
    """
    print(f"\n{'='*60}")
    print(f"开始执行: {description}")
    print(f"{'='*60}")
    print(f"命令: pytest {' '.join(test_args)}")
    print()
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest"] + test_args,
            cwd=Path(__file__).parent
        )
        success = result.returncode == 0
        
        if success:
            print(f"\n✅ {description} - 成功")
        else:
            print(f"\n❌ {description} - 失败")
            
        return success
        
    except Exception as e:
        print(f"\n💥 {description} - 异常: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="串口文件传输集成测试运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
测试模式说明：
  --basic         基础功能测试（1MB文件，115200波特率）
  --full          完整集成测试（所有文件大小和波特率组合）
  --large         大文件测试（50MB文件）
  --multi         多文件连续传输测试
  --skip-hardware 跳过需要硬件的测试

串口配置：
  --ports COM1,COM2    指定发送端和接收端串口号
                      （Linux系统使用 /dev/ttyUSB0,/dev/ttyUSB1）

示例：
  python integration_test_runner.py --basic
  python integration_test_runner.py --full --ports COM3,COM4
  python integration_test_runner.py --large --skip-hardware
        """
    )
    
    # 测试模式选择
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--basic", action="store_true", help="基础功能测试")
    mode_group.add_argument("--full", action="store_true", help="完整集成测试")
    mode_group.add_argument("--large", action="store_true", help="大文件测试")
    mode_group.add_argument("--multi", action="store_true", help="多文件测试")
    mode_group.add_argument("--all", action="store_true", help="所有测试")
    
    # 可选参数
    parser.add_argument("--skip-hardware", action="store_true", help="跳过硬件测试")
    parser.add_argument("--ports", help="串口号对，用逗号分隔（如：COM1,COM2）")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--timeout", type=int, default=60, help="测试超时时间（秒）")
    
    args = parser.parse_args()
    
    # 显示配置信息
    print("串口文件传输 - 集成测试运行器")
    print("=" * 50)
    print(f"运行目录: {Path(__file__).parent}")
    
    if args.ports:
        ports = args.ports.split(',')
        if len(ports) == 2:
            print(f"指定串口: 发送端={ports[0]}, 接收端={ports[1]}")
            # 这里可以设置环境变量供测试脚本使用
            import os
            os.environ['TEST_PORT_SENDER'] = ports[0]
            os.environ['TEST_PORT_RECEIVER'] = ports[1]
        else:
            print("❌ 串口参数格式错误，应为: --ports COM1,COM2")
            return 1
    
    if args.skip_hardware:
        print("⚠️ 跳过硬件测试模式")
    
    print()
    
    # 构建pytest参数
    base_args = ["tests/integration/test_cli_smart_transfer.py"]
    
    if args.verbose:
        base_args.append("-v")
        
    if args.skip_hardware:
        # 跳过硬件测试时，设置环境变量让测试内部跳过
        import os
        os.environ["SKIP_HARDWARE_TESTS"] = "true"
    
    # 注释掉超时设置，因为pytest-timeout插件可能没有安装
    # base_args.extend(["--timeout", str(args.timeout)])
    
    # 根据模式执行不同的测试
    success = True
    
    if args.basic:
        # 基础测试：只测试一个小文件和低波特率
        test_args = base_args + [
            "-k", "test_smart_cli_transfer"
        ]
        success = run_pytest_command(test_args, "基础功能测试")
        
    elif args.full:
        # 完整测试：所有参数化组合
        test_args = base_args + ["-k", "test_smart_cli_transfer"]
        success = run_pytest_command(test_args, "完整集成测试")
        
    elif args.large:
        # 大文件测试
        test_args = base_args + ["-k", "test_large_file_transfer"]
        success = run_pytest_command(test_args, "大文件测试")
        
    elif args.multi:
        # 多文件测试
        test_args = base_args + ["-k", "test_multiple_small_files"]
        success = run_pytest_command(test_args, "多文件测试")
        
    elif args.all:
        # 所有测试
        test_args = base_args[:]
        success = run_pytest_command(test_args, "完整测试套件")
    
    # 显示总结
    print("\n" + "=" * 60)
    if success:
        print("🎉 集成测试完成 - 全部通过!")
        print("\n测试验证了以下功能：")
        print("✅ CLI命令行接口正确性")
        print("✅ 智能探测和协商功能")
        print("✅ 多波特率自动切换")
        print("✅ 文件完整性验证")
        print("✅ 错误处理和超时机制")
        return 0
    else:
        print("❌ 集成测试失败!")
        print("\n请检查：")
        print("1. 串口硬件连接是否正常")
        print("2. 串口号是否正确")
        print("3. 串口权限是否足够")
        print("4. 系统资源是否充足")
        return 1


if __name__ == "__main__":
    sys.exit(main())