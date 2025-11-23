"""Tesseract OCR engine parameter models."""

import functools
import re
import subprocess

from ocrbridge.core.models import OCREngineParams
from pydantic import Field, field_validator

# Default fallback languages if tesseract --list-langs fails
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
            return installed
        else:
            # Fallback to common languages
            return set(DEFAULT_TESSERACT_LANGUAGES)

    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        # Fallback to default languages
        return set(DEFAULT_TESSERACT_LANGUAGES)


class TesseractParams(OCREngineParams):
    """Tesseract OCR engine parameters with validation."""

    _LANGUAGE_SEGMENT_PATTERN = re.compile(r"^[a-z_]{3,7}$")
    _MAX_LANGUAGES = 5

    lang: str | None = Field(
        default="eng",
        pattern=r"^[a-z_]{3,7}(\+[a-z_]{3,7})*$",
        description="Language code(s): 'eng', 'fra', 'eng+fra' (max 5)",
        examples=["eng", "eng+fra", "eng+fra+deu"],
    )

    psm: int | None = Field(
        default=3,
        ge=0,
        le=13,
        description="Page segmentation mode (0-13)",
    )

    oem: int | None = Field(
        default=1,
        ge=0,
        le=3,
        description="OCR Engine mode: 0=Legacy, 1=LSTM, 2=Both, 3=Default",
    )

    dpi: int | None = Field(
        default=300, ge=70, le=2400, description="Image DPI for PDF conversion (70-2400)"
    )

    @field_validator("lang", mode="before")
    @classmethod
    def normalize_language(cls, v: str | None) -> str | None:
        """Normalize language codes to lowercase and trim whitespace."""
        if v is None:
            return v
        return v.strip().lower()

    @field_validator("lang", mode="after")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        """Validate language count, format, and availability."""
        if v is None:
            return v

        langs = v.split("+")

        if len(langs) > cls._MAX_LANGUAGES:
            raise ValueError(f"Maximum {cls._MAX_LANGUAGES} languages allowed, got {len(langs)}")

        invalid_format = [
            lang for lang in langs if not cls._LANGUAGE_SEGMENT_PATTERN.fullmatch(lang)
        ]
        if invalid_format:
            raise ValueError(
                f"Invalid language format: {', '.join(invalid_format)}. "
                "Use 3-7 lowercase letters or underscores (e.g., 'eng', 'chi_sim')."
            )

        installed = get_installed_languages()
        invalid = [lang for lang in langs if lang not in installed]

        if invalid:
            available_sample = ", ".join(sorted(installed)[:10])
            raise ValueError(
                f"Language(s) not installed: {', '.join(invalid)}. Available: {available_sample}..."
            )

        return v
