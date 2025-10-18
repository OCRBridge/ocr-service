"""Base OCR engine interface."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

from src.models import TesseractParams
from src.models.ocr_params import OcrmacParams


class OCREngine(ABC):
    """Abstract base class for OCR engines."""

    @abstractmethod
    def process(
        self, file_path: Path, params: Union[TesseractParams, OcrmacParams, None]
    ) -> str:
        """
        Process a document and return HOCR XML output.

        Args:
            file_path: Path to the document to process
            params: Engine-specific parameters

        Returns:
            HOCR XML string

        Raises:
            ValueError: If parameters are invalid
            RuntimeError: If OCR processing fails
            TimeoutError: If processing exceeds timeout
        """
        pass
