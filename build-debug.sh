#!/bin/bash
# Build debug script for Railway deployment
set -e

echo "=========================================="
echo "AutoPredict Build Debug Script"
echo "=========================================="
echo ""

echo "1. Checking Python version..."
python --version
echo ""

echo "2. Checking working directory..."
pwd
ls -la
echo ""

echo "3. Checking backend directory..."
if [ -d "backend" ]; then
    echo "✓ Backend directory exists"
    ls -la backend/ | head -10
else
    echo "✗ Backend directory not found!"
    exit 1
fi
echo ""

echo "4. Checking main.py..."
if [ -f "main.py" ]; then
    echo "✓ main.py exists"
    python -c "import main; print('✓ main.py imports successfully')"
else
    echo "✗ main.py not found!"
    exit 1
fi
echo ""

echo "5. Checking requirements.txt..."
if [ -f "requirements.txt" ]; then
    echo "✓ requirements.txt exists"
    wc -l requirements.txt
else
    echo "✗ requirements.txt not found!"
    exit 1
fi
echo ""

echo "6. Testing FastAPI import..."
python -c "from backend.app import app; print('✓ FastAPI app imported'); print(f'Routes: {len(app.routes)}')"
echo ""

echo "=========================================="
echo "Build verification complete!"
echo "=========================================="

