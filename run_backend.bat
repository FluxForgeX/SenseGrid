@echo off
title SenseGrid Backend
cd /d "%~dp0backend"
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo [ERROR] Virtual environment not found at backend\.venv
    pause
    exit /b 1
)
echo Starting SenseGrid Backend on http://127.0.0.1:8000...
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
pause
