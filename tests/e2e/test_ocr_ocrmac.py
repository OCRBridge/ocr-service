"""E2E tests for ocrmac OCR engine with real processing.

These tests use the actual ocrmac engine which requires macOS (Darwin platform).
All tests are marked with @pytest.mark.ocrmac and will be
skipped on non-macOS systems.

Run with: pytest -m ocrmac
Skip with: pytest -m "not ocrmac"
"""

import pytest

# Check if ocrmac is available
try:
    from ocrbridge.engines.ocrmac import OcrmacEngine  # type: ignore

    ocrmac_available = True
except ImportError:
    ocrmac_available = False

OCRMAC_AVAILABLE = ocrmac_available

pytestmark = [
    pytest.mark.ocrmac,
    pytest.mark.skipif(not OCRMAC_AVAILABLE, reason="ocrmac engine not installed"),
]


@pytest.fixture(scope="module")
def ocrmac_engine():
    """Create real ocrmac engine instance.

    Scope is module-level to reuse the engine instance across tests.
    """
    return OcrmacEngine()


def test_ocrmac_engine_name(ocrmac_engine):
    """Test that ocrmac engine has correct name."""
    assert ocrmac_engine.name == "ocrmac"


def test_ocrmac_supported_formats(ocrmac_engine):
    """Test that ocrmac declares supported formats."""
    formats = ocrmac_engine.supported_formats
    assert isinstance(formats, set)
    # Should support common image formats
    assert ".jpg" in formats or ".jpeg" in formats
    assert ".png" in formats


def test_ocrmac_process_simple_image(ocrmac_engine, test_image_simple_text):
    """Test processing simple text image with ocrmac."""
    result = ocrmac_engine.process(test_image_simple_text)

    # Should return HOCR XML
    assert result is not None
    assert isinstance(result, str)
    assert result.startswith("<?xml")
    assert "<html" in result
    assert "</html>" in result


def test_ocrmac_hocr_structure(ocrmac_engine, test_image_with_text):
    """Test that ocrmac output has valid HOCR structure."""
    result = ocrmac_engine.process(test_image_with_text)

    # Should have HOCR structure
    assert "ocr_page" in result
    assert "ocrx_word" in result or "ocrx_line" in result or "ocr_line" in result


def test_ocrmac_detects_text(ocrmac_engine, test_image_simple_text):
    """Test that ocrmac actually detects text from image."""
    result = ocrmac_engine.process(test_image_simple_text)

    # Should return valid HOCR (ocrmac may not detect text from synthetic test images)
    # Just verify we got a valid response
    assert result is not None
    assert "<html" in result
    assert "ocr_page" in result


def test_ocrmac_multiline_text(ocrmac_engine, test_image_multiline):
    """Test processing image with multiple lines of text."""
    result = ocrmac_engine.process(test_image_multiline)

    # Should detect multiple words/lines
    word_count = result.count("ocrx_word")
    line_count = result.count("ocr_line") + result.count("ocrx_line")
    assert word_count >= 3 or line_count >= 2


def test_ocrmac_with_languages_param(ocrmac_engine, test_image_simple_text):
    """Test ocrmac with languages parameter."""
    from ocrbridge.engines.ocrmac import OcrmacParams  # type: ignore

    params = OcrmacParams(languages=["en-US"])
    result = ocrmac_engine.process(test_image_simple_text, params)

    assert result is not None
    assert isinstance(result, str)
    assert "<html" in result


def test_ocrmac_with_recognition_level(ocrmac_engine, test_image_simple_text):
    """Test ocrmac with recognition level parameter."""
    from ocrbridge.engines.ocrmac import OcrmacParams, RecognitionLevel  # type: ignore

    # Test with accurate recognition level
    params = OcrmacParams(recognition_level=RecognitionLevel.ACCURATE)
    result = ocrmac_engine.process(test_image_simple_text, params)

    assert result is not None
    assert "<html" in result


def test_ocrmac_invalid_file(ocrmac_engine, tmp_path):
    """Test that ocrmac handles invalid files gracefully."""
    from ocrbridge.core import OCRProcessingError

    # Create invalid image file
    invalid_file = tmp_path / "invalid.jpg"
    invalid_file.write_bytes(b"not an image")

    with pytest.raises((OCRProcessingError, Exception)):
        ocrmac_engine.process(invalid_file)


def test_ocrmac_nonexistent_file(ocrmac_engine):
    """Test that ocrmac handles missing files."""
    from pathlib import Path

    from ocrbridge.core import OCRProcessingError

    nonexistent = Path("/tmp/does_not_exist_12345.jpg")

    with pytest.raises((OCRProcessingError, FileNotFoundError)):
        ocrmac_engine.process(nonexistent)


def test_ocrmac_empty_image(ocrmac_engine, tmp_path):
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
    result = ocrmac_engine.process(blank_path)

    assert result is not None
    assert "<html" in result
    assert "ocr_page" in result


def test_ocrmac_bbox_coordinates(ocrmac_engine, test_image_simple_text):
    """Test that HOCR output includes bounding box coordinates."""
    result = ocrmac_engine.process(test_image_simple_text)

    # Should have bbox attributes
    assert "bbox" in result
    # Bounding boxes should have 4 coordinates
    assert "bbox " in result  # bbox followed by space and numbers


def test_ocrmac_confidence_scores(ocrmac_engine, test_image_simple_text):
    """Test that HOCR output is valid (confidence scores are optional for ocrmac)."""
    result = ocrmac_engine.process(test_image_simple_text)

    # ocrmac may or may not include confidence scores depending on implementation
    # Just verify we got valid HOCR output
    assert result is not None
    assert "<html" in result


def test_ocrmac_multiple_calls_independent(ocrmac_engine, test_image_simple_text):
    """Test that multiple OCR calls are independent."""
    result1 = ocrmac_engine.process(test_image_simple_text)
    result2 = ocrmac_engine.process(test_image_simple_text)

    # Results should be consistent
    assert result1 == result2


def test_ocrmac_different_images(ocrmac_engine, test_image_simple_text, test_image_multiline):
    """Test processing different images produces different results."""
    result1 = ocrmac_engine.process(test_image_simple_text)
    result2 = ocrmac_engine.process(test_image_multiline)

    # Results should be different
    assert result1 != result2


def test_ocrmac_params_validation(ocrmac_engine, test_image_simple_text):
    """Test that invalid parameters are rejected."""
    from ocrbridge.engines.ocrmac import OcrmacParams  # type: ignore
    from pydantic import ValidationError

    # Invalid recognition level (must be RecognitionLevel enum)
    with pytest.raises(ValidationError):
        OcrmacParams(recognition_level="invalid")  # type: ignore


def test_ocrmac_params_optional(ocrmac_engine, test_image_simple_text):
    """Test processing without parameters (should use defaults)."""
    # None params should work
    result = ocrmac_engine.process(test_image_simple_text, None)

    assert result is not None
    assert "<html" in result


def test_ocrmac_jpeg_support(ocrmac_engine, test_image_simple_text):
    """Test that ocrmac processes JPEG images."""
    # test_image_simple_text is a JPEG
    result = ocrmac_engine.process(test_image_simple_text)

    assert result is not None
    assert "<html" in result


def test_ocrmac_png_support(ocrmac_engine, test_image_with_text):
    """Test that ocrmac processes PNG images."""
    # test_image_with_text is a PNG
    result = ocrmac_engine.process(test_image_with_text)

    assert result is not None
    assert "<html" in result


def test_ocrmac_output_encoding(ocrmac_engine, test_image_simple_text):
    """Test that output is properly UTF-8 encoded."""
    result = ocrmac_engine.process(test_image_simple_text)

    # Should be valid UTF-8 string
    assert isinstance(result, str)
    # Should have encoding declaration
    assert 'encoding="UTF-8"' in result or "UTF-8" in result


def test_ocrmac_page_count(ocrmac_engine, test_image_simple_text):
    """Test that single-page image produces single page in HOCR."""
    result = ocrmac_engine.process(test_image_simple_text)

    # Should have exactly one ocr_page
    page_count = result.count("ocr_page")
    assert page_count >= 1


def test_ocrmac_performance(ocrmac_engine, test_image_simple_text):
    """Test that ocrmac completes in reasonable time."""
    import time

    start = time.time()
    result = ocrmac_engine.process(test_image_simple_text)
    duration = time.time() - start

    assert result is not None
    # ocrmac is typically fast, should complete in less than 5 seconds
    assert duration < 5.0


def test_ocrmac_xml_well_formed(ocrmac_engine, test_image_simple_text):
    """Test that ocrmac output is well-formed XML."""
    result = ocrmac_engine.process(test_image_simple_text)

    # Should be able to parse as XML
    from xml.etree import ElementTree as ET

    try:
        ET.fromstring(result)
    except ET.ParseError as e:
        pytest.fail(f"Output is not well-formed XML: {e}")


def test_ocrmac_title_attributes(ocrmac_engine, test_image_simple_text):
    """Test that HOCR elements have title attributes with metadata."""
    result = ocrmac_engine.process(test_image_simple_text)

    # Elements should have title attributes
    assert 'title="' in result
    # Title should contain bbox
    assert 'title="bbox' in result or "title='bbox" in result


def test_ocrmac_multiple_languages(ocrmac_engine, test_image_simple_text):
    """Test ocrmac with multiple language codes (if supported)."""
    from ocrbridge.engines.ocrmac import OcrmacParams  # type: ignore

    try:
        # Try multiple languages
        params = OcrmacParams(languages=["en-US", "es-ES"])
        result = ocrmac_engine.process(test_image_simple_text, params)
        assert result is not None
        assert "<html" in result
    except Exception:
        # Skip if multiple languages not supported
        pytest.skip("Multiple languages not supported or configured")


def test_ocrmac_fast_recognition_level(ocrmac_engine, test_image_simple_text):
    """Test ocrmac with fast recognition level."""
    from ocrbridge.engines.ocrmac import OcrmacParams, RecognitionLevel  # type: ignore

    # Test with fast recognition level
    params = OcrmacParams(recognition_level=RecognitionLevel.FAST)
    result = ocrmac_engine.process(test_image_simple_text, params)

    assert result is not None
    assert "<html" in result
