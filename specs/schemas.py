"""Specification for OCRBridge v2.0 Parameter Models.

This file serves as a reference for updating the external `ocrbridge` packages.
The `ocr-service` will expect the installed packages to provide Pydantic models
matching these specifications.
"""

from enum import IntEnum

from ocrbridge.core.models import OCREngineParams
from pydantic import ConfigDict, Field


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


class TesseractParams(OCREngineParams):
    """Configuration parameters for Tesseract OCR engine."""

    model_config = ConfigDict(extra="forbid")

    lang: str = Field(
        default="eng", description="Language code(s) for OCR (e.g., 'eng', 'fra', 'eng+fra')."
    )
    psm: TesseractPSM | None = Field(
        default=TesseractPSM.AUTO, description="Page Segmentation Mode."
    )
    oem: TesseractOEM | None = Field(default=TesseractOEM.LSTM_ONLY, description="OCR Engine Mode.")
    dpi: int = Field(default=300, ge=70, le=2400, description="Image DPI for processing.")
