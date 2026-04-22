@echo off
title NEXUS — Local AI and Dev Workspace

echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install from https://python.org
    pause
    exit /b 1
)

echo Installing dependencies...
pip install -q PyQt6 psutil

echo Launching NEXUS...
python run_nexus.py
echo NEXUS launched successfully!
pause
