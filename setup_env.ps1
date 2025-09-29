# 串口文件传输工具 - PowerShell环境配置脚本
# 设置UTF-8编码环境，解决中文编码问题

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "串口文件传输工具 - 环境配置" -ForegroundColor Cyan  
Write-Host "===============================================" -ForegroundColor Cyan

# 设置Python UTF-8模式
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

# 设置控制台输出编码为UTF-8
$OutputEncoding = [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "✅ 已设置Python UTF-8编码模式" -ForegroundColor Green
Write-Host "✅ 已设置PowerShell UTF-8输出编码" -ForegroundColor Green
Write-Host "✅ 环境配置完成" -ForegroundColor Green

Write-Host ""
Write-Host "环境变量设置：" -ForegroundColor Yellow
Write-Host "  PYTHONIOENCODING=$env:PYTHONIOENCODING" -ForegroundColor White
Write-Host "  PYTHONUTF8=$env:PYTHONUTF8" -ForegroundColor White

Write-Host ""
Write-Host "💡 使用建议：" -ForegroundColor Yellow
Write-Host "  1. 在当前PowerShell窗口中运行开发工具" -ForegroundColor White
Write-Host "  2. 或者将环境变量添加到用户/系统环境变量中" -ForegroundColor White
Write-Host "  3. 可以将此脚本添加到PowerShell配置文件中" -ForegroundColor White

# 验证编码设置
Write-Host ""
Write-Host "🔍 验证编码设置：" -ForegroundColor Yellow
python -c "import locale; import sys; print(f'系统默认编码: {locale.getpreferredencoding()}'); print(f'文件系统编码: {sys.getfilesystemencoding()}'); print(f'标准输出编码: {sys.stdout.encoding}')"
