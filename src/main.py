"""
Main entry point for the character traits extraction API service.

This module provides the entry point for running the API with Uvicorn.
"""

import logging
import uvicorn
import os

from src.api.api import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Run the API server using Uvicorn."""
    # Get host and port from environment or use defaults
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    
    logger.info(f"Starting Character Traits Extractor API on {host}:{port}")
    
    # Run the application with Uvicorn
    uvicorn.run(
        "src.api.api:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()