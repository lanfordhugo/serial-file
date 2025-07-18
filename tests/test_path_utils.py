"""
路径处理工具测试
==============

测试路径处理工具的各种功能，包括文件名清理、路径标准化、冲突解决等。
"""

import pytest
import tempfile
from pathlib import Path
from src.serial_file_transfer.utils.path_utils import (
    sanitize_filename,
    normalize_path,
    resolve_file_conflict,
    create_safe_path,
    ensure_directory_exists,
    get_relative_path_info,
)


class TestSanitizeFilename:
    """测试文件名清理功能"""

    def test_sanitize_normal_filename(self):
        """测试正常文件名"""
        result = sanitize_filename("normal_file.txt")
        assert result == "normal_file.txt"

    def test_sanitize_unsafe_chars(self):
        """测试包含不安全字符的文件名"""
        result = sanitize_filename('file<>:"/\\|?*.txt')
        assert result == "file_________.txt"

    def test_sanitize_empty_filename(self):
        """测试空文件名"""
        result = sanitize_filename("")
        assert result == "unnamed_file"

    def test_sanitize_whitespace_filename(self):
        """测试只包含空格的文件名"""
        result = sanitize_filename("   ")
        assert result == "unnamed_file"

    def test_sanitize_long_filename(self):
        """测试过长的文件名"""
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 255
        assert result.endswith(".txt")


class TestNormalizePath:
    """测试路径标准化功能"""

    def test_normalize_forward_slashes(self):
        """测试正斜杠路径"""
        result = normalize_path("folder/subfolder/file.txt")
        assert result == "folder/subfolder/file.txt"

    def test_normalize_backward_slashes(self):
        """测试反斜杠路径"""
        result = normalize_path("folder\\subfolder\\file.txt")
        assert result == "folder/subfolder/file.txt"

    def test_normalize_mixed_slashes(self):
        """测试混合斜杠路径"""
        result = normalize_path("folder\\subfolder/file.txt")
        assert result == "folder/subfolder/file.txt"

    def test_normalize_multiple_slashes(self):
        """测试多重斜杠"""
        result = normalize_path("folder//subfolder///file.txt")
        assert result == "folder/subfolder/file.txt"

    def test_normalize_leading_slash(self):
        """测试开头斜杠"""
        result = normalize_path("/folder/file.txt")
        assert result == "folder/file.txt"


class TestResolveFileConflict:
    """测试文件冲突解决功能"""

    def test_no_conflict(self):
        """测试无冲突情况"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "test.txt"
            result = resolve_file_conflict(test_path)
            assert result == test_path

    def test_single_conflict(self):
        """测试单个冲突"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建冲突文件
            test_path = Path(temp_dir) / "test.txt"
            test_path.write_text("existing")
            
            result = resolve_file_conflict(test_path)
            expected = Path(temp_dir) / "test_1.txt"
            assert result == expected

    def test_multiple_conflicts(self):
        """测试多个冲突"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建多个冲突文件
            base_path = Path(temp_dir) / "test.txt"
            base_path.write_text("existing")
            (Path(temp_dir) / "test_1.txt").write_text("existing")
            (Path(temp_dir) / "test_2.txt").write_text("existing")
            
            result = resolve_file_conflict(base_path)
            expected = Path(temp_dir) / "test_3.txt"
            assert result == expected


class TestCreateSafePath:
    """测试安全路径创建功能"""

    def test_create_simple_path(self):
        """测试创建简单路径"""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            result = create_safe_path(base_path, "file.txt")
            expected = base_path / "file.txt"
            assert result == expected

    def test_create_nested_path(self):
        """测试创建嵌套路径"""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            result = create_safe_path(base_path, "folder/subfolder/file.txt")
            expected = base_path / "folder" / "subfolder" / "file.txt"
            assert result == expected

    def test_create_path_with_unsafe_chars(self):
        """测试包含不安全字符的路径"""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            result = create_safe_path(base_path, "folder<>/file*.txt")
            expected = base_path / "folder__" / "file_.txt"
            assert result == expected

    def test_create_path_with_conflict(self):
        """测试有冲突的路径创建"""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            # 创建冲突文件
            conflict_path = base_path / "file.txt"
            conflict_path.write_text("existing")
            
            result = create_safe_path(base_path, "file.txt")
            expected = base_path / "file_1.txt"
            assert result == expected


class TestEnsureDirectoryExists:
    """测试目录创建功能"""

    def test_create_new_directory(self):
        """测试创建新目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "new_folder"
            result = ensure_directory_exists(new_dir)
            assert result is True
            assert new_dir.exists()
            assert new_dir.is_dir()

    def test_create_nested_directories(self):
        """测试创建嵌套目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_dir = Path(temp_dir) / "level1" / "level2" / "level3"
            result = ensure_directory_exists(nested_dir)
            assert result is True
            assert nested_dir.exists()
            assert nested_dir.is_dir()

    def test_existing_directory(self):
        """测试已存在的目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            existing_dir = Path(temp_dir)
            result = ensure_directory_exists(existing_dir)
            assert result is True


class TestGetRelativePathInfo:
    """测试相对路径信息获取功能"""

    def test_file_path_info(self):
        """测试文件路径信息"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("test")
            
            root_name, is_folder = get_relative_path_info(test_file)
            assert root_name == ""
            assert is_folder is False

    def test_folder_path_info(self):
        """测试文件夹路径信息"""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_folder = Path(temp_dir) / "test_folder"
            test_folder.mkdir()
            
            root_name, is_folder = get_relative_path_info(test_folder)
            assert root_name == "test_folder"
            assert is_folder is True

    def test_nonexistent_path_info(self):
        """测试不存在路径的信息"""
        nonexistent = Path("/nonexistent/path")
        root_name, is_folder = get_relative_path_info(nonexistent)
        assert root_name == ""
        assert is_folder is False
