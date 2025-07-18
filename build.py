#!/usr/bin/env python3
"""
串口文件传输工具 - Python构建脚本
================================

这是一个用于构建串口文件传输工具可执行文件的Python脚本。
替代原有的build.bat脚本，提供更好的中文字符支持和跨平台兼容性。

主要功能：
- 环境检查（Python版本、依赖文件）
- 自动安装构建依赖（PyInstaller等）
- 清理之前的构建文件
- 交互式构建选项（单文件/目录模式）
- 执行PyInstaller构建
- 构建结果验证和测试
- 详细的中文状态反馈

使用方法：
    python build.py

作者：lanford
版本：1.0.0
创建时间：2025-01-18
"""

import sys
import os
import subprocess
import shutil
import logging
import threading
import queue
from pathlib import Path
from typing import Optional, Tuple, List, TextIO
import time
from datetime import datetime

# ============================================================================
# 常量定义
# ============================================================================

# 版本信息
SCRIPT_VERSION = "1.0.0"
SCRIPT_NAME = "串口文件传输工具构建脚本"

# 构建配置
MAIN_FILE = "main.py"
APP_NAME = "SerialFileTransfer"
REQUIREMENTS_FILE = "requirements.txt"

# 目录配置
DIST_DIR = "dist"
BUILD_DIR = "build"
SRC_DIR = "src"

# PyInstaller隐藏导入模块
HIDDEN_IMPORTS = [
    "serial_file_transfer",
    "serial",
    "serial.tools",
    "serial.tools.list_ports",
    "ymodem",
    "numpy"
]

# PyInstaller收集模块
COLLECT_ALL = [
    "serial_file_transfer",
    "serial",
    "ymodem"
]

# 颜色输出支持（Windows兼容）
class Colors:
    """控制台颜色输出类"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

    @staticmethod
    def disable_on_windows():
        """在Windows上禁用颜色输出（如果不支持）"""
        if os.name == 'nt':
            try:
                # 尝试启用Windows控制台颜色支持
                import colorama
                colorama.init()
            except ImportError:
                # 如果没有colorama，禁用颜色
                for attr in dir(Colors):
                    if not attr.startswith('_') and attr != 'disable_on_windows':
                        setattr(Colors, attr, '')

# ============================================================================
# 工具函数
# ============================================================================

def print_banner():
    """显示脚本横幅信息"""
    print("=" * 80)
    print(f"{Colors.CYAN}{Colors.BOLD}{SCRIPT_NAME} v{SCRIPT_VERSION}{Colors.END}")
    print("=" * 80)
    print(f"{Colors.YELLOW}🚀 开始构建串口文件传输工具可执行文件{Colors.END}")
    print()

def print_step(step_name: str, description: str = ""):
    """打印步骤信息"""
    print(f"{Colors.BLUE}📋 {step_name}{Colors.END}")
    if description:
        print(f"   {description}")
    print()

def print_success(message: str):
    """打印成功信息"""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message: str):
    """打印错误信息"""
    print(f"{Colors.RED}❌ 错误: {message}{Colors.END}")

def print_warning(message: str):
    """打印警告信息"""
    print(f"{Colors.YELLOW}⚠️  警告: {message}{Colors.END}")

def print_info(message: str):
    """打印信息"""
    print(f"{Colors.CYAN}ℹ️  {message}{Colors.END}")

def print_build_success():
    """打印构建成功的视觉反馈"""
    print()
    print(f"{Colors.GREEN}{Colors.BOLD}{'=' * 80}{Colors.END}")
    print(f"{Colors.GREEN}{Colors.BOLD}🎉 构建成功完成！{Colors.END}")
    print(f"{Colors.GREEN}{Colors.BOLD}{'=' * 80}{Colors.END}")
    print()

def print_build_failure():
    """打印构建失败的视觉反馈"""
    print()
    print(f"{Colors.RED}{Colors.BOLD}{'=' * 80}{Colors.END}")
    print(f"{Colors.RED}{Colors.BOLD}💥 构建失败！{Colors.END}")
    print(f"{Colors.RED}{Colors.BOLD}{'=' * 80}{Colors.END}")
    print()

def print_section_separator():
    """打印章节分隔符"""
    print(f"{Colors.BLUE}{'─' * 60}{Colors.END}")

def show_build_tips():
    """显示构建提示信息"""
    print(f"{Colors.YELLOW}💡 构建提示:{Colors.END}")
    print(f"   • 构建过程可能需要2-5分钟，请耐心等待")
    print(f"   • 如需取消构建，请按 Ctrl+C")
    print(f"   • 构建日志将保存到 logs/ 目录")
    print()

def get_system_encoding() -> str:
    """获取系统控制台编码"""
    try:
        import locale

        # Windows系统特殊处理
        if os.name == 'nt':
            try:
                # 尝试获取控制台代码页
                import ctypes
                cp = ctypes.windll.kernel32.GetConsoleOutputCP()
                if cp == 65001:  # UTF-8
                    return 'utf-8'
                elif cp == 936:  # GBK/GB2312
                    return 'gbk'
                elif cp == 950:  # Big5
                    return 'big5'
                else:
                    # 对于其他代码页，尝试使用locale
                    encoding = locale.getpreferredencoding()
                    return encoding or 'gbk'
            except:
                # 如果获取失败，使用locale
                try:
                    encoding = locale.getpreferredencoding()
                    return encoding or 'gbk'
                except:
                    return 'gbk'  # Windows默认使用GBK
        else:
            # 非Windows系统
            encoding = locale.getpreferredencoding()
            return encoding or 'utf-8'
    except:
        return 'utf-8'

def safe_decode_output(output: str, encoding: str = None) -> str:
    """安全解码输出，处理编码问题"""
    if not output:
        return ""

    if encoding is None:
        encoding = get_system_encoding()

    try:
        # 如果已经是字符串，直接返回
        if isinstance(output, str):
            return output

        # 如果是字节，尝试解码
        if isinstance(output, bytes):
            # 尝试多种编码
            encodings_to_try = [encoding, 'utf-8', 'gbk', 'cp936', 'latin1']

            for enc in encodings_to_try:
                try:
                    return output.decode(enc)
                except (UnicodeDecodeError, LookupError):
                    continue

            # 如果所有编码都失败，使用errors='replace'
            return output.decode(encoding, errors='replace')

        return str(output)
    except Exception:
        return str(output)

class ProgressIndicator:
    """构建进度指示器"""

    def __init__(self):
        """初始化进度指示器"""
        self.current_stage = ""
        self.start_time = time.time()
        self.stages = [
            "初始化构建环境",
            "分析依赖关系",
            "收集模块文件",
            "编译Python代码",
            "打包资源文件",
            "生成可执行文件",
            "优化文件大小",
            "完成构建"
        ]
        self.current_stage_index = 0

    def update_stage_from_output(self, output_line: str):
        """根据输出内容更新构建阶段"""
        output_lower = output_line.lower()

        # 根据PyInstaller的输出判断当前阶段
        if "analyzing" in output_lower or "analysis" in output_lower:
            self._set_stage(1, "分析依赖关系")
        elif "collecting" in output_lower or "collect" in output_lower:
            self._set_stage(2, "收集模块文件")
        elif "building" in output_lower or "compile" in output_lower:
            self._set_stage(3, "编译Python代码")
        elif "copying" in output_lower or "copy" in output_lower:
            self._set_stage(4, "打包资源文件")
        elif "exe" in output_lower and ("build" in output_lower or "creat" in output_lower):
            self._set_stage(5, "生成可执行文件")
        elif "strip" in output_lower or "optim" in output_lower:
            self._set_stage(6, "优化文件大小")
        elif "success" in output_lower or "complete" in output_lower:
            self._set_stage(7, "完成构建")

    def _set_stage(self, stage_index: int, stage_name: str):
        """设置当前阶段"""
        if stage_index > self.current_stage_index:
            self.current_stage_index = stage_index
            self.current_stage = stage_name
            self._show_progress()

    def _show_progress(self):
        """显示进度信息"""
        if self.current_stage:
            elapsed_time = time.time() - self.start_time
            progress_percent = (self.current_stage_index / len(self.stages)) * 100

            # 创建进度条
            bar_length = 30
            filled_length = int(bar_length * self.current_stage_index // len(self.stages))
            bar = '█' * filled_length + '░' * (bar_length - filled_length)

            print(f"\r{Colors.CYAN}📊 构建进度: [{bar}] {progress_percent:.0f}% - {self.current_stage} ({elapsed_time:.1f}s){Colors.END}", end='', flush=True)

    def finish(self):
        """完成进度显示"""
        print()  # 换行

class RealTimeOutputHandler:
    """实时输出流处理器"""

    def __init__(self, logger: logging.Logger, prefix: str = "", show_progress: bool = False):
        """
        初始化实时输出处理器

        Args:
            logger: 日志记录器
            prefix: 输出前缀
            show_progress: 是否显示进度指示器
        """
        self.logger = logger
        self.prefix = prefix
        self.output_lines = []
        self.error_lines = []
        self.system_encoding = get_system_encoding()
        self.show_progress = show_progress
        self.progress_indicator = ProgressIndicator() if show_progress else None

    def _should_display_line(self, line: str, is_error: bool = False) -> bool:
        """判断是否应该显示这一行输出"""
        if not line.strip():
            return False

        # 错误信息总是显示
        if is_error:
            return True

        line_lower = line.lower()

        # 显示重要的进度信息
        important_keywords = [
            'analyzing', 'analysis', 'collecting', 'building', 'copying',
            'exe', 'success', 'complete', 'error', 'warning', 'failed',
            'info:', 'warning:', 'error:', 'critical:'
        ]

        # 过滤掉过于详细的调试信息
        skip_keywords = [
            'debug:', 'trace:', 'verbose:', 'importing module',
            'looking for', 'found module', 'checking'
        ]

        # 检查是否包含跳过关键词
        for keyword in skip_keywords:
            if keyword in line_lower:
                return False

        # 检查是否包含重要关键词
        for keyword in important_keywords:
            if keyword in line_lower:
                return True

        # 默认显示（但可以根据需要调整）
        return len(line.strip()) > 10  # 只显示有意义的长行

    def _format_output_line(self, line: str, is_error: bool = False) -> str:
        """格式化输出行"""
        if not line.strip():
            return ""

        # 添加前缀
        formatted_line = f"   {self.prefix}{line.strip()}" if self.prefix else f"   {line.strip()}"

        # 错误信息使用红色，普通信息使用灰色
        if is_error:
            return f"{Colors.RED}{formatted_line}{Colors.END}"
        else:
            return f"{Colors.WHITE}{formatted_line}{Colors.END}"

    def _read_stream(self, stream: TextIO, output_queue: queue.Queue, is_error: bool = False):
        """读取输出流的线程函数"""
        try:
            for line in iter(stream.readline, ''):
                if line:
                    output_queue.put((line, is_error))
            stream.close()
        except Exception as e:
            output_queue.put((f"读取流异常: {e}", True))

    def run_command_with_realtime_output(
        self,
        command: List[str],
        description: str = "",
        show_command: bool = False
    ) -> Tuple[bool, str, str]:
        """
        执行命令并实时显示输出

        Args:
            command: 要执行的命令列表
            description: 命令描述
            show_command: 是否显示完整命令

        Returns:
            (成功标志, 标准输出, 错误输出)
        """
        try:
            if description:
                print_info(f"执行: {description}")

            if show_command:
                print_info(f"命令: {' '.join(command)}")

            # 启动进程
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding=self.system_encoding,
                errors='replace',
                bufsize=1,
                universal_newlines=True
            )

            # 创建输出队列
            output_queue = queue.Queue()

            # 启动读取线程
            stdout_thread = threading.Thread(
                target=self._read_stream,
                args=(process.stdout, output_queue, False)
            )
            stderr_thread = threading.Thread(
                target=self._read_stream,
                args=(process.stderr, output_queue, True)
            )

            stdout_thread.daemon = True
            stderr_thread.daemon = True
            stdout_thread.start()
            stderr_thread.start()

            # 实时处理输出
            while process.poll() is None or not output_queue.empty():
                try:
                    line, is_error = output_queue.get(timeout=0.1)

                    # 记录到相应的列表
                    if is_error:
                        self.error_lines.append(line)
                    else:
                        self.output_lines.append(line)

                    # 更新进度指示器
                    if self.progress_indicator and not is_error:
                        self.progress_indicator.update_stage_from_output(line)

                    # 格式化并显示（只显示重要信息，避免刷屏）
                    if self._should_display_line(line, is_error):
                        formatted_line = self._format_output_line(line, is_error)
                        if formatted_line:
                            if self.progress_indicator:
                                # 如果有进度指示器，先清除进度行再显示输出
                                print(f"\r{' ' * 100}\r", end='')  # 清除进度行
                                print(formatted_line)
                                self.progress_indicator._show_progress()  # 重新显示进度
                            else:
                                print(formatted_line)

                    # 记录到日志
                    if is_error:
                        self.logger.error(line.strip())
                    else:
                        self.logger.info(line.strip())

                except queue.Empty:
                    continue
                except Exception as e:
                    self.logger.error(f"处理输出异常: {e}")

            # 等待进程结束
            return_code = process.wait()

            # 等待线程结束
            stdout_thread.join(timeout=1)
            stderr_thread.join(timeout=1)

            # 合并输出
            stdout_output = ''.join(self.output_lines)
            stderr_output = ''.join(self.error_lines)

            success = return_code == 0
            return success, stdout_output, stderr_output

        except Exception as e:
            error_msg = f"命令执行异常: {e}"
            self.logger.error(error_msg)
            return False, "", error_msg

def run_command(command: List[str], description: str = "", check: bool = True) -> Tuple[bool, str]:
    """
    执行系统命令（传统模式，用于快速命令）

    Args:
        command: 要执行的命令列表
        description: 命令描述
        check: 是否检查返回码

    Returns:
        (成功标志, 输出信息)
    """
    try:
        if description:
            print_info(f"执行: {description}")

        # 获取系统编码
        system_encoding = get_system_encoding()

        # 执行命令
        result = subprocess.run(
            command,
            capture_output=True,
            text=False,  # 使用字节模式，手动处理编码
            timeout=30   # 添加超时防止卡死
        )

        # 手动解码输出
        stdout_output = safe_decode_output(result.stdout, system_encoding)
        stderr_output = safe_decode_output(result.stderr, system_encoding)

        if check and result.returncode != 0:
            error_msg = f"命令执行失败: {' '.join(command)}\n错误输出: {stderr_output}"
            return False, error_msg

        return True, stdout_output

    except subprocess.TimeoutExpired:
        error_msg = f"命令执行超时: {' '.join(command)}"
        return False, error_msg
    except Exception as e:
        error_msg = f"命令执行异常: {e}"
        return False, error_msg

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小显示"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

# ============================================================================
# 主要功能类
# ============================================================================

class BuildManager:
    """构建管理器类"""

    def __init__(self):
        """初始化构建管理器"""
        self.project_root = Path.cwd()
        self.build_type = "onefile"  # 默认单文件模式
        self.test_mode = False  # 测试模式标志

        # 初始化颜色支持
        Colors.disable_on_windows()

        # 初始化日志记录
        self.setup_logging()

    def setup_logging(self):
        """设置日志记录"""
        # 创建logs目录
        log_dir = self.project_root / "logs"
        log_dir.mkdir(exist_ok=True)

        # 设置日志文件名（包含时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"build_{timestamp}.log"

        # 配置日志记录器
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )

        self.logger = logging.getLogger(__name__)
        self.logger.info(f"构建日志开始记录: {log_file}")

    def log_and_print_error(self, message: str):
        """记录并打印错误信息"""
        self.logger.error(message)
        print_error(message)

    def log_and_print_warning(self, message: str):
        """记录并打印警告信息"""
        self.logger.warning(message)
        print_warning(message)

    def log_and_print_info(self, message: str):
        """记录并打印信息"""
        self.logger.info(message)
        print_info(message)
    
    def check_environment(self) -> bool:
        """检查构建环境"""
        print_step("环境检查", "检查Python版本和必要文件...")

        # 检查Python版本
        python_version = sys.version_info
        if python_version < (3, 7):
            print_error(f"Python版本过低: {python_version.major}.{python_version.minor}.{python_version.micro}")
            print_error("需要Python 3.7或更高版本")
            return False

        print_success(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")

        # 检查main.py文件
        main_file_path = self.project_root / MAIN_FILE
        if not main_file_path.exists():
            print_error(f"找不到主程序文件: {MAIN_FILE}")
            print_error("请确保在项目根目录下运行此脚本")
            return False

        print_success(f"找到主程序文件: {MAIN_FILE}")

        # 检查src目录
        src_dir_path = self.project_root / SRC_DIR
        if not src_dir_path.exists():
            print_error(f"找不到源代码目录: {SRC_DIR}")
            return False

        print_success(f"找到源代码目录: {SRC_DIR}")

        # 检查requirements.txt文件（可选）
        requirements_path = self.project_root / REQUIREMENTS_FILE
        if requirements_path.exists():
            print_success(f"找到依赖文件: {REQUIREMENTS_FILE}")
        else:
            print_warning(f"未找到依赖文件: {REQUIREMENTS_FILE}")

        print_success("环境检查完成")
        return True

    def install_dependencies(self) -> bool:
        """安装构建依赖"""
        print_step("依赖管理", "检查并安装必要的构建依赖...")

        # 检查PyInstaller是否已安装
        print_info("检查PyInstaller...")
        success, output = run_command([sys.executable, "-c", "import PyInstaller"], check=False)

        if not success:
            print_info("PyInstaller未安装，正在安装...")
            success, output = run_command(
                [sys.executable, "-m", "pip", "install", "pyinstaller"],
                "安装PyInstaller"
            )
            if not success:
                print_error("PyInstaller安装失败")
                print_error(output)
                return False
            print_success("PyInstaller安装成功")
        else:
            print_success("PyInstaller已安装")

        # 安装项目依赖
        requirements_path = self.project_root / REQUIREMENTS_FILE
        if requirements_path.exists():
            print_info(f"安装项目依赖: {REQUIREMENTS_FILE}")
            success, output = run_command(
                [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)],
                f"安装{REQUIREMENTS_FILE}中的依赖"
            )
            if not success:
                print_error("项目依赖安装失败")
                print_error(output)
                return False
            print_success("项目依赖安装成功")
        else:
            print_info("跳过项目依赖安装（未找到requirements.txt）")

        print_success("依赖管理完成")
        return True

    def clean_previous_builds(self) -> bool:
        """清理之前的构建文件"""
        print_step("清理构建", "清理之前的构建文件和目录...")

        cleaned_items = []

        # 清理dist目录
        dist_path = self.project_root / DIST_DIR
        if dist_path.exists():
            try:
                shutil.rmtree(dist_path)
                cleaned_items.append(DIST_DIR)
                print_success(f"已删除目录: {DIST_DIR}")
            except Exception as e:
                print_error(f"删除{DIST_DIR}目录失败: {e}")
                return False

        # 清理build目录
        build_path = self.project_root / BUILD_DIR
        if build_path.exists():
            try:
                shutil.rmtree(build_path)
                cleaned_items.append(BUILD_DIR)
                print_success(f"已删除目录: {BUILD_DIR}")
            except Exception as e:
                print_error(f"删除{BUILD_DIR}目录失败: {e}")
                return False

        # 清理.spec文件
        spec_files = list(self.project_root.glob("*.spec"))
        for spec_file in spec_files:
            try:
                spec_file.unlink()
                cleaned_items.append(spec_file.name)
                print_success(f"已删除文件: {spec_file.name}")
            except Exception as e:
                print_error(f"删除{spec_file.name}失败: {e}")
                return False

        if cleaned_items:
            print_success(f"清理完成，共删除 {len(cleaned_items)} 项")
        else:
            print_info("没有需要清理的文件")

        return True

    def get_build_options(self) -> bool:
        """获取构建选项"""
        print_step("构建选项", "选择构建类型...")

        # 测试模式自动选择
        if self.test_mode:
            self.build_type = "onefile"
            print_success("测试模式: 自动选择单文件模式")
            return True

        print("构建选项:")
        print(f"{Colors.CYAN}1. 单文件模式 (推荐){Colors.END} - 生成一个独立的.exe文件")
        print(f"{Colors.CYAN}2. 目录模式{Colors.END} - 启动更快，生成多个文件")
        print()

        while True:
            try:
                choice = input("请选择构建类型 (1 或 2): ").strip()

                if choice == "1":
                    self.build_type = "onefile"
                    print_success("已选择: 单文件模式")
                    break
                elif choice == "2":
                    self.build_type = "onedir"
                    print_success("已选择: 目录模式")
                    break
                else:
                    print_warning("请输入 1 或 2")

            except KeyboardInterrupt:
                print_error("用户取消选择")
                return False
            except Exception as e:
                print_error(f"输入处理异常: {e}")
                return False

        return True

    def run_pyinstaller(self) -> bool:
        """执行PyInstaller构建"""
        print_step("PyInstaller构建", f"使用{self.build_type}模式构建可执行文件...")

        # 构建PyInstaller命令
        command = [
            sys.executable, "-m", "PyInstaller",
            f"--{self.build_type}",
            "--console",
            "--name", APP_NAME,
            "--add-data", f"{SRC_DIR}{os.pathsep}{SRC_DIR}",
            "--noconfirm"
        ]

        # 添加隐藏导入
        for module in HIDDEN_IMPORTS:
            command.extend(["--hidden-import", module])

        # 添加收集模块
        for module in COLLECT_ALL:
            command.extend(["--collect-all", module])

        # 添加主文件
        command.append(MAIN_FILE)

        # 显示构建命令（调试用）
        print_info("PyInstaller命令:")
        print(f"   {' '.join(command)}")
        print()

        # 执行构建
        start_time = time.time()

        # 测试模式跳过实际构建
        if self.test_mode:
            print_info("测试模式: 跳过实际PyInstaller构建")
            # 创建模拟的输出文件用于测试
            dist_dir = self.project_root / DIST_DIR
            dist_dir.mkdir(exist_ok=True)
            if self.build_type == "onefile":
                mock_exe = dist_dir / f"{APP_NAME}.exe"
            else:
                app_dir = dist_dir / APP_NAME
                app_dir.mkdir(exist_ok=True)
                mock_exe = app_dir / f"{APP_NAME}.exe"

            # 创建一个模拟的exe文件
            mock_exe.write_text("Mock executable for testing", encoding='utf-8')
            print_success("测试模式: 已创建模拟可执行文件")
        else:
            # 使用实时输出处理器
            print_info("开始构建，请耐心等待...")
            print_info("构建过程中将显示实时进度和关键信息：")
            print()

            # 创建实时输出处理器（启用进度指示器）
            output_handler = RealTimeOutputHandler(
                self.logger,
                "PyInstaller: ",
                show_progress=True
            )

            # 执行构建并显示实时输出
            success, stdout_output, stderr_output = output_handler.run_command_with_realtime_output(
                command,
                "执行PyInstaller构建",
                show_command=False
            )

            # 完成进度显示
            if output_handler.progress_indicator:
                output_handler.progress_indicator.finish()

            print()  # 添加空行分隔

            if not success:
                self._handle_build_failure(stderr_output, stdout_output)
                return False

        end_time = time.time()
        build_time = end_time - start_time

        print_success(f"PyInstaller构建完成，耗时: {build_time:.1f}秒")
        return True

    def _handle_build_failure(self, stderr_output: str, stdout_output: str):
        """处理构建失败"""
        print_build_failure()

        # 分析错误类型
        error_type = self._analyze_error_type(stderr_output, stdout_output)

        print_error(f"构建失败类型: {error_type}")
        print()

        # 显示错误详情
        if stderr_output:
            print_error("错误详情:")
            error_lines = stderr_output.strip().split('\n')
            # 显示最后10行错误信息
            for line in error_lines[-10:]:
                if line.strip():
                    print(f"   {Colors.RED}{line.strip()}{Colors.END}")
            print()

        # 提供解决建议
        self._provide_error_solutions(error_type)

        # 询问是否重试
        self._offer_retry_options()

    def _analyze_error_type(self, stderr_output: str, stdout_output: str) -> str:
        """分析错误类型"""
        combined_output = (stderr_output + stdout_output).lower()

        if "modulenotfounderror" in combined_output or "no module named" in combined_output:
            return "缺少依赖模块"
        elif "permission denied" in combined_output or "access denied" in combined_output:
            return "权限不足"
        elif "memory" in combined_output and "error" in combined_output:
            return "内存不足"
        elif "disk" in combined_output and ("full" in combined_output or "space" in combined_output):
            return "磁盘空间不足"
        elif "timeout" in combined_output:
            return "构建超时"
        elif "syntax" in combined_output and "error" in combined_output:
            return "代码语法错误"
        elif "import" in combined_output and "error" in combined_output:
            return "导入错误"
        else:
            return "未知错误"

    def _provide_error_solutions(self, error_type: str):
        """提供错误解决方案"""
        print_info("建议的解决方案:")

        solutions = {
            "缺少依赖模块": [
                "检查 requirements.txt 文件是否包含所有依赖",
                "运行 'pip install -r requirements.txt' 安装依赖",
                "确认虚拟环境已正确激活"
            ],
            "权限不足": [
                "以管理员身份运行命令提示符",
                "检查文件和目录的写入权限",
                "关闭可能占用文件的程序（如杀毒软件）"
            ],
            "内存不足": [
                "关闭其他占用内存的程序",
                "尝试使用 --onedir 模式而非 --onefile",
                "增加虚拟内存设置"
            ],
            "磁盘空间不足": [
                "清理磁盘空间，至少保留2GB可用空间",
                "删除之前的构建文件",
                "将项目移动到空间更大的磁盘"
            ],
            "构建超时": [
                "检查网络连接是否正常",
                "重新运行构建脚本",
                "尝试在网络较好的环境下构建"
            ],
            "代码语法错误": [
                "检查 main.py 和相关源代码文件",
                "运行 'python main.py' 测试代码是否正常",
                "修复语法错误后重新构建"
            ],
            "导入错误": [
                "检查模块导入路径是否正确",
                "确认所有依赖模块已正确安装",
                "检查 PYTHONPATH 环境变量"
            ],
            "未知错误": [
                "查看完整的错误日志文件",
                "尝试重新运行构建脚本",
                "检查 PyInstaller 版本是否兼容"
            ]
        }

        for i, solution in enumerate(solutions.get(error_type, solutions["未知错误"]), 1):
            print(f"   {i}. {solution}")
        print()

    def _offer_retry_options(self):
        """提供重试选项"""
        print_info("您可以选择:")
        print("   1. 修复问题后重新运行构建脚本")
        print("   2. 查看详细日志文件进行诊断")
        print("   3. 尝试使用不同的构建选项")
        print()

        # 显示日志文件位置
        log_files = list((self.project_root / "logs").glob("build_*.log"))
        if log_files:
            latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
            print_info(f"最新日志文件: {latest_log}")
        print()

    def verify_build_result(self) -> bool:
        """验证构建结果"""
        print_step("构建验证", "检查构建结果...")

        # 确定可执行文件路径
        if self.build_type == "onefile":
            exe_path = self.project_root / DIST_DIR / f"{APP_NAME}.exe"
        else:
            exe_path = self.project_root / DIST_DIR / APP_NAME / f"{APP_NAME}.exe"

        # 检查可执行文件是否存在
        if not exe_path.exists():
            print_error(f"构建失败 - 可执行文件不存在: {exe_path}")
            return False

        print_success(f"可执行文件已生成: {exe_path}")

        # 显示文件大小
        try:
            file_size = exe_path.stat().st_size
            print_info(f"文件大小: {format_file_size(file_size)}")
        except Exception as e:
            print_warning(f"无法获取文件大小: {e}")

        # 测试可执行文件
        print_info("测试可执行文件...")
        success, output = run_command(
            [str(exe_path), "--version"],
            "测试可执行文件版本信息",
            check=False
        )

        if success:
            print_success("可执行文件测试通过")
            if output.strip():
                print_info(f"版本信息: {output.strip()}")
        else:
            print_warning("可执行文件测试失败，但文件已生成")
            print_warning("这可能是正常的，取决于程序的命令行参数处理")

        print_success("构建验证完成")
        return True

    def cleanup_and_summary(self):
        """构建后清理和总结"""
        print_step("构建清理", "清理临时文件...")

        # 清理build目录（保留dist目录）
        build_path = self.project_root / BUILD_DIR
        if build_path.exists():
            try:
                shutil.rmtree(build_path)
                print_success(f"已清理临时目录: {BUILD_DIR}")
            except Exception as e:
                print_warning(f"清理临时目录失败: {e}")

        # 显示构建总结
        print()
        print("=" * 80)
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 构建成功完成！{Colors.END}")
        print("=" * 80)

        # 显示输出文件信息
        if self.build_type == "onefile":
            exe_path = self.project_root / DIST_DIR / f"{APP_NAME}.exe"
            print(f"{Colors.CYAN}📁 输出文件: {exe_path}{Colors.END}")
        else:
            dist_dir = self.project_root / DIST_DIR / APP_NAME
            print(f"{Colors.CYAN}📁 输出目录: {dist_dir}{Colors.END}")
            exe_path = dist_dir / f"{APP_NAME}.exe"
            print(f"{Colors.CYAN}📄 可执行文件: {exe_path}{Colors.END}")

        # 使用建议
        print()
        print(f"{Colors.YELLOW}💡 使用建议:{Colors.END}")
        print(f"   • 可以直接运行生成的可执行文件")
        print(f"   • 建议在目标机器上测试程序功能")
        print(f"   • 如需分发，请包含整个输出目录（目录模式）")
        print()

    def run(self):
        """运行完整的构建流程"""
        try:
            print_banner()

            # 执行构建步骤
            if not self.check_environment():
                return False

            if not self.install_dependencies():
                return False

            if not self.clean_previous_builds():
                return False

            if not self.get_build_options():
                return False

            if not self.run_pyinstaller():
                return False

            if not self.verify_build_result():
                return False

            self.cleanup_and_summary()
            return True

        except KeyboardInterrupt:
            print_error("用户中断构建过程")
            return False
        except Exception as e:
            print_error(f"构建过程发生异常: {e}")
            return False

def main():
    """主函数"""
    try:
        # 检查是否为测试模式
        test_mode = len(sys.argv) > 1 and sys.argv[1] == "--test"

        # 创建构建管理器并运行
        builder = BuildManager()
        builder.test_mode = test_mode  # 设置测试模式
        success = builder.run()

        if success:
            print_success("🎉 构建完成！请检查 'dist' 目录中的可执行文件。")
            if not test_mode:
                input("\n按回车键退出...")
        else:
            print_error("💥 构建失败！请检查上述错误信息。")
            if not test_mode:
                input("\n按回车键退出...")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n👋 用户中断程序，退出")
        sys.exit(0)
    except Exception as e:
        print_error(f"程序异常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
