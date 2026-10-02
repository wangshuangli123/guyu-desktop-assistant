@echo off
setlocal
cd /d "%~dp0"
set "TEMP=%~dp0temp"
set "TMP=%~dp0temp"
set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONUTF8=1"
"%~dp0runtime\venv\Scripts\python.exe" "%~dp0tests\run_all.py"
set "RESULT=%ERRORLEVEL%"
echo Verification exit code: %RESULT%
echo Results: STATUS.json and logs directory.
pause
exit /b %RESULT%
