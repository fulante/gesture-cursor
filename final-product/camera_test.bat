@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  Camera diagnostic - Gesture Mouse Control
echo ============================================================
echo.
echo Process integrity SID (S-1-16-4096 = Low, S-1-16-8192 = Medium):
whoami /groups | findstr /i "S-1-16"
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv not found in "%CD%".
    echo Please run setup.bat first.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" camera_test.py
echo.
pause
