from unittest.mock import patch

import pytest
from fastapi import HTTPException

from src.api.dependencies import get_settings, verify_api_key


@pytest.mark.asyncio
async def test_get_settings():
    """Test get_settings dependency returns the settings object."""
    settings = await get_settings()
    assert settings is not None


@pytest.mark.asyncio
async def test_verify_api_key_auth_disabled():
    """Test that verification is skipped when auth is disabled."""
    with patch("src.api.dependencies.settings") as mock_settings:
        mock_settings.api_key_enabled = False

        result = await verify_api_key(api_key=None)
        assert result == "auth_disabled"


@pytest.mark.asyncio
async def test_verify_api_key_missing_header():
    """Test that 401 is raised when auth is enabled but header is missing."""
    with patch("src.api.dependencies.settings") as mock_settings:
        mock_settings.api_key_enabled = True
        mock_settings.api_key_header_name = "X-API-Key"

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(api_key=None)

        assert exc_info.value.status_code == 401
        assert "API key required" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_api_key_no_keys_configured():
    """Test that 500 is raised when auth is enabled but no keys are configured."""
    with patch("src.api.dependencies.settings") as mock_settings:
        mock_settings.api_key_enabled = True
        mock_settings.api_keys_list = []  # simulating empty list property

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(api_key="some-key")

        assert exc_info.value.status_code == 500
        assert "no API keys are configured" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_api_key_invalid_key():
    """Test that 401 is raised when the provided key is invalid."""
    with patch("src.api.dependencies.settings") as mock_settings:
        mock_settings.api_key_enabled = True
        mock_settings.api_keys_list = ["valid-key"]

        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(api_key="invalid-key")

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verify_api_key_valid_key():
    """Test that the key is returned when it is valid."""
    with patch("src.api.dependencies.settings") as mock_settings:
        mock_settings.api_key_enabled = True
        mock_settings.api_keys_list = ["valid-key-1", "valid-key-2"]

        result = await verify_api_key(api_key="valid-key-2")
        assert result == "valid-key-2"
