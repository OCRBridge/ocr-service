"""File validation utilities for format and size checks."""

import functools
import subprocess
from dataclasses import dataclass
from typing import IO

import structlog
from fastapi import HTTPException, UploadFile

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

DEFAULT_TESSERACT_LANGUAGES = {
    "eng",
    "fra",
    "deu",
    "spa",
    "ita",
    "por",
    "rus",
    "ara",
    "chi_sim",
    "jpn",
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
    # Read file to determine size
    contents = await file.read()
    file_size = len(contents)

    # Reset file pointer for subsequent processing
    await file.seek(0)

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


# Tesseract parameter validation utilities

tesseract_logger = structlog.get_logger()


@functools.lru_cache(maxsize=1)
def get_installed_languages() -> set[str]:
    """
    Get list of installed Tesseract language data files.

    Uses subprocess to call 'tesseract --list-langs' and caches the result.
    Fallback to common languages if command fails.

    Returns:
        Set of installed language codes (e.g., {'eng', 'fra', 'deu'})
    """
    try:
        result = subprocess.run(
            ["tesseract", "--list-langs"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            # Parse output, skip header line "List of available languages (N):"
            langs = result.stdout.strip().split("\n")[1:]
            installed = {lang.strip() for lang in langs if lang.strip()}
            installed.update(DEFAULT_TESSERACT_LANGUAGES)

            tesseract_logger.info(
                "tesseract_languages_detected",
                count=len(installed),
                languages=sorted(installed)[:10],  # Log first 10
            )

            return installed
        else:
            tesseract_logger.warning(
                "tesseract_list_langs_failed",
                returncode=result.returncode,
                stderr=result.stderr,
            )
            # Fallback to common languages
            return set(DEFAULT_TESSERACT_LANGUAGES)

    except FileNotFoundError:
        tesseract_logger.error("tesseract_not_found")
        # Fallback to default languages
        return set(DEFAULT_TESSERACT_LANGUAGES)
    except subprocess.TimeoutExpired:
        tesseract_logger.error("tesseract_list_langs_timeout")
        return set(DEFAULT_TESSERACT_LANGUAGES)
    except Exception as e:
        tesseract_logger.error("tesseract_list_langs_error", error=str(e))
        return set(DEFAULT_TESSERACT_LANGUAGES)


@dataclass
class TesseractConfig:
    """Resolved Tesseract configuration for processing."""

    lang: str  # Never None, defaults to 'eng'
    config_string: str  # CLI config string (e.g., "--psm 6 --oem 1 --dpi 300")


def build_tesseract_config(
    lang: str | None = None,
    psm: int | None = None,
    oem: int | None = None,
    dpi: int | None = None,
) -> TesseractConfig:
    """
    Build Tesseract configuration from validated parameters.

    Converts optional parameters to resolved config with defaults applied.

    Args:
        lang: Language code(s), defaults to 'eng' if None
        psm: Page segmentation mode (0-13), omitted if None
        oem: OCR engine mode (0-3), omitted if None
        dpi: Image DPI (70-2400), omitted if None

    Returns:
        TesseractConfig with resolved language and config string
    """
    # Default language to English if not specified
    resolved_lang = lang or "eng"

    # Build config string from non-None parameters
    config_parts = []

    if psm is not None:
        config_parts.append(f"--psm {psm}")

    if oem is not None:
        config_parts.append(f"--oem {oem}")

    if dpi is not None:
        config_parts.append(f"--dpi {dpi}")

    config_string = " ".join(config_parts)

    return TesseractConfig(lang=resolved_lang, config_string=config_string)


# EasyOCR parameter validation utilities

EASYOCR_SUPPORTED_LANGUAGES = {
    # Latin scripts
    "en",  # English
    "fr",  # French
    "de",  # German
    "es",  # Spanish
    "pt",  # Portuguese
    "it",  # Italian
    "nl",  # Dutch
    "pl",  # Polish
    "ru",  # Russian
    "tr",  # Turkish
    "sv",  # Swedish
    "cs",  # Czech
    "da",  # Danish
    "no",  # Norwegian
    "fi",  # Finnish
    "ro",  # Romanian
    "hu",  # Hungarian
    "sk",  # Slovak
    "hr",  # Croatian
    "sr",  # Serbian (Cyrillic)
    "bg",  # Bulgarian
    "uk",  # Ukrainian
    "be",  # Belarusian
    "lt",  # Lithuanian
    "lv",  # Latvian
    "et",  # Estonian
    "sl",  # Slovenian
    "sq",  # Albanian
    "is",  # Icelandic
    "ga",  # Irish
    "cy",  # Welsh
    "af",  # Afrikaans
    "ms",  # Malay
    "id",  # Indonesian
    "tl",  # Tagalog
    "vi",  # Vietnamese
    "sw",  # Swahili
    # Asian scripts
    "ch_sim",  # Chinese (Simplified)
    "ch_tra",  # Chinese (Traditional)
    "ja",  # Japanese
    "ko",  # Korean
    "th",  # Thai
    "hi",  # Hindi
    "bn",  # Bengali
    "ta",  # Tamil
    "te",  # Telugu
    "kn",  # Kannada
    "ml",  # Malayalam
    "mr",  # Marathi
    "ne",  # Nepali
    "si",  # Sinhala
    "ur",  # Urdu
    "fa",  # Persian (Farsi)
    "ar",  # Arabic
    "he",  # Hebrew
    "my",  # Burmese
    "km",  # Khmer
    "lo",  # Lao
    "ka",  # Georgian
    "hy",  # Armenian
    "mn",  # Mongolian
    # Additional languages
    "az",  # Azerbaijani
    "kk",  # Kazakh
    "uz",  # Uzbek
    "ky",  # Kyrgyz
    "tg",  # Tajik
    "pa",  # Punjabi
    "gu",  # Gujarati
    "or",  # Oriya
    "as",  # Assamese
    "oc",  # Occitan
    "eu",  # Basque
    "ca",  # Catalan
    "gl",  # Galician
    "mt",  # Maltese
    "la",  # Latin
    "eo",  # Esperanto
    "mi",  # Maori
}
