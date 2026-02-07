# Language Learning Suite - Windows Setup Script

Write-Host "--- Language Learning Suite Setup ---" -ForegroundColor Cyan

# 1. Check Python
if (!(get-command python -erroraction silentlycontinue)) {
    Write-Host "Error: Python not found. Please install Python 3.9+ and add it to your PATH." -ForegroundColor Red
    exit 1
}

$version = python --version
Write-Host "Found Python: $version"

# 2. Virtual Environment
if (!(Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}
else {
    Write-Host "Virtual environment already exists." -ForegroundColor Cyan
}

# 3. Install Dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\pip.exe" install -r requirements.txt

# 4. Success
Write-Host "`nSetup complete!" -ForegroundColor Green
Write-Host "To start the server:" -ForegroundColor Cyan
Write-Host "  .\scripts\start-server.bat"
Write-Host "`nTo run tests:" -ForegroundColor Cyan
Write-Host "  .\scripts\manage-server.ps1 test"
