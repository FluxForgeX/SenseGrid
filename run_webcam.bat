@echo off
title SenseGrid Live Webcam Detection
cd /d "%~dp0backend"
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo [ERROR] Virtual environment not found at backend\.venv
    pause
    exit /b 1
)
echo ===================================================
echo   Starting SenseGrid Live Webcam Model Detection
echo ===================================================
python live_webcam_detection.py %*
pause
