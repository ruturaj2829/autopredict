# Multi-stage Dockerfile for Railway deployment with detailed logging
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for better caching
COPY requirements.txt /tmp/requirements.txt
COPY requirements-production.txt /tmp/requirements-production.txt

# Install Python dependencies with verbose output and progress tracking
# Strategy: Install CPU-only PyTorch first (smaller), then other deps
RUN set -x && \
    echo "=== Step 1: Upgrading pip, setuptools, wheel ===" && \
    pip install --no-cache-dir --upgrade pip setuptools wheel && \
    echo "=== Step 2: Installing CPU-only PyTorch (much lighter, ~200MB vs ~2GB) ===" && \
    pip install --no-cache-dir --progress-bar off torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    echo "=== Step 3: Installing other requirements (torch already installed, pip will skip) ===" && \
    pip install --no-cache-dir --progress-bar off -r /tmp/requirements.txt && \
    echo "=== Step 4: Verifying installation ===" && \
    python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}')" && \
    python -c "import fastapi; print(f'FastAPI version: {fastapi.__version__}')" && \
    echo "=== Step 5: Installation complete, showing top packages ===" && \
    pip list | head -30 && \
    echo "=== Step 6: Disk usage ===" && \
    du -sh /opt/venv

# Production stage
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code (excluding files in .railwayignore)
COPY backend/ ./backend/
COPY models/ ./models/
COPY scheduler/ ./scheduler/
COPY manufacturing/ ./manufacturing/
COPY ueba/ ./ueba/
COPY agents/ ./agents/
COPY voice/ ./voice/
COPY main.py ./
COPY requirements.txt ./

# Create artifacts directory if needed
RUN mkdir -p artifacts

# Expose port
ENV PORT=8000
EXPOSE $PORT

# Health check - use simple root endpoint that doesn't require models
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:$PORT/ || exit 1

# Start command with detailed logging
CMD echo "=== Starting FastAPI application ===" && \
    echo "Python version: $(python --version)" && \
    echo "Working directory: $(pwd)" && \
    echo "Port: $PORT" && \
    echo "Available modules:" && \
    ls -la backend/ models/ 2>/dev/null | head -10 && \
    uvicorn main:app --host 0.0.0.0 --port $PORT --log-level info

