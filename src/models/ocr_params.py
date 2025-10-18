"""Data models for engine-specific OCR parameters."""

import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


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
