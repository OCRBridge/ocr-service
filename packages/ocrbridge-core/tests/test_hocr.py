"""Tests for HOCR utilities."""

import pytest
from ocrbridge.core.utils import (
    HOCRInfo,
    HOCRParseError,
    HOCRValidationError,
    extract_bbox,
    parse_hocr,
    validate_hocr,
)


VALID_HOCR = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta name="ocr-system" content="tesseract" />
</head>
<body>
  <div class="ocr_page" id="page_1" title="bbox 0 0 100 100">
    <span class="ocr_line" id="line_1" title="bbox 10 20 90 30">
      <span class="ocrx_word" id="word_1" title="bbox 10 20 40 30; x_wconf 95">Hello</span>
      <span class="ocrx_word" id="word_2" title="bbox 50 20 90 30; x_wconf 90">World</span>
    </span>
  </div>
</body>
</html>"""


def test_parse_hocr_valid():
    """Test parsing valid HOCR."""
    info = parse_hocr(VALID_HOCR)
    assert isinstance(info, HOCRInfo)
    assert info.page_count >= 1
    assert info.word_count == 2
    assert info.has_bounding_boxes is True


def test_parse_hocr_invalid():
    """Test parsing invalid HOCR."""
    with pytest.raises(HOCRParseError):
        parse_hocr("<invalid>xml")


def test_validate_hocr_valid():
    """Test validating valid HOCR."""
    # Should not raise
    validate_hocr(VALID_HOCR)


def test_validate_hocr_no_pages():
    """Test validating HOCR with no pages."""
    hocr_no_pages = """<?xml version="1.0" encoding="UTF-8"?>
    <html xmlns="http://www.w3.org/1999/xhtml">
    <body></body>
    </html>"""

    with pytest.raises(HOCRValidationError, match="at least one ocr_page"):
        validate_hocr(hocr_no_pages)


def test_validate_hocr_no_bbox():
    """Test validating HOCR without bounding boxes."""
    hocr_no_bbox = """<?xml version="1.0" encoding="UTF-8"?>
    <html xmlns="http://www.w3.org/1999/xhtml">
    <body>
      <div class="ocr_page" id="page_1">
        <span class="ocrx_word" id="word_1">Hello</span>
      </div>
    </body>
    </html>"""

    with pytest.raises(HOCRValidationError, match="bounding box"):
        validate_hocr(hocr_no_bbox)


def test_extract_bbox_valid():
    """Test extracting bounding box from title."""
    bbox = extract_bbox("bbox 10 20 50 60; x_wconf 95")
    assert bbox == (10, 20, 50, 60)


def test_extract_bbox_no_bbox():
    """Test extracting bbox when none present."""
    bbox = extract_bbox("x_wconf 95")
    assert bbox is None


def test_extract_bbox_empty():
    """Test extracting bbox from empty string."""
    bbox = extract_bbox("")
    assert bbox is None
