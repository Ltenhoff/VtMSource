@echo off
setlocal
cd /d "%~dp0\.."
echo ==========================================
echo Nocturne Archive - New PY Version
echo ==========================================
where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python launcher "py" was not found.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto :fail
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto :fail
python -m pip install -r requirements.txt
if errorlevel 1 goto :fail
python -m PyInstaller --noconfirm --clean NocturneArchive.spec
if errorlevel 1 goto :fail
if not exist "dist\NocturneArchive.exe" goto :fail
echo.
echo SUCCESS: dist\NocturneArchive.exe
pause
exit /b 0
:fail
echo.
echo BUILD FAILED.
pause
exit /b 1
