"""Pydantic models for API request/response and validation."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TesseractParams(BaseModel):
    """OCR configuration parameters with validation."""

    lang: str | None = Field(
        default=None,
        pattern=r"^[a-z]{3}(\+[a-z]{3})*$",
        description="Language code(s): 'eng', 'fra', 'eng+fra' (max 5)",
        examples=["eng", "eng+fra", "eng+fra+deu"],
    )

    psm: Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13] | None = Field(
        default=None, description="Page segmentation mode (0-13)"
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

    @field_validator("lang", mode="after")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        """Validate language count and availability."""
        if v is None:
            return v

        # Max 5 languages
        langs = v.split("+")
        if len(langs) > 5:
            raise ValueError(f"Maximum 5 languages allowed, got {len(langs)}")

        # Check installed (cached)
        from src.utils.validators import get_installed_languages

        installed = get_installed_languages()
        invalid = [lang for lang in langs if lang not in installed]

        if invalid:
            available_sample = ", ".join(sorted(installed)[:10])
            raise ValueError(
                f"Language(s) not installed: {', '.join(invalid)}. Available: {available_sample}..."
            )

        return v
