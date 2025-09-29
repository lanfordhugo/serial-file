#!/usr/bin/env python3
"""
主程序入口测试
==============

测试main.py主入口程序的各种功能。
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import main
from main import SerialFileTransferApp, create_parser


class TestSerialFileTransferApp:
    """主应用程序测试类"""

    def test_init(self):
        """测试应用初始化"""
        app = SerialFileTransferApp()
        assert app.running is True

    def test_show_banner(self, capsys):
        """测试横幅显示"""
        app = SerialFileTransferApp()
        app.show_banner()

        captured = capsys.readouterr()
        assert "串口文件传输工具 v1.4.0" in captured.out
        assert "基于串口通信的可靠文件传输工具" in captured.out

    def test_show_menu(self, capsys):
        """测试菜单显示"""
        app = SerialFileTransferApp()
        app.show_menu()

        captured = capsys.readouterr()
        assert "1. 🚀 智能发送文件/文件夹" in captured.out
        assert "2. 📡 智能接收文件" in captured.out
        assert "3. 查看帮助" in captured.out
        assert "4. 退出程序" in captured.out

    @patch("builtins.input")
    def test_get_user_choice_valid(self, mock_input):
        """测试有效用户选择"""
        app = SerialFileTransferApp()
        mock_input.return_value = "1"

        choice = app.get_user_choice()
        assert choice == "1"

    @patch("builtins.input")
    def test_get_user_choice_invalid_then_valid(self, mock_input):
        """测试无效选择后重试"""
        app = SerialFileTransferApp()
        mock_input.side_effect = ["7", "0", "3"]

        choice = app.get_user_choice()
        assert choice == "3"
        assert mock_input.call_count == 3

    @patch("builtins.input")
    def test_get_user_choice_keyboard_interrupt(self, mock_input):
        """测试键盘中断处理"""
        app = SerialFileTransferApp()
        mock_input.side_effect = KeyboardInterrupt()

        choice = app.get_user_choice()
        assert choice == "4"

    @patch("builtins.input")
    def test_show_help(self, mock_input, capsys):
        """测试帮助信息显示"""
        app = SerialFileTransferApp()
        mock_input.return_value = ""  # 模拟按回车

        app.show_help()

        captured = capsys.readouterr()
        assert "帮助信息" in captured.out
        assert "文件传输模式" in captured.out
        assert "文件发送" in captured.out
        assert "文件接收" in captured.out
        assert "使用步骤" in captured.out




class TestCommandLineParser:
    """命令行参数解析测试类"""

    def test_create_parser(self):
        """测试解析器创建"""
        parser = create_parser()
        assert parser is not None
        # 解析器的prog名称可能会因运行环境而变化，只检查是否包含main或pytest
        assert "main" in parser.prog or "pytest" in parser.prog

    def test_parser_no_args(self):
        """测试无参数解析（智能模式下直接运行交互界面）"""
        parser = create_parser()
        args = parser.parse_args([])
        # 智能模式下不再有send/receive参数
        assert args is not None

    def test_parser_version(self, capsys):
        """测试版本参数"""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])

        captured = capsys.readouterr()
        assert "串口文件传输工具 v1.4.0" in captured.out


class TestMainFunction:
    """主函数测试类"""

    @patch("main.SerialFileTransferApp")
    @patch("sys.argv", ["main.py"])
    def test_main_interactive_mode(self, mock_app_class):
        """测试交互式模式（智能模式下的唯一模式）"""
        mock_app = Mock()
        mock_app_class.return_value = mock_app

        main.main()

        mock_app_class.assert_called_once()
        mock_app.run_interactive.assert_called_once()

    @patch("sys.argv", ["main.py"])
    @patch("main.SerialFileTransferApp")
    def test_main_keyboard_interrupt(self, mock_app_class, capsys):
        """测试键盘中断处理"""
        mock_app_class.side_effect = KeyboardInterrupt()

        main.main()

        captured = capsys.readouterr()
        assert "用户中断程序" in captured.out


if __name__ == "__main__":
    pytest.main([__file__])
