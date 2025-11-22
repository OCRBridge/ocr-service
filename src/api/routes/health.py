"""Health check and metrics endpoints."""

import structlog
from fastapi import APIRouter, Depends
from redis import asyncio as aioredis

from src.api.dependencies import get_redis

router = APIRouter()
logger = structlog.get_logger()


@router.get("/health")
async def health_check(redis: aioredis.Redis = Depends(get_redis)):
    """
    Health check endpoint with Redis connection verification.

    Returns:
        Health status and version information
    """
    # Check Redis connection
    try:
        await redis.ping()  # type: ignore[misc]
        redis_status = "connected"
    except Exception as e:
        logger.error("health_check_redis_failed", error=str(e))
        redis_status = "disconnected"

    return {
        "status": "healthy" if redis_status == "connected" else "degraded",
        "version": "1.0.0",
        "redis": redis_status,
    }


# Note: /metrics endpoint is mounted directly in main.py using prometheus ASGI app
