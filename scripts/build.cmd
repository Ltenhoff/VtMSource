@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

echo ==========================================
echo Nocturne Archive - New PY Version
echo ==========================================
echo Project: %CD%
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo ERROR: The Windows Python launcher "py" is not installed.
    echo Install Python 3.12 or newer from python.org.
    echo Enable "Add Python to PATH" during installation.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating isolated build environment...
    py -3 -m venv .venv
    if errorlevel 1 goto :failed
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :failed

echo Installing requirements...
python -m pip install --upgrade pip
if errorlevel 1 goto :failed

python -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo Building single-file Windows executable...
python -m PyInstaller --noconfirm --clean NocturneArchive.spec
if errorlevel 1 goto :failed

if not exist "dist\NocturneArchive.exe" (
    echo ERROR: The build process ended without creating the EXE.
    goto :failed
)

echo.
echo SUCCESS
echo EXE: %CD%\dist\NocturneArchive.exe
echo.
pause
exit /b 0

:failed
echo.
echo BUILD FAILED. Review the error above.
echo.
pause
exit /b 1
