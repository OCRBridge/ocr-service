"""Tesseract OCR engine implementation."""

from pathlib import Path

import pytesseract
import structlog
from pdf2image import convert_from_path

from src.config import settings
from src.models.ocr_params import TesseractParams
from src.models.responses import ErrorCode
from src.models.upload import FileFormat
from src.services.ocr.base import OCREngine
from src.utils.validators import build_tesseract_config

logger = structlog.get_logger(__name__)


class TesseractEngineError(Exception):
    """Exception raised when Tesseract processing fails."""

    def __init__(self, message: str, error_code: ErrorCode):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class TesseractEngine(OCREngine):
    """Tesseract OCR engine implementation."""

    def process(
        self,
        file_path: Path,
        params: TesseractParams | None = None,
    ) -> str:
        """
        Process a document using Tesseract and return HOCR XML output.

        Args:
            file_path: Path to the document to process
            params: Tesseract-specific parameters (lang, psm, oem, dpi)

        Returns:
            HOCR XML string

        Raises:
            ValueError: If parameters are invalid
            RuntimeError: If OCR processing fails
            TimeoutError: If processing exceeds timeout
        """
        # Build configuration from parameters or defaults
        if params and isinstance(params, TesseractParams):
            config = build_tesseract_config(
                lang=params.lang,
                psm=params.psm,
                oem=params.oem,
                dpi=params.dpi,
            )
            lang = config.lang
            config_string = config.config_string
        else:
            # Use settings defaults
            lang = settings.tesseract_lang
            config = build_tesseract_config(
                lang=None, psm=settings.tesseract_psm, oem=settings.tesseract_oem, dpi=None
            )
            config_string = config.config_string

        pdf_dpi = settings.pdf_dpi

        try:
            # Detect file format from file extension
            file_format = self._detect_format(file_path)

            # Handle PDF separately
            if file_format == FileFormat.PDF:
                return self._process_pdf(file_path, lang, config_string, pdf_dpi)
            else:
                return self._process_image(file_path, lang, config_string)

        except pytesseract.TesseractError as e:
            logger.error("tesseract_error", error=str(e), file=str(file_path))
            raise RuntimeError(f"OCR engine error: {str(e)}")
        except Exception as e:
            logger.error("ocr_processing_failed", error=str(e), file=str(file_path))
            raise RuntimeError(f"OCR processing failed: {str(e)}")

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

    def _process_image(self, image_path: Path, lang: str, config_string: str) -> str:
        """
        Process image file with Tesseract.

        Args:
            image_path: Path to image file
            lang: Language code(s)
            config_string: Tesseract configuration string

        Returns:
            HOCR XML string
        """
        logger.info("processing_image", file=str(image_path), engine="tesseract")

        # Run Tesseract with HOCR output
        hocr_output = pytesseract.image_to_pdf_or_hocr(
            str(image_path), lang=lang, config=config_string, extension="hocr"
        )

        # Decode bytes to string
        hocr_content = hocr_output.decode("utf-8")

        logger.info("image_processed", file=str(image_path), engine="tesseract")

        return hocr_content

    def _process_pdf(self, pdf_path: Path, lang: str, config_string: str, pdf_dpi: int) -> str:
        """
        Process PDF file by converting to images then OCR.

        Args:
            pdf_path: Path to PDF file
            lang: Language code(s)
            config_string: Tesseract configuration string
            pdf_dpi: DPI for PDF conversion

        Returns:
            HOCR XML string with all pages combined
        """
        logger.info("processing_pdf", file=str(pdf_path), engine="tesseract")

        # Convert PDF to images
        try:
            images = convert_from_path(str(pdf_path), dpi=pdf_dpi, thread_count=2)
        except Exception as e:
            logger.error("pdf_conversion_failed", error=str(e))
            raise RuntimeError(f"PDF conversion failed: {str(e)}")

        logger.info("pdf_converted", file=str(pdf_path), pages=len(images), engine="tesseract")

        # Process each page
        page_hocr_list = []
        for i, image in enumerate(images, start=1):
            logger.debug("processing_page", page=i, total=len(images), engine="tesseract")

            # Run Tesseract on page image
            hocr_output = pytesseract.image_to_pdf_or_hocr(
                image, lang=lang, config=config_string, extension="hocr"
            )

            page_hocr_list.append(hocr_output.decode("utf-8"))

        # Combine pages (for multi-page PDF)
        if len(page_hocr_list) == 1:
            hocr_content = page_hocr_list[0]
        else:
            hocr_content = self._merge_hocr_pages(page_hocr_list)

        logger.info("pdf_processed", file=str(pdf_path), pages=len(images), engine="tesseract")

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
<meta name="ocr-system" content="tesseract {pytesseract.get_tesseract_version()}" />
</head>
<body>{combined_body}</body>
</html>"""

        return hocr_template
