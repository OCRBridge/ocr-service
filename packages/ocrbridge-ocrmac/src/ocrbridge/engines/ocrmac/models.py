"""ocrmac OCR engine parameter models."""

import re
from enum import Enum

from ocrbridge.core.models import OCREngineParams
from pydantic import Field, field_validator


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


class OcrmacParams(OCREngineParams):
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
