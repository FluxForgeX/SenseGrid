@echo off
title SenseGrid Frontend
cd /d "%~dp0frontend"
echo Starting SenseGrid Frontend on http://localhost:5173...
npm run dev
pause
