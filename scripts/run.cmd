@echo off
cd /d "%~dp0\.."
if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv
call .venv\Scripts\activate.bat
pip install -r requirements.txt
set PYTHONPATH=%CD%\src
python main.py
