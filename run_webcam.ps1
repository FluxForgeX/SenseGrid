param(
    [double]$duration = 60.0,
    [double]$interval = 0.0,
    [double]$confidence = 0.35,
    [int]$camera = 0
)

Set-Location "$PSScriptRoot\backend"
& ".\.venv\Scripts\Activate.ps1"
Write-Host "===================================================" -ForegroundColor Green
Write-Host "  Starting SenseGrid Live Webcam Model Detection" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
python live_webcam_detection.py --duration $duration --interval $interval --confidence $confidence --camera $camera
