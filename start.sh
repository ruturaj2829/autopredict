#!/bin/bash
set -e

echo "=== AutoPredict Backend Startup Script ==="
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"
echo "Port: ${PORT:-8000}"

# Test imports
echo "=== Testing imports ==="
python -c "from backend.app import app; print('✓ App import successful')" || {
    echo "✗ App import failed!"
    exit 1
}

# Start uvicorn
echo "=== Starting uvicorn server ==="
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --log-level info \
    --access-log \
    --timeout-keep-alive 30

