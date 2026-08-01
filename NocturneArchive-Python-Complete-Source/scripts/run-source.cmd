@echo off
setlocal
set PYTHONPATH=%~dp0..\src
if exist "%~dp0..\.venv\Scripts\python.exe" (
  "%~dp0..\.venv\Scripts\python.exe" "%~dp0..\main.py"
) else (
  python "%~dp0..\main.py"
)
if errorlevel 1 pause
