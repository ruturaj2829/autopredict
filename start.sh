#!/bin/bash
set -e

# Ensure we have a port
PORT=${PORT:-8000}
export PORT

echo "=========================================="
echo "AutoPredict Backend Startup"
echo "=========================================="
echo "Python: $(python --version)"
echo "Working dir: $(pwd)"
echo "Port: $PORT"
echo "=========================================="

# Verify critical files exist
echo "Checking files..."
[ -f "main.py" ] || { echo "ERROR: main.py not found!"; exit 1; }
[ -d "backend" ] || { echo "ERROR: backend/ not found!"; exit 1; }
echo "✓ Files OK"

# Test Python import (this will catch syntax errors)
echo "Testing imports..."
python -c "
import sys
sys.path.insert(0, '.')
try:
    from backend.app import app
    print('✓ App imported successfully')
    print(f'✓ App has {len(app.routes)} routes')
except Exception as e:
    print(f'✗ Import failed: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
" || {
    echo "✗ Import test failed!"
    exit 1
}

# Start uvicorn with explicit error handling
echo "=========================================="
echo "Starting uvicorn server..."
echo "=========================================="

exec python -m uvicorn main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --log-level info \
    --access-log \
    --timeout-keep-alive 30 \
    --no-use-colors
