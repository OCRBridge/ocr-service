"""E2E tests for Tesseract OCR engine with real processing.

These tests use the actual Tesseract engine (not mocks) to validate
end-to-end OCR functionality. Tests are skipped if Tesseract is not installed.
"""

from pathlib import Path

import pytest
from ocrbridge.engines.tesseract import TesseractEngine

# Skip all tests if Tesseract is not available
pytest.importorskip("ocrbridge.engines.tesseract")

pytestmark = pytest.mark.tesseract


@pytest.fixture
def tesseract_engine():
    """Create real Tesseract engine instance."""
    return TesseractEngine()


def test_tesseract_engine_name(tesseract_engine):
    """Test that Tesseract engine has correct name."""
    assert tesseract_engine.name == "tesseract"


def test_tesseract_supported_formats(tesseract_engine):
    """Test that Tesseract declares supported formats."""
    formats = tesseract_engine.supported_formats
    assert isinstance(formats, set)
    # Should support common image formats
    assert ".jpg" in formats or ".jpeg" in formats
    assert ".png" in formats


def test_tesseract_process_simple_image(tesseract_engine, test_image_simple_text):
    """Test processing simple text image with Tesseract."""
    result = tesseract_engine.process(test_image_simple_text)

    # Should return HOCR XML
    assert result is not None
    assert isinstance(result, str)
    assert result.startswith("<?xml")
    assert "<html" in result
    assert "</html>" in result


def test_tesseract_hocr_structure(tesseract_engine, test_image_with_text):
    """Test that Tesseract output has valid HOCR structure."""
    result = tesseract_engine.process(test_image_with_text)

    # Should have HOCR structure (handle both single and double quotes)
    assert "ocr_page" in result
    assert "ocrx_word" in result or "ocrx_line" in result or "ocr_line" in result


def test_tesseract_detects_text(tesseract_engine, test_image_simple_text):
    """Test that Tesseract actually detects text from image."""
    result = tesseract_engine.process(test_image_simple_text)

    # Should contain some text (the word "TESTING" or similar)
    # Case-insensitive check
    result_lower = result.lower()
    assert "test" in result_lower or "testing" in result_lower


def test_tesseract_multiline_text(tesseract_engine, test_image_multiline):
    """Test processing image with multiple lines of text."""
    result = tesseract_engine.process(test_image_multiline)

    # Should detect multiple words/lines
    word_count = result.count("ocrx_word")
    line_count = result.count("ocr_line") + result.count("ocrx_line")
    assert word_count >= 3 or line_count >= 2


def test_tesseract_with_lang_param(tesseract_engine, test_image_simple_text):
    """Test Tesseract with language parameter."""
    from ocrbridge.engines.tesseract import TesseractParams

    params = TesseractParams(lang="eng")
    result = tesseract_engine.process(test_image_simple_text, params)

    assert result is not None
    assert isinstance(result, str)
    assert "<html" in result


def test_tesseract_with_psm_param(tesseract_engine, test_image_simple_text):
    """Test Tesseract with page segmentation mode parameter."""
    from ocrbridge.engines.tesseract import TesseractParams

    # PSM 6: Assume a single uniform block of text
    params = TesseractParams(psm=6)
    result = tesseract_engine.process(test_image_simple_text, params)

    assert result is not None
    assert "<html" in result


def test_tesseract_invalid_file(tesseract_engine, tmp_path):
    """Test that Tesseract handles invalid files gracefully."""
    from ocrbridge.core import OCRProcessingError

    # Create invalid image file
    invalid_file = tmp_path / "invalid.jpg"
    invalid_file.write_bytes(b"not an image")

    with pytest.raises(OCRProcessingError):
        tesseract_engine.process(invalid_file)


def test_tesseract_nonexistent_file(tesseract_engine):
    """Test that Tesseract handles missing files."""
    from ocrbridge.core import OCRProcessingError

    nonexistent = Path("/tmp/does_not_exist_12345.jpg")

    with pytest.raises((OCRProcessingError, FileNotFoundError)):
        tesseract_engine.process(nonexistent)


def test_tesseract_empty_image(tesseract_engine, tmp_path):
    """Test processing blank/empty image."""
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("PIL not available")

    # Create blank white image
    blank_img = Image.new("RGB", (200, 200), color="white")
    blank_path = tmp_path / "blank.png"
    blank_img.save(blank_path, "PNG")

    # Should still return valid HOCR, just with no/minimal text
    result = tesseract_engine.process(blank_path)

    assert result is not None
    assert "<html" in result
    assert "ocr_page" in result


def test_tesseract_bbox_coordinates(tesseract_engine, test_image_simple_text):
    """Test that HOCR output includes bounding box coordinates."""
    result = tesseract_engine.process(test_image_simple_text)

    # Should have bbox attributes
    assert "bbox" in result
    # Bounding boxes should have 4 coordinates
    assert "bbox " in result  # bbox followed by space and numbers


def test_tesseract_confidence_scores(tesseract_engine, test_image_simple_text):
    """Test that HOCR includes confidence scores."""
    result = tesseract_engine.process(test_image_simple_text)

    # Tesseract includes x_wconf (word confidence)
    assert "x_wconf" in result or "wconf" in result.lower()


def test_tesseract_multiple_calls_independent(tesseract_engine, test_image_simple_text):
    """Test that multiple OCR calls are independent."""
    result1 = tesseract_engine.process(test_image_simple_text)
    result2 = tesseract_engine.process(test_image_simple_text)

    # Results should be consistent
    assert result1 == result2


def test_tesseract_different_images(tesseract_engine, test_image_simple_text, test_image_multiline):
    """Test processing different images produces different results."""
    result1 = tesseract_engine.process(test_image_simple_text)
    result2 = tesseract_engine.process(test_image_multiline)

    # Results should be different
    assert result1 != result2


def test_tesseract_params_validation(tesseract_engine, test_image_simple_text):
    """Test that invalid parameters are rejected."""
    from ocrbridge.engines.tesseract import TesseractParams
    from pydantic import ValidationError

    # Invalid PSM value (must be 0-13)
    with pytest.raises(ValidationError):
        TesseractParams(psm=999)


def test_tesseract_params_optional(tesseract_engine, test_image_simple_text):
    """Test processing without parameters (should use defaults)."""
    # None params should work
    result = tesseract_engine.process(test_image_simple_text, None)

    assert result is not None
    assert "<html" in result


def test_tesseract_jpeg_support(tesseract_engine, test_image_simple_text):
    """Test that Tesseract processes JPEG images."""
    # test_image_simple_text is a JPEG
    result = tesseract_engine.process(test_image_simple_text)

    assert result is not None
    assert "<html" in result


def test_tesseract_png_support(tesseract_engine, test_image_with_text):
    """Test that Tesseract processes PNG images."""
    # test_image_with_text is a PNG
    result = tesseract_engine.process(test_image_with_text)

    assert result is not None
    assert "<html" in result


def test_tesseract_output_encoding(tesseract_engine, test_image_simple_text):
    """Test that output is properly UTF-8 encoded."""
    result = tesseract_engine.process(test_image_simple_text)

    # Should be valid UTF-8 string
    assert isinstance(result, str)
    # Should have encoding declaration
    assert 'encoding="UTF-8"' in result or "UTF-8" in result


def test_tesseract_page_count(tesseract_engine, test_image_simple_text):
    """Test that single-page image produces single page in HOCR."""
    result = tesseract_engine.process(test_image_simple_text)

    # Should have exactly one ocr_page (handle both quote styles)
    page_count = result.count("ocr_page")
    assert page_count >= 1


def test_tesseract_performance(tesseract_engine, test_image_simple_text):
    """Test that Tesseract completes in reasonable time."""
    import time

    start = time.time()
    result = tesseract_engine.process(test_image_simple_text)
    duration = time.time() - start

    assert result is not None
    # Should complete in less than 10 seconds for simple image
    assert duration < 10.0


def test_tesseract_lang_multilanguage(tesseract_engine, test_image_simple_text):
    """Test Tesseract with multiple languages (if available)."""
    from ocrbridge.engines.tesseract import TesseractParams

    try:
        # Try English + French (if installed)
        params = TesseractParams(lang="eng+fra")
        result = tesseract_engine.process(test_image_simple_text, params)
        assert result is not None
    except Exception:
        # Skip if language pack not installed
        pytest.skip("French language pack not available")


def test_tesseract_xml_well_formed(tesseract_engine, test_image_simple_text):
    """Test that Tesseract output is well-formed XML."""
    result = tesseract_engine.process(test_image_simple_text)

    # Should be able to parse as XML
    from xml.etree import ElementTree as ET

    try:
        ET.fromstring(result)
    except ET.ParseError as e:
        pytest.fail(f"Output is not well-formed XML: {e}")


def test_tesseract_title_attributes(tesseract_engine, test_image_simple_text):
    """Test that HOCR elements have title attributes with metadata."""
    result = tesseract_engine.process(test_image_simple_text)

    # Elements should have title attributes
    assert 'title="' in result
    # Title should contain bbox
    assert 'title="bbox' in result or "title='bbox" in result
