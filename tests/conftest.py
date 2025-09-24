"""
测试配置与通用夹具
==================

统一管理测试夹具、Fake对象和测试常量，避免重复代码。
"""

import pytest
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from unittest.mock import MagicMock
import sys

# 添加项目根目录到Python路径 - 统一处理导入
ROOT_DIR = Path(__file__).parent.parent
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from serial_file_transfer.config.settings import SerialConfig, TransferConfig
from serial_file_transfer.config.constants import SerialCommand


# ==================== 测试常量 ====================
class TestConstants:
    """测试常量，避免魔法数字"""
    # 文件大小
    SMALL_FILE_SIZE = 1024      # 1KB
    MEDIUM_FILE_SIZE = 10240    # 10KB  
    LARGE_FILE_SIZE = 102400    # 100KB
    
    # 传输参数
    DEFAULT_BAUDRATE = 115200
    HIGH_BAUDRATE = 1728000
    DEFAULT_CHUNK_SIZE = 1024
    LARGE_CHUNK_SIZE = 16384
    
    # 超时设置
    SHORT_TIMEOUT = 0.1
    MEDIUM_TIMEOUT = 1.0
    LONG_TIMEOUT = 5.0
    
    # 重试次数
    DEFAULT_RETRY = 3
    MAX_RETRY = 5


# ==================== Fake对象 ====================
class FakeSerial:
    """
    串口模拟对象，替代真实串口进行测试
    支持读写缓冲、异常模拟、状态管理
    """
    
    def __init__(self, port: str = "FAKE_PORT", baudrate: int = 115200, 
                 timeout: float = 0.1, **kwargs):
        self.port = port
        self.baudrate = baudrate  
        self.timeout = timeout
        self.is_open = False
        
        # 读写缓冲区
        self._write_buffer: List[bytes] = []
        self._read_buffer: bytes = b""
        self._read_position = 0
        
        # 异常模拟
        self._should_fail_open = False
        self._should_fail_write = False  
        self._should_fail_read = False
        self._write_partial_bytes = None  # 模拟部分写入
        
        # 统计信息
        self.open_count = 0
        self.close_count = 0
        self.write_count = 0
        self.read_count = 0
    
    def open(self):
        """打开串口"""
        if self._should_fail_open:
            raise Exception("模拟串口打开失败")
        self.is_open = True
        self.open_count += 1
    
    def close(self):
        """关闭串口"""  
        self.is_open = False
        self.close_count += 1
    
    def write(self, data: bytes) -> int:
        """写入数据"""
        if not self.is_open:
            raise Exception("串口未打开")
        if self._should_fail_write:
            raise Exception("模拟写入失败")
        
        self._write_buffer.append(data)
        self.write_count += 1
        
        # 模拟部分写入
        if self._write_partial_bytes is not None:
            return min(self._write_partial_bytes, len(data))
        
        return len(data)
    
    def read(self, size: int = 1) -> bytes:
        """读取数据"""
        if not self.is_open:
            raise Exception("串口未打开")  
        if self._should_fail_read:
            raise Exception("模拟读取失败")
        
        self.read_count += 1
        
        # 从缓冲区读取
        if self._read_position >= len(self._read_buffer):
            return b""
        
        end_pos = min(self._read_position + size, len(self._read_buffer))
        result = self._read_buffer[self._read_position:end_pos]
        self._read_position = end_pos
        
        return result
    
    def reset_buffers(self):
        """重置缓冲区"""
        self._write_buffer.clear()
        self._read_buffer = b""
        self._read_position = 0
    
    def set_read_data(self, data: bytes):
        """设置要读取的数据"""
        self._read_buffer = data
        self._read_position = 0
    
    def get_written_data(self) -> List[bytes]:
        """获取写入的数据"""
        return self._write_buffer.copy()
    
    def simulate_open_failure(self, should_fail: bool = True):
        """模拟打开失败"""
        self._should_fail_open = should_fail
    
    def simulate_write_failure(self, should_fail: bool = True):
        """模拟写入失败"""
        self._should_fail_write = should_fail
    
    def simulate_read_failure(self, should_fail: bool = True):  
        """模拟读取失败"""
        self._should_fail_read = should_fail
    
    def simulate_partial_write(self, bytes_written: Optional[int]):
        """模拟部分写入"""
        self._write_partial_bytes = bytes_written


class FakeProgressCallback:
    """进度回调模拟对象"""
    
    def __init__(self):
        self.calls: List[Dict[str, Any]] = []
        self.total_progress = 0
    
    def __call__(self, current: int, total: int, **kwargs):
        """进度回调"""
        self.calls.append({
            'current': current,
            'total': total,
            'timestamp': time.time(),
            **kwargs
        })
        self.total_progress = current
    
    def reset(self):
        """重置状态"""
        self.calls.clear()
        self.total_progress = 0
    
    @property
    def call_count(self) -> int:
        """调用次数"""
        return len(self.calls)
    
    @property  
    def final_progress(self) -> int:
        """最终进度"""
        return self.calls[-1]['current'] if self.calls else 0


# ==================== 通用夹具 ====================
@pytest.fixture
def test_constants():
    """测试常量夹具"""
    return TestConstants


@pytest.fixture
def fake_serial():
    """Fake串口对象夹具"""
    return FakeSerial()


@pytest.fixture  
def fake_progress():
    """Fake进度回调夹具"""
    return FakeProgressCallback()


@pytest.fixture
def temp_dir():
    """临时目录夹具"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def test_file_small(temp_dir, test_constants):
    """小测试文件夹具"""
    file_path = temp_dir / "small_test.txt"
    file_path.write_bytes(b"A" * test_constants.SMALL_FILE_SIZE)
    return file_path


@pytest.fixture
def test_file_medium(temp_dir, test_constants):
    """中等测试文件夹具"""  
    file_path = temp_dir / "medium_test.txt"
    file_path.write_bytes(b"B" * test_constants.MEDIUM_FILE_SIZE)
    return file_path


@pytest.fixture
def test_file_large(temp_dir, test_constants):
    """大测试文件夹具"""
    file_path = temp_dir / "large_test.txt"  
    file_path.write_bytes(b"C" * test_constants.LARGE_FILE_SIZE)
    return file_path


@pytest.fixture
def serial_config_default():
    """默认串口配置夹具"""
    return SerialConfig(port="COM1", baudrate=115200, timeout=0.1)


@pytest.fixture
def serial_config_high_speed():
    """高速串口配置夹具"""
    return SerialConfig(port="COM1", baudrate=1728000, timeout=0.2)


@pytest.fixture
def transfer_config_default():
    """默认传输配置夹具"""
    return TransferConfig(
        max_data_length=1024,
        request_timeout=1.0,
        retry_count=3,
        show_progress=False
    )


@pytest.fixture
def transfer_config_fast():
    """快速传输配置夹具"""
    return TransferConfig(
        max_data_length=16384,
        request_timeout=0.5, 
        retry_count=2,
        show_progress=False
    )


# ==================== 测试工具函数 ====================
def create_test_data(size: int, pattern: bytes = b"TEST") -> bytes:
    """创建指定大小的测试数据"""
    if not pattern:
        pattern = b"X"
    
    repeat_count = (size + len(pattern) - 1) // len(pattern)
    data = pattern * repeat_count
    return data[:size]


def assert_file_content_equals(file1: Path, file2: Path):
    """断言两个文件内容相同"""
    assert file1.exists(), f"文件不存在: {file1}"
    assert file2.exists(), f"文件不存在: {file2}"
    
    content1 = file1.read_bytes()
    content2 = file2.read_bytes()
    
    assert len(content1) == len(content2), f"文件大小不同: {len(content1)} vs {len(content2)}"
    assert content1 == content2, "文件内容不同"


def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1) -> bool:
    """等待条件满足，替代sleep的更好方式"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)
    
    return False


# ==================== Pytest配置 ====================
def pytest_configure(config):
    """Pytest配置钩子"""
    # 注册自定义标记
    config.addinivalue_line(
        "markers", "slow: 标记慢速测试，通常需要较长时间执行"
    )
    config.addinivalue_line(
        "markers", "integration: 标记集成测试，需要外部依赖或硬件"  
    )
    config.addinivalue_line(
        "markers", "hardware: 标记需要真实硬件的测试"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试收集，为未标记的测试添加默认行为"""
    for item in items:
        # 为包含"integration"的测试文件自动添加integration标记
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # 为包含"slow"的测试方法自动添加slow标记  
        if "slow" in item.name.lower():
            item.add_marker(pytest.mark.slow)
