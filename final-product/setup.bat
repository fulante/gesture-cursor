@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  Gesture Cursor - environment setup
echo ============================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Windows Python launcher "py" was not found.
    echo Install Python 3.12 from https://www.python.org/downloads/ first.
    pause
    exit /b 1
)

py -3.12 -m venv .venv
if errorlevel 1 (
    echo.
    echo [ERROR] Could not create .venv with Python 3.12.
    echo Install Python 3.12 and run this script again.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt -c constraints.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Dependency installation failed. Check the network and retry.
    pause
    exit /b 1
)

echo.
echo Done. Double-click run.bat to start Gesture Cursor.
pause
