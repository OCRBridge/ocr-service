"""FastAPI dependency providers for shared resources."""

import structlog
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from src.config import Settings, settings

logger = structlog.get_logger()

# API Key security scheme (only used if authentication is enabled)
api_key_header_scheme = APIKeyHeader(name=settings.api_key_header_name, auto_error=False)


async def get_settings() -> Settings:
    """Get application settings."""
    return settings


async def verify_api_key(api_key: str | None = Security(api_key_header_scheme)) -> str:
    """Verify API key from request header.

    This dependency validates the API key if authentication is enabled in settings.
    If authentication is disabled, this dependency is a no-op.

    Args:
        api_key: API key from request header

    Returns:
        The validated API key

    Raises:
        HTTPException: 401 if API key is missing or invalid (when auth enabled)
    """
    # Skip authentication if not enabled
    if not settings.api_key_enabled:
        return "auth_disabled"

    # Check if API key was provided
    if not api_key:
        logger.warning("api_key_missing", header_name=settings.api_key_header_name)
        raise HTTPException(
            status_code=401,
            detail=f"API key required. Provide via '{settings.api_key_header_name}' header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Validate API key against configured keys
    valid_keys = settings.api_keys_list
    if not valid_keys:
        logger.error("api_keys_not_configured")
        raise HTTPException(
            status_code=500,
            detail="Authentication is enabled but no API keys are configured.",
        )

    if api_key not in valid_keys:
        logger.warning("api_key_invalid", key_prefix=api_key[:8] if len(api_key) >= 8 else "short")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Log successful authentication
    logger.debug("api_key_validated", key_prefix=api_key[:8])
    return api_key
