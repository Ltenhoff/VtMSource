@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0bootstrap-and-build.ps1"
if errorlevel 1 pause
