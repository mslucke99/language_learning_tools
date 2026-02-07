.PHONY: server server-bg server-kill test help install dev

# Variables
PYTHON := python
PYTHONPATH := .
PORT := 5000
HOST := 0.0.0.0

help:
	@echo Language Learning Suite - Available Commands
	@echo.
	@echo Server:
	@echo   make server           - Start API server in foreground
	@echo   make server-bg        - Start API server in background
	@echo   make server-kill      - Kill background API server
	@echo.
	@echo Testing:
	@echo   make test             - Run backend tests
	@echo.
	@echo Setup:
	@echo   make install          - Install dependencies
	@echo   make dev              - Install dev dependencies

# Install dependencies
install:
	pip install -r requirements.txt

# Install dev dependencies
dev:
	pip install -r requirements.txt
	pip install pytest pytest-cov

# Start server in foreground
server:
	set PYTHONPATH=$(PYTHONPATH) && $(PYTHON) src/api/server.py

# Start server in background
server-bg:
	@echo Starting API server in background on http://0.0.0.0:$(PORT)
	@set PYTHONPATH=$(PYTHONPATH) && start /B $(PYTHON) src/api/server.py > server.log 2>&1
	@echo Server started. Check server.log for output

# Kill background server (for Windows)
server-kill:
	@echo Killing API server processes...
	@taskkill /F /IM python.exe /FI "WINDOWTITLE eq *server.py*" 2>nul || echo No server processes found
	@echo Done

# Run tests
test:
	set PYTHONPATH=$(PYTHONPATH) && $(PYTHON) test_backend.py
