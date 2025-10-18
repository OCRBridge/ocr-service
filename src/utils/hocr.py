"""HOCR XML parsing and validation utilities."""

import re
import xml.etree.ElementTree as ET
from typing import NamedTuple


class HOCRParseError(Exception):
    """Raised when HOCR parsing fails."""

    pass


class HOCRValidationError(Exception):
    """Raised when HOCR validation fails."""

    pass


class HOCRInfo(NamedTuple):
    """Parsed HOCR information."""

    page_count: int
    word_count: int
    has_bounding_boxes: bool


def parse_hocr(hocr_content: str) -> HOCRInfo:
    """
    Parse HOCR content and extract information.

    Args:
        hocr_content: HOCR XML string

    Returns:
        HOCRInfo with parsed data

    Raises:
        HOCRParseError: If parsing fails
    """
    try:
        root = ET.fromstring(hocr_content)
    except ET.ParseError as e:
        raise HOCRParseError(f"Failed to parse HOCR XML: {e}")

    # Count pages (elements with class="ocr_page")
    page_count = len(root.findall(".//*[@class='ocr_page']"))
    if page_count == 0:
        # Try with namespace
        namespace = {"html": "http://www.w3.org/1999/xhtml"}
        page_count = len(root.findall(".//*[@class='ocr_page']", namespace))

    # Count words (elements with class="ocrx_word")
    word_count = len(root.findall(".//*[@class='ocrx_word']"))
    if word_count == 0:
        # Try with namespace
        word_count = len(root.findall(".//*[@class='ocrx_word']", namespace))

    # Check for bounding boxes
    has_bounding_boxes = "bbox" in hocr_content

    return HOCRInfo(
        page_count=max(page_count, 1),  # At least 1 page
        word_count=word_count,
        has_bounding_boxes=has_bounding_boxes,
    )


def validate_hocr(hocr_content: str) -> None:
    """
    Validate HOCR content meets requirements.

    Args:
        hocr_content: HOCR XML string

    Raises:
        HOCRValidationError: If validation fails
    """
    try:
        info = parse_hocr(hocr_content)
    except HOCRParseError as e:
        raise HOCRValidationError(f"HOCR parsing failed: {e}")

    if info.page_count == 0:
        raise HOCRValidationError("HOCR must contain at least one ocr_page")

    if not info.has_bounding_boxes:
        raise HOCRValidationError("HOCR must contain bounding box coordinates")


def extract_bbox(element_title: str) -> tuple[int, int, int, int] | None:
    """
    Extract bounding box coordinates from title attribute.

    Args:
        element_title: Title attribute value (e.g., "bbox 10 20 50 40")

    Returns:
        Tuple of (x0, y0, x1, y1) or None if no bbox found
    """
    match = re.search(r"bbox (\d+) (\d+) (\d+) (\d+)", element_title)
    if match:
        return tuple(map(int, match.groups()))
    return None


def easyocr_to_hocr(easyocr_results: list, image_width: int, image_height: int) -> str:
    """
    Convert EasyOCR results to HOCR XML format.

    EasyOCR output format: [([[x1,y1], [x2,y2], [x3,y3], [x4,y4]], text, confidence), ...]
    HOCR format: XML with bbox coordinates and confidence (x_wconf)

    Args:
        easyocr_results: List of (bbox, text, confidence) tuples from EasyOCR
        image_width: Image width in pixels
        image_height: Image height in pixels

    Returns:
        HOCR XML string with recognized text and bounding boxes
    """
    # Build HOCR XML structure
    hocr_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"',
        '    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">',
        '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">',
        '<head>',
        '  <meta http-equiv="content-type" content="text/html; charset=utf-8" />',
        '  <meta name="ocr-system" content="easyocr" />',
        '  <meta name="ocr-capabilities" content="ocr_page ocr_carea ocr_par ocr_line ocrx_word" />',
        '</head>',
        '<body>',
        f'  <div class="ocr_page" id="page_1" title="bbox 0 0 {image_width} {image_height}">',
    ]

    # Add each text detection as an ocrx_word element
    for idx, result in enumerate(easyocr_results):
        # EasyOCR bbox format: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        bbox, text, confidence = result

        # Extract coordinates (convert to min/max format)
        x_coords = [point[0] for point in bbox]
        y_coords = [point[1] for point in bbox]
        x_min, x_max = int(min(x_coords)), int(max(x_coords))
        y_min, y_max = int(min(y_coords)), int(max(y_coords))

        # Convert confidence (0.0-1.0) to percentage (0-100)
        conf_percent = int(confidence * 100)

        # Escape text for XML
        escaped_text = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

        # Create HOCR word element
        hocr_lines.append(
            f'    <span class="ocrx_word" id="word_1_{idx + 1}" '
            f'title="bbox {x_min} {y_min} {x_max} {y_max}; x_wconf {conf_percent}">'
            f"{escaped_text}</span>"
        )

    # Close HOCR structure
    hocr_lines.extend(["  </div>", "</body>", "</html>"])

    return "\n".join(hocr_lines)
