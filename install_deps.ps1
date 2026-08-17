# Tungsten Video Editor - Dependency Installer (PowerShell)
# ========================================================

Write-Host "Tungsten Video Editor - Dependency Installer" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
$pythonVersion = python --version 2>$null
if (-not $?) {
    Write-Error "ERROR: Python not found in PATH"
    Write-Host "Please install Python 3.10+ from https://python.org" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "Found: $pythonVersion" -ForegroundColor Green

Write-Host "Creating virtual environment..." -ForegroundColor Yellow
python -m venv .venv
if (-not $?) {
    Write-Error "ERROR: Failed to create virtual environment"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Activating virtual environment and installing dependencies..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

Write-Host "Installing runtime dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt
if (-not $?) {
    Write-Error "ERROR: Failed to install runtime dependencies"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Installing development dependencies..." -ForegroundColor Yellow
pip install -r requirements-dev.txt
if (-not $?) {
    Write-Error "ERROR: Failed to install development dependencies"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To run the application:" -ForegroundColor Yellow
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  python main.py"
Write-Host ""
Write-Host "To build the portable executable:" -ForegroundColor Yellow
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  python build_exe.py"
Write-Host ""
Read-Host "Press Enter to exit"