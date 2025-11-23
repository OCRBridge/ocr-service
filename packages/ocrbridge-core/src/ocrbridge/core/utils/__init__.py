"""Utility modules for OCR Bridge."""

from .hocr import (
    HOCRInfo,
    HOCRParseError,
    HOCRValidationError,
    easyocr_to_hocr,
    extract_bbox,
    parse_hocr,
    validate_hocr,
)

__all__ = [
    "HOCRInfo",
    "HOCRParseError",
    "HOCRValidationError",
    "parse_hocr",
    "validate_hocr",
    "extract_bbox",
    "easyocr_to_hocr",
]
