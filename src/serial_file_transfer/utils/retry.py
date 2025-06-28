"""重试与退避工具
====================

提供通用的带指数退避的重试装饰器和辅助函数。
"""

from __future__ import annotations

import time
import random
from typing import Callable, TypeVar, Any

_T = TypeVar("_T")


def exponential_backoff(base: float, attempt: int, jitter_ratio: float = 0.1) -> float:
    """计算指数退避时间

    Args:
        base: 基础延时（秒）
        attempt: 第 *attempt* 次重试（从 0 开始）
        jitter_ratio: 抖动比例，默认 10%

    Returns:
        等待时间，秒
    """
    delay = base * (2 ** attempt)
    jitter = random.uniform(0, delay * jitter_ratio)
    return delay + jitter


def retry_call(
    func: Callable[[], _T],
    *,
    max_retry: int,
    base_delay: float,
    logger=None,
) -> _T | None:
    """带退避的同步重试调用

    Args:
        func: 无参可调用对象，返回真值即视为成功
        max_retry: 最大重试次数
        base_delay: 指数退避基础时间，秒
        logger: 可选日志记录器

    Returns:
        func 的返回值，若始终失败则返回 None
    """
    for attempt in range(max_retry + 1):
        result = func()
        if result:
            return result
        if attempt == max_retry:
            break
        wait = exponential_backoff(base_delay, attempt)
        if logger:
            logger.debug(f"重试第{attempt + 1}次将在 {wait:.2f}s 后进行 …")
        time.sleep(wait)
    return None 