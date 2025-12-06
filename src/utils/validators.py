"File validation utilities for format and size checks."

from typing import IO

import magic
import structlog
from fastapi import HTTPException, UploadFile

from src.config import settings
from src.models.upload import FileFormat

logger = structlog.get_logger()


class UnsupportedFormatError(Exception):
    """Raised when file format is not supported."""

    pass


class FileTooLargeError(Exception):
    """Raised when file size exceeds maximum limit."""

    pass


# Supported MIME types
SUPPORTED_MIME_TYPES = {format.value for format in FileFormat}


def validate_file_format(file_header: bytes) -> str:
    """
    Validate file format using python-magic (libmagic).

    Args:
        file_header: File header bytes (at least 2048 bytes recommended)

    Returns:
        MIME type string if format is supported

    Raises:
        UnsupportedFormatError: If format is not supported
    """
    try:
        # Detect MIME type from buffer
        mime_type = magic.from_buffer(file_header, mime=True)
    except Exception as e:
        logger.error("magic_detection_failed", error=str(e))
        raise UnsupportedFormatError(f"Failed to detect file format: {e}")

    if mime_type not in SUPPORTED_MIME_TYPES:
        raise UnsupportedFormatError(
            f"Unsupported file format: {mime_type}. Supported: JPEG, PNG, PDF, TIFF"
        )

    return mime_type


def validate_file_size(file_size: int) -> None:
    """
    Validate file size is within limits.

    Args:
        file_size: File size in bytes

    Raises:
        FileTooLargeError: If file size exceeds maximum
    """
    max_size = settings.max_upload_size_bytes
    if file_size > max_size:
        raise FileTooLargeError(
            f"File size {file_size} bytes exceeds maximum {max_size} bytes ({settings.max_upload_size_mb}MB)"
        )


def validate_upload_file(file: IO[bytes]) -> tuple[str, int]:
    """
    Validate uploaded file format and size.

    Args:
        file: File object to validate

    Returns:
        Tuple of (mime_type, file_size)

    Raises:
        UnsupportedFormatError: If format not supported
        FileTooLargeError: If file too large
    """
    # Read header for magic detection (2KB is usually sufficient)
    header = file.read(2048)
    mime_type = validate_file_format(header)

    # Reset file pointer
    file.seek(0)

    # Get file size
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning

    # Validate size
    validate_file_size(file_size)

    return mime_type, file_size


# Synchronous endpoint file size validation
SYNC_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB


async def validate_sync_file_size(file: UploadFile) -> UploadFile:
    """Validate file size for synchronous OCR endpoints.

    Args:
        file: Uploaded file from FastAPI

    Returns:
        Same file if valid

    Raises:
        HTTPException: 413 Payload Too Large if file exceeds limit
    """
    # Use the underlying SpooledTemporaryFile to get size without reading content
    # This avoids loading the entire file into memory for size check.
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning for subsequent processing

    sync_max_size = settings.sync_max_file_size_bytes
    if file_size > sync_max_size:
        size_mb = file_size / (1024 * 1024)
        limit_mb = settings.sync_max_file_size_mb
        raise HTTPException(
            status_code=413,
            detail=f"File size ({size_mb:.2f}MB) exceeds {limit_mb}MB limit. "
            f"Use async endpoints (/upload/{{engine}}) for larger files.",
        )

    return file
