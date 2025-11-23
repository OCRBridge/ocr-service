"""EasyOCR engine implementation for deep learning-based OCR."""

import tempfile
from pathlib import Path

import numpy as np
from ocrbridge.core import OCREngine, OCRProcessingError, UnsupportedFormatError
from ocrbridge.core.utils import easyocr_to_hocr
from pdf2image import convert_from_path
from PIL import Image

from .models import EasyOCRParams


def detect_gpu_availability() -> bool:
    """Detect if CUDA GPU is available for EasyOCR.

    Returns:
        True if CUDA GPU is available, False otherwise
    """
    try:
        import torch

        return torch.cuda.is_available()
    except ImportError:
        return False
    except Exception:
        return False


def get_easyocr_device() -> tuple[bool, str]:
    """Automatically detect and determine the best device for EasyOCR.

    Returns:
        Tuple of (use_gpu, device_name)
    """
    if detect_gpu_availability():
        import torch

        device_name = f"cuda:{torch.cuda.current_device()}"
        return True, device_name
    else:
        return False, "cpu"


class EasyOCREngine(OCREngine):
    """EasyOCR engine implementation.

    Uses deep learning models for multilingual OCR with automatic GPU acceleration.
    GPU is automatically detected and used when available, with graceful fallback to CPU.
    Supports 80+ languages with superior accuracy for Asian scripts.
    """

    def __init__(self):
        """Initialize EasyOCR engine."""
        self.reader = None
        self._current_languages: list[str] | None = None

    @property
    def name(self) -> str:
        """Return engine name."""
        return "easyocr"

    @property
    def supported_formats(self) -> set[str]:
        """Return supported file extensions."""
        return {".jpg", ".jpeg", ".png", ".pdf", ".tiff", ".tif"}

    def _create_reader(self, languages: list[str]):
        """Create EasyOCR Reader instance with specified configuration.

        Args:
            languages: List of language codes

        Returns:
            easyocr.Reader instance
        """
        try:
            import easyocr
        except ImportError as e:
            raise OCRProcessingError(
                "EasyOCR not installed. Install with: pip install easyocr"
            ) from e

        # Automatically determine device (GPU or CPU)
        use_gpu, _ = get_easyocr_device()

        # Create reader with language list and GPU setting
        reader = easyocr.Reader(
            lang_list=languages,
            gpu=use_gpu,
        )

        return reader

    def process(self, file_path: Path, params: EasyOCRParams | None = None) -> str:
        """Process document with EasyOCR and return HOCR XML.

        Args:
            file_path: Path to image or PDF file
            params: EasyOCR parameters (languages, thresholds)

        Returns:
            HOCR XML string with recognized text and bounding boxes

        Raises:
            OCRProcessingError: If EasyOCR processing fails
            UnsupportedFormatError: If file format not supported
        """
        # Use defaults if no params provided
        if params is None:
            params = EasyOCRParams()

        # Validate file exists
        if not file_path.exists():
            raise OCRProcessingError(f"File not found: {file_path}")

        # Validate file format
        suffix = file_path.suffix.lower()
        if suffix not in self.supported_formats:
            raise UnsupportedFormatError(
                f"Unsupported file format: {suffix}. "
                f"Supported formats: {', '.join(sorted(self.supported_formats))}"
            )

        # Create or recreate reader if languages changed
        if self.reader is None or self._current_languages != params.languages:
            self.reader = self._create_reader(params.languages)
            self._current_languages = params.languages

        try:
            # Handle PDF separately
            if suffix == ".pdf":
                return self._process_pdf(file_path, params)
            else:
                return self._process_image(file_path, params)

        except Exception as e:
            raise OCRProcessingError(f"EasyOCR processing failed: {e}") from e

    def _process_image(self, image_path: Path, params: EasyOCRParams) -> str:
        """Process single image with EasyOCR.

        Args:
            image_path: Path to image file
            params: EasyOCR parameters

        Returns:
            HOCR XML string
        """
        # Process image with EasyOCR
        results = self.reader.readtext(  # type: ignore
            str(image_path),
            detail=1,  # Include bounding boxes and confidence
            paragraph=False,  # Return individual text boxes
        )

        # Convert results to HOCR format
        hocr_output = self._to_hocr(results, image_path)

        return hocr_output

    def _process_pdf(self, pdf_path: Path, params: EasyOCRParams) -> str:
        """Process PDF file by converting to images then OCR.

        Args:
            pdf_path: Path to PDF file
            params: EasyOCR parameters

        Returns:
            HOCR XML string with all pages combined
        """
        # Convert PDF to images
        try:
            images = convert_from_path(str(pdf_path), dpi=300, thread_count=2)
        except Exception as e:
            raise OCRProcessingError(f"PDF conversion failed: {str(e)}")

        # Process each page
        page_hocr_list = []
        for image in images:
            # Convert PIL Image to numpy array for EasyOCR
            img_array = np.array(image)

            # Run EasyOCR on page image
            results = self.reader.readtext(  # type: ignore
                img_array,
                detail=1,
                paragraph=False,
            )

            # Convert results to HOCR for this page
            # Save image temporarily to get dimensions
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                temp_path = Path(tmp_file.name)
                image.save(temp_path, format="PNG")

            try:
                page_hocr = self._to_hocr(results, temp_path)
                page_hocr_list.append(page_hocr)
            finally:
                # Clean up temp file
                temp_path.unlink(missing_ok=True)

        # Merge all pages into single HOCR document
        if len(page_hocr_list) == 1:
            hocr_content = page_hocr_list[0]
        else:
            hocr_content = self._merge_hocr_pages(page_hocr_list)

        return hocr_content

    def _merge_hocr_pages(self, page_hocr_list: list[str]) -> str:
        """Merge multiple HOCR pages into single document.

        Args:
            page_hocr_list: List of HOCR XML strings, one per page

        Returns:
            Combined HOCR XML string
        """
        # Extract body content from each page and combine
        combined_body = ""
        for page_hocr in page_hocr_list:
            # Extract content between <body> tags
            start = page_hocr.find("<body>")
            end = page_hocr.find("</body>")
            if start != -1 and end != -1:
                combined_body += page_hocr[start + 6 : end]

        # Wrap in complete HOCR structure
        hocr_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="content-type" content="text/html; charset=utf-8" />
<meta name="ocr-system" content="easyocr" />
</head>
<body>{combined_body}</body>
</html>"""

        return hocr_template

    def _to_hocr(self, easyocr_results: list, image_path: Path) -> str:
        """Convert EasyOCR results to HOCR XML format.

        Args:
            easyocr_results: List of (bbox, text, confidence) tuples from EasyOCR
            image_path: Path to original image (for dimensions)

        Returns:
            HOCR XML string
        """
        # Get image dimensions
        try:
            with Image.open(image_path) as img:
                image_width, image_height = img.size
        except Exception:
            # Use default dimensions if image can't be opened
            image_width, image_height = 1000, 1000

        # Convert to HOCR using utility from core
        hocr_xml = easyocr_to_hocr(easyocr_results, image_width, image_height)

        return hocr_xml
