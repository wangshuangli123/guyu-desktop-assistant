@echo off
setlocal
cd /d "%~dp0"
set "TEMP=%~dp0temp"
set "TMP=%~dp0temp"
set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONUTF8=1"
if not exist "%~dp0runtime\venv\Scripts\pythonw.exe" (
  echo Local Python environment missing. See START_HERE.txt.
  pause
  exit /b 1
)
start "" "%~dp0runtime\venv\Scripts\pythonw.exe" "%~dp0gui.py"
endlocal
