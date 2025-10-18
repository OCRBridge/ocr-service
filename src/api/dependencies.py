"""FastAPI dependency providers for shared resources."""

from typing import AsyncGenerator

from fastapi import Depends, Request
from redis import asyncio as aioredis

from src.config import Settings, settings


async def get_redis(request: Request) -> aioredis.Redis:
    """Get Redis client from app state."""
    return request.app.state.redis


async def get_settings() -> Settings:
    """Get application settings."""
    return settings
