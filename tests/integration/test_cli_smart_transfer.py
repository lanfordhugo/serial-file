#!/usr/bin/env python3
"""
CLI级智能收发集成测试
====================

运行方式：
1) pytest -v tests/integration/test_cli_smart_transfer.py
2) python tests/integration/test_cli_smart_transfer.py  # 单脚本运行

功能特性：
- 100% CLI路径测试，不直接import业务代码
- 进程独立：发送端和接收端运行在不同进程
- 多文件大小测试：1MB、10MB等
- 多波特率测试：115200/460800/921600/1728000
- 超时保护：防死锁
- 失败自动打印日志，方便排查
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import List

import pytest

# ---------- 测试矩阵 ----------
BAUDRATES: List[int] = [115200, 460800, 921600, 1728000]
FILE_SIZES_MB: List[int] = [1, 10]              # 1 MB、10 MB
PORT_SENDER = "COM1"
PORT_RECEIVER = "COM2"

# 根据操作系统调整串口号
if os.name != 'nt':  # 非Windows系统
    PORT_SENDER = "/dev/ttyUSB0"
    PORT_RECEIVER = "/dev/ttyUSB1"

# CLI入口命令
CLI_ENTRY = [sys.executable, "-m", "serial_file_transfer"]

# ---------- 配置常量 ----------
TRANSFER_TIMEOUT = 600  # 传输超时 (秒)
RECEIVER_EXTRA_TIMEOUT = 30  # 接收端额外等待时间 (秒)


# ---------- 工具函数 ----------
def _generate_test_file(size_mb: int, dst: Path) -> Path:
    """
    生成指定大小的随机文件
    
    Args:
        size_mb: 文件大小（MB）
        dst: 目标文件路径
        
    Returns:
        生成的文件路径
    """
    print(f"生成测试文件: {dst} ({size_mb}MB)")
    data = os.urandom(size_mb * 1024 * 1024)
    dst.write_bytes(data)
    print(f"✅ 测试文件生成完成: {dst.stat().st_size} 字节")
    return dst


def _run_transfer(src_file: Path, baudrate: int, tmp_dir: Path) -> bool:
    """
    启动接收端→发送端→验证结果
    
    Args:
        src_file: 源文件路径
        baudrate: 传输波特率
        tmp_dir: 临时目录
        
    Returns:
        传输是否成功
    """
    recv_dir = tmp_dir / "received"
    recv_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== 开始传输测试 ===")
    print(f"源文件: {src_file}")
    print(f"文件大小: {src_file.stat().st_size} 字节")
    print(f"波特率: {baudrate}")
    print(f"发送端口: {PORT_SENDER}")
    print(f"接收端口: {PORT_RECEIVER}")
    print(f"接收目录: {recv_dir}")

    # 1) 拼接命令
    recv_cmd = CLI_ENTRY + [
        "receive", "--smart",
        "--port", PORT_RECEIVER,
        "--save", str(recv_dir),
        "--baudrate", str(baudrate)
    ]
    
    send_cmd = CLI_ENTRY + [
        "send", "--smart",
        "--port", PORT_SENDER,
        "--path", str(src_file),
        "--baudrate", str(baudrate)
    ]

    print(f"接收端命令: {' '.join(recv_cmd)}")
    print(f"发送端命令: {' '.join(send_cmd)}")

    # 2) 先启动接收端
    print("\n⚡ 启动接收端...")
    recv_proc = subprocess.Popen(
        recv_cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT, 
        text=True,
        cwd=Path(__file__).parent.parent.parent  # 项目根目录
    )
    
    # 给接收端准备时间
    time.sleep(1.0)
    print("✅ 接收端已启动，等待连接...")

    # 3) 启动发送端并等待其结束
    print("\n⚡ 启动发送端...")
    send_result = subprocess.run(
        send_cmd, 
        capture_output=True, 
        text=True, 
        timeout=TRANSFER_TIMEOUT,
        cwd=Path(__file__).parent.parent.parent  # 项目根目录
    )
    print(f"✅ 发送端完成，退出码: {send_result.returncode}")

    # 4) 等待接收端退出（最长比发送端多30s）
    print("\n⏳ 等待接收端完成...")
    try:
        recv_stdout, _ = recv_proc.communicate(timeout=RECEIVER_EXTRA_TIMEOUT)
        print(f"✅ 接收端完成，退出码: {recv_proc.returncode}")
    except subprocess.TimeoutExpired:
        print("⚠️ 接收端超时，强制终止")
        recv_proc.kill()
        recv_stdout, _ = recv_proc.communicate()

    # 5) 收集和显示日志
    print(f"\n=== 日志输出 ===")
    
    if send_result.returncode != 0:
        print("❌ 发送端失败")
        print("=== 发送端STDOUT ===")
        print(send_result.stdout)
        print("=== 发送端STDERR ===")
        print(send_result.stderr)
    else:
        print("✅ 发送端成功")
        
    if recv_proc.returncode != 0:
        print("❌ 接收端失败")
        print("=== 接收端输出 ===")
        print(recv_stdout)
    else:
        print("✅ 接收端成功")

    # 6) 结果判断
    if send_result.returncode != 0 or recv_proc.returncode != 0:
        print("❌ 传输过程失败")
        return False

    # 7) 验证接收文件
    dst_file = recv_dir / src_file.name
    if not dst_file.exists():
        print(f"❌ 接收文件不存在: {dst_file}")
        return False

    # 8) 内容比对
    src_data = src_file.read_bytes()
    dst_data = dst_file.read_bytes()
    
    if src_data == dst_data:
        print(f"✅ 文件内容验证通过: {len(src_data)} 字节")
        return True
    else:
        print(f"❌ 文件内容不匹配: 源文件{len(src_data)}字节 vs 接收文件{len(dst_data)}字节")
        return False


def _check_hardware_available() -> bool:
    """
    检查硬件是否可用（简单端口存在性检查）
    
    Returns:
        硬件是否可用
    """
    import os
    
    # 检查是否有跳过硬件的环境变量或命令行参数
    if "--skip-hardware" in sys.argv:
        return False
        
    # 检查环境变量
    if os.environ.get("SKIP_HARDWARE_TESTS", "").lower() in ("true", "1", "yes"):
        return False
    
    # 这里可以添加串口存在性检查
    # 目前暂时返回True，依赖实际测试时的错误处理
    return True


# ---------- pytest参数化测试 ----------
@pytest.mark.integration
@pytest.mark.hardware
@pytest.mark.parametrize("baudrate", BAUDRATES)
@pytest.mark.parametrize("size_mb", FILE_SIZES_MB)
def test_smart_cli_transfer(tmp_path: Path, baudrate: int, size_mb: int):
    """
    智能模式CLI传输集成测试
    
    测试不同波特率和文件大小的组合，验证：
    1. 智能探测和协商功能
    2. 波特率自动切换
    3. 文件完整性验证
    4. 错误处理机制
    
    Args:
        tmp_path: pytest提供的临时目录
        baudrate: 传输波特率
        size_mb: 文件大小（MB）
    """
    # 跳过硬件不可用的情况
    if not _check_hardware_available():
        pytest.skip("串口硬件不可用")

    print(f"\n{'='*60}")
    print(f"测试参数: {size_mb}MB文件, {baudrate}bps波特率")
    print(f"{'='*60}")

    # 生成测试文件
    src_file = _generate_test_file(size_mb, tmp_path / f"test_{size_mb}mb_{baudrate}.bin")
    
    # 执行传输测试
    result = _run_transfer(src_file, baudrate, tmp_path)
    
    # pytest断言
    assert result, f"传输失败: {size_mb}MB文件, {baudrate}bps波特率"
    
    print(f"🎉 测试通过: {size_mb}MB文件, {baudrate}bps波特率")


@pytest.mark.integration
@pytest.mark.hardware
def test_large_file_transfer(tmp_path: Path):
    """
    大文件传输专项测试（50MB）
    
    测试大文件传输的稳定性和性能
    """
    if not _check_hardware_available():
        pytest.skip("串口硬件不可用")

    size_mb = 50
    baudrate = 1728000  # 使用最高波特率
    
    print(f"\n{'='*60}")
    print(f"大文件测试: {size_mb}MB, {baudrate}bps")
    print(f"{'='*60}")

    src_file = _generate_test_file(size_mb, tmp_path / f"large_test_{size_mb}mb.bin")
    result = _run_transfer(src_file, baudrate, tmp_path)
    
    assert result, f"大文件传输失败: {size_mb}MB"
    print(f"🎉 大文件测试通过: {size_mb}MB")


@pytest.mark.integration  
@pytest.mark.hardware
def test_multiple_small_files(tmp_path: Path):
    """
    多个小文件连续传输测试
    
    测试多次传输的稳定性
    """
    if not _check_hardware_available():
        pytest.skip("串口硬件不可用")

    baudrate = 460800
    file_count = 5
    size_mb = 1
    
    print(f"\n{'='*60}")
    print(f"多文件测试: {file_count}个{size_mb}MB文件")
    print(f"{'='*60}")

    # 连续传输多个文件
    for i in range(file_count):
        src_file = _generate_test_file(size_mb, tmp_path / f"multi_test_{i}.bin")
        result = _run_transfer(src_file, baudrate, tmp_path)
        assert result, f"第{i+1}个文件传输失败"
        print(f"✅ 第{i+1}/{file_count}个文件传输完成")
        
        # 文件间间隔
        time.sleep(2)

    print(f"🎉 多文件测试通过: {file_count}个文件")


# ---------- 单脚本运行入口 ----------
def run_manual_test():
    """手动运行测试（非pytest模式）"""
    print("串口文件传输 - CLI集成测试")
    print("=" * 50)
    
    if not _check_hardware_available():
        print("❌ 串口硬件不可用，跳过测试")
        return

    # 创建临时目录
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        print("开始基础功能测试...")
        
        # 基础测试：1MB文件，115200波特率
        size_mb = 1
        baudrate = 115200
        
        print(f"\n测试配置: {size_mb}MB文件, {baudrate}bps")
        src_file = _generate_test_file(size_mb, tmp_path / f"manual_test_{size_mb}mb.bin")
        result = _run_transfer(src_file, baudrate, tmp_path)
        
        if result:
            print("🎉 手动测试成功！")
        else:
            print("❌ 手动测试失败！")
            sys.exit(1)


if __name__ == "__main__":
    # 检查命令行参数决定运行模式
    if len(sys.argv) > 1 and "--manual" in sys.argv:
        run_manual_test()
    else:
        # 使用pytest运行
        test_args = [__file__, "-v"]
        
        # 支持硬件标记过滤
        if "--skip-hardware" in sys.argv:
            test_args.extend(["-m", "not hardware"])
        
        sys.exit(pytest.main(test_args)) 