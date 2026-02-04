#!/bin/bash
# Language Learning Suite - Linux/macOS Setup Script

echo "--- Language Learning Suite Setup ---"

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Please install Python 3.9+."
    exit 1
fi

python3 --version

# 2. Virtual Environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
else
    echo "Virtual environment already exists."
fi

# 3. Install Dependencies
echo "Installing dependencies..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Success
echo ""
echo "Setup complete!"
echo "To start the server:"
echo "  ./scripts/manage-server.ps1 server (using powershell for linux)"
echo "  OR run manually: export PYTHONPATH=. && python3 src/api/server.py"

echo ""
echo "To run tests:"
echo "  python3 -m pytest tests/unit tests/integration"
