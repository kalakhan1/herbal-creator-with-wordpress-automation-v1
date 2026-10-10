Write-Host "Starting Herbal Creator..." -ForegroundColor Green

if (-not (Test-Path ".venv")) {
    Write-Host "venv not found. Run .\setup.ps1 first." -ForegroundColor Red
    exit 1
}

& ".\.venv\Scripts\Activate.ps1"
python main.py