@echo off
setlocal
cd /d "%~dp0legacy"

echo ============================================================
echo  LEGACY MODE - original pre-v1.1 gesture logic
echo  For comparison only: scroll/right-click have known defects.
echo ============================================================
echo.

"..\.venv\Scripts\python.exe" main.py %*
if errorlevel 1 pause
