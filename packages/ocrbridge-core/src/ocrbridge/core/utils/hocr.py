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

    # Define namespace for XML queries (used if elements not found without it)
    namespace = {"html": "http://www.w3.org/1999/xhtml"}

    # Count pages (elements with class="ocr_page")
    page_count = len(root.findall(".//*[@class='ocr_page']"))
    if page_count == 0:
        # Try with namespace
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
        coords = match.groups()
        return (int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3]))
    return None


def _group_easyocr_words_into_lines(easyocr_results: list) -> list[dict]:
    """
    Group EasyOCR word detections into lines based on vertical position.

    Args:
        easyocr_results: List of (bbox, text, confidence) tuples from EasyOCR

    Returns:
        List of line dictionaries, each containing:
            - bbox: (x_min, y_min, x_max, y_max) in pixels
            - words: List of word dictionaries with text, confidence, bbox
    """
    if not easyocr_results:
        return []

    # Convert EasyOCR results to word dictionaries
    words = []
    for result in easyocr_results:
        # EasyOCR bbox format: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        bbox, text, confidence = result

        # Extract coordinates (convert to min/max format)
        x_coords = [point[0] for point in bbox]
        y_coords = [point[1] for point in bbox]
        x_min, x_max = int(min(x_coords)), int(max(x_coords))
        y_min, y_max = int(min(y_coords)), int(max(y_coords))

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


def easyocr_to_hocr(easyocr_results: list, image_width: int, image_height: int) -> str:
    """
    Convert EasyOCR results to HOCR XML format with hierarchical structure.

    EasyOCR output format: [([[x1,y1], [x2,y2], [x3,y3], [x4,y4]], text, confidence), ...]
    HOCR format: XML with bbox coordinates and confidence (x_wconf)
    Creates proper hOCR structure: ocr_page → ocr_line → ocrx_word

    Args:
        easyocr_results: List of (bbox, text, confidence) tuples from EasyOCR
        image_width: Image width in pixels
        image_height: Image height in pixels

    Returns:
        HOCR XML string with recognized text and bounding boxes in hierarchical structure
    """
    # Build HOCR XML structure
    hocr_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">',
        '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">',
        "<head>",
        '  <meta http-equiv="content-type" content="text/html; charset=utf-8" />',
        '  <meta name="ocr-system" content="easyocr" />',
        '  <meta name="ocr-capabilities" content="ocr_page ocr_carea ocr_par ocr_line ocrx_word" />',
        "</head>",
        "<body>",
        f'  <div class="ocr_page" id="page_1" title="bbox 0 0 {image_width} {image_height}">',
    ]

    # Group words into lines
    lines = _group_easyocr_words_into_lines(easyocr_results)

    # Add each line with its words
    word_counter = 1
    for line_idx, line_data in enumerate(lines, start=1):
        line_bbox = line_data["bbox"]

        # Create line element
        hocr_lines.append(
            f'    <span class="ocr_line" id="line_1_{line_idx}" '
            f'title="bbox {line_bbox[0]} {line_bbox[1]} {line_bbox[2]} {line_bbox[3]}">'
        )

        # Add words to this line
        for word_data in line_data["words"]:
            # Convert confidence (0.0-1.0) to percentage (0-100)
            conf_percent = int(word_data["confidence"] * 100)

            # Escape text for XML
            escaped_text = (
                word_data["text"]
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;")
            )

            # Create HOCR word element
            word_bbox = word_data["bbox"]
            hocr_lines.append(
                f'      <span class="ocrx_word" id="word_1_{word_counter}" '
                f'title="bbox {word_bbox[0]} {word_bbox[1]} {word_bbox[2]} {word_bbox[3]}; x_wconf {conf_percent}">'
                f"{escaped_text}</span>"
            )

            word_counter += 1

        # Close line element
        hocr_lines.append("    </span>")

    # Close HOCR structure
    hocr_lines.extend(["  </div>", "</body>", "</html>"])

    return "\n".join(hocr_lines)
