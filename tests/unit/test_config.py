"""Unit tests for application configuration.

Tests for Settings class, default values, environment overrides,
and property conversions.
"""

import pytest
from pydantic import ValidationError

from src.config import Settings


def test_settings_defaults():
    """Test that settings have correct default values."""
    settings = Settings()

    # API Configuration
    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 8000
    assert settings.api_workers == 4

    # File Storage
    assert settings.upload_dir == "/tmp/uploads"
    assert settings.results_dir == "/tmp/results"
    assert settings.max_upload_size_mb == 25

    # Job Configuration
    assert settings.job_expiration_hours == 48

    # Synchronous Endpoint Configuration
    assert settings.sync_timeout_seconds == 30
    assert settings.sync_max_file_size_mb == 5

    # Logging
    assert settings.log_level == "INFO"
    assert settings.log_format == "json"

    # Development
    assert settings.debug is False
    assert settings.reload is False


def test_max_upload_size_bytes_property():
    """Test conversion from MB to bytes for max upload size."""
    settings = Settings(max_upload_size_mb=10)

    # 10 MB = 10 * 1024 * 1024 bytes
    expected_bytes = 10 * 1024 * 1024
    assert settings.max_upload_size_bytes == expected_bytes


def test_sync_max_file_size_bytes_property():
    """Test conversion from MB to bytes for sync max file size."""
    settings = Settings(sync_max_file_size_mb=5)

    # 5 MB = 5 * 1024 * 1024 bytes
    expected_bytes = 5 * 1024 * 1024
    assert settings.sync_max_file_size_bytes == expected_bytes


def test_settings_from_env(monkeypatch):
    """Test that settings can be overridden via environment variables."""
    # Set environment variables
    monkeypatch.setenv("API_HOST", "127.0.0.1")
    monkeypatch.setenv("API_PORT", "9000")
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "50")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DEBUG", "true")

    # Create new settings instance (reads from environment)
    settings = Settings()

    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 9000
    assert settings.max_upload_size_mb == 50
    assert settings.log_level == "DEBUG"
    assert settings.debug is True


def test_settings_integer_validation(monkeypatch):
    """Test that integer fields are properly validated."""
    monkeypatch.setenv("API_PORT", "not_an_integer")

    with pytest.raises(ValidationError):
        Settings()


def test_settings_boolean_validation(monkeypatch):
    """Test that boolean fields accept various formats."""
    test_cases = [
        ("true", True),
        ("True", True),
        ("1", True),
        ("yes", True),
        ("false", False),
        ("False", False),
        ("0", False),
        ("no", False),
    ]

    for env_value, expected_bool in test_cases:
        monkeypatch.setenv("DEBUG", env_value)
        settings = Settings()
        assert settings.debug == expected_bool


def test_sync_timeout_validation():
    """Test that sync_timeout_seconds validates range (5-60)."""
    # Valid values
    Settings(sync_timeout_seconds=5)  # Min
    Settings(sync_timeout_seconds=30)  # Default
    Settings(sync_timeout_seconds=60)  # Max

    # Invalid values
    with pytest.raises(ValidationError):
        Settings(sync_timeout_seconds=4)  # Below minimum

    with pytest.raises(ValidationError):
        Settings(sync_timeout_seconds=61)  # Above maximum


def test_sync_max_file_size_validation():
    """Test that sync_max_file_size_mb validates range (1-25)."""
    # Valid values
    Settings(sync_max_file_size_mb=1)  # Min
    Settings(sync_max_file_size_mb=5)  # Default
    Settings(sync_max_file_size_mb=25)  # Max

    # Invalid values
    with pytest.raises(ValidationError):
        Settings(sync_max_file_size_mb=0)  # Below minimum

    with pytest.raises(ValidationError):
        Settings(sync_max_file_size_mb=26)  # Above maximum


def test_settings_extra_fields_ignored():
    """Test that extra fields are ignored (not strict mode)."""
    # Should not raise error for extra fields
    settings = Settings(unknown_field="value")  # type: ignore[call-arg]

    # Unknown field should not be stored
    assert not hasattr(settings, "unknown_field")


def test_settings_custom_upload_dir(monkeypatch):
    """Test custom upload and results directories."""
    monkeypatch.setenv("UPLOAD_DIR", "/custom/uploads")
    monkeypatch.setenv("RESULTS_DIR", "/custom/results")

    settings = Settings()

    assert settings.upload_dir == "/custom/uploads"
    assert settings.results_dir == "/custom/results"


def test_settings_log_format_options(monkeypatch):
    """Test different log format options."""
    # JSON format
    monkeypatch.setenv("LOG_FORMAT", "json")
    settings = Settings()
    assert settings.log_format == "json"

    # Console format
    monkeypatch.setenv("LOG_FORMAT", "console")
    settings = Settings()
    assert settings.log_format == "console"


def test_settings_job_expiration_override(monkeypatch):
    """Test overriding job expiration time."""
    monkeypatch.setenv("JOB_EXPIRATION_HOURS", "72")

    settings = Settings()

    assert settings.job_expiration_hours == 72


def test_settings_bytes_conversion_accuracy():
    """Test that MB to bytes conversion is accurate."""
    settings = Settings(max_upload_size_mb=1, sync_max_file_size_mb=1)

    # 1 MB should equal 1,048,576 bytes
    assert settings.max_upload_size_bytes == 1_048_576
    assert settings.sync_max_file_size_bytes == 1_048_576


def test_settings_multiple_instances():
    """Test that multiple Settings instances can coexist with different values."""
    settings1 = Settings(api_port=8000)
    settings2 = Settings(api_port=9000)

    assert settings1.api_port == 8000
    assert settings2.api_port == 9000


def test_settings_immutable_after_creation():
    """Test that settings can be modified after creation."""
    settings = Settings()
    original_port = settings.api_port

    # Pydantic BaseSettings allows mutation
    settings.api_port = 9999
    assert settings.api_port == 9999
    assert settings.api_port != original_port
