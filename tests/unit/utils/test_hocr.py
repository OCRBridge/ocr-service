"""Unit tests for HOCR parsing and conversion utilities.

Tests HOCR XML parsing, validation, bounding box extraction,
and EasyOCR to HOCR conversion with line grouping.
"""

import pytest

# Generic HOCR utilities from ocrbridge-core
from ocrbridge.core.utils.hocr import (
    HOCRInfo,
    HOCRParseError,
    HOCRValidationError,
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
# Integration Tests (Parse → Validate workflow)
# ==============================================================================


def test_parse_and_validate_workflow(sample_hocr):
    """Test complete workflow of parsing and validating HOCR."""
    # Parse
    info = parse_hocr(sample_hocr)
    assert info.page_count >= 1

    # Validate
    validate_hocr(sample_hocr)  # Should not raise
