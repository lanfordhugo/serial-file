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
        assert "串口文件传输工具 v1.1.0" in captured.out
        assert "基于串口通信的可靠文件传输工具" in captured.out

    def test_show_menu(self, capsys):
        """测试菜单显示"""
        app = SerialFileTransferApp()
        app.show_menu()

        captured = capsys.readouterr()
        assert "1. 🚀 智能发送文件/文件夹 (推荐)" in captured.out
        assert "2. 📡 智能接收文件 (推荐)" in captured.out
        assert "3. 发送文件/文件夹 (手动模式)" in captured.out
        assert "4. 接收文件 (手动模式)" in captured.out
        assert "5. 查看帮助" in captured.out
        assert "6. 退出程序" in captured.out

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
        mock_input.side_effect = ["7", "0", "5"]

        choice = app.get_user_choice()
        assert choice == "5"
        assert mock_input.call_count == 3

    @patch("builtins.input")
    def test_get_user_choice_keyboard_interrupt(self, mock_input):
        """测试键盘中断处理"""
        app = SerialFileTransferApp()
        mock_input.side_effect = KeyboardInterrupt()

        choice = app.get_user_choice()
        assert choice == "6"

    @patch("builtins.input")
    def test_show_help(self, mock_input, capsys):
        """测试帮助信息显示"""
        app = SerialFileTransferApp()
        mock_input.return_value = ""  # 模拟按回车

        app.show_help()

        captured = capsys.readouterr()
        assert "帮助信息" in captured.out
        assert "📁 发送文件/文件夹" in captured.out
        assert "📥 接收文件" in captured.out
        assert "🔧 使用步骤" in captured.out

    @patch("main.FileTransferCLI.send")
    def test_handle_send_success(self, mock_send, capsys):
        """测试发送操作成功"""
        app = SerialFileTransferApp()
        mock_send.return_value = True

        app.handle_send()

        captured = capsys.readouterr()
        assert "📤 发送文件/文件夹" in captured.out
        assert "✅ 发送操作完成" in captured.out
        mock_send.assert_called_once()

    @patch("main.FileTransferCLI.send")
    def test_handle_send_failure(self, mock_send, capsys):
        """测试发送操作失败"""
        app = SerialFileTransferApp()
        mock_send.return_value = False

        app.handle_send()

        captured = capsys.readouterr()
        assert "❌ 发送操作失败" in captured.out
        mock_send.assert_called_once()

    @patch("main.FileTransferCLI.send")
    def test_handle_send_exception(self, mock_send, capsys):
        """测试发送操作异常"""
        app = SerialFileTransferApp()
        mock_send.side_effect = Exception("测试异常")

        app.handle_send()

        captured = capsys.readouterr()
        assert "💥 发送操作异常" in captured.out
        assert "测试异常" in captured.out
        mock_send.assert_called_once()

    @patch("main.FileTransferCLI.receive")
    def test_handle_receive_success(self, mock_receive, capsys):
        """测试接收操作成功"""
        app = SerialFileTransferApp()
        mock_receive.return_value = True

        app.handle_receive()

        captured = capsys.readouterr()
        assert "📥 接收文件" in captured.out
        assert "✅ 接收操作完成" in captured.out
        mock_receive.assert_called_once()

    @patch("main.FileTransferCLI.receive")
    def test_handle_receive_failure(self, mock_receive, capsys):
        """测试接收操作失败"""
        app = SerialFileTransferApp()
        mock_receive.return_value = False

        app.handle_receive()

        captured = capsys.readouterr()
        assert "❌ 接收操作失败" in captured.out
        mock_receive.assert_called_once()


class TestCommandLineParser:
    """命令行参数解析测试类"""

    def test_create_parser(self):
        """测试解析器创建"""
        parser = create_parser()
        assert parser is not None
        # 解析器的prog名称可能会因运行环境而变化，只检查是否包含main或pytest
        assert "main" in parser.prog or "pytest" in parser.prog

    def test_parser_no_args(self):
        """测试无参数解析"""
        parser = create_parser()
        args = parser.parse_args([])

        assert not args.send
        assert not args.receive

    def test_parser_send_arg(self):
        """测试发送参数"""
        parser = create_parser()
        args = parser.parse_args(["--send"])

        assert args.send is True
        assert args.receive is False

    def test_parser_receive_arg(self):
        """测试接收参数"""
        parser = create_parser()
        args = parser.parse_args(["--receive"])

        assert args.receive is True
        assert args.send is False

    def test_parser_mutually_exclusive(self):
        """测试互斥参数"""
        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["--send", "--receive"])


class TestMainFunction:
    """主函数测试类"""

    @patch("main.SerialFileTransferApp")
    @patch("sys.argv", ["main.py"])
    def test_main_interactive_mode(self, mock_app_class):
        """测试交互式模式"""
        mock_app = Mock()
        mock_app_class.return_value = mock_app

        main.main()

        mock_app_class.assert_called_once()
        mock_app.run_interactive.assert_called_once()

    @patch("main.SerialFileTransferApp")
    @patch("sys.argv", ["main.py", "--send"])
    def test_main_send_mode(self, mock_app_class):
        """测试发送模式"""
        mock_app = Mock()
        mock_app_class.return_value = mock_app

        main.main()

        mock_app_class.assert_called_once()
        mock_app.run_send_mode.assert_called_once()

    @patch("main.SerialFileTransferApp")
    @patch("sys.argv", ["main.py", "--receive"])
    def test_main_receive_mode(self, mock_app_class):
        """测试接收模式"""
        mock_app = Mock()
        mock_app_class.return_value = mock_app

        main.main()

        mock_app_class.assert_called_once()
        mock_app.run_receive_mode.assert_called_once()

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
