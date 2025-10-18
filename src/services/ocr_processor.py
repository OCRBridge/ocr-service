"""OCR processing service using Tesseract with HOCR output."""

from pathlib import Path
from typing import Optional

import pytesseract
import structlog
from pdf2image import convert_from_path

from src.config import settings
from src.models import TesseractParams
from src.models.job import ErrorCode
from src.models.upload import FileFormat
from src.utils.validators import build_tesseract_config

logger = structlog.get_logger()


class OCRProcessorError(Exception):
    """Base exception for OCR processing errors."""

    def __init__(self, message: str, error_code: ErrorCode):
        super().__init__(message)
        self.error_code = error_code


class OCRProcessor:
    """Tesseract OCR wrapper for processing documents and generating HOCR output."""

    def __init__(self, tesseract_params: Optional[TesseractParams] = None):
        """
        Initialize OCR processor with Tesseract configuration.

        Args:
            tesseract_params: Optional Tesseract parameters. If None, uses config defaults.
        """
        if tesseract_params:
            # Build config from provided parameters
            config = build_tesseract_config(
                lang=tesseract_params.lang,
                psm=tesseract_params.psm,
                oem=tesseract_params.oem,
                dpi=tesseract_params.dpi,
            )
            self.lang = config.lang
            self.config_string = config.config_string
        else:
            # Use settings defaults
            self.lang = settings.tesseract_lang
            config = build_tesseract_config(
                lang=None, psm=settings.tesseract_psm, oem=settings.tesseract_oem, dpi=None
            )
            self.config_string = config.config_string

        self.pdf_dpi = settings.pdf_dpi

    async def process_document(self, file_path: Path, file_format: FileFormat) -> str:
        """
        Process document and generate HOCR output.

        Args:
            file_path: Path to document file
            file_format: Document format (JPEG, PNG, PDF, TIFF)

        Returns:
            HOCR XML string

        Raises:
            OCRProcessorError: If processing fails
        """
        try:
            # Handle PDF separately
            if file_format == FileFormat.PDF:
                return await self._process_pdf(file_path)
            else:
                return await self._process_image(file_path)

        except pytesseract.TesseractError as e:
            logger.error("tesseract_error", error=str(e), file=str(file_path))
            raise OCRProcessorError(f"OCR engine error: {str(e)}", ErrorCode.OCR_ENGINE_ERROR)
        except Exception as e:
            logger.error("ocr_processing_failed", error=str(e), file=str(file_path))
            raise OCRProcessorError(f"OCR processing failed: {str(e)}", ErrorCode.INTERNAL_ERROR)

    async def _process_image(self, image_path: Path) -> str:
        """
        Process image file with Tesseract.

        Args:
            image_path: Path to image file

        Returns:
            HOCR XML string
        """
        logger.info("processing_image", file=str(image_path))

        # Run Tesseract with HOCR output
        hocr_output = pytesseract.image_to_pdf_or_hocr(
            str(image_path), lang=self.lang, config=self.config_string, extension="hocr"
        )

        # Decode bytes to string
        hocr_content = hocr_output.decode("utf-8")

        logger.info("image_processed", file=str(image_path))

        return hocr_content

    async def _process_pdf(self, pdf_path: Path) -> str:
        """
        Process PDF file by converting to images then OCR.

        Args:
            pdf_path: Path to PDF file

        Returns:
            HOCR XML string with all pages combined
        """
        logger.info("processing_pdf", file=str(pdf_path))

        # Convert PDF to images
        try:
            images = convert_from_path(str(pdf_path), dpi=self.pdf_dpi, thread_count=2)
        except Exception as e:
            logger.error("pdf_conversion_failed", error=str(e))
            raise OCRProcessorError(f"PDF conversion failed: {str(e)}", ErrorCode.CORRUPTED_FILE)

        logger.info("pdf_converted", file=str(pdf_path), pages=len(images))

        # Process each page
        page_hocr_list = []
        for i, image in enumerate(images, start=1):
            logger.debug("processing_page", page=i, total=len(images))

            # Run Tesseract on page image
            hocr_output = pytesseract.image_to_pdf_or_hocr(
                image, lang=self.lang, config=self.config_string, extension="hocr"
            )

            page_hocr_list.append(hocr_output.decode("utf-8"))

        # Combine pages (for multi-page PDF)
        if len(page_hocr_list) == 1:
            hocr_content = page_hocr_list[0]
        else:
            hocr_content = self._merge_hocr_pages(page_hocr_list)

        logger.info("pdf_processed", file=str(pdf_path), pages=len(images))

        return hocr_content

    def _merge_hocr_pages(self, page_hocr_list: list[str]) -> str:
        """
        Merge multiple HOCR pages into single document.

        Args:
            page_hocr_list: List of HOCR XML strings, one per page

        Returns:
            Combined HOCR XML string
        """
        # For now, concatenate pages within a single HTML document
        # In production, would properly merge XML structures

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
