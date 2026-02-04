# Language Learning Suite - Server Management Script
# Run: .\manage-server.ps1 [command]

param(
    [string]$Command = "help"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$PythonPath = $ProjectRoot
$Port = 5000
$Host_Addr = "0.0.0.0"

function Start-Server {
    Write-Host "Starting API server in foreground..."
    Write-Host "API running on http://localhost:$Port"
    Write-Host "Press Ctrl+C to stop`n"
    
    $env:PYTHONPATH = $PythonPath
    python src/api/server.py
}

function Start-ServerBackground {
    Write-Host "Starting API server in background..."
    Write-Host "API running on http://localhost:$Port"
    Write-Host "Logs: tail -f server.log"
    Write-Host "Stop: .\manage-server.ps1 kill`n"
    
    # Kill any existing server processes first
    Get-Process python -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*server.py*"
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    
    Start-Sleep -Milliseconds 500
    
    # Set environment variable
    $env:PYTHONPATH = $PythonPath
    
    # Start new process using Start-Process (more reliable on Windows)
    $process = Start-Process -FilePath "python" `
        -ArgumentList "src/api/server.py" `
        -WorkingDirectory $PythonPath `
        -WindowStyle Hidden `
        -RedirectStandardOutput "$ProjectRoot/databases/server_stdout.log" `
        -PassThru
    
    Write-Host "Server started with PID: $($process.Id)"
    Write-Host "To stop: .\manage-server.ps1 kill"
}

function Stop-Server {
    Write-Host "Stopping API server..."
    
    # Find and kill python processes running server.py
    $processes = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*server.py*"
    }
    
    if ($processes) {
        $processes | Stop-Process -Force
        Write-Host "Server stopped (killed $($processes.Count) process(es))"
    }
    else {
        Write-Host "No server process found"
    }
}

function Run-Tests {
    Write-Host "Running backend tests..."
    $env:PYTHONPATH = $PythonPath
    python -m pytest "$ProjectRoot/tests/unit" "$ProjectRoot/tests/integration"
}

function Install-Dependencies {
    Write-Host "Installing dependencies..."
    pip install -r requirements.txt
    Write-Host "Dependencies installed"
}

function Install-DevDependencies {
    Write-Host "Installing dev dependencies..."
    pip install -r requirements.txt
    pip install pytest pytest-cov
    Write-Host "Dev dependencies installed"
}

function Show-Help {
    @"
Language Learning Suite - Server Management

USAGE:
  .\manage-server.ps1 [command]

COMMANDS:
  server       - Start API server in foreground
  server-bg    - Start API server in background (runs in separate process)
  kill         - Kill background API server
  test         - Run backend tests
  install      - Install dependencies
  dev          - Install dev dependencies (includes testing tools)
  help         - Show this help message

EXAMPLES:
  .\manage-server.ps1 server          # Run server and see output
  .\manage-server.ps1 server-bg       # Run server in background
  .\manage-server.ps1 kill            # Stop background server
  .\manage-server.ps1 test            # Run tests

SERVER INFO:
  Port: $Port
  Host: $Host_Addr
  URL: http://localhost:$Port/api

"@
}

# Execute command
switch ($Command.ToLower()) {
    "server" { Start-Server }
    "server-bg" { Start-ServerBackground }
    "kill" { Stop-Server }
    "stop" { Stop-Server }
    "test" { Run-Tests }
    "install" { Install-Dependencies }
    "dev" { Install-DevDependencies }
    "help" { Show-Help }
    "" { Show-Help }
    default { 
        Write-Host "Unknown command: $Command"
        Write-Host "Run '.\manage-server.ps1 help' for usage"
    }
}
