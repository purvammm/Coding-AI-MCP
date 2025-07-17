@echo off
REM Windows installation script for MCP AI Coding Agent

echo ================================================
echo MCP AI Coding Agent - Windows Installation
echo ================================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

echo Python found!

REM Run the setup script
python setup.py

if errorlevel 1 (
    echo Setup failed!
    pause
    exit /b 1
)

echo.
echo ================================================
echo Installation Complete!
echo ================================================
echo.
echo To start the application:
echo   1. Run: venv\Scripts\python run.py
echo   2. Open your browser to: http://localhost:8000
echo.
echo For local AI models, install Ollama from: https://ollama.ai
echo.
pause
