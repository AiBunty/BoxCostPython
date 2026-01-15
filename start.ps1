# Quick Start Development Script for Windows PowerShell

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "BoxCostPython - Quick Start" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "❌ Virtual environment not found. Creating..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "🔧 Activating virtual environment..." -ForegroundColor Cyan
& ".\venv\Scripts\Activate.ps1"

# Check if dependencies are installed
Write-Host "🔧 Checking dependencies..." -ForegroundColor Cyan
$pipList = pip list
if ($pipList -notmatch "fastapi") {
    Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
    Write-Host "✅ Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "✅ Dependencies already installed" -ForegroundColor Green
}

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  .env file not found. Copying from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✅ .env file created. Please edit it with your configuration" -ForegroundColor Green
    Write-Host ""
    Write-Host "⚠️  IMPORTANT: Edit .env with your DATABASE_URL and API keys!" -ForegroundColor Red
    Write-Host ""
}

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "✅ Setup complete! Starting development server..." -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""
Write-Host "API will be available at:" -ForegroundColor Cyan
Write-Host "  - Root:   http://localhost:8000" -ForegroundColor White
Write-Host "  - Docs:   http://localhost:8000/docs" -ForegroundColor White
Write-Host "  - ReDoc:  http://localhost:8000/redoc" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start the development server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
