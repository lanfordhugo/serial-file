@echo off
REM ============================================================================
REM PyInstaller Build Script for Serial File Transfer Tool
REM ============================================================================
REM Simple, practical build script that just works
REM ============================================================================

setlocal enabledelayedexpansion

echo ============================================================================
echo Serial File Transfer Tool - Build Script
echo ============================================================================
echo.

REM Basic checks
echo Checking environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not installed
    pause & exit /b 1
)

if not exist "main.py" (
    echo ERROR: main.py not found
    pause & exit /b 1
)

REM Install PyInstaller if needed
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Install dependencies
if exist "requirements.txt" (
    echo Installing dependencies...
    pip install -r requirements.txt
)

REM Clean previous builds
echo Cleaning previous builds...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "*.spec" del "*.spec"

REM Ask user for build type
echo.
echo Build options:
echo 1. Single file (recommended) - One .exe file
echo 2. Directory - Faster startup, multiple files
echo.
set /p choice="Choose (1 or 2): "

if "%choice%"=="2" (
    set BUILD_TYPE=--onedir
    echo Building directory distribution...
) else (
    set BUILD_TYPE=--onefile
    echo Building single file executable...
)

REM Build
echo.
echo Running PyInstaller...
python -m PyInstaller %BUILD_TYPE% ^
    --console ^
    --name "SerialFileTransfer" ^
    --add-data "src;src" ^
    --hidden-import "serial_file_transfer" ^
    --hidden-import "serial" ^
    --hidden-import "serial.tools" ^
    --hidden-import "serial.tools.list_ports" ^
    --hidden-import "ymodem" ^
    --hidden-import "numpy" ^
    --collect-all "serial_file_transfer" ^
    --collect-all "serial" ^
    --collect-all "ymodem" ^
    --noconfirm ^
    main.py

REM Check result
if "%choice%"=="2" (
    set EXE_PATH=dist\SerialFileTransfer\SerialFileTransfer.exe
) else (
    set EXE_PATH=dist\SerialFileTransfer.exe
)

if exist "!EXE_PATH!" (
    echo.
    echo SUCCESS! Executable created: !EXE_PATH!
    
    REM Show file size
    for %%A in ("!EXE_PATH!") do (
        set /a SIZE_MB=%%~zA/1048576
        echo File size: %%~zA bytes (~!SIZE_MB! MB)
    )
    
    REM Test it automatically
    echo.
    echo Testing executable...
    "!EXE_PATH!" --version
    if errorlevel 1 (
        echo WARNING: Executable test failed
    ) else (
        echo Test completed successfully
    )

    REM Cleanup
    if exist "build" rmdir /s /q "build"

    echo.
    echo Build completed! Check the 'dist' folder.
    pause
    goto :eof

) else (
    echo ERROR: Build failed - executable not found
    pause & exit /b 1
)


