"""Rate limiting middleware using slowapi with Redis backend."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from src.config import settings

# Create rate limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
    default_limits=[f"{settings.rate_limit_requests}/{settings.rate_limit_window_seconds}second"],
)
