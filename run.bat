@echo off
title RaidR Launcher
cd /d "%~dp0"

:: Check if Python is installed / on PATH
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found on your PATH!
    echo Please install Python or check your environment variables.
    pause
    exit /b
)

:: Run RaidR
echo Starting RaidR...
python main.py

:: If the app exits with an error code, keep the window open so you can read the traceback
if %errorlevel% neq 0 (
    echo.
    echo RaidR exited with an error. Check logs above.
    pause
)