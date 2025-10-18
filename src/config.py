"""Application configuration using Pydantic Settings."""

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
    tesseract_lang: str = "eng"
    tesseract_psm: int = 3  # Auto page segmentation
    tesseract_oem: int = 1  # LSTM only
    pdf_dpi: int = 300

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


# Global settings instance
settings = Settings()
