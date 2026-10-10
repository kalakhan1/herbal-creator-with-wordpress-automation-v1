Write-Host "===========================================" -ForegroundColor Green
Write-Host " Herbal Creator - Setup" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python not found. Install from python.org" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".venv")) {
    Write-Host "Creating venv..." -ForegroundColor Cyan
    python -m venv .venv
}

& ".\.venv\Scripts\Activate.ps1"

Write-Host "Installing packages..." -ForegroundColor Cyan
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host "Downloading NLTK data..." -ForegroundColor Cyan
python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('punkt_tab', quiet=True); nltk.download('stopwords', quiet=True)"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env — edit it to add your store + WordPress credentials" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "===========================================" -ForegroundColor Green
Write-Host " Setup complete!" -ForegroundColor Green
Write-Host " Run: .\start.ps1" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green