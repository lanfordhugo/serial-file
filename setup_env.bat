@echo off
REM 串口文件传输工具 - 环境配置脚本
REM 设置UTF-8编码环境，解决中文编码问题

echo ===============================================
echo 串口文件传输工具 - 环境配置
echo ===============================================

REM 设置Python UTF-8模式
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

REM 设置控制台代码页为UTF-8
chcp 65001 >nul 2>&1

echo ✅ 已设置Python UTF-8编码模式
echo ✅ 已设置控制台UTF-8代码页
echo ✅ 环境配置完成

echo.
echo 环境变量设置：
echo   PYTHONIOENCODING=%PYTHONIOENCODING%
echo   PYTHONUTF8=%PYTHONUTF8%

echo.
echo 💡 使用建议：
echo   1. 在当前命令行窗口中运行开发工具
echo   2. 或者将环境变量添加到系统环境变量中
echo   3. 重启命令行窗口后环境变量会失效

pause
