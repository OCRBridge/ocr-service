"""Unit tests for HOCR parsing and conversion utilities.

Tests HOCR XML parsing, validation, bounding box extraction,
and EasyOCR to HOCR conversion with line grouping.
"""

import pytest

from src.utils.hocr import (
    HOCRInfo,
    HOCRParseError,
    HOCRValidationError,
    easyocr_to_hocr,
    extract_bbox,
    parse_hocr,
    validate_hocr,
)

# ==============================================================================
# HOCR Parsing Tests
# ==============================================================================


def test_parse_hocr_valid(sample_hocr):
    """Test parsing valid HOCR XML."""
    info = parse_hocr(sample_hocr)

    assert isinstance(info, HOCRInfo)
    assert info.page_count >= 1
    assert info.word_count >= 1
    assert info.has_bounding_boxes is True


def test_parse_hocr_multi_page(sample_hocr_multi_page):
    """Test parsing HOCR with multiple pages."""
    info = parse_hocr(sample_hocr_multi_page)

    assert info.page_count == 2
    assert info.word_count == 4  # 2 words per page


def test_parse_hocr_counts_pages(sample_hocr):
    """Test that parse_hocr correctly counts ocr_page elements."""
    info = parse_hocr(sample_hocr)

    # sample_hocr has 1 page
    assert info.page_count == 1


def test_parse_hocr_counts_words(sample_hocr):
    """Test that parse_hocr correctly counts ocrx_word elements."""
    info = parse_hocr(sample_hocr)

    # sample_hocr has 2 words: "Hello" and "World"
    assert info.word_count == 2


def test_parse_hocr_detects_bboxes(sample_hocr):
    """Test that parse_hocr detects presence of bounding boxes."""
    info = parse_hocr(sample_hocr)

    assert info.has_bounding_boxes is True


def test_parse_hocr_no_bbox(invalid_hocr_no_bbox):
    """Test HOCR without bounding boxes is detected."""
    info = parse_hocr(invalid_hocr_no_bbox)

    assert info.has_bounding_boxes is False


def test_parse_hocr_invalid_xml():
    """Test that invalid XML raises HOCRParseError."""
    invalid_xml = "<html><unclosed>"

    with pytest.raises(HOCRParseError) as exc_info:
        parse_hocr(invalid_xml)

    assert "Failed to parse" in str(exc_info.value)


def test_parse_hocr_empty_string():
    """Test parsing empty string raises HOCRParseError."""
    with pytest.raises(HOCRParseError):
        parse_hocr("")


def test_parse_hocr_minimum_page_count():
    """Test that page_count returns 0 when no pages found."""
    hocr_no_pages = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body></body>
</html>"""

    info = parse_hocr(hocr_no_pages)

    # Should return actual count (0 if no pages)
    assert info.page_count == 0


# ==============================================================================
# HOCR Validation Tests
# ==============================================================================


def test_validate_hocr_valid(sample_hocr):
    """Test that valid HOCR passes validation."""
    # Should not raise any exception
    validate_hocr(sample_hocr)


def test_validate_hocr_no_pages(invalid_hocr_no_pages):
    """Test that HOCR without pages raises HOCRValidationError."""
    with pytest.raises(HOCRValidationError) as exc_info:
        validate_hocr(invalid_hocr_no_pages)

    error_message = str(exc_info.value)
    assert "page" in error_message.lower()


def test_validate_hocr_no_bboxes(invalid_hocr_no_bbox):
    """Test that HOCR without bounding boxes raises HOCRValidationError."""
    with pytest.raises(HOCRValidationError) as exc_info:
        validate_hocr(invalid_hocr_no_bbox)

    error_message = str(exc_info.value)
    assert "bounding box" in error_message.lower()


def test_validate_hocr_invalid_xml():
    """Test that invalid XML is caught during validation."""
    with pytest.raises(HOCRValidationError) as exc_info:
        validate_hocr("<invalid>xml")

    assert "parsing failed" in str(exc_info.value).lower()


# ==============================================================================
# Bounding Box Extraction Tests
# ==============================================================================


def test_extract_bbox_valid():
    """Test extracting valid bounding box coordinates."""
    title = "bbox 10 20 100 200; x_wconf 95"

    bbox = extract_bbox(title)

    assert bbox == (10, 20, 100, 200)


def test_extract_bbox_only_bbox():
    """Test extracting bbox when title only contains bbox."""
    title = "bbox 0 0 500 500"

    bbox = extract_bbox(title)

    assert bbox == (0, 0, 500, 500)


def test_extract_bbox_large_coordinates():
    """Test extracting bbox with large coordinate values."""
    title = "bbox 1000 2000 3000 4000"

    bbox = extract_bbox(title)

    assert bbox == (1000, 2000, 3000, 4000)


def test_extract_bbox_no_bbox():
    """Test that title without bbox returns None."""
    title = "x_wconf 95"

    bbox = extract_bbox(title)

    assert bbox is None


def test_extract_bbox_empty_string():
    """Test that empty title returns None."""
    bbox = extract_bbox("")

    assert bbox is None


def test_extract_bbox_returns_tuple():
    """Test that extracted bbox is a tuple of integers."""
    title = "bbox 10 20 30 40"

    bbox = extract_bbox(title)

    assert isinstance(bbox, tuple)
    assert len(bbox) == 4
    assert all(isinstance(coord, int) for coord in bbox)


# ==============================================================================
# EasyOCR to HOCR Conversion Tests
# ==============================================================================


def test_easyocr_to_hocr_simple(sample_easyocr_results):
    """Test basic EasyOCR to HOCR conversion."""
    hocr = easyocr_to_hocr(sample_easyocr_results, image_width=300, image_height=100)

    # Should be valid XML
    assert hocr.startswith('<?xml version="1.0"')
    assert "<html" in hocr
    assert "</html>" in hocr

    # Should contain page with correct dimensions
    assert 'class="ocr_page"' in hocr
    assert "bbox 0 0 300 100" in hocr

    # Should contain recognized words
    assert "Hello" in hocr
    assert "World" in hocr

    # Should contain confidence scores
    assert "x_wconf 95" in hocr
    assert "x_wconf 92" in hocr


def test_easyocr_to_hocr_multi_line(sample_easyocr_multiline):
    """Test EasyOCR to HOCR conversion with multiple lines."""
    hocr = easyocr_to_hocr(sample_easyocr_multiline, image_width=300, image_height=150)

    # Should contain multiple line elements
    assert hocr.count('class="ocr_line"') >= 2

    # Should contain all words
    assert "First" in hocr
    assert "Line" in hocr
    assert "Second" in hocr


def test_easyocr_to_hocr_empty():
    """Test conversion with empty results."""
    hocr = easyocr_to_hocr([], image_width=100, image_height=100)

    # Should still be valid HOCR structure
    assert "<html" in hocr
    assert 'class="ocr_page"' in hocr
    # But no words or lines
    assert 'class="ocrx_word"' not in hocr


def test_easyocr_to_hocr_confidence_conversion():
    """Test that confidence is converted from 0-1 to 0-100."""
    results = [([[10, 10], [50, 10], [50, 50], [10, 50]], "Test", 0.75)]

    hocr = easyocr_to_hocr(results, image_width=100, image_height=100)

    # 0.75 should be converted to 75
    assert "x_wconf 75" in hocr


def test_easyocr_to_hocr_xml_escaping():
    """Test that special XML characters are properly escaped."""
    results = [
        ([[10, 10], [50, 10], [50, 50], [10, 50]], "Test&<>'\"", 0.95),
    ]

    hocr = easyocr_to_hocr(results, image_width=100, image_height=100)

    # Should escape XML special characters
    assert "&amp;" in hocr
    assert "&lt;" in hocr
    assert "&gt;" in hocr
    assert "&quot;" in hocr or "&apos;" in hocr


def test_easyocr_to_hocr_system_metadata():
    """Test that HOCR includes correct metadata."""
    hocr = easyocr_to_hocr([], image_width=100, image_height=100)

    assert 'name="ocr-system" content="easyocr"' in hocr
    assert 'name="ocr-capabilities"' in hocr


# ==============================================================================
# Line Grouping Tests
# ==============================================================================


def test_group_easyocr_words_single_line():
    """Test grouping words on a single line via HOCR output."""
    # Two words with same vertical position (y=10-50)
    results = [
        ([[10, 10], [100, 10], [100, 50], [10, 50]], "Hello", 0.95),
        ([[110, 10], [200, 10], [200, 50], [110, 50]], "World", 0.92),
    ]

    hocr = easyocr_to_hocr(results, image_width=220, image_height=60)
    # Should produce a single line group and include both words
    assert hocr.count('class="ocr_line"') == 1
    assert "Hello" in hocr and "World" in hocr


def test_group_easyocr_words_multi_line(sample_easyocr_multiline):
    """Test grouping words into multiple lines via HOCR output."""
    hocr = easyocr_to_hocr(sample_easyocr_multiline, image_width=220, image_height=120)
    assert hocr.count('class="ocr_line"') == 2
    # Both lines' words should be present in the HOCR
    assert "First" in hocr and "Second" in hocr


def test_group_easyocr_words_empty():
    """Test grouping with empty results via HOCR output."""
    hocr = easyocr_to_hocr([], image_width=10, image_height=10)
    # No words or lines should be present
    assert 'class="ocr_line"' not in hocr


def test_group_easyocr_words_single_word():
    """Test grouping with single word via HOCR output."""
    results = [([[10, 10], [100, 10], [100, 50], [10, 50]], "Solo", 0.95)]

    hocr = easyocr_to_hocr(results, image_width=120, image_height=60)
    assert hocr.count('class="ocr_line"') == 1
    assert "Solo" in hocr


def test_group_easyocr_words_line_bbox():
    """Test that line bbox encompasses all words via HOCR output."""
    results = [
        ([[10, 10], [100, 10], [100, 50], [10, 50]], "Word1", 0.95),
        ([[110, 15], [200, 15], [200, 45], [110, 45]], "Word2", 0.92),
    ]

    hocr = easyocr_to_hocr(results, image_width=210, image_height=60)
    # Expect the line bbox to cover from x=10..200 and y around 10..50
    assert 'class="ocr_line"' in hocr
    assert "bbox 10" in hocr and "200" in hocr


def test_group_easyocr_words_left_to_right_sorting():
    """Test that words within a line are sorted left to right via HOCR output."""
    # Add words in reverse order (right to left)
    results = [
        ([[110, 10], [200, 10], [200, 50], [110, 50]], "Second", 0.92),
        ([[10, 10], [100, 10], [100, 50], [10, 50]], "First", 0.95),
    ]

    hocr = easyocr_to_hocr(results, image_width=220, image_height=60)
    # In HOCR string, "First" should appear before "Second"
    assert hocr.find("First") != -1 and hocr.find("Second") != -1
    assert hocr.find("First") < hocr.find("Second")


def test_group_easyocr_words_vertical_sorting():
    """Test that lines are sorted top to bottom via HOCR output."""
    # Add lines in reverse order (bottom to top)
    results = [
        # Bottom line (y=60-100)
        ([[10, 60], [100, 60], [100, 100], [10, 100]], "Bottom", 0.90),
        # Top line (y=10-50)
        ([[10, 10], [100, 10], [100, 50], [10, 50]], "Top", 0.95),
    ]

    hocr = easyocr_to_hocr(results, image_width=120, image_height=110)
    # "Top" should appear earlier than "Bottom" in the HOCR output
    assert hocr.find("Top") < hocr.find("Bottom")


def test_group_easyocr_words_threshold_calculation():
    """Test that line grouping uses a reasonable threshold via HOCR output."""
    # Mix of different height words
    results = [
        # Tall word
        ([[10, 10], [50, 10], [50, 100], [10, 100]], "Tall", 0.95),
        # Short word nearby (should be same line due to threshold)
        ([[60, 40], [100, 40], [100, 70], [60, 70]], "Short", 0.92),
    ]

    hocr = easyocr_to_hocr(results, image_width=120, image_height=110)
    # Expect at least one line containing both words
    assert hocr.count('class="ocr_line"') >= 1
    assert "Tall" in hocr and "Short" in hocr


# ==============================================================================
# Integration Tests (Parse → Validate workflow)
# ==============================================================================


def test_parse_and_validate_workflow(sample_hocr):
    """Test complete workflow of parsing and validating HOCR."""
    # Parse
    info = parse_hocr(sample_hocr)
    assert info.page_count >= 1

    # Validate
    validate_hocr(sample_hocr)  # Should not raise


def test_easyocr_to_hocr_produces_valid_hocr(sample_easyocr_results):
    """Test that EasyOCR conversion produces valid, parseable HOCR."""
    # Convert
    hocr = easyocr_to_hocr(sample_easyocr_results, image_width=300, image_height=100)

    # Parse (should not raise)
    info = parse_hocr(hocr)
    assert info.page_count >= 1
    assert info.word_count >= 1

    # Validate (should not raise)
    validate_hocr(hocr)
