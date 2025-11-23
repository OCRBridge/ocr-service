"""Base OCR engine interface."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TypeVar

from .models import OCREngineParams

T = TypeVar("T", bound=OCREngineParams)


class OCREngine(ABC):
    """Abstract base class for OCR engines.

    All OCR engines must inherit from this class and implement the required
    abstract methods and properties. This ensures a consistent interface across
    all engines and enables dynamic engine discovery via entry points.
    """

    @abstractmethod
    def process(self, file_path: Path, params: T | None = None) -> str:
        """Process a document and return HOCR XML output.

        Args:
            file_path: Path to the image or PDF file to process
            params: Engine-specific parameters (subclass of OCREngineParams)

        Returns:
            HOCR XML as a string conforming to the hOCR standard

        Raises:
            OCRProcessingError: If processing fails for any reason
            UnsupportedFormatError: If file format is not supported by this engine
            TimeoutError: If processing exceeds the configured timeout
            InvalidParametersError: If provided parameters are invalid
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the engine name identifier.

        This name is used for engine discovery and selection. It should be
        lowercase and match the entry point name.

        Returns:
            Engine name (e.g., 'tesseract', 'easyocr', 'ocrmac')
        """
        pass

    @property
    @abstractmethod
    def supported_formats(self) -> set[str]:
        """Return set of supported file extensions.

        Returns:
            Set of file extensions including the dot (e.g., {'.jpg', '.png', '.pdf'})
        """
        pass
