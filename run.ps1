param (
    [Parameter(Mandatory = $false)]
    [string]$Command = "help",

    [Parameter(Mandatory = $false)]
    [string]$Module = ""
)

$PYTHONPATH = $PSScriptRoot
$env:PYTHONPATH = $PYTHONPATH

switch ($Command) {
    "help" {
        Write-Host "Language Learning Suite - PowerShell Runner" -ForegroundColor Cyan
        Write-Host "`nServer:"
        Write-Host "  .\run.ps1 server           - Start API server in foreground"
        Write-Host "  .\run.ps1 server-bg        - Start API server in background"
        Write-Host "  .\run.ps1 server-kill      - Kill API server processes"
        Write-Host "`nApp:"
        Write-Host "  .\run.ps1 app              - Start Desktop Application"
        Write-Host "`nTesting:"
        Write-Host "  .\run.ps1 test             - Run all tests"
        Write-Host "  .\run.ps1 test-backend     - Run backend API tests"
        Write-Host "`nSetup:"
        Write-Host "  .\run.ps1 install          - Install dependencies"
        Write-Host "  .\run.ps1 setup            - Run full environment setup"
    }

    "install" {
        Write-Host "Installing dependencies..." -ForegroundColor Green
        pip install -r requirements.txt
    }

    "setup" {
        Write-Host "Running environment setup..." -ForegroundColor Green
        .\setup.ps1
    }

    "server" {
        Write-Host "Starting API server on http://localhost:5000..." -ForegroundColor Green
        python src/api/server.py
    }

    "server-bg" {
        Write-Host "Starting API server in background..." -ForegroundColor Green
        Start-Process python -ArgumentList "src/api/server.py" -WindowStyle Hidden -RedirectStandardOutput "server.log" -RedirectStandardError "server.err"
        Write-Host "Server started in background. Logs: server.log" -ForegroundColor Gray
    }

    "server-kill" {
        Write-Host "Killing API server processes..." -ForegroundColor Yellow
        Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*server.py*" } | Stop-Process -Force
        Write-Host "Done."
    }

    "app" {
        Write-Host "Starting Desktop App..." -ForegroundColor Green
        python src/main.py
    }

    "test" {
        Write-Host "Running tests..." -ForegroundColor Green
        pytest
    }

    "test-backend" {
        Write-Host "Running Backend API tests..." -ForegroundColor Green
        python test_backend.py
    }

    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host "Use '.\run.ps1 help' for available commands."
    }
}
