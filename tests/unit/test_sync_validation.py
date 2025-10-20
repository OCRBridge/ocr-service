"""Unit tests for synchronous endpoint file size validation."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, UploadFile

from src.utils.validators import validate_sync_file_size


@pytest.mark.asyncio
async def test_validate_sync_file_size_accepts_valid_size():
    """Test that validate_sync_file_size accepts files <= 5MB."""
    # Create mock file with 1MB content
    content = b"0" * (1 * 1024 * 1024)  # 1MB
    mock_file = MagicMock(spec=UploadFile)
    mock_file.read = AsyncMock(return_value=content)
    mock_file.seek = AsyncMock()
    mock_file.filename = "test.jpg"

    # Should not raise exception
    result = await validate_sync_file_size(mock_file)

    assert result == mock_file
    mock_file.seek.assert_called_once_with(0)  # Should reset file pointer


@pytest.mark.asyncio
async def test_validate_sync_file_size_accepts_max_size():
    """Test that validate_sync_file_size accepts exactly 5MB."""
    # Create mock file with exactly 5MB content
    content = b"0" * (5 * 1024 * 1024)  # 5MB
    mock_file = MagicMock(spec=UploadFile)
    mock_file.read = AsyncMock(return_value=content)
    mock_file.seek = AsyncMock()
    mock_file.filename = "test.jpg"

    # Should not raise exception
    result = await validate_sync_file_size(mock_file)

    assert result == mock_file


@pytest.mark.asyncio
async def test_validate_sync_file_size_accepts_small_file():
    """Test that validate_sync_file_size accepts small files (< 1KB)."""
    # Create mock file with small content
    content = b"small content"
    mock_file = MagicMock(spec=UploadFile)
    mock_file.read = AsyncMock(return_value=content)
    mock_file.seek = AsyncMock()
    mock_file.filename = "test.jpg"

    # Should not raise exception
    result = await validate_sync_file_size(mock_file)

    assert result == mock_file


@pytest.mark.asyncio
async def test_validate_sync_file_size_rejects_oversized():
    """Test that validate_sync_file_size rejects files > 5MB."""
    # Create mock file with 6MB content
    content = b"0" * (6 * 1024 * 1024)  # 6MB
    mock_file = MagicMock(spec=UploadFile)
    mock_file.read = AsyncMock(return_value=content)
    mock_file.seek = AsyncMock()
    mock_file.filename = "large.jpg"

    # Should raise HTTPException with status 413
    with pytest.raises(HTTPException) as exc_info:
        await validate_sync_file_size(mock_file)

    assert exc_info.value.status_code == 413
    assert "5MB limit" in exc_info.value.detail
    assert "6.00MB" in exc_info.value.detail  # Shows actual size


@pytest.mark.asyncio
async def test_validate_sync_file_size_rejects_much_larger():
    """Test that validate_sync_file_size rejects very large files."""
    # Create mock file with 25MB content (async endpoint limit)
    content = b"0" * (25 * 1024 * 1024)  # 25MB
    mock_file = MagicMock(spec=UploadFile)
    mock_file.read = AsyncMock(return_value=content)
    mock_file.seek = AsyncMock()
    mock_file.filename = "very_large.pdf"

    # Should raise HTTPException with status 413
    with pytest.raises(HTTPException) as exc_info:
        await validate_sync_file_size(mock_file)

    assert exc_info.value.status_code == 413
    assert "5MB limit" in exc_info.value.detail
    assert "async endpoints" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_validate_sync_file_size_error_message_format():
    """Test that error message includes helpful information."""
    # Create mock file with 10MB content
    content = b"0" * (10 * 1024 * 1024)  # 10MB
    mock_file = MagicMock(spec=UploadFile)
    mock_file.read = AsyncMock(return_value=content)
    mock_file.filename = "test.jpg"

    # Should raise HTTPException with detailed message
    with pytest.raises(HTTPException) as exc_info:
        await validate_sync_file_size(mock_file)

    detail = exc_info.value.detail

    # Should include actual size
    assert "10.00MB" in detail

    # Should include limit
    assert "5MB" in detail

    # Should suggest async endpoints
    assert "/upload/" in detail or "async" in detail.lower()


@pytest.mark.asyncio
async def test_validate_sync_file_size_resets_file_pointer():
    """Test that file pointer is reset even for valid files."""
    # Create mock file
    content = b"0" * (1 * 1024 * 1024)  # 1MB
    mock_file = MagicMock(spec=UploadFile)
    mock_file.read = AsyncMock(return_value=content)
    mock_file.seek = AsyncMock()
    mock_file.filename = "test.jpg"

    # Validate file
    await validate_sync_file_size(mock_file)

    # File pointer should be reset to beginning
    mock_file.seek.assert_called_once_with(0)


@pytest.mark.asyncio
async def test_validate_sync_file_size_boundary_just_over():
    """Test file size just over 5MB limit (5MB + 1 byte)."""
    # Create mock file with 5MB + 1 byte
    content = b"0" * (5 * 1024 * 1024 + 1)
    mock_file = MagicMock(spec=UploadFile)
    mock_file.read = AsyncMock(return_value=content)
    mock_file.filename = "boundary.jpg"

    # Should raise HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await validate_sync_file_size(mock_file)

    assert exc_info.value.status_code == 413


@pytest.mark.asyncio
async def test_validate_sync_file_size_boundary_just_under():
    """Test file size just under 5MB limit (5MB - 1 byte)."""
    # Create mock file with 5MB - 1 byte
    content = b"0" * (5 * 1024 * 1024 - 1)
    mock_file = MagicMock(spec=UploadFile)
    mock_file.read = AsyncMock(return_value=content)
    mock_file.seek = AsyncMock()
    mock_file.filename = "boundary.jpg"

    # Should not raise exception
    result = await validate_sync_file_size(mock_file)
    assert result == mock_file


@pytest.mark.asyncio
async def test_validate_sync_file_size_uses_config():
    """Test that validate_sync_file_size uses config for limit."""
    from src.config import settings

    # Verify the limit is actually from config
    expected_limit_bytes = settings.sync_max_file_size_bytes
    assert expected_limit_bytes == 5 * 1024 * 1024  # 5MB

    # Create mock file just over config limit
    content = b"0" * (expected_limit_bytes + 1)
    mock_file = MagicMock(spec=UploadFile)
    mock_file.read = AsyncMock(return_value=content)
    mock_file.filename = "test.jpg"

    # Should raise HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await validate_sync_file_size(mock_file)

    assert exc_info.value.status_code == 413
