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

    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"

    # File Storage
    upload_dir: str = "/tmp/uploads"
    results_dir: str = "/tmp/results"
    max_upload_size_mb: int = 25

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Job Configuration
    job_expiration_hours: int = 48

    # OCR Configuration
    default_ocr_engine: str = Field(
        default="tesseract",
        description="Default OCR engine to use (tesseract, easyocr, or ocrmac)",
    )
    tesseract_lang: str = "eng"
    tesseract_psm: int = 3  # Auto page segmentation
    tesseract_oem: int = 1  # LSTM only
    pdf_dpi: int = 300

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
