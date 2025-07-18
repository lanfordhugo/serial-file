#!/usr/bin/env python3
"""
性能基准测试脚本
================

用于测试串口文件传输的性能，支持多种配置对比测试。
"""

import sys
import time
import os
import threading
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
from datetime import datetime

# 添加src路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from serial_file_transfer.config.settings import SerialConfig, TransferConfig
from serial_file_transfer.core.serial_manager import SerialManager
from serial_file_transfer.transfer.sender import FileSender
from serial_file_transfer.transfer.receiver import FileReceiver
from serial_file_transfer.utils.logger import get_logger

logger = get_logger(__name__)

class PerformanceTest:
    """性能测试类"""
    
    def __init__(self):
        self.test_results: List[Dict] = []
        self.test_files = {
            "small": "test_files/test_100k.txt",    # 100KB
            "medium": "test_files/test_1m.txt",     # 1MB
            "large": None  # 将动态创建大文件
        }
        # 接收文件管理
        self.received_files: List[Path] = []  # 记录创建的接收文件，用于清理
        
    def create_test_files(self):
        """创建测试文件"""
        test_dir = Path("test_files")
        test_dir.mkdir(exist_ok=True)
        
        # 创建100KB测试文件
        small_file = test_dir / "test_100k.txt"
        if not small_file.exists():
            with open(small_file, 'w', encoding='utf-8') as f:
                content = "这是性能测试文件内容。" * 100  # 约2KB
                for i in range(50):  # 总共约100KB
                    f.write(f"第{i+1}段：{content}\n")
            print(f"✅ 创建测试文件: {small_file} ({small_file.stat().st_size} 字节)")
        
        # 创建1MB测试文件
        medium_file = test_dir / "test_1m.txt"
        if not medium_file.exists():
            with open(medium_file, 'w', encoding='utf-8') as f:
                content = "性能测试数据" * 100  # 约1.2KB
                for i in range(850):  # 总共约1MB
                    f.write(f"块{i:04d}：{content}\n")
            print(f"✅ 创建测试文件: {medium_file} ({medium_file.stat().st_size} 字节)")
        
        # 创建5MB测试文件
        large_file = test_dir / "test_5m.txt"
        if not large_file.exists():
            with open(large_file, 'w', encoding='utf-8') as f:
                content = "大文件性能测试内容" * 50  # 约1KB
                for i in range(5000):  # 总共约5MB
                    f.write(f"数据块{i:05d}：{content}\n")
            print(f"✅ 创建测试文件: {large_file} ({large_file.stat().st_size} 字节)")
        
        self.test_files["large"] = str(large_file)
        
    def _get_received_file_path(self, test_name: str) -> Path:
        """
        获取接收文件路径，使用固定命名避免文件膨胀
        
        Args:
            test_name: 测试名称
            
        Returns:
            接收文件路径
        """
        received_dir = Path("received_files")
        received_dir.mkdir(exist_ok=True)
        
        # 使用固定的文件名，每次测试会覆盖之前的文件
        received_file = received_dir / f"received_{test_name}_latest.txt"
        
        # 记录文件路径用于清理
        if received_file not in self.received_files:
            self.received_files.append(received_file)
            
        return received_file
        
    def cleanup_received_files(self):
        """清理接收的测试文件"""
        cleaned_count = 0
        for file_path in self.received_files:
            if file_path.exists():
                try:
                    file_path.unlink()
                    cleaned_count += 1
                    logger.debug(f"已清理接收文件: {file_path}")
                except OSError as e:
                    logger.warning(f"清理文件失败 {file_path}: {e}")
        
        if cleaned_count > 0:
            print(f"🧹 已清理 {cleaned_count} 个接收测试文件")
        
        self.received_files.clear()
        
    def run_single_test(self, 
                       test_name: str,
                       file_path: str, 
                       baudrate: int,
                       chunk_size: int,
                       timeout: float = 1.0) -> Optional[Dict]:
        """运行单个性能测试"""
        
        print(f"\n🧪 开始测试: {test_name}")
        print(f"   文件: {file_path}")
        print(f"   波特率: {baudrate}")
        print(f"   块大小: {chunk_size}")
        print(f"   超时: {timeout}s")
        
        # 检查文件是否存在
        if not Path(file_path).exists():
            print(f"❌ 测试文件不存在: {file_path}")
            return None
            
        file_size = Path(file_path).stat().st_size
        print(f"   文件大小: {file_size} 字节 ({file_size/1024:.1f} KB)")
        
        # 配置
        sender_config = SerialConfig(port="COM5", baudrate=baudrate, timeout=timeout)
        receiver_config = SerialConfig(port="COM7", baudrate=baudrate, timeout=timeout)
        
        # 显式构造 TransferConfig（分别实例化，互不影响）
        receiver_transfer_cfg = TransferConfig(
            max_data_length=chunk_size,
            request_timeout=int(timeout * 10),
            retry_count=3,
            show_progress=True,
        )

        sender_transfer_cfg = TransferConfig(
            max_data_length=chunk_size,
            request_timeout=int(timeout * 10),
            retry_count=3,
            show_progress=True,
        )

        # 使用固定命名的接收文件
        received_file = self._get_received_file_path(test_name)

        def receiver_thread():
            try:
                with SerialManager(receiver_config) as receiver_serial:
                    receiver = FileReceiver(
                        receiver_serial, str(received_file), receiver_transfer_cfg
                    )
                    return receiver.start_transfer()
            except Exception as e:
                logger.error(f"接收端异常: {e}")
                return False

        # 发送端函数
        def sender_thread():
            try:
                time.sleep(1)  # 等待接收端准备
                with SerialManager(sender_config) as sender_serial:
                    sender = FileSender(sender_serial, file_path, sender_transfer_cfg)
                    return sender.start_transfer()
            except Exception as e:
                logger.error(f"发送端异常: {e}")
                return False
        
        # 启动测试
        start_time = time.time()
        
        # 启动接收端
        receiver_t = threading.Thread(target=receiver_thread)
        receiver_t.daemon = True
        receiver_t.start()
        
        # 启动发送端
        sender_t = threading.Thread(target=sender_thread)
        sender_t.daemon = True
        sender_t.start()
        
        # 等待完成（最多等待60秒）
        receiver_t.join(timeout=60)
        sender_t.join(timeout=60)
        
        end_time = time.time()
        transfer_time = end_time - start_time
        
        # 检查结果
        if received_file.exists():
            received_size = received_file.stat().st_size
            if received_size == file_size:
                transfer_speed = (file_size / 1024) / transfer_time  # KB/s
                efficiency = (transfer_speed * 8) / baudrate * 100  # 效率百分比
                
                result = {
                    "test_name": test_name,
                    "file_path": file_path,
                    "file_size": file_size,
                    "baudrate": baudrate,
                    "chunk_size": chunk_size,
                    "timeout": timeout,
                    "transfer_time": transfer_time,
                    "transfer_speed_kbps": transfer_speed,
                    "efficiency_percent": efficiency,
                    "timestamp": datetime.now().isoformat(),
                    "success": True
                }
                
                print(f"✅ 测试成功!")
                print(f"   传输时间: {transfer_time:.2f} 秒")
                print(f"   传输速度: {transfer_speed:.2f} KB/s")
                print(f"   传输效率: {efficiency:.1f}%")
                
                return result
            else:
                print(f"❌ 文件大小不匹配: 期望{file_size}, 实际{received_size}")
        else:
            print(f"❌ 接收文件不存在: {received_file}")
        
        return {
            "test_name": test_name,
            "success": False,
            "error": "传输失败",
            "timestamp": datetime.now().isoformat()
        }
    
    def run_baseline_tests(self) -> List[Dict]:
        """运行基准测试"""
        print("🚀 开始基准性能测试")
        print("=" * 50)
        
        # 优化：增大块大小至 16KB，缩短串口超时，提升吞吐
        baseline_tests = [
            ("baseline_100k", self.test_files["small"], 1728000, 16384, 0.1),
            ("baseline_1m", self.test_files["medium"], 1728000, 16384, 0.1),
            ("baseline_5m", self.test_files["large"], 1728000, 16384, 0.2),
        ]
        
        results = []
        for test_config in baseline_tests:
            result = self.run_single_test(*test_config)
            if result:
                results.append(result)
                self.test_results.append(result)
            
            # 测试间隔
            time.sleep(2)
        
        return results
    
    def save_results(self, filename: Optional[str] = None):
        """保存测试结果"""
        if filename is None:
            filename = f"performance_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        
        print(f"📊 测试结果已保存到: {filename}")
    
    def print_summary(self):
        """打印测试摘要"""
        if not self.test_results:
            print("❌ 没有测试结果")
            return
        
        print("\n" + "=" * 60)
        print("📊 测试结果摘要")
        print("=" * 60)
        
        successful_tests = [r for r in self.test_results if r.get('success', False)]
        
        if successful_tests:
            print(f"✅ 成功测试: {len(successful_tests)}/{len(self.test_results)}")
            print()
            
            for result in successful_tests:
                print(f"🧪 {result['test_name']}")
                print(f"   文件大小: {result['file_size']/1024:.1f} KB")
                print(f"   传输速度: {result['transfer_speed_kbps']:.2f} KB/s")
                print(f"   传输效率: {result['efficiency_percent']:.1f}%")
                print(f"   块大小: {result['chunk_size']} 字节")
                print()
        else:
            print("❌ 所有测试都失败了")

def main():
    """主函数"""
    print("🧪 串口文件传输性能测试工具")
    print("=" * 50)
    
    # 创建测试实例
    test = PerformanceTest()
    
    try:
        # 创建测试文件
        test.create_test_files()
        
        # 运行基准测试
        baseline_results = test.run_baseline_tests()
        
        # 保存和显示结果
        test.save_results("performance_results.json")
        test.print_summary()
        
        print("\n🎯 基准测试完成！")
        print("接下来可以进行优化测试...")
        
    finally:
        # 清理接收文件
        test.cleanup_received_files()

if __name__ == "__main__":
    main()
