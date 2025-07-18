"""
测试模块
========

包含所有单元测试和集成测试。
"""

# 为了支持直接运行单个测试文件，确保项目源码包可被导入
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).parent.parent.resolve()
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
