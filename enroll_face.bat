@echo off
title SenseGrid Face Enrollment
cd /d "%~dp0backend"
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo [ERROR] Virtual environment not found at backend\.venv
    pause
    exit /b 1
)
python enroll_face.py %*
pause
