@echo off
setlocal
set DATA=%~dp0..\NocturneArchive.Data
if exist "%DATA%" (
  echo This permanently removes local campaigns, PDF copies, IndexedDB, and browser data.
  choice /M "Delete %DATA%"
  if errorlevel 2 exit /b 0
  rmdir /S /Q "%DATA%"
)
echo Data folder is clean.
pause
