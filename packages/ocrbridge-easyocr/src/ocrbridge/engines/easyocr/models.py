"""EasyOCR engine parameter models."""

from ocrbridge.core.models import OCREngineParams
from pydantic import Field, field_validator

# EasyOCR supported languages (80+ languages)
EASYOCR_SUPPORTED_LANGUAGES = {
    # Latin scripts
    "en", "fr", "de", "es", "pt", "it", "nl", "pl", "ru", "tr",
    "sv", "cs", "da", "no", "fi", "ro", "hu", "sk", "hr", "sr",
    "bg", "uk", "be", "lt", "lv", "et", "sl", "sq", "is", "ga",
    "cy", "af", "ms", "id", "tl", "vi", "sw",
    # Asian scripts
    "ch_sim", "ch_tra", "ja", "ko", "th", "hi", "bn", "ta", "te",
    "kn", "ml", "mr", "ne", "si", "ur", "fa", "ar", "he", "my",
    "km", "lo", "ka", "hy", "mn",
    # Additional
    "az", "kk", "uz", "ky", "tg", "pa", "gu", "or", "as", "oc",
    "eu", "ca", "gl", "mt", "la", "eo", "mi",
}


class EasyOCRParams(OCREngineParams):
    """EasyOCR engine parameters with validation."""

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
