Set-Location "$PSScriptRoot\backend"
& ".\.venv\Scripts\Activate.ps1"
Write-Host "Starting SenseGrid Backend on http://127.0.0.1:8000..." -ForegroundColor Green
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
