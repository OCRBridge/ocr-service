"""OCR Bridge Core - Base interfaces and utilities for OCR engines."""

from .base import OCREngine
from .exceptions import (
    EngineNotAvailableError,
    InvalidParametersError,
    OCRBridgeError,
    OCRProcessingError,
    UnsupportedFormatError,
)
from .models import OCREngineParams

__all__ = [
    "OCREngine",
    "OCREngineParams",
    "OCRBridgeError",
    "OCRProcessingError",
    "UnsupportedFormatError",
    "EngineNotAvailableError",
    "InvalidParametersError",
]

__version__ = "0.1.0"
