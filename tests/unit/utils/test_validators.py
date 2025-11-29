"""Unit tests for file validation utilities.

Security-critical tests for magic byte detection and file size validation.
"""

import io

import pytest
from fastapi import HTTPException, UploadFile

from src.utils.validators import (
    SUPPORTED_MIME_TYPES,
    FileTooLargeError,
    UnsupportedFormatError,
    validate_file_format,
    validate_file_size,
    validate_sync_file_size,
    validate_upload_file,
)

# ==============================================================================
# File Format Validation Tests
# ==============================================================================


@pytest.mark.parametrize(
    "magic_bytes,expected_mime",
    [
        (b"\xff\xd8\xff", "image/jpeg"),
        (b"\xff\xd8\xff\xe0", "image/jpeg"),
        # PNG requires IHDR chunk for robust detection by libmagic
        (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", "image/png"),
        (b"%PDF-", "application/pdf"),
        (b"%PDF-1.4", "application/pdf"),
        # TIFF headers often need more context for libmagic to be sure, but basic headers usually work
        (b"II*\x00", "image/tiff"),  # Little-endian TIFF
        (b"MM\x00*", "image/tiff"),  # Big-endian TIFF
    ],
)
def test_validate_file_format_valid(magic_bytes, expected_mime):
    """Test magic byte detection for all supported formats."""
    # Pad with additional bytes to simulate real file header
    # libmagic often needs a bit more context
    header = magic_bytes + b"\x00" * 50

    result = validate_file_format(header)

    assert result == expected_mime


def test_validate_file_format_unsupported():
    """Test that unsupported formats raise UnsupportedFormatError."""
    # A purely random binary file usually results in application/octet-stream
    invalid_header = b"INVALID_FORMAT\x00" * 10

    with pytest.raises(UnsupportedFormatError) as exc_info:
        validate_file_format(invalid_header)

    assert "Unsupported file format" in str(exc_info.value)


def test_validate_file_format_empty():
    """Test that empty file header raises UnsupportedFormatError."""
    with pytest.raises(UnsupportedFormatError):
        validate_file_format(b"")


def test_validate_file_format_short_header():
    """Test that short headers raise UnsupportedFormatError."""
    # libmagic might identify this as something else or fail to match supported types
    with pytest.raises(UnsupportedFormatError):
        validate_file_format(b"\xff\xd8")  # Incomplete JPEG header


def test_supported_mime_types_constant():
    """Test that SUPPORTED_MIME_TYPES constant is correctly defined."""
    assert "image/jpeg" in SUPPORTED_MIME_TYPES
    assert "image/png" in SUPPORTED_MIME_TYPES
    assert "application/pdf" in SUPPORTED_MIME_TYPES
    assert "image/tiff" in SUPPORTED_MIME_TYPES
    assert len(SUPPORTED_MIME_TYPES) == 4


# ==============================================================================
# File Size Validation Tests
# ==============================================================================


def test_validate_file_size_within_limit():
    """Test that file within size limit passes validation."""
    # 1MB file (well within 25MB limit)
    file_size = 1 * 1024 * 1024

    # Should not raise any exception
    validate_file_size(file_size)


def test_validate_file_size_at_limit():
    """Test that file exactly at size limit passes validation."""
    from src.config import settings

    # Exactly at the limit
    file_size = settings.max_upload_size_bytes

    # Should not raise any exception
    validate_file_size(file_size)


def test_validate_file_size_exceeds_limit():
    """Test that file exceeding size limit raises FileTooLargeError."""
    from src.config import settings

    # 1 byte over the limit
    file_size = settings.max_upload_size_bytes + 1

    with pytest.raises(FileTooLargeError) as exc_info:
        validate_file_size(file_size)

    error_message = str(exc_info.value)
    assert "exceeds maximum" in error_message
    assert str(file_size) in error_message


def test_validate_file_size_zero():
    """Test that zero-byte files are allowed."""
    # Should not raise any exception
    validate_file_size(0)


# ==============================================================================
# Upload File Validation Tests
# ==============================================================================


def test_validate_upload_file_valid_jpeg(sample_jpeg_bytes):
    """Test validation of valid JPEG file."""
    file = io.BytesIO(sample_jpeg_bytes)

    mime_type, file_size = validate_upload_file(file)

    assert mime_type == "image/jpeg"
    assert file_size == len(sample_jpeg_bytes)
    # File pointer should be reset to beginning
    assert file.tell() == 0


def test_validate_upload_file_valid_png(sample_png_bytes):
    """Test validation of valid PNG file."""
    file = io.BytesIO(sample_png_bytes)

    mime_type, file_size = validate_upload_file(file)

    assert mime_type == "image/png"
    assert file_size == len(sample_png_bytes)


def test_validate_upload_file_valid_pdf(sample_pdf_bytes):
    """Test validation of valid PDF file."""
    file = io.BytesIO(sample_pdf_bytes)

    mime_type, file_size = validate_upload_file(file)

    assert mime_type == "application/pdf"
    assert file_size == len(sample_pdf_bytes)


def test_validate_upload_file_invalid_format(invalid_file_bytes):
    """Test that invalid file format raises UnsupportedFormatError."""
    file = io.BytesIO(invalid_file_bytes)

    with pytest.raises(UnsupportedFormatError):
        validate_upload_file(file)


def test_validate_upload_file_too_large():
    """Test that oversized file raises FileTooLargeError."""
    from src.config import settings

    # Create file that exceeds max_upload_size_bytes (25MB)
    oversized_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * (settings.max_upload_size_bytes + 1000)
    file = io.BytesIO(oversized_bytes)

    with pytest.raises(FileTooLargeError):
        validate_upload_file(file)


# ==============================================================================
# Sync File Size Validation Tests (FastAPI Dependency)
# ==============================================================================


@pytest.mark.asyncio
async def test_validate_sync_file_size_valid(sample_jpeg_bytes):
    """Test that file within sync size limit passes validation."""
    file_obj = io.BytesIO(sample_jpeg_bytes)
    upload_file = UploadFile(filename="test.jpg", file=file_obj)

    # Should return the same file without raising exception
    result = await validate_sync_file_size(upload_file)

    assert result is upload_file
    # File pointer should be reset
    await upload_file.seek(0)
    content = await upload_file.read()
    assert content == sample_jpeg_bytes


@pytest.mark.asyncio
async def test_validate_sync_file_size_too_large(large_file_bytes):
    """Test that file exceeding sync size limit raises HTTPException 413."""
    file_obj = io.BytesIO(large_file_bytes)
    upload_file = UploadFile(filename="large.jpg", file=file_obj)

    with pytest.raises(HTTPException) as exc_info:
        await validate_sync_file_size(upload_file)

    assert exc_info.value.status_code == 413
    assert "exceeds" in exc_info.value.detail.lower()
    assert "async" in exc_info.value.detail.lower()  # Suggests async endpoint


@pytest.mark.asyncio
async def test_validate_sync_file_size_at_limit():
    """Test file exactly at sync size limit (5MB)."""
    from src.config import settings

    # Create file exactly at 5MB limit
    file_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * (settings.sync_max_file_size_bytes - 4)
    file_obj = io.BytesIO(file_bytes)
    upload_file = UploadFile(filename="at_limit.jpg", file=file_obj)

    # Should pass
    result = await validate_sync_file_size(upload_file)
    assert result is upload_file
