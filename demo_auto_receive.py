#!/usr/bin/env python3
"""
智能协商模式自动接收演示
======================

演示新的智能协商模式功能：
1. 完全自动化的文件接收
2. 自动路径创建和目录结构重建
3. 跨平台路径兼容性
4. 文件名冲突处理

使用方法：
    python demo_auto_receive.py
"""

import sys
import tempfile
from pathlib import Path

# 添加src路径到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from serial_file_transfer.core.probe_structures import CapabilityNegoData
from serial_file_transfer.utils.path_utils import (
    create_safe_path,
    normalize_path,
    sanitize_filename,
    resolve_file_conflict,
    get_relative_path_info,
)


def demo_protocol_enhancement():
    """演示协议增强功能"""
    print("=" * 60)
    print("🚀 智能协商协议增强演示")
    print("=" * 60)
    
    # 创建包含根路径信息的协商数据
    nego_data = CapabilityNegoData(
        session_id=12345,
        transfer_mode=2,  # 批量传输模式
        file_count=5,
        total_size=1024 * 1024,
        selected_baudrate=921600,
        chunk_size=1024,
        root_path="project_files",  # 新增：根路径信息
    )
    
    print(f"📋 协商数据:")
    print(f"   会话ID: {nego_data.session_id}")
    print(f"   传输模式: {'批量传输' if nego_data.transfer_mode == 2 else '单文件传输'}")
    print(f"   文件数量: {nego_data.file_count}")
    print(f"   总大小: {nego_data.total_size / 1024:.1f} KB")
    print(f"   波特率: {nego_data.selected_baudrate}")
    print(f"   块大小: {nego_data.chunk_size}")
    print(f"   🆕 根路径: '{nego_data.root_path}'")
    
    # 测试序列化和反序列化
    packed = nego_data.pack()
    unpacked = CapabilityNegoData.unpack(packed)
    
    print(f"\n✅ 序列化测试:")
    print(f"   打包大小: {len(packed)} 字节")
    print(f"   解包成功: {unpacked is not None}")
    print(f"   根路径保持: {unpacked.root_path == nego_data.root_path if unpacked else False}")


def demo_path_processing():
    """演示路径处理功能"""
    print("\n" + "=" * 60)
    print("📁 智能路径处理演示")
    print("=" * 60)
    
    # 演示路径标准化
    test_paths = [
        "folder\\subfolder\\file.txt",  # Windows风格
        "folder/subfolder/file.txt",    # Unix风格
        "folder//subfolder///file.txt", # 多重斜杠
        "/folder/subfolder/file.txt",   # 绝对路径
    ]
    
    print("🔧 路径标准化:")
    for path in test_paths:
        normalized = normalize_path(path)
        print(f"   '{path}' -> '{normalized}'")
    
    # 演示文件名清理
    unsafe_names = [
        "file<>name.txt",
        'file"with|chars?.txt',
        "   file with spaces   .txt",
        "a" * 300 + ".txt",  # 过长文件名
    ]
    
    print("\n🧹 文件名清理:")
    for name in unsafe_names:
        safe_name = sanitize_filename(name)
        display_name = name if len(name) <= 50 else name[:47] + "..."
        print(f"   '{display_name}' -> '{safe_name}'")


def demo_auto_path_creation():
    """演示自动路径创建功能"""
    print("\n" + "=" * 60)
    print("🏗️  自动路径创建演示")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir)
        print(f"📂 临时目录: {base_path}")
        
        # 模拟接收的文件路径列表
        received_files = [
            "docs/readme.txt",
            "src/main.py",
            "src/utils/helper.py",
            "tests/test_main.py",
            "config/settings.json",
        ]
        
        print("\n📥 模拟接收文件:")
        for file_path in received_files:
            safe_path = create_safe_path(base_path, file_path)
            # 创建文件以演示
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            safe_path.write_text(f"模拟文件内容: {file_path}")
            
            relative_path = safe_path.relative_to(base_path)
            print(f"   ✅ 创建: {relative_path}")
        
        # 显示创建的目录结构
        print(f"\n🌳 创建的目录结构:")
        for item in sorted(base_path.rglob("*")):
            if item.is_file():
                relative = item.relative_to(base_path)
                indent = "   " + "  " * (len(relative.parts) - 1)
                print(f"{indent}📄 {relative.name}")
            elif item != base_path:
                relative = item.relative_to(base_path)
                indent = "   " + "  " * (len(relative.parts) - 1)
                print(f"{indent}📁 {relative.name}/")


def demo_conflict_resolution():
    """演示文件冲突解决功能"""
    print("\n" + "=" * 60)
    print("⚡ 文件冲突解决演示")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir)
        
        # 创建原始文件
        original_file = base_path / "document.txt"
        original_file.write_text("原始文件内容")
        print(f"📄 创建原始文件: {original_file.name}")
        
        # 模拟冲突文件
        conflict_files = ["document.txt", "document.txt", "document.txt"]
        
        print(f"\n🔄 处理冲突文件:")
        for i, filename in enumerate(conflict_files):
            safe_path = create_safe_path(base_path, filename)
            safe_path.write_text(f"冲突文件内容 {i+1}")
            
            relative_path = safe_path.relative_to(base_path)
            print(f"   📄 冲突 #{i+1}: {filename} -> {relative_path}")
        
        # 显示最终文件列表
        print(f"\n📋 最终文件列表:")
        for file_path in sorted(base_path.glob("*.txt")):
            print(f"   📄 {file_path.name}")


def main():
    """主演示函数"""
    print("🎯 串口文件传输 - 智能协商模式优化演示")
    print("=" * 60)
    print("本演示展示了智能协商模式的新功能：")
    print("✨ 完全自动化的文件接收")
    print("✨ 自动路径创建和目录结构重建")
    print("✨ 跨平台路径兼容性处理")
    print("✨ 智能文件名冲突解决")
    
    try:
        demo_protocol_enhancement()
        demo_path_processing()
        demo_auto_path_creation()
        demo_conflict_resolution()
        
        print("\n" + "=" * 60)
        print("🎉 演示完成！所有新功能都正常工作。")
        print("=" * 60)
        print("\n💡 使用提示:")
        print("1. 接收端不再需要手动输入文件名或路径")
        print("2. 系统会自动在当前目录下重建发送端的目录结构")
        print("3. 自动处理文件名冲突和跨平台兼容性问题")
        print("4. 支持递归传输整个文件夹结构")
        
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
