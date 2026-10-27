@echo off
title SenseGrid Launcher
echo =========================================
echo   Starting SenseGrid Backend and Frontend
echo =========================================
echo.
start "SenseGrid Backend" cmd /c "%~dp0run_backend.bat"
timeout /t 2 /nobreak >nul
start "SenseGrid Frontend" cmd /c "%~dp0run_frontend.bat"
echo Services launched in separate windows!
echo Backend:  http://127.0.0.1:8000 (API Docs: http://127.0.0.1:8000/docs)
echo Frontend: http://localhost:5173
echo.
