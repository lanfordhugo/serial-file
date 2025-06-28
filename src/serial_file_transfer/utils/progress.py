"""
进度显示模块
============

提供文件传输进度显示功能。
"""

import sys
import time
from typing import Optional
from datetime import datetime


class ProgressBar:
    """进度条显示器"""
    
    def __init__(self, total: int = 100, width: int = 50, show_rate: bool = True):
        """
        初始化进度条
        
        Args:
            total: 总数量/大小
            width: 进度条宽度（字符数）
            show_rate: 是否显示速率
        """
        self.total = total
        self.width = width
        self.show_rate = show_rate
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.last_progress = 0
        
    def update(self, current: int, rate: Optional[float] = None) -> None:
        """
        更新进度
        
        Args:
            current: 当前进度
            rate: 传输速率（可选）
        """
        if self.total <= 0:
            return
            
        # 计算进度百分比
        progress_percent = min(100.0, (current / self.total) * 100)
        
        # 计算进度条
        filled_width = int((progress_percent / 100) * self.width)
        bar = '█' * filled_width + '░' * (self.width - filled_width)
        
        # 时间戳
        now = datetime.now()
        milliseconds = now.microsecond // 1000
        timestamp = now.strftime(f"%Y-%m-%d %H:%M:%S.{milliseconds:03d}")
        
        # 构建显示字符串
        display_parts = [
            f'\r\033[0m[{timestamp}]',
            f'Progress: [{progress_percent:6.2f}%]',
            f'[{bar}]'
        ]
        
        # 添加速率信息
        if self.show_rate and rate is not None:
            display_parts.append(f'[{rate:6.2f}k/s]')
        elif self.show_rate:
            # 自动计算速率
            current_time = time.time()
            time_diff = current_time - self.last_update_time
            if time_diff > 0.1:  # 避免除零和频繁更新
                data_diff = current - self.last_progress
                calculated_rate = (data_diff / time_diff) / 1024  # KB/s
                display_parts.append(f'[{calculated_rate:6.2f}k/s]')
                self.last_update_time = current_time
                self.last_progress = current
        
        # 输出进度
        sys.stdout.write(''.join(display_parts))
        sys.stdout.flush()
        
        # 完成时换行
        if progress_percent >= 100:
            sys.stdout.write('\n')
    
    def finish(self) -> None:
        """完成进度显示"""
        sys.stdout.write('\n')
        sys.stdout.flush()


def progress_bar(progress: float, rate: float = 0) -> None:
    """
    显示进度条（兼容原有函数）
    
    Args:
        progress: 进度百分比(0-100)
        rate: 传输速率(k/s)
    """
    # 时间戳
    now = datetime.now()
    milliseconds = now.microsecond // 1000
    timestamp = now.strftime(f"%Y-%m-%d %H:%M:%S.{milliseconds:03d}")
    
    # 构建进度条
    width = 30
    filled_width = int((progress / 100) * width)
    bar = '█' * filled_width + '░' * (width - filled_width)
    
    # 输出
    display_str = f'\r\033[0m[{timestamp}] Progress: [{progress:6.2f}%][{bar}][{rate:6.2f}k/s]'
    sys.stdout.write(display_str)
    sys.stdout.flush()


class TransferProgressTracker:
    """传输进度跟踪器"""
    
    def __init__(self, file_size: int, file_name: str = ""):
        """
        初始化进度跟踪器
        
        Args:
            file_size: 文件总大小（字节）
            file_name: 文件名（可选）
        """
        self.file_size = file_size
        self.file_name = file_name
        self.transferred = 0
        self.start_time = time.time()
        self.progress_bar = ProgressBar(file_size)
        
    def update(self, bytes_transferred: int) -> None:
        """
        更新传输进度
        
        Args:
            bytes_transferred: 已传输的字节数
        """
        self.transferred = bytes_transferred
        
        # 计算传输速率
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 0:
            rate = (self.transferred / elapsed_time) / 1024  # KB/s
        else:
            rate = 0
            
        # 更新进度条
        self.progress_bar.update(self.transferred, rate)
    
    def finish(self) -> None:
        """完成传输"""
        elapsed_time = time.time() - self.start_time
        avg_rate = (self.transferred / elapsed_time / 1024) if elapsed_time > 0 else 0
        
        self.progress_bar.finish()
        
        if self.file_name:
            print(f"文件 [{self.file_name}] 传输完成！")
        else:
            print("文件传输完成！")
            
        print(f"总大小: {self.file_size / 1024:.2f} KB")
        print(f"传输时间: {elapsed_time:.2f} 秒")
        print(f"平均速率: {avg_rate:.2f} KB/s") 