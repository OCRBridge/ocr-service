"""FastAPI dependency providers for shared resources."""

from src.config import Settings, settings


async def get_settings() -> Settings:
    """Get application settings."""
    return settings
