"""Railway entry point - imports FastAPI app from backend."""
import logging
import os
import sys
from pathlib import Path

# Configure logging for Railway deployment visibility
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
LOGGER = logging.getLogger("main")

# Log startup information
LOGGER.info("=" * 60)
LOGGER.info("Starting AutoPredict Backend")
LOGGER.info("=" * 60)
LOGGER.info("Python version: %s", sys.version)
LOGGER.info("Working directory: %s", os.getcwd())
LOGGER.info("Port: %s", os.getenv("PORT", "8000"))
LOGGER.info("Environment: %s", os.getenv("RAILWAY_ENVIRONMENT", "production"))

# Check critical paths
backend_path = Path("backend")
if backend_path.exists():
    LOGGER.info("✓ Backend directory found")
else:
    LOGGER.error("✗ Backend directory not found!")
    sys.exit(1)

# Import FastAPI app
try:
    from backend.app import app
    LOGGER.info("✓ FastAPI app imported successfully")
    LOGGER.info("✓ Available routes: %s", [r.path for r in app.routes[:5]])
except Exception as e:
    LOGGER.error("✗ Failed to import FastAPI app: %s", e, exc_info=True)
    sys.exit(1)

LOGGER.info("=" * 60)

__all__ = ["app"]

