"""Health check and metrics endpoints."""

import structlog
from fastapi import APIRouter

router = APIRouter()
logger = structlog.get_logger()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Health status and version information
    """
    return {
        "status": "healthy",
        "version": "2.0.0",
    }


# Note: /metrics endpoint is mounted directly in main.py using prometheus ASGI app
