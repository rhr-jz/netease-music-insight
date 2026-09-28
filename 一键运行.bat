@echo off
chcp 65001 >nul
title Music Insight
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo 未找到 Python。请安装 Python 3.10 或更新版本，并勾选 Add Python to PATH。
  echo 也可以从 GitHub Releases 下载 EXE 版，无需安装 Python。
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/2] 首次运行：创建独立运行环境...
  python -m venv .venv
  if errorlevel 1 goto setup_error
)

".venv\Scripts\python.exe" -c "import requests, qrcode, PIL, qqmusic_api" >nul 2>nul
if errorlevel 1 (
  echo [2/2] 安装 Python 依赖...
  ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
  if errorlevel 1 goto setup_error
)

".venv\Scripts\python.exe" run.py %*
set EXIT_CODE=%ERRORLEVEL%
echo.
pause
exit /b %EXIT_CODE%

:setup_error
echo 安装失败。请检查网络、磁盘空间和文件夹写入权限后重试。
pause
exit /b 1
