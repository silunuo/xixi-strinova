@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title 汐汐小桌宠
set "XIXI_PYTHON_ARGS="

if exist "%~dp0.venv\Scripts\python.exe" (
    set "XIXI_PYTHON=%~dp0.venv\Scripts\python.exe"
    goto python_ready
)
if exist "%~dp0venv\Scripts\python.exe" (
    set "XIXI_PYTHON=%~dp0venv\Scripts\python.exe"
    goto python_ready
)
where py >nul 2>nul
if not errorlevel 1 (
    set "XIXI_PYTHON=py"
    set "XIXI_PYTHON_ARGS=-3"
    goto python_ready
)
where python >nul 2>nul
if not errorlevel 1 (
    set "XIXI_PYTHON=python"
    goto python_ready
)
goto need_python

:python_ready
"%XIXI_PYTHON%" %XIXI_PYTHON_ARGS% -c "import sys; sys.exit(sys.version_info < (3, 8))" >nul 2>nul
if errorlevel 1 goto need_python
"%XIXI_PYTHON%" %XIXI_PYTHON_ARGS% -c "import PyQt5, numpy, pygame, PIL" >nul 2>nul
if errorlevel 1 (
    echo.
    echo 缺少运行依赖，请在 PowerShell 执行下面的命令后重新启动：
    echo.
    echo   ^& "%XIXI_PYTHON%" %XIXI_PYTHON_ARGS% -m pip install -r "%~dp0requirements.txt"
    echo.
    pause
    exit /b 1
)
"%XIXI_PYTHON%" %XIXI_PYTHON_ARGS% "%~dp0pet_qt.py"
if errorlevel 1 (
    pause
    exit /b 1
)
exit /b 0

:need_python
echo.
echo 请先安装 Python 3.8 或以上版本：https://www.python.org/downloads/
echo 安装时勾选 Add Python to PATH，完成后重新双击本文件。
echo 也可以在项目的 .venv 或 venv 目录中准备 Python 环境。
echo.
pause
exit /b 1
