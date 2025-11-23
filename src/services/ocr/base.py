"""Base OCR engine interface."""

from abc import ABC, abstractmethod
from pathlib import Path

from src.models.ocr_params import EasyOCRParams, OcrmacParams, TesseractParams


class OCREngine(ABC):
    """Abstract base class for OCR engines."""

    @abstractmethod
    def process(
        self, file_path: Path, params: TesseractParams | OcrmacParams | EasyOCRParams | None
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
