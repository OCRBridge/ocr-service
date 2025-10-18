"""File validation utilities for format and size checks."""

from typing import IO

from src.config import settings


class UnsupportedFormatError(Exception):
    """Raised when file format is not supported."""

    pass


class FileTooLargeError(Exception):
    """Raised when file size exceeds maximum limit."""

    pass


# Magic byte signatures for supported formats
MAGIC_BYTES = {
    b"\xff\xd8\xff": "image/jpeg",  # JPEG
    b"\x89PNG\r\n\x1a\n": "image/png",  # PNG
    b"%PDF-": "application/pdf",  # PDF
    b"II*\x00": "image/tiff",  # TIFF (little-endian)
    b"MM\x00*": "image/tiff",  # TIFF (big-endian)
}


def validate_file_format(file_header: bytes) -> str:
    """
    Validate file format using magic bytes.

    Args:
        file_header: First 8-12 bytes of the file

    Returns:
        MIME type string if format is supported

    Raises:
        UnsupportedFormatError: If format is not supported
    """
    for magic, mime_type in MAGIC_BYTES.items():
        if file_header.startswith(magic):
            return mime_type

    raise UnsupportedFormatError("Unsupported file format. Supported: JPEG, PNG, PDF, TIFF")


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
    # Read magic bytes
    header = file.read(12)
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
