"""Data models for engine-specific OCR parameters."""

import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from src.utils.validators import EASYOCR_SUPPORTED_LANGUAGES


class RecognitionLevel(str, Enum):
    """ocrmac recognition level options."""

    FAST = "fast"
    BALANCED = "balanced"
    ACCURATE = "accurate"


class OcrmacParams(BaseModel):
    """ocrmac OCR engine parameters."""

    languages: Optional[list[str]] = Field(
        None,
        description="Language codes in IETF BCP 47 format (e.g., en-US, fr-FR, zh-Hans). Max 5.",
        min_length=1,
        max_length=5,
        examples=[["en-US"], ["en-US", "fr-FR"], ["zh-Hans"]],
    )

    recognition_level: RecognitionLevel = Field(
        RecognitionLevel.BALANCED,
        description="Recognition level: fast (fewer languages, faster), balanced (default), accurate (slower)",
    )

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, v: Optional[list[str]]) -> Optional[list[str]]:
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

    gpu: bool = Field(
        default=False,
        description="Enable GPU acceleration for EasyOCR processing (requires CUDA)",
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
