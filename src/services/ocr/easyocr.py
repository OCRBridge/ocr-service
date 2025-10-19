"""EasyOCR engine implementation for deep learning-based OCR."""

import logging
from pathlib import Path
from typing import Optional

from src.models.ocr_params import EasyOCRParams
from src.services.ocr.base import OCREngine
from src.utils.gpu import get_easyocr_device

logger = logging.getLogger(__name__)


class EasyOCREngine(OCREngine):
    """
    EasyOCR engine implementation.

    Uses deep learning models for multilingual OCR with automatic GPU acceleration.
    GPU is automatically detected and used when available, with graceful fallback to CPU.
    Supports 80+ languages with superior accuracy for Asian scripts.
    """

    def __init__(self, params: Optional[EasyOCRParams] = None):
        """
        Initialize EasyOCR engine with parameters.

        Args:
            params: EasyOCR-specific parameters (languages, thresholds)
        """
        self.params = params or EasyOCRParams()
        self.reader = None
        logger.info(
            "easyocr_engine_initialized",
            languages=self.params.languages,
            text_threshold=self.params.text_threshold,
            link_threshold=self.params.link_threshold,
        )

    def create_easyocr_reader(self):
        """
        Create EasyOCR Reader instance with specified configuration.

        Models are cached after first initialization for performance.
        Automatically detects and uses GPU if available, falls back to CPU gracefully.

        Returns:
            easyocr.Reader instance
        """
        try:
            import easyocr
        except ImportError as e:
            raise RuntimeError(
                "EasyOCR not installed. Install with: pip install easyocr"
            ) from e

        # Automatically determine device (GPU or CPU)
        use_gpu, device_name = get_easyocr_device()

        logger.info(
            "creating_easyocr_reader",
            languages=self.params.languages,
            gpu_used=use_gpu,
            device=device_name,
        )

        # Create reader with language list and GPU setting
        reader = easyocr.Reader(
            lang_list=self.params.languages,
            gpu=use_gpu,
        )

        return reader

    def process(self, file_path: Path, params: Optional[EasyOCRParams] = None) -> str:
        """
        Process document with EasyOCR and return HOCR XML.

        Args:
            file_path: Path to image or PDF file
            params: EasyOCR parameters (uses instance params if not provided)

        Returns:
            HOCR XML string with recognized text and bounding boxes

        Raises:
            RuntimeError: If EasyOCR processing fails
            ValueError: If file format not supported
            TimeoutError: If processing exceeds timeout
        """
        if params:
            self.params = params

        # Validate file exists
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info("easyocr_processing_started", file_path=str(file_path))

        # Create reader (cached on subsequent calls for same languages)
        if self.reader is None:
            self.reader = self.create_easyocr_reader()

        # Process image with EasyOCR
        try:
            results = self.reader.readtext(
                str(file_path),
                detail=1,  # Include bounding boxes and confidence
                paragraph=False,  # Return individual text boxes
            )
        except Exception as e:
            logger.error("easyocr_processing_failed", error=str(e), file_path=str(file_path))
            raise RuntimeError(f"EasyOCR processing failed: {e}") from e

        logger.info(
            "easyocr_processing_completed",
            file_path=str(file_path),
            text_boxes_found=len(results),
        )

        # Convert results to HOCR format
        hocr_output = self.to_hocr(results, file_path)

        return hocr_output

    def to_hocr(self, easyocr_results: list, image_path: Path) -> str:
        """
        Convert EasyOCR results to HOCR XML format.

        Args:
            easyocr_results: List of (bbox, text, confidence) tuples from EasyOCR
            image_path: Path to original image (for dimensions)

        Returns:
            HOCR XML string
        """
        from src.utils.hocr import easyocr_to_hocr

        # Get image dimensions
        try:
            from PIL import Image

            with Image.open(image_path) as img:
                image_width, image_height = img.size
        except Exception as e:
            logger.warning(
                "failed_to_get_image_dimensions",
                error=str(e),
                using_defaults=True,
            )
            # Use default dimensions if image can't be opened
            image_width, image_height = 1000, 1000

        # Convert to HOCR
        hocr_xml = easyocr_to_hocr(easyocr_results, image_width, image_height)

        return hocr_xml
