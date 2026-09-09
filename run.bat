@echo off
setlocal

rem Start AgriSmart AI from Windows Terminal or Command Prompt.
set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

if exist "%PROJECT_DIR%.venv\Scripts\python.exe" (
    "%PROJECT_DIR%.venv\Scripts\python.exe" "%PROJECT_DIR%main.py"
    exit /b %errorlevel%
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%PROJECT_DIR%main.py"
    exit /b %errorlevel%
)

where python >nul 2>nul
if %errorlevel%==0 (
    python "%PROJECT_DIR%main.py"
    exit /b %errorlevel%
)

echo Python 3 was not found.
echo Install it from https://www.python.org/downloads/ then run:
echo   py -3 -m venv .venv
echo   .venv\Scripts\python -m pip install -r requirements.txt
echo   .\run.bat
exit /b 1
