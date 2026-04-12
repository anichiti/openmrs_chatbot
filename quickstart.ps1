# ==============================================================================
# OpenMRS Clinical Chatbot - Quick Start PowerShell Script
# ==============================================================================
# Run in PowerShell (can right-click and "Run with PowerShell")

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║          OpenMRS Clinical Chatbot - Quick Start                           ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found. Download from: https://www.python.org/" -ForegroundColor Red
    exit
}

# Check MySQL
Write-Host "[2/5] Checking MySQL..." -ForegroundColor Yellow
try {
    $mysqlCheck = mysql --version 2>&1
    Write-Host "✓ MySQL available" -ForegroundColor Green
} catch {
    Write-Host "⚠ MySQL not found in PATH (might still be installed)" -ForegroundColor Yellow
}

# Check Ollama
Write-Host "[3/5] Checking Ollama..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "✓ Ollama is running" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ Ollama not running on localhost:11434" -ForegroundColor Red
    Write-Host "   Please start Ollama: ollama serve" -ForegroundColor Yellow
}

# Setup virtual environment
Write-Host "[4/5] Setting up Python environment..." -ForegroundColor Yellow
Set-Location ./openmrs_chatbot
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate venv
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Install requirements
Write-Host "[5/5] Installing Python packages..." -ForegroundColor Yellow
pip install -q -r requirements.txt
Write-Host "✓ Setup complete!" -ForegroundColor Green

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "READY TO RUN!" -ForegroundColor Green
Write-Host ""
Write-Host "Command Line Version:" -ForegroundColor Yellow
Write-Host "  python main.py"
Write-Host ""
Write-Host "Web Interface Version:" -ForegroundColor Yellow
Write-Host "  python app.py"
Write-Host "  Then open: http://localhost:5000"
Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
