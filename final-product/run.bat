@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv not found in "%CD%".
    echo Please run setup.bat first.
    pause
    exit /b 1
)

echo Starting Gesture Mouse Control...
echo Press q or Esc in the preview window to exit.
echo.
".venv\Scripts\python.exe" main.py %*
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo [INFO] main.py exited with code %EXIT_CODE%.
    pause
)
exit /b %EXIT_CODE%
