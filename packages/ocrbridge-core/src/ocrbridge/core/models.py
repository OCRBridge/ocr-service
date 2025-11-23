"""Base models for OCR engine parameters."""

from pydantic import BaseModel


class OCREngineParams(BaseModel):
    """Base class for all engine-specific parameters.

    Engine implementations should subclass this model to define their specific
    parameters with appropriate validation rules.

    Example:
        class TesseractParams(OCREngineParams):
            lang: str = "eng"
            psm: int = Field(default=3, ge=0, le=13)
    """

    class Config:
        extra = "forbid"  # Reject unknown parameters to catch typos/errors
