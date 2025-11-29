"""Specification for OCRBridge v2.0 Parameter Models.

This file serves as a reference for updating the external `ocrbridge` packages.
The `ocr-service` will expect the installed packages to provide Pydantic models
matching these specifications.
"""

from enum import IntEnum
from typing import List, Optional

from pydantic import BaseModel, Field


class TesseractPSM(IntEnum):
    """Page Segmentation Modes for Tesseract."""
    OSD_ONLY = 0
    AUTO_OSD = 1
    AUTO_ONLY = 2
    AUTO = 3
    SINGLE_COLUMN = 4
    SINGLE_BLOCK_VERT = 5
    SINGLE_BLOCK = 6
    SINGLE_LINE = 7
    SINGLE_WORD = 8
    CIRCLE_WORD = 9
    SINGLE_CHAR = 10
    SPARSE_TEXT = 11
    SPARSE_TEXT_OSD = 12
    RAW_LINE = 13


class TesseractOEM(IntEnum):
    """OCR Engine Modes for Tesseract."""
    LEGACY_ONLY = 0
    LSTM_ONLY = 1
    LEGACY_LSTM = 2
    DEFAULT = 3


class TesseractParams(BaseModel):
    """Configuration parameters for Tesseract OCR engine."""
    
    lang: str = Field(
        default="eng",
        description="Language code(s) for OCR (e.g., 'eng', 'fra', 'eng+fra')."
    )
    psm: Optional[TesseractPSM] = Field(
        default=TesseractPSM.AUTO,
        description="Page Segmentation Mode."
    )
    oem: Optional[TesseractOEM] = Field(
        default=TesseractOEM.LSTM_ONLY,
        description="OCR Engine Mode."
    )
    dpi: int = Field(
        default=300,
        ge=70,
        le=2400,
        description="Image DPI for processing."
    )


class EasyOCRParams(BaseModel):
    """Configuration parameters for EasyOCR engine."""
    
    languages: List[str] = Field(
        default=["en"],
        min_length=1,
        description="List of language codes to recognize (e.g., ['en', 'fr'])."
    )
    gpu: bool = Field(
        default=True,
        description="Enable GPU acceleration if available."
    )
    detail: int = Field(
        default=1,
        ge=0,
        le=1,
        description="Output detail level (0=simple, 1=detailed)."
    )
    paragraph: bool = Field(
        default=False,
        description="Combine result into paragraph structure."
    )
    contrast_ths: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Contrast threshold for text detection."
    )
    adjust_contrast: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Contrast adjustment factor."
    )
