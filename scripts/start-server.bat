@echo off
REM Quick start script for Language Learning Suite API Server
REM Run: start-server.bat [option]

setlocal enabledelayedexpansion

set PYTHONPATH=.
set PORT=5000

if "%1"=="" goto foreground
if "%1"=="bg" goto background
if "%1"=="kill" goto kill
if "%1"=="help" goto help
goto unknown

:foreground
echo Starting API server in foreground...
echo.
cd /d "%~dp0.."
python src/api/server.py
goto end

:background
echo Starting API server in background...
echo Logs: databases/server_stdout.log
echo Stop: scripts/start-server.bat kill
echo.
cd /d "%~dp0.."
powershell -ExecutionPolicy Bypass -File scripts/manage-server.ps1 server-bg
goto end

:kill
echo Stopping API server...
cd /d "%~dp0.."
powershell -ExecutionPolicy Bypass -File scripts/manage-server.ps1 kill
goto end

:help
echo Language Learning Suite - Quick Start
echo.
echo Usage: start-server.bat [option]
echo.
echo Options:
echo   (none)   Start server in foreground
echo   bg       Start server in background
echo   kill     Stop background server
echo   help     Show this help
echo.
echo Examples:
echo   start-server.bat
echo   start-server.bat bg
echo   start-server.bat kill
goto end

:unknown
echo Unknown option: %1
echo Run: start-server.bat help
exit /b 1

:end
endlocal
