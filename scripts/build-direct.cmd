@echo off
cd /d "%~dp0\.."
python -m PyInstaller --noconfirm --clean NocturneArchive.spec
if errorlevel 1 (
  echo BUILD FAILED
  pause
  exit /b 1
)
if not exist "dist\NocturneArchive.exe" (
  echo BUILD FAILED: EXE not found
  pause
  exit /b 1
)
echo SUCCESS: dist\NocturneArchive.exe
pause
