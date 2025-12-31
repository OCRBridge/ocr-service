"""Application configuration using Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4

    # File Storage
    upload_dir: str = Field(
        default="./data/uploads",
        description="Directory for temporary uploaded files",
    )
    results_dir: str = Field(
        default="./data/results",
        description="Directory for OCR results cache",
    )
    max_upload_size_mb: int = 25

    # Job Configuration
    job_expiration_hours: int = 48

    # Synchronous Endpoint Configuration
    sync_timeout_seconds: int = Field(
        default=30,
        description="Maximum processing time for synchronous OCR requests",
        ge=5,
        le=60,
    )
    sync_max_file_size_mb: int = Field(
        default=5,
        description="Maximum file size in MB for synchronous OCR requests",
        ge=1,
        le=25,  # Must be <= max_upload_size_mb
    )

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Development
    debug: bool = False
    reload: bool = False
    strict_engine_loading: bool = Field(
        default=False,
        description="Fail startup if any engine fails to load (useful for debugging)",
    )

    # Circuit Breaker
    circuit_breaker_enabled: bool = Field(
        default=True,
        description="Enable circuit breaker for failing OCR engines",
    )
    circuit_breaker_threshold: int = Field(
        default=5,
        description="Number of consecutive failures before opening circuit",
        ge=1,
    )
    circuit_breaker_timeout_seconds: int = Field(
        default=300,
        description="Seconds to wait before attempting to close an open circuit",
        ge=60,
    )
    circuit_breaker_success_threshold: int = Field(
        default=3,
        description="Number of consecutive successes required to reset failure count",
        ge=1,
    )

    # Security - Authentication
    api_key_enabled: bool = Field(
        default=False,
        description="Enable API key authentication (recommended for production)",
    )
    api_keys: str = Field(
        default="",
        description="Comma-separated list of valid API keys (use env var for production)",
    )
    api_key_header_name: str = Field(
        default="X-API-Key",
        description="HTTP header name for API key",
    )

    # Security - CORS
    cors_enabled: bool = Field(
        default=False,
        description="Enable CORS middleware",
    )
    cors_origins: str = Field(
        default="",
        description="Comma-separated allowed CORS origins (empty=disabled, *=all origins)",
    )
    cors_allow_credentials: bool = Field(
        default=False,
        description="Allow credentials in CORS requests",
    )

    # Security - Rate Limiting
    rate_limit_enabled: bool = Field(
        default=True,
        description="Enable rate limiting (recommended for production)",
    )
    rate_limit_storage_uri: str = Field(
        default="memory://",
        description="Storage backend for rate limiting. Use 'redis://host:port' for multi-worker deployments",
    )
    testing: bool = Field(
        default=False,
        description="Testing mode (disables rate limiting)",
    )
    rate_limit_default: str = Field(
        default="100/hour",
        description="Default rate limit for all endpoints (e.g., '100/hour', '10/minute')",
    )
    rate_limit_ocr_process: str = Field(
        default="10/minute",
        description="Rate limit for OCR processing endpoints (expensive operations)",
    )
    rate_limit_ocr_info: str = Field(
        default="100/minute",
        description="Rate limit for OCR info/discovery endpoints (lightweight)",
    )

    @property
    def api_keys_list(self) -> list[str]:
        """Parse comma-separated API keys into list."""
        if not self.api_keys:
            return []
        return [key.strip() for key in self.api_keys.split(",") if key.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        """Convert max upload size from MB to bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def sync_max_file_size_bytes(self) -> int:
        """Convert sync max file size from MB to bytes."""
        return self.sync_max_file_size_mb * 1024 * 1024


# Global settings instance
settings = Settings()
