"""Tesseract OCR engine implementation."""

from pathlib import Path

import pytesseract
from ocrbridge.core import OCREngine, OCRProcessingError, UnsupportedFormatError
from pdf2image import convert_from_path

from .models import TesseractParams


class TesseractEngine(OCREngine):
    """Tesseract OCR engine implementation.

    Supports:
    - Image formats: JPEG, PNG, TIFF
    - PDF files (converted to images first)
    - Multi-page PDFs
    - Multiple language support
    """

    @property
    def name(self) -> str:
        """Return engine name."""
        return "tesseract"

    @property
    def supported_formats(self) -> set[str]:
        """Return supported file extensions."""
        return {".jpg", ".jpeg", ".png", ".pdf", ".tiff", ".tif"}

    def process(self, file_path: Path, params: TesseractParams | None = None) -> str:
        """Process a document using Tesseract and return HOCR XML output.

        Args:
            file_path: Path to the document to process
            params: Tesseract-specific parameters (lang, psm, oem, dpi)

        Returns:
            HOCR XML string

        Raises:
            OCRProcessingError: If OCR processing fails
            UnsupportedFormatError: If file format is not supported
        """
        # Use defaults if no params provided
        if params is None:
            params = TesseractParams()

        # Validate file format
        suffix = file_path.suffix.lower()
        if suffix not in self.supported_formats:
            raise UnsupportedFormatError(
                f"Unsupported file format: {suffix}. "
                f"Supported formats: {', '.join(sorted(self.supported_formats))}"
            )

        # Build Tesseract configuration
        lang = params.lang or "eng"
        config_parts = []

        if params.psm is not None:
            config_parts.append(f"--psm {params.psm}")

        if params.oem is not None:
            config_parts.append(f"--oem {params.oem}")

        if params.dpi is not None:
            config_parts.append(f"--dpi {params.dpi}")

        config_string = " ".join(config_parts)

        try:
            # Handle PDF separately
            if suffix == ".pdf":
                return self._process_pdf(file_path, lang, config_string, params.dpi or 300)
            else:
                return self._process_image(file_path, lang, config_string)

        except pytesseract.TesseractError as e:
            raise OCRProcessingError(f"Tesseract engine error: {str(e)}")
        except Exception as e:
            raise OCRProcessingError(f"OCR processing failed: {str(e)}")

    def _process_image(self, image_path: Path, lang: str, config_string: str) -> str:
        """Process image file with Tesseract.

        Args:
            image_path: Path to image file
            lang: Language code(s)
            config_string: Tesseract configuration string

        Returns:
            HOCR XML string
        """
        # Run Tesseract with HOCR output
        hocr_output = pytesseract.image_to_pdf_or_hocr(
            str(image_path), lang=lang, config=config_string, extension="hocr"
        )

        # Decode bytes to string
        hocr_content = (
            hocr_output.decode("utf-8") if isinstance(hocr_output, bytes) else hocr_output
        )

        return hocr_content

    def _process_pdf(self, pdf_path: Path, lang: str, config_string: str, dpi: int) -> str:
        """Process PDF file by converting to images then OCR.

        Args:
            pdf_path: Path to PDF file
            lang: Language code(s)
            config_string: Tesseract configuration string
            dpi: DPI for PDF conversion

        Returns:
            HOCR XML string with all pages combined
        """
        # Convert PDF to images
        try:
            images = convert_from_path(str(pdf_path), dpi=dpi, thread_count=2)
        except Exception as e:
            raise OCRProcessingError(f"PDF conversion failed: {str(e)}")

        # Process each page
        page_hocr_list = []
        for image in images:
            # Run Tesseract on page image
            hocr_output = pytesseract.image_to_pdf_or_hocr(
                image, lang=lang, config=config_string, extension="hocr"
            )

            page_hocr = (
                hocr_output.decode("utf-8") if isinstance(hocr_output, bytes) else hocr_output
            )
            page_hocr_list.append(page_hocr)

        # Combine pages (for multi-page PDF)
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
        try:
            version = pytesseract.get_tesseract_version()
        except Exception:
            version = "unknown"

        hocr_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="content-type" content="text/html; charset=utf-8" />
<meta name="ocr-system" content="tesseract {version}" />
</head>
<body>{combined_body}</body>
</html>"""

        return hocr_template
