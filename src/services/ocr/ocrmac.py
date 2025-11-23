"""ocrmac OCR engine implementation."""

import platform
import xml.etree.ElementTree as ET
from pathlib import Path

import structlog
from fastapi import HTTPException
from pdf2image import convert_from_path
from PIL import Image

from src.config import settings
from src.models.ocr_params import OcrmacParams, RecognitionLevel
from src.models.upload import FileFormat
from src.services.ocr.base import OCREngine

logger = structlog.get_logger(__name__)


class OcrmacEngineError(Exception):
    """Exception raised when ocrmac processing fails."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class OcrmacEngine(OCREngine):
    """ocrmac OCR engine implementation."""

    def _check_sonoma_requirement(self, recognition_level: str) -> None:
        """
        Check if macOS Sonoma is available for LiveText recognition.

        Args:
            recognition_level: Recognition level string ("livetext", "fast", "balanced", "accurate")

        Raises:
            HTTPException: If livetext requested but Sonoma not available (HTTP 400)
        """
        if recognition_level != "livetext":
            return

        if platform.system() != "Darwin":
            logger.error(
                "livetext_platform_incompatible",
                platform=platform.system(),
                recognition_level=recognition_level,
            )
            raise HTTPException(
                status_code=400,
                detail="LiveText recognition requires macOS Sonoma (14.0) or later. Available recognition levels: fast, balanced, accurate",
            )

        mac_version = platform.mac_ver()[0]
        if not mac_version:
            logger.error("macos_version_detection_failed", recognition_level=recognition_level)
            raise HTTPException(
                status_code=400,
                detail="Unable to determine macOS version. LiveText requires macOS Sonoma (14.0) or later. Available recognition levels: fast, balanced, accurate",
            )

        try:
            major_version = int(mac_version.split(".")[0])
            if major_version < 14:
                logger.warning(
                    "livetext_requires_sonoma",
                    current_version=mac_version,
                    recognition_level=recognition_level,
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"LiveText recognition requires macOS Sonoma (14.0) or later. Current version: {mac_version}. Available recognition levels: fast, balanced, accurate",
                )
        except (ValueError, IndexError) as e:
            logger.error(
                "macos_version_parse_failed",
                version=mac_version,
                error=str(e),
                recognition_level=recognition_level,
            )
            raise HTTPException(
                status_code=400,
                detail=f"Invalid macOS version format: {mac_version}. LiveText requires macOS Sonoma (14.0) or later. Available recognition levels: fast, balanced, accurate",
            )

        logger.info(
            "livetext_platform_validated",
            macos_version=mac_version,
            recognition_level=recognition_level,
        )

    def process(
        self,
        file_path: Path,
        params: OcrmacParams | None = None,
    ) -> str:
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

        if platform.system() != "Darwin":
            raise RuntimeError("ocrmac is only available on macOS systems")

        # Extract parameters
        languages = params.languages if params and params.languages else None
        recognition_level = params.recognition_level if params else RecognitionLevel.BALANCED

        # Map RecognitionLevel enum to ocrmac string values
        recognition_level_str = recognition_level.value  # "fast", "balanced", or "accurate"

        pdf_dpi = settings.pdf_dpi

        try:
            # Detect file format from file extension
            file_format = self._detect_format(file_path)

            # Handle PDF separately
            if file_format == FileFormat.PDF:
                return self._process_pdf(file_path, languages, recognition_level_str, pdf_dpi)
            else:
                return self._process_image(file_path, languages, recognition_level_str)

        except Exception as e:
            logger.error("ocrmac_processing_failed", error=str(e), file=str(file_path))
            raise RuntimeError(f"ocrmac processing failed: {str(e)}")

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

    def _process_image(
        self, image_path: Path, languages: list[str] | None, recognition_level_str: str
    ) -> str:
        """
        Process image file with ocrmac.

        Args:
            image_path: Path to image file
            languages: Language codes or None for auto-detection
            recognition_level_str: Recognition level ("fast", "balanced", "accurate", or "livetext")

        Returns:
            HOCR XML string

        Raises:
            HTTPException: If platform requirements not met (HTTP 400)
            RuntimeError: If ocrmac processing fails
        """
        # Validate platform requirements for livetext
        self._check_sonoma_requirement(recognition_level_str)

        # Import ocrmac (will fail if not installed)
        try:
            from ocrmac import ocrmac
        except ImportError:
            logger.error("ocrmac_not_installed")
            raise RuntimeError("ocrmac is not installed. Install with: pip install ocrmac")

        # Determine framework parameter
        framework_type = "livetext" if recognition_level_str == "livetext" else "vision"

        logger.info(
            "processing_image",
            file=str(image_path),
            engine="ocrmac",
            languages=languages,
            recognition_level=recognition_level_str,
            framework=framework_type,
        )

        # Create ocrmac OCR instance with parameters
        # Note: ocrmac library only accepts "fast" and "accurate" as recognition_level values
        # "balanced" is an API-level abstraction that maps to ocrmac's default behavior
        try:
            if recognition_level_str == "livetext":
                # LiveText framework doesn't accept recognition_level parameter
                ocr_instance = ocrmac.OCR(
                    str(image_path),
                    language_preference=languages,
                    framework=framework_type,
                )
            elif recognition_level_str == "balanced":
                # "balanced" is API-level default - don't pass recognition_level to use ocrmac's default
                ocr_instance = ocrmac.OCR(
                    str(image_path),
                    language_preference=languages,
                )
            else:
                # "fast" or "accurate" - pass to ocrmac as-is
                ocr_instance = ocrmac.OCR(
                    str(image_path),
                    language_preference=languages,
                    recognition_level=recognition_level_str,
                )
        except (TypeError, AttributeError) as e:
            if "framework" in str(e):
                logger.error(
                    "ocrmac_library_incompatible",
                    error=str(e),
                    recognition_level=recognition_level_str,
                )
                raise RuntimeError(
                    "ocrmac library version does not support LiveText framework. "
                    "Please upgrade to a newer version of ocrmac that supports the framework parameter."
                )
            raise

        # Perform OCR recognition
        annotations = ocr_instance.recognize()

        # Validate annotation format before conversion
        try:
            for annotation in annotations:
                if not isinstance(annotation, tuple) or len(annotation) != 3:
                    error_sample = str(annotations[:3])[:500]  # First 500 chars of sample
                    logger.error(
                        "unexpected_annotation_format",
                        framework=framework_type,
                        sample=error_sample,
                        recognition_level=recognition_level_str,
                    )
                    raise RuntimeError(
                        f"LiveText processing returned unexpected output format: expected 3-tuple, got {type(annotation)}"
                    )
                _, _, bbox = annotation
                if not isinstance(bbox, list) or len(bbox) != 4:
                    error_sample = str(annotations[:3])[:500]  # First 500 chars of sample
                    logger.error(
                        "unexpected_bbox_format",
                        framework=framework_type,
                        sample=error_sample,
                        recognition_level=recognition_level_str,
                    )
                    raise RuntimeError(
                        f"LiveText processing returned unexpected bbox format: expected 4-element list, got {bbox}"
                    )
        except (IndexError, ValueError, TypeError) as e:
            error_sample = str(annotations[:3])[:500]  # First 500 chars of sample
            logger.error(
                "annotation_validation_failed",
                error=str(e),
                framework=framework_type,
                sample=error_sample,
                recognition_level=recognition_level_str,
            )
            raise RuntimeError(f"Annotation validation failed: {str(e)}")

        # Get image dimensions for bounding box conversion
        image_width, image_height = self._get_image_dimensions(image_path)

        # Convert ocrmac output to HOCR format
        hocr_content = self._convert_to_hocr(
            annotations, image_width, image_height, languages, recognition_level_str
        )

        logger.info(
            "image_processed",
            file=str(image_path),
            engine="ocrmac",
            framework=framework_type,
            recognition_level=recognition_level_str,
        )

        return hocr_content

    def _process_pdf(
        self,
        pdf_path: Path,
        languages: list[str] | None,
        recognition_level_str: str,
        pdf_dpi: int,
    ) -> str:
        """
        Process PDF file by converting to images then OCR with ocrmac.

        Args:
            pdf_path: Path to PDF file
            languages: Language codes or None for auto-detection
            recognition_level_str: Recognition level ("fast", "balanced", "accurate", or "livetext")
            pdf_dpi: DPI for PDF conversion

        Returns:
            HOCR XML string with all pages combined

        Raises:
            HTTPException: If platform requirements not met (HTTP 400)
            RuntimeError: If PDF conversion or ocrmac processing fails
        """
        # Validate platform requirements for livetext
        self._check_sonoma_requirement(recognition_level_str)

        # Import ocrmac (will fail if not installed)
        try:
            from ocrmac import ocrmac
        except ImportError:
            logger.error("ocrmac_not_installed")
            raise RuntimeError("ocrmac is not installed. Install with: pip install ocrmac")

        # Determine framework parameter
        framework_type = "livetext" if recognition_level_str == "livetext" else "vision"

        logger.info(
            "processing_pdf",
            file=str(pdf_path),
            engine="ocrmac",
            framework=framework_type,
            recognition_level=recognition_level_str,
        )

        # Convert PDF to images
        try:
            images = convert_from_path(str(pdf_path), dpi=pdf_dpi, thread_count=2)
        except Exception as e:
            logger.error("pdf_conversion_failed", error=str(e))
            raise RuntimeError(f"PDF conversion failed: {str(e)}")

        logger.info("pdf_converted", file=str(pdf_path), pages=len(images), engine="ocrmac")

        # Process each page
        page_hocr_list = []
        for i, image in enumerate(images, start=1):
            logger.debug("processing_page", page=i, total=len(images), engine="ocrmac")

            # Get image dimensions
            image_width, image_height = self._get_image_dimensions(image)

            # Save image temporarily for ocrmac processing
            # ocrmac requires a file path, not a PIL Image object
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                temp_path = Path(tmp_file.name)
                image.save(temp_path, format="PNG")

            try:
                # Create ocrmac OCR instance with parameters
                # Note: ocrmac library only accepts "fast" and "accurate" as recognition_level values
                # "balanced" is an API-level abstraction that maps to ocrmac's default behavior
                try:
                    if recognition_level_str == "livetext":
                        # LiveText framework doesn't accept recognition_level parameter
                        ocr_instance = ocrmac.OCR(
                            str(temp_path),
                            language_preference=languages,
                            framework=framework_type,
                        )
                    elif recognition_level_str == "balanced":
                        # "balanced" is API-level default - don't pass recognition_level to use ocrmac's default
                        ocr_instance = ocrmac.OCR(
                            str(temp_path),
                            language_preference=languages,
                        )
                    else:
                        # "fast" or "accurate" - pass to ocrmac as-is
                        ocr_instance = ocrmac.OCR(
                            str(temp_path),
                            language_preference=languages,
                            recognition_level=recognition_level_str,
                        )
                except (TypeError, AttributeError) as e:
                    if "framework" in str(e):
                        logger.error(
                            "ocrmac_library_incompatible",
                            error=str(e),
                            recognition_level=recognition_level_str,
                        )
                        raise RuntimeError(
                            "ocrmac library version does not support LiveText framework. "
                            "Please upgrade to a newer version of ocrmac that supports the framework parameter."
                        )
                    raise

                # Perform OCR recognition
                annotations = ocr_instance.recognize()

                # Validate annotation format before conversion
                try:
                    for annotation in annotations:
                        if not isinstance(annotation, tuple) or len(annotation) != 3:
                            error_sample = str(annotations[:3])[:500]  # First 500 chars
                            logger.error(
                                "unexpected_annotation_format",
                                framework=framework_type,
                                sample=error_sample,
                                recognition_level=recognition_level_str,
                                page=i,
                            )
                            raise RuntimeError(
                                f"LiveText processing returned unexpected output format: expected 3-tuple, got {type(annotation)}"
                            )
                        _, _, bbox = annotation
                        if not isinstance(bbox, list) or len(bbox) != 4:
                            error_sample = str(annotations[:3])[:500]  # First 500 chars
                            logger.error(
                                "unexpected_bbox_format",
                                framework=framework_type,
                                sample=error_sample,
                                recognition_level=recognition_level_str,
                                page=i,
                            )
                            raise RuntimeError(
                                f"LiveText processing returned unexpected bbox format: expected 4-element list, got {bbox}"
                            )
                except (IndexError, ValueError, TypeError) as e:
                    error_sample = str(annotations[:3])[:500]  # First 500 chars
                    logger.error(
                        "annotation_validation_failed",
                        error=str(e),
                        framework=framework_type,
                        sample=error_sample,
                        recognition_level=recognition_level_str,
                        page=i,
                    )
                    raise RuntimeError(f"Annotation validation failed: {str(e)}")

                # Convert ocrmac output to HOCR format
                hocr_content = self._convert_to_hocr(
                    annotations, image_width, image_height, languages, recognition_level_str
                )

                page_hocr_list.append(hocr_content)
            finally:
                # Clean up temporary file
                temp_path.unlink(missing_ok=True)

        # Combine pages (for multi-page PDF)
        if len(page_hocr_list) == 1:
            hocr_content = page_hocr_list[0]
        else:
            hocr_content = self._merge_hocr_pages(page_hocr_list)

        logger.info("pdf_processed", file=str(pdf_path), pages=len(images), engine="ocrmac")

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
<meta name="ocr-system" content="ocrmac via restful-ocr" />
</head>
<body>{combined_body}</body>
</html>"""

        return hocr_template

    def _get_image_dimensions(self, image_source: Path | Image.Image) -> tuple[int, int]:
        """
        Get image width and height from file path or PIL Image object.

        Args:
            image_source: Either a Path to an image file or a PIL.Image.Image object

        Returns:
            Tuple of (width, height)

        Raises:
            RuntimeError: If image cannot be opened or processed
        """
        try:
            if isinstance(image_source, Image.Image):
                # Already a PIL Image object, just return size
                return image_source.size
            else:
                # It's a file path, open it
                with Image.open(image_source) as img:
                    return img.size  # Returns (width, height)
        except Exception as e:
            logger.error("failed_to_get_image_dimensions", error=str(e))
            raise RuntimeError(f"Failed to get image dimensions: {str(e)}")

    def _group_words_into_lines(
        self, annotations: list, image_width: int, image_height: int
    ) -> list[dict]:
        """
        Group word annotations into lines based on vertical position.

        Args:
            annotations: List of ocrmac annotations (text, confidence, bbox)
            image_width: Image width in pixels
            image_height: Image height in pixels

        Returns:
            List of line dictionaries, each containing:
                - bbox: (x_min, y_min, x_max, y_max) in pixels
                - words: List of word dictionaries with text, confidence, bbox
        """
        if not annotations:
            return []

        # Convert annotations to word dictionaries with absolute coordinates
        words = []
        for annotation in annotations:
            text = annotation[0]
            confidence = annotation[1]
            bbox = annotation[2]

            # Convert relative bbox to absolute pixels
            # ocrmac bbox: [x_min, y_min, width, height] (relative 0.0-1.0)
            # Note: ocrmac uses bottom-left origin (macOS), need to flip to top-left (hOCR)
            x_min = int(bbox[0] * image_width)
            x_max = int((bbox[0] + bbox[2]) * image_width)

            # ocrmac y-coordinates are from bottom-left origin
            y_min_from_bottom = int(bbox[1] * image_height)
            y_max_from_bottom = int((bbox[1] + bbox[3]) * image_height)

            # Flip to top-left origin for hOCR standard
            y_min = image_height - y_max_from_bottom
            y_max = image_height - y_min_from_bottom

            # Calculate vertical center for line grouping
            y_center = (y_min + y_max) / 2
            height = y_max - y_min

            words.append(
                {
                    "text": text,
                    "confidence": confidence,
                    "bbox": (x_min, y_min, x_max, y_max),
                    "y_center": y_center,
                    "height": height,
                    "x_min": x_min,
                }
            )

        if not words:
            return []

        # Calculate median word height for threshold
        heights = [w["height"] for w in words]
        heights.sort()
        median_height = heights[len(heights) // 2]

        # Threshold: words are on same line if y_centers within 50% of median height
        line_threshold = median_height * 0.5

        # Sort words by vertical position (top to bottom)
        words.sort(key=lambda w: w["y_center"])

        # Group words into lines
        lines = []
        current_line_words = [words[0]]
        current_y_center = words[0]["y_center"]

        for word in words[1:]:
            # Check if word belongs to current line
            if abs(word["y_center"] - current_y_center) <= line_threshold:
                current_line_words.append(word)
            else:
                # Start new line
                lines.append(current_line_words)
                current_line_words = [word]
                current_y_center = word["y_center"]

        # Don't forget the last line
        if current_line_words:
            lines.append(current_line_words)

        # Process each line: sort words left-to-right and calculate bbox
        result_lines = []
        for line_words in lines:
            # Sort words left to right
            line_words.sort(key=lambda w: w["x_min"])

            # Calculate line bounding box
            line_x_min = min(w["bbox"][0] for w in line_words)
            line_y_min = min(w["bbox"][1] for w in line_words)
            line_x_max = max(w["bbox"][2] for w in line_words)
            line_y_max = max(w["bbox"][3] for w in line_words)

            result_lines.append(
                {"bbox": (line_x_min, line_y_min, line_x_max, line_y_max), "words": line_words}
            )

        return result_lines

    def _convert_to_hocr(
        self,
        annotations: list,
        image_width: int,
        image_height: int,
        languages: list[str] | None,
        recognition_level: str,
    ) -> str:
        """
        Convert ocrmac annotations to HOCR XML format with standard hierarchy.

        Creates proper hOCR structure: ocr_page → ocr_line → ocrx_word

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
            HOCR XML string with standard hierarchy
        """
        # Create root structure
        html = ET.Element("html", xmlns="http://www.w3.org/1999/xhtml")

        # Add head with metadata
        head = ET.SubElement(html, "head")
        meta_content_type = ET.SubElement(head, "meta")
        meta_content_type.set("http-equiv", "content-type")
        meta_content_type.set("content", "text/html; charset=utf-8")

        meta_ocr_system = ET.SubElement(head, "meta")
        meta_ocr_system.set("name", "ocr-system")
        if recognition_level == "livetext":
            meta_ocr_system.set("content", "ocrmac-livetext via restful-ocr")
        else:
            meta_ocr_system.set("content", "ocrmac via restful-ocr")

        meta_langs = ET.SubElement(head, "meta")
        meta_langs.set("name", "ocr-langs")
        lang_str = ",".join(languages) if languages else "auto"
        meta_langs.set("content", lang_str)

        meta_recognition = ET.SubElement(head, "meta")
        meta_recognition.set("name", "ocr-recognition-level")
        meta_recognition.set("content", recognition_level)

        # Create body
        body = ET.SubElement(html, "body")

        # Create page container
        page = ET.SubElement(body, "div")
        page.set("class", "ocr_page")
        page.set("id", "page_1")
        page.set("title", f"bbox 0 0 {image_width} {image_height}")

        # Group words into lines
        lines = self._group_words_into_lines(annotations, image_width, image_height)

        # Create ocr_line elements with words
        word_counter = 1
        for line_idx, line_data in enumerate(lines, start=1):
            line_bbox = line_data["bbox"]

            # Create line element
            line_elem = ET.SubElement(page, "span")
            line_elem.set("class", "ocr_line")
            line_elem.set("id", f"line_1_{line_idx}")
            line_elem.set(
                "title", f"bbox {line_bbox[0]} {line_bbox[1]} {line_bbox[2]} {line_bbox[3]}"
            )

            # Add words to this line
            for word_data in line_data["words"]:
                # Convert confidence from float (0.0-1.0) to integer (0-100)
                # Note: Apple's Vision framework returns quantized confidence scores:
                #   - Fast mode: 0.3 (30%) or 0.5 (50%)
                #   - Accurate/Balanced: 0.5 (50%) or 1.0 (100%)
                # This is expected behavior from the Vision framework's ML model,
                # not a limitation of ocrmac or our implementation.
                x_wconf = int(word_data["confidence"] * 100)

                # Create word span
                word_elem = ET.SubElement(line_elem, "span")
                word_elem.set("class", "ocrx_word")
                word_elem.set("id", f"word_1_{word_counter}")
                word_bbox = word_data["bbox"]
                word_elem.set(
                    "title",
                    f"bbox {word_bbox[0]} {word_bbox[1]} {word_bbox[2]} {word_bbox[3]}; x_wconf {x_wconf}",
                )
                word_elem.text = word_data["text"]

                word_counter += 1

        # Create the complete HOCR document with DOCTYPE
        hocr_doctype = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>'
        html_content = ET.tostring(html, encoding="unicode", method="xml")

        hocr_document = f"{xml_declaration}\n{hocr_doctype}\n{html_content}"

        return hocr_document
