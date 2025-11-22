"""EasyOCR engine implementation for deep learning-based OCR."""

from pathlib import Path

import structlog
from pdf2image import convert_from_path

from src.config import settings
from src.models.ocr_params import EasyOCRParams
from src.models.upload import FileFormat
from src.services.ocr.base import OCREngine
from src.utils.gpu import get_easyocr_device

logger = structlog.get_logger()


class EasyOCREngine(OCREngine):
    """
    EasyOCR engine implementation.

    Uses deep learning models for multilingual OCR with automatic GPU acceleration.
    GPU is automatically detected and used when available, with graceful fallback to CPU.
    Supports 80+ languages with superior accuracy for Asian scripts.
    """

    def __init__(self, params: EasyOCRParams | None = None):
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
            raise RuntimeError("EasyOCR not installed. Install with: pip install easyocr") from e

        # Automatically determine device (GPU or CPU)
        use_gpu, device_name = get_easyocr_device()

        logger.info(
            "creating_easyocr_reader",
            languages=self.params.languages,
            gpu_used=use_gpu,
            device=device_name,
        )

        # Create reader with language list and GPU setting
        reader = easyocr.Reader(  # type: ignore[attr-defined]
            lang_list=self.params.languages,
            gpu=use_gpu,
        )

        return reader

    def _detect_format(self, file_path: Path) -> FileFormat:
        """
        Detect file format from extension.

        Args:
            file_path: Path to file

        Returns:
            FileFormat enum value

        Raises:
            ValueError: If file format is unsupported
        """
        suffix = file_path.suffix.lower()
        format_map = {
            ".jpg": FileFormat.JPEG,
            ".jpeg": FileFormat.JPEG,
            ".png": FileFormat.PNG,
            ".pdf": FileFormat.PDF,
            ".tiff": FileFormat.TIFF,
            ".tif": FileFormat.TIFF,
        }

        if suffix not in format_map:
            raise ValueError(f"Unsupported file format: {suffix}")

        return format_map[suffix]

    def process(self, file_path: Path, params: EasyOCRParams | None = None) -> str:  # type: ignore[override]
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

        try:
            # Detect file format from file extension
            file_format = self._detect_format(file_path)

            # Handle PDF separately
            if file_format == FileFormat.PDF:
                return self._process_pdf(file_path)
            else:
                return self._process_image(file_path)

        except Exception as e:
            logger.error("easyocr_processing_failed", error=str(e), file_path=str(file_path))
            raise RuntimeError(f"EasyOCR processing failed: {e}") from e

    def _process_image(self, image_path: Path) -> str:
        """
        Process single image with EasyOCR.

        Args:
            image_path: Path to image file

        Returns:
            HOCR XML string

        Raises:
            RuntimeError: If EasyOCR processing fails
        """
        logger.info("easyocr_processing_started", file_path=str(image_path), engine="easyocr")

        # Create reader (cached on subsequent calls for same languages)
        if self.reader is None:
            self.reader = self.create_easyocr_reader()

        # Process image with EasyOCR
        results = self.reader.readtext(
            str(image_path),
            detail=1,  # Include bounding boxes and confidence
            paragraph=False,  # Return individual text boxes
        )

        logger.info(
            "image_processed",
            file=str(image_path),
            text_boxes_found=len(results),
            engine="easyocr",
        )

        # Convert results to HOCR format
        hocr_output = self.to_hocr(results, image_path)

        return hocr_output

    def _process_pdf(self, pdf_path: Path) -> str:
        """
        Process PDF file by converting to images then OCR.

        Args:
            pdf_path: Path to PDF file

        Returns:
            HOCR XML string with all pages combined

        Raises:
            RuntimeError: If PDF conversion or processing fails
        """
        logger.info("processing_pdf", file=str(pdf_path), engine="easyocr")

        # Convert PDF to images
        try:
            pdf_dpi = settings.pdf_dpi
            images = convert_from_path(str(pdf_path), dpi=pdf_dpi, thread_count=2)
        except Exception as e:
            logger.error("pdf_conversion_failed", error=str(e))
            raise RuntimeError(f"PDF conversion failed: {str(e)}")

        logger.info("pdf_converted", file=str(pdf_path), pages=len(images), engine="easyocr")

        # Create reader (cached on subsequent calls for same languages)
        if self.reader is None:
            self.reader = self.create_easyocr_reader()

        # Process each page
        page_hocr_list = []
        for i, image in enumerate(images, start=1):
            logger.debug("processing_page", page=i, total=len(images), engine="easyocr")

            # Convert PIL Image to numpy array for EasyOCR
            # EasyOCR accepts: file path (string), bytes, or numpy array
            import numpy as np  # type: ignore[import-untyped]

            img_array = np.array(image)

            # Run EasyOCR on page image
            results = self.reader.readtext(
                img_array,  # Numpy array from PIL Image
                detail=1,  # Include bounding boxes and confidence
                paragraph=False,  # Return individual text boxes
            )

            # Convert results to HOCR for this page
            # Save image temporarily to get dimensions
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                temp_path = Path(tmp_file.name)
                image.save(temp_path, format="PNG")

            try:
                page_hocr = self.to_hocr(results, temp_path)
                page_hocr_list.append(page_hocr)
            finally:
                # Clean up temp file
                temp_path.unlink(missing_ok=True)

            logger.debug("page_processed", page=i, engine="easyocr")

        # Merge all pages into single HOCR document
        if len(page_hocr_list) == 1:
            hocr_content = page_hocr_list[0]
        else:
            hocr_content = self._merge_hocr_pages(page_hocr_list)

        logger.info("pdf_processed", file=str(pdf_path), pages=len(images), engine="easyocr")

        return hocr_content

    def _merge_hocr_pages(self, page_hocr_list: list[str]) -> str:
        """
        Merge multiple HOCR pages into single document.

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
