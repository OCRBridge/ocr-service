"""Data models for engine-specific OCR parameters."""

import re
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from src.utils.validators import EASYOCR_SUPPORTED_LANGUAGES


class TesseractParams(BaseModel):
    """OCR configuration parameters with validation."""

    _LANGUAGE_SEGMENT_PATTERN = re.compile(r"^[a-z_]{3,7}$")
    _MAX_LANGUAGES = 5

    lang: str | None = Field(
        default=None,
        pattern=r"^[a-z_]{3,7}(\+[a-z_]{3,7})*$",
        description="Language code(s): 'eng', 'fra', 'eng+fra' (max 5)",
        examples=["eng", "eng+fra", "eng+fra+deu"],
    )

    psm: int | None = Field(
        default=None,
        ge=0,
        le=13,
        description="Page segmentation mode (0-13)",
    )

    oem: int | None = Field(
        default=None,
        ge=0,
        le=3,
        description="OCR Engine mode: 0=Legacy, 1=LSTM, 2=Both, 3=Default",
    )

    dpi: int | None = Field(
        default=None, ge=70, le=2400, description="Image DPI (70-2400, typical: 300)"
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

        from src.utils.validators import get_installed_languages

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


class RecognitionLevel(str, Enum):
    """ocrmac recognition level options.

    Platform requirements:
    - fast, balanced, accurate: macOS 10.15+ (Vision framework)
    - livetext: macOS Sonoma 14.0+ (LiveText framework)

    Performance notes:
    - fast: ~131ms per image (fewer languages, faster processing)
    - balanced: ~150ms per image (default, good balance)
    - accurate: ~207ms per image (slower, highest accuracy)
    - livetext: ~174ms per image (enhanced accuracy, Sonoma+ only)
    """

    FAST = "fast"
    BALANCED = "balanced"
    ACCURATE = "accurate"
    LIVETEXT = "livetext"


class OcrmacParams(BaseModel):
    """ocrmac OCR engine parameters."""

    languages: list[str] | None = Field(
        default=None,
        description="Language codes in IETF BCP 47 format (e.g., en-US, fr-FR, zh-Hans). Max 5.",
        min_length=1,
        max_length=5,
        examples=[["en-US"], ["en-US", "fr-FR"], ["zh-Hans"]],
    )

    recognition_level: RecognitionLevel = Field(
        default=RecognitionLevel.BALANCED,
        description="Recognition level: fast (~131ms), balanced (default, ~150ms), accurate (~207ms), livetext (~174ms, requires macOS Sonoma 14.0+)",
    )

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, v: list[str] | None) -> list[str] | None:
        """Validate IETF BCP 47 language code format."""
        if v is None:
            return v

        if len(v) > 5:
            raise ValueError("Maximum 5 languages allowed")

        # IETF BCP 47 format: language[-Script][-Region]
        # Examples: en, en-US, zh-Hans, zh-Hans-CN
        pattern = r"^[a-z]{2,3}(-[A-Z][a-z]{3})?(-[A-Z]{2})?$"

        for lang in v:
            if not re.match(pattern, lang, re.IGNORECASE):
                raise ValueError(
                    f"Invalid IETF BCP 47 language code: '{lang}'. "
                    f"Expected format: 'en-US', 'fr-FR', 'zh-Hans'"
                )

        return v


class EasyOCRParams(BaseModel):
    """EasyOCR OCR engine parameters."""

    languages: list[str] = Field(
        default=["en"],
        description="EasyOCR language codes (e.g., 'en', 'ch_sim', 'ja'). Max 5 languages.",
        min_length=1,
        max_length=5,
        examples=[["en"], ["ch_sim", "en"], ["ja", "ko", "en"]],
    )

    text_threshold: float = Field(
        default=0.7,
        description="Confidence threshold for text detection (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    link_threshold: float = Field(
        default=0.7,
        description="Threshold for linking text regions (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, v: list[str]) -> list[str]:
        """Validate EasyOCR language codes against supported languages."""
        if not v:
            raise ValueError("At least one language required for EasyOCR")

        if len(v) > 5:
            raise ValueError("Maximum 5 languages allowed for EasyOCR")

        # Check all languages are supported
        invalid_langs = [lang for lang in v if lang not in EASYOCR_SUPPORTED_LANGUAGES]

        if invalid_langs:
            raise ValueError(
                f"Unsupported EasyOCR language codes: {invalid_langs}. "
                f"Use EasyOCR format (e.g., 'en', 'ch_sim', 'ja'), not Tesseract format ('eng', 'chi_sim')"
            )

        return v

    @field_validator("text_threshold", "link_threshold")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        """Validate threshold is within valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")

        return v
