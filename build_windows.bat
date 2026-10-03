@echo off
rem Copyright (c) 2026 GANOMABI / amiinarii.
setlocal
cd /d "%~dp0"
py -3 -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
py -3 build_windows.py
if errorlevel 1 exit /b 1
echo.
echo Ready: dist\GanoV-Cache-Switch.exe
pause
