@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
  echo Python 3.10+ must be installed and added to PATH.
  pause
  exit /b 1
)
echo Starting OutcomeOS at http://127.0.0.1:8766
start "" "http://127.0.0.1:8766"
python main.py
pause
