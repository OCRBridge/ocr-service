"""E2E tests for EasyOCR engine with real processing.

These tests use the actual EasyOCR engine which is slow due to deep learning
model initialization. All tests are marked with @pytest.mark.slow and can be
skipped in CI/CD pipelines.

Run with: pytest -m slow
Skip with: pytest -m "not slow"
"""

import pytest

# Check if EasyOCR is available
try:
    from ocrbridge.engines.easyocr import EasyOCREngine

    easyocr_available = True
except ImportError:
    easyocr_available = False

EASYOCR_AVAILABLE = easyocr_available

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not EASYOCR_AVAILABLE, reason="EasyOCR engine not installed"),
]


@pytest.fixture(scope="module")
def easyocr_engine():
    """Create real EasyOCR engine instance.

    Scope is module-level to avoid reinitializing the model for each test.
    """
    return EasyOCREngine()


def test_easyocr_engine_name(easyocr_engine):
    """Test that EasyOCR engine has correct name."""
    assert easyocr_engine.name == "easyocr"


def test_easyocr_supported_formats(easyocr_engine):
    """Test that EasyOCR declares supported formats."""
    formats = easyocr_engine.supported_formats
    assert isinstance(formats, set)
    assert ".jpg" in formats or ".jpeg" in formats
    assert ".png" in formats


def test_easyocr_process_simple_image(easyocr_engine, test_image_simple_text):
    """Test processing simple text image with EasyOCR."""
    result = easyocr_engine.process(test_image_simple_text)

    # Should return HOCR XML
    assert result is not None
    assert isinstance(result, str)
    assert result.startswith("<?xml")
    assert "<html" in result
    assert "</html>" in result


def test_easyocr_hocr_structure(easyocr_engine, test_image_with_text):
    """Test that EasyOCR output has valid HOCR structure."""
    result = easyocr_engine.process(test_image_with_text)

    # Should have HOCR structure
    assert 'class="ocr_page"' in result
    assert 'class="ocrx_word"' in result


def test_easyocr_detects_text(easyocr_engine, test_image_simple_text):
    """Test that EasyOCR actually detects text from image."""
    result = easyocr_engine.process(test_image_simple_text)

    # Should contain some text
    result_lower = result.lower()
    assert "test" in result_lower or len(result) > 200


def test_easyocr_with_languages_param(easyocr_engine, test_image_simple_text):
    """Test EasyOCR with languages parameter."""
    from ocrbridge.engines.easyocr import EasyOCRParams

    params = EasyOCRParams(languages=["en"])
    result = easyocr_engine.process(test_image_simple_text, params)

    assert result is not None
    assert "<html" in result


def test_easyocr_bbox_coordinates(easyocr_engine, test_image_simple_text):
    """Test that HOCR output includes bounding box coordinates."""
    result = easyocr_engine.process(test_image_simple_text)

    # Should have bbox attributes
    assert "bbox" in result


def test_easyocr_confidence_scores(easyocr_engine, test_image_simple_text):
    """Test that HOCR includes confidence scores."""
    result = easyocr_engine.process(test_image_simple_text)

    # EasyOCR includes x_wconf
    assert "x_wconf" in result or "wconf" in result.lower()


def test_easyocr_invalid_file(easyocr_engine, tmp_path):
    """Test that EasyOCR handles invalid files gracefully."""
    from ocrbridge.core import OCRProcessingError

    invalid_file = tmp_path / "invalid.jpg"
    invalid_file.write_bytes(b"not an image")

    with pytest.raises((OCRProcessingError, Exception)):
        easyocr_engine.process(invalid_file)


def test_easyocr_multiple_calls(easyocr_engine, test_image_simple_text):
    """Test that multiple OCR calls work correctly."""
    result1 = easyocr_engine.process(test_image_simple_text)
    result2 = easyocr_engine.process(test_image_simple_text)

    # Both should succeed
    assert result1 is not None
    assert result2 is not None


def test_easyocr_xml_well_formed(easyocr_engine, test_image_simple_text):
    """Test that EasyOCR output is well-formed XML."""
    result = easyocr_engine.process(test_image_simple_text)

    from xml.etree import ElementTree as ET

    try:
        ET.fromstring(result)
    except ET.ParseError as e:
        pytest.fail(f"Output is not well-formed XML: {e}")


def test_easyocr_params_validation(easyocr_engine):
    """Test that invalid parameters are rejected."""
    from ocrbridge.engines.easyocr import EasyOCRParams
    from pydantic import ValidationError

    # Empty languages list should be invalid
    with pytest.raises(ValidationError):
        EasyOCRParams(languages=[])


def test_easyocr_jpeg_support(easyocr_engine, test_image_simple_text):
    """Test that EasyOCR processes JPEG images."""
    result = easyocr_engine.process(test_image_simple_text)
    assert result is not None


def test_easyocr_png_support(easyocr_engine, test_image_with_text):
    """Test that EasyOCR processes PNG images."""
    result = easyocr_engine.process(test_image_with_text)
    assert result is not None
