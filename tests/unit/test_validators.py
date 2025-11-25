"""Unit tests for file validation utilities.

Security-critical tests for magic byte detection, file size validation,
and Tesseract configuration building.
"""

import io
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, UploadFile

from src.utils.validators import (
    DEFAULT_TESSERACT_LANGUAGES,
    MAGIC_BYTES,
    FileTooLargeError,
    TesseractConfig,
    UnsupportedFormatError,
    build_tesseract_config,
    get_installed_languages,
    validate_file_format,
    validate_file_size,
    validate_sync_file_size,
    validate_upload_file,
)


# ==============================================================================
# Magic Byte Validation Tests
# ==============================================================================


@pytest.mark.parametrize(
    "magic_bytes,expected_mime",
    [
        (b"\xff\xd8\xff", "image/jpeg"),
        (b"\xff\xd8\xff\xe0", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\n", "image/png"),
        (b"%PDF-", "application/pdf"),
        (b"%PDF-1.4", "application/pdf"),
        (b"II*\x00", "image/tiff"),  # Little-endian TIFF
        (b"MM\x00*", "image/tiff"),  # Big-endian TIFF
    ],
)
def test_validate_file_format_valid(magic_bytes, expected_mime):
    """Test magic byte detection for all supported formats."""
    # Pad with additional bytes to simulate real file header
    header = magic_bytes + b"\x00" * 10

    result = validate_file_format(header)

    assert result == expected_mime


def test_validate_file_format_unsupported():
    """Test that unsupported formats raise UnsupportedFormatError."""
    invalid_header = b"INVALID_FORMAT\x00" * 10

    with pytest.raises(UnsupportedFormatError) as exc_info:
        validate_file_format(invalid_header)

    assert "Unsupported file format" in str(exc_info.value)
    assert "JPEG" in str(exc_info.value)
    assert "PNG" in str(exc_info.value)


def test_validate_file_format_empty():
    """Test that empty file header raises UnsupportedFormatError."""
    with pytest.raises(UnsupportedFormatError):
        validate_file_format(b"")


def test_validate_file_format_short_header():
    """Test that short headers (less than magic bytes) raise UnsupportedFormatError."""
    with pytest.raises(UnsupportedFormatError):
        validate_file_format(b"\xff\xd8")  # Incomplete JPEG header


def test_magic_bytes_constant():
    """Test that MAGIC_BYTES constant is correctly defined."""
    assert b"\xff\xd8\xff" in MAGIC_BYTES
    assert b"\x89PNG\r\n\x1a\n" in MAGIC_BYTES
    assert b"%PDF-" in MAGIC_BYTES
    assert b"II*\x00" in MAGIC_BYTES
    assert b"MM\x00*" in MAGIC_BYTES
    assert len(MAGIC_BYTES) == 5


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


# ==============================================================================
# Tesseract Language Detection Tests
# ==============================================================================


def test_get_installed_languages_success():
    """Test successful tesseract language detection."""
    mock_output = "List of available languages (3):\neng\nfra\ndeu\n"

    with patch("subprocess.run") as mock_run:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = mock_output
        mock_run.return_value = mock_result

        # Clear cache before test
        get_installed_languages.cache_clear()

        languages = get_installed_languages()

        assert "eng" in languages
        assert "fra" in languages
        assert "deu" in languages
        # Should also include defaults
        assert DEFAULT_TESSERACT_LANGUAGES.issubset(languages)


def test_get_installed_languages_command_not_found():
    """Test fallback when tesseract command not found."""
    with patch("subprocess.run", side_effect=FileNotFoundError):
        get_installed_languages.cache_clear()

        languages = get_installed_languages()

        # Should return default languages
        assert languages == DEFAULT_TESSERACT_LANGUAGES


def test_get_installed_languages_command_fails():
    """Test fallback when tesseract command fails."""
    with patch("subprocess.run") as mock_run:
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Error: tesseract not found"
        mock_run.return_value = mock_result

        get_installed_languages.cache_clear()

        languages = get_installed_languages()

        # Should return default languages
        assert languages == DEFAULT_TESSERACT_LANGUAGES


def test_get_installed_languages_timeout():
    """Test fallback when tesseract command times out."""
    import subprocess

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("tesseract", 5)):
        get_installed_languages.cache_clear()

        languages = get_installed_languages()

        # Should return default languages
        assert languages == DEFAULT_TESSERACT_LANGUAGES


def test_get_installed_languages_cached():
    """Test that language detection is cached."""
    mock_output = "List of available languages (1):\neng\n"

    with patch("subprocess.run") as mock_run:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = mock_output
        mock_run.return_value = mock_result

        get_installed_languages.cache_clear()

        # First call
        languages1 = get_installed_languages()
        # Second call
        languages2 = get_installed_languages()

        # Should only call subprocess once
        assert mock_run.call_count == 1
        assert languages1 == languages2


def test_default_tesseract_languages_constant():
    """Test that DEFAULT_TESSERACT_LANGUAGES contains common languages."""
    assert "eng" in DEFAULT_TESSERACT_LANGUAGES
    assert "fra" in DEFAULT_TESSERACT_LANGUAGES
    assert "deu" in DEFAULT_TESSERACT_LANGUAGES
    assert "spa" in DEFAULT_TESSERACT_LANGUAGES
    assert len(DEFAULT_TESSERACT_LANGUAGES) >= 5


# ==============================================================================
# Tesseract Config Building Tests
# ==============================================================================


def test_build_tesseract_config_all_defaults():
    """Test config building with all default values."""
    config = build_tesseract_config()

    assert config.lang == "eng"
    assert config.config_string == ""  # No options specified


def test_build_tesseract_config_custom_lang():
    """Test config building with custom language."""
    config = build_tesseract_config(lang="fra")

    assert config.lang == "fra"
    assert config.config_string == ""


def test_build_tesseract_config_with_psm():
    """Test config building with PSM parameter."""
    config = build_tesseract_config(psm=6)

    assert config.lang == "eng"
    assert "--psm 6" in config.config_string


def test_build_tesseract_config_with_oem():
    """Test config building with OEM parameter."""
    config = build_tesseract_config(oem=1)

    assert config.lang == "eng"
    assert "--oem 1" in config.config_string


def test_build_tesseract_config_with_dpi():
    """Test config building with DPI parameter."""
    config = build_tesseract_config(dpi=300)

    assert config.lang == "eng"
    assert "--dpi 300" in config.config_string


def test_build_tesseract_config_all_params():
    """Test config building with all parameters specified."""
    config = build_tesseract_config(lang="eng+fra", psm=3, oem=1, dpi=300)

    assert config.lang == "eng+fra"
    assert "--psm 3" in config.config_string
    assert "--oem 1" in config.config_string
    assert "--dpi 300" in config.config_string


def test_build_tesseract_config_none_params():
    """Test that None parameters are omitted from config string."""
    config = build_tesseract_config(lang="deu", psm=None, oem=None, dpi=None)

    assert config.lang == "deu"
    assert config.config_string == ""
    assert "psm" not in config.config_string
    assert "oem" not in config.config_string
    assert "dpi" not in config.config_string


def test_build_tesseract_config_ordering():
    """Test that config options maintain consistent ordering."""
    config = build_tesseract_config(dpi=300, psm=6, oem=1)

    # Options should appear in specific order: psm, oem, dpi
    parts = config.config_string.split()
    assert parts.index("--psm") < parts.index("--oem")
    assert parts.index("--oem") < parts.index("--dpi")


def test_tesseract_config_dataclass():
    """Test TesseractConfig dataclass structure."""
    config = TesseractConfig(lang="eng", config_string="--psm 3")

    assert isinstance(config, TesseractConfig)
    assert config.lang == "eng"
    assert config.config_string == "--psm 3"


# ==============================================================================
# EasyOCR Language Support Tests
# ==============================================================================


def test_easyocr_supported_languages():
    """Test that EASYOCR_SUPPORTED_LANGUAGES constant is defined."""
    from src.utils.validators import EASYOCR_SUPPORTED_LANGUAGES

    assert "en" in EASYOCR_SUPPORTED_LANGUAGES
    assert "fr" in EASYOCR_SUPPORTED_LANGUAGES
    assert "ch_sim" in EASYOCR_SUPPORTED_LANGUAGES
    assert "ja" in EASYOCR_SUPPORTED_LANGUAGES
    assert len(EASYOCR_SUPPORTED_LANGUAGES) > 50  # EasyOCR supports 80+ languages
