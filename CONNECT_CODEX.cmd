@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONDONTWRITEBYTECODE=1"
set "TEMP=%~dp0temp"
set "TMP=%~dp0temp"
if not exist "%~dp0runtime\venv\Scripts\python.exe" (
  echo 缺少项目运行环境，请先按 README 安装依赖。
  pause
  exit /b 1
)
"%~dp0runtime\venv\Scripts\python.exe" -B "%~dp0scripts\codex_connection.py"
if errorlevel 1 pause
endlocal
