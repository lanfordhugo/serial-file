"""
进度显示模块
============

提供文件传输进度显示功能。
"""

import sys
import time
from typing import Optional, Any, Dict
from datetime import datetime


class SpeedMeter:
    """实时传输速率计算器"""

    def __init__(self, alpha: float = 0.3):
        """
        初始化速率计算器

        Args:
            alpha: EMA 平滑系数 (0.0 - 1.0)，值越大越接近瞬时速度
        """
        self.last_bytes = 0
        self.last_ts = time.time()
        self.ema_rate = 0.0  # 指数移动平均速率 (bytes/s)
        self.alpha = alpha

    def update(self, current_bytes: int) -> float:
        """
        更新并返回实时传输速率 (KB/s)

        Args:
            current_bytes: 当前已传输的总字节数

        Returns:
            float: 实时传输速率 (KB/s)
        """
        now = time.time()
        interval = now - self.last_ts

        if interval > 0.05:  # 至少等待50ms更新，避免频繁计算和抖动
            instant_rate = (current_bytes - self.last_bytes) / interval  # bytes/s
            self.ema_rate = self.alpha * instant_rate + (1 - self.alpha) * self.ema_rate
            self.last_bytes = current_bytes
            self.last_ts = now

        return self.ema_rate / 1024  # 返回KB/s


class ProgressBar:
    """简化版进度条显示器 (纯文本，无ANSI颜色)"""

    def __init__(
        self,
        total: int = 100,
        width: int = 50,
        show_rate: bool = True,
        refresh_interval: float = 1.0,
    ):
        """
        初始化进度条

        Args:
            total: 总数量/大小
            width: 进度条宽度（字符数）
            show_rate: 是否显示速率
            refresh_interval: 最小刷新间隔(秒)，减少重复绘制
        """
        self.total = total
        self.width = width
        self.show_rate = show_rate
        self.refresh_interval = refresh_interval
        self.start_time = time.time()
        self.speed_meter = SpeedMeter()  # 使用新的速率计算器
        self.last_display_length = 0  # 记录上次显示字符串的长度，用于清空行
        self._last_draw_ts = 0.0

    def update(self, current: int) -> None:
        """
        更新进度

        Args:
            current: 当前进度
        """
        if self.total <= 0:
            return

        # 计算进度百分比
        progress_percent = min(100.0, (current / self.total) * 100)

        now_ts = time.time()
        # 若未到刷新间隔且非完成状态，直接返回
        if (
            progress_percent < 100.0
            and (now_ts - self._last_draw_ts) < self.refresh_interval
        ):
            return
        self._last_draw_ts = now_ts

        # 计算进度条
        filled_width = int((progress_percent / 100) * self.width)
        bar = "█" * filled_width + "░" * (self.width - filled_width)

        # 计算实时速率
        current_rate_kbps = self.speed_meter.update(current)

        # 构建显示字符串
        display_parts = [f"Progress: [{progress_percent:6.2f}%]", f"[{bar}]"]

        # 添加速率信息
        if self.show_rate:
            display_parts.append(f"[{current_rate_kbps:6.2f}k/s]")

        display_str = "".join(display_parts)

        # 用空格填充，覆盖旧内容
        current_len = len(display_str)
        padding = " " * max(0, self.last_display_length - current_len)

        print("\r" + display_str + padding, end="", flush=True)
        self.last_display_length = current_len

        if progress_percent >= 100:
            print()  # 换行完成

    def finish(self) -> None:
        """完成进度显示"""
        print("\r" + " " * self.last_display_length + "\r", end="\n", flush=True)


def progress_bar(progress: float, rate: float = 0) -> None:
    """
    显示进度条（兼容原有函数，已废弃，请使用 ProgressBar 类）

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
    bar = "█" * filled_width + "░" * (width - filled_width)

    # 输出
    display_str = (
        f"\r\033[0m[{timestamp}] Progress: [{progress:6.2f}%][{bar}][{rate:6.2f}k/s]"
    )
    sys.stdout.write(display_str)
    sys.stdout.flush()


class TransferProgressTracker:  # 此类已废弃，请使用 ProgressBar
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
        self.progress_bar = ProgressBar(file_size)  # 内部仍使用ProgressBar

    def update(self, bytes_transferred: int) -> None:
        """
        更新传输进度

        Args:
            bytes_transferred: 已传输的字节数
        """
        self.transferred = bytes_transferred
        self.progress_bar.update(self.transferred)  # 调用ProgressBar的更新方法

    def finish(self) -> None:
        """完成传输"""
        elapsed_time = time.time() - self.start_time
        avg_rate = (self.transferred / elapsed_time / 1024) if elapsed_time > 0 else 0

        self.progress_bar.finish()

        if self.file_name:
            print(f"文件 [{self.file_name}] 传输完成！")
        else:
            print("文件传输完成！")

        print(
            f"总大小: {self.transferred / 1024:.2f} KB"
        )  # 使用self.transferred 替换 self.file_size 确保显示实际传输量
        print(f"传输时间: {elapsed_time:.2f} 秒")
        print(f"平均速率: {avg_rate:.2f} KB/s")
