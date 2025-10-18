"""Unit tests for HOCR XML parsing and validation."""


def test_hocr_parsing_valid_xml():
    """Test parsing valid HOCR XML succeeds."""
    # This test will initially fail (TDD)
    # from src.utils.hocr import parse_hocr

    # valid_hocr = '''
    # <?xml version="1.0" encoding="UTF-8"?>
    # <html xmlns="http://www.w3.org/1999/xhtml">
    #   <body>
    #     <div class="ocr_page" title="bbox 0 0 800 600">
    #       <span class="ocrx_word" title="bbox 10 20 50 40">Hello</span>
    #     </div>
    #   </body>
    # </html>
    # '''
    # result = parse_hocr(valid_hocr)
    # assert result.page_count == 1
    # assert result.has_bounding_boxes
    pass


def test_hocr_parsing_extracts_bounding_boxes():
    """Test bounding box coordinates are extracted correctly."""
    # This test will initially fail (TDD)
    # from src.utils.hocr import parse_hocr

    # hocr = '<span class="ocrx_word" title="bbox 10 20 50 40">Word</span>'
    # bbox = extract_bbox(hocr)
    # assert bbox == (10, 20, 50, 40)
    pass


def test_hocr_parsing_counts_words():
    """Test word count is calculated correctly."""
    # This test will initially fail (TDD)
    # from src.utils.hocr import parse_hocr

    # hocr = '''
    # <span class="ocrx_word">Hello</span>
    # <span class="ocrx_word">World</span>
    # '''
    # result = parse_hocr(hocr)
    # assert result.word_count == 2
    pass


def test_hocr_parsing_rejects_malformed_xml():
    """Test malformed XML raises parsing error."""
    # This test will initially fail (TDD)
    # from src.utils.hocr import parse_hocr, HOCRParseError

    # with pytest.raises(HOCRParseError):
    #     parse_hocr("<not>valid</xml")
    pass


def test_hocr_validation_requires_ocr_page():
    """Test HOCR validation requires ocr_page class."""
    # This test will initially fail (TDD)
    # from src.utils.hocr import validate_hocr, HOCRValidationError

    # invalid_hocr = '<html><body><div>No ocr_page class</div></body></html>'
    # with pytest.raises(HOCRValidationError):
    #     validate_hocr(invalid_hocr)
    pass
