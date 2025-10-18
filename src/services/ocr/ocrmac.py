"""ocrmac OCR engine implementation."""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional
from PIL import Image

from src.models.ocr_params import OcrmacParams, RecognitionLevel
from src.services.ocr.base import OCREngine
import structlog

logger = structlog.get_logger(__name__)


class OcrmacEngineError(Exception):
    """Exception raised when ocrmac processing fails."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class OcrmacEngine(OCREngine):
    """ocrmac OCR engine implementation."""

    def process(self, file_path: Path, params: Optional[OcrmacParams] = None) -> str:
        """
        Process a document using ocrmac and return HOCR XML output.

        Args:
            file_path: Path to the document to process
            params: ocrmac-specific parameters (languages, recognition_level)

        Returns:
            HOCR XML string (converted from ocrmac output)

        Raises:
            ValueError: If parameters are invalid
            RuntimeError: If OCR processing fails or ocrmac is not available
            TimeoutError: If processing exceeds timeout
        """
        # Validate platform
        import platform
        if platform.system() != 'Darwin':
            raise RuntimeError("ocrmac is only available on macOS systems")

        # Import ocrmac (will fail if not installed)
        try:
            from ocrmac import ocrmac
        except ImportError:
            logger.error("ocrmac_not_installed")
            raise RuntimeError(
                "ocrmac is not installed. Install with: pip install ocrmac"
            )

        # Extract parameters
        languages = params.languages if params and params.languages else None
        recognition_level = params.recognition_level if params else RecognitionLevel.BALANCED

        # Map RecognitionLevel enum to ocrmac string values
        recognition_level_str = recognition_level.value  # "fast", "balanced", or "accurate"

        try:
            logger.info(
                "processing_image",
                file=str(file_path),
                engine="ocrmac",
                languages=languages,
                recognition_level=recognition_level_str
            )

            # Create ocrmac OCR instance with parameters
            ocr_instance = ocrmac.OCR(
                str(file_path),
                language_preference=languages,
                recognition_level=recognition_level_str
            )

            # Perform OCR recognition
            annotations = ocr_instance.recognize()

            # Get image dimensions for bounding box conversion
            image_width, image_height = self._get_image_dimensions(file_path)

            # Convert ocrmac output to HOCR format
            hocr_content = self._convert_to_hocr(
                annotations, image_width, image_height, languages, recognition_level_str
            )

            logger.info("image_processed", file=str(file_path), engine="ocrmac")

            return hocr_content

        except Exception as e:
            logger.error("ocrmac_processing_failed", error=str(e), file=str(file_path))
            raise RuntimeError(f"ocrmac processing failed: {str(e)}")

    def _get_image_dimensions(self, image_path: Path) -> tuple[int, int]:
        """
        Get image width and height.

        Args:
            image_path: Path to image file

        Returns:
            Tuple of (width, height)

        Raises:
            RuntimeError: If image cannot be opened
        """
        try:
            with Image.open(image_path) as img:
                return img.size  # Returns (width, height)
        except Exception as e:
            logger.error("failed_to_get_image_dimensions", error=str(e))
            raise RuntimeError(f"Failed to get image dimensions: {str(e)}")

    def _convert_to_hocr(
        self,
        annotations: list,
        image_width: int,
        image_height: int,
        languages: Optional[list[str]],
        recognition_level: str
    ) -> str:
        """
        Convert ocrmac annotations to HOCR XML format.

        ocrmac output format:
        [
            ("text content", confidence_score, [x_min, y_min, width, height]),
            ...
        ]

        Where coordinates are relative (0.0 to 1.0)

        Args:
            annotations: List of ocrmac annotations
            image_width: Image width in pixels
            image_height: Image height in pixels
            languages: Language codes used (for metadata)
            recognition_level: Recognition level used (for metadata)

        Returns:
            HOCR XML string
        """
        # Create root structure
        html = ET.Element('html', xmlns="http://www.w3.org/1999/xhtml")

        # Add head with metadata
        head = ET.SubElement(html, 'head')
        meta_content_type = ET.SubElement(head, 'meta')
        meta_content_type.set('http-equiv', 'content-type')
        meta_content_type.set('content', 'text/html; charset=utf-8')

        meta_ocr_system = ET.SubElement(head, 'meta')
        meta_ocr_system.set('name', 'ocr-system')
        meta_ocr_system.set('content', 'ocrmac via restful-ocr')

        meta_langs = ET.SubElement(head, 'meta')
        meta_langs.set('name', 'ocr-langs')
        lang_str = ','.join(languages) if languages else 'auto'
        meta_langs.set('content', lang_str)

        meta_recognition = ET.SubElement(head, 'meta')
        meta_recognition.set('name', 'ocr-recognition-level')
        meta_recognition.set('content', recognition_level)

        # Create body
        body = ET.SubElement(html, 'body')

        # Create page container
        page = ET.SubElement(body, 'div')
        page.set('class', 'ocr_page')
        page.set('id', 'page_1')
        page.set('title', f'bbox 0 0 {image_width} {image_height}')

        # Convert each annotation to a word span
        for idx, annotation in enumerate(annotations, start=1):
            # ocrmac returns tuples: (text, confidence, bbox)
            text = annotation[0]
            confidence = annotation[1]
            bbox = annotation[2]

            # Convert relative bbox to absolute pixels
            # ocrmac bbox: [x_min, y_min, width, height] (relative 0.0-1.0)
            x_min = int(bbox[0] * image_width)
            y_min = int(bbox[1] * image_height)
            x_max = int((bbox[0] + bbox[2]) * image_width)
            y_max = int((bbox[1] + bbox[3]) * image_height)

            # Convert confidence from float (0.0-1.0) to integer (0-100)
            x_wconf = int(confidence * 100)

            # Create word span
            word = ET.SubElement(page, 'span')
            word.set('class', 'ocrx_word')
            word.set('id', f'word_1_{idx}')
            word.set('title', f'bbox {x_min} {y_min} {x_max} {y_max}; x_wconf {x_wconf}')
            word.text = text

        # Convert to string with proper formatting
        tree = ET.ElementTree(html)

        # Create the complete HOCR document with DOCTYPE
        hocr_doctype = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>'
        html_content = ET.tostring(html, encoding='unicode', method='html')

        hocr_document = f"{xml_declaration}\n{hocr_doctype}\n{html_content}"

        return hocr_document
