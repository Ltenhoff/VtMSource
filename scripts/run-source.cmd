@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

where py >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python is not installed.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 goto :failed
)

call ".venv\Scripts\activate.bat"
python -m pip install -r requirements.txt
if errorlevel 1 goto :failed

set "PYTHONPATH=%CD%\src"
python main.py
if errorlevel 1 goto :failed
exit /b 0

:failed
echo.
echo RUN FAILED.
pause
exit /b 1
