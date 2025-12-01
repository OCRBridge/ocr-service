"""Shared pytest fixtures and configuration for all tests."""

import io
from unittest.mock import patch

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient

# ==============================================================================
# Application Fixtures
# ==============================================================================


@pytest.fixture
def app():
    """Create FastAPI app instance for testing."""
    from src.main import app

    return app


@pytest.fixture
def client(app, mock_engine_registry):
    """Synchronous test client for FastAPI endpoints.

    Sets up app state with mock engine registry for API tests.
    TestClient is created with raise_server_exceptions=True to see errors clearly.
    """
    # Manually inject mock engine registry before starting TestClient
    # This bypasses the lifespan initialization
    with TestClient(app, raise_server_exceptions=True) as test_client:
        # Set mock registry on app state
        app.state.engine_registry = mock_engine_registry

        # Register dynamic per-engine routes for tests
        # (since we bypass lifespan, we must include them manually)
        from src.api.routes.v2.dynamic_routes import register_engine_routes

        register_engine_routes(app, mock_engine_registry)

        yield test_client


# ==============================================================================
# Mock Engine Registry Fixtures
# ==============================================================================


@pytest.fixture
def mock_engine_registry():
    """Registry with mock engines for testing.

    Patches entry_points in the registry module to return mock engines.
    Returns EngineRegistry instance with mock Tesseract engine.
    """
    from tests.mocks.mock_engines import MockTesseractEngine
    from tests.mocks.mock_entry_points import mock_entry_points_factory

    engines = {"tesseract": MockTesseractEngine}
    mock_ep = mock_entry_points_factory(engines)

    # Patch entry_points where it's used in the registry module
    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        from src.services.ocr.registry_v2 import EngineRegistry

        yield EngineRegistry()


@pytest.fixture
def mock_tesseract_engine():
    """Individual mock Tesseract engine instance."""
    from tests.mocks.mock_engines import MockTesseractEngine

    return MockTesseractEngine()


# ==============================================================================
# File Fixtures
# ==============================================================================


@pytest.fixture
def sample_jpeg_bytes():
    """Valid JPEG file bytes with proper magic bytes and JFIF header."""
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00" + b"\x00" * 100


@pytest.fixture
def sample_png_bytes():
    """Valid PNG file bytes with proper magic bytes and IHDR chunk."""
    return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 100


@pytest.fixture
def sample_pdf_bytes():
    """Valid PDF file bytes with proper magic bytes and header."""
    return b"%PDF-1.4\n%\xc3\xa4\xc3\xbc\xc3\xb6\xc3\x9f\n" + b"\x00" * 100


@pytest.fixture
def sample_tiff_le_bytes():
    """Valid TIFF (little-endian) file bytes."""
    return b"II*\x00" + b"\x00" * 100


@pytest.fixture
def sample_tiff_be_bytes():
    """Valid TIFF (big-endian) file bytes."""
    return b"MM\x00*" + b"\x00" * 100


@pytest.fixture
def invalid_file_bytes():
    """Invalid file format bytes (not a supported format)."""
    return b"INVALID_FORMAT" + b"\x00" * 100


@pytest.fixture
def large_file_bytes():
    """File exceeding the 5MB sync upload limit (6MB)."""
    # 6MB file (exceeds 5MB sync limit)
    return b"\xff\xd8\xff\xe0" + b"\x00" * (6 * 1024 * 1024)


@pytest.fixture
def sample_upload_file(sample_jpeg_bytes):
    """FastAPI UploadFile instance for testing file uploads."""
    file_obj = io.BytesIO(sample_jpeg_bytes)
    return UploadFile(filename="test.jpg", file=file_obj)


@pytest.fixture
def create_upload_file():
    """Factory fixture to create UploadFile instances with custom content.

    Returns:
        Callable that takes bytes and filename and returns UploadFile

    Example:
        >>> upload_file = create_upload_file(b"\\xff\\xd8\\xff", "image.jpg")
    """

    def _create(content: bytes, filename: str = "test.jpg") -> UploadFile:
        file_obj = io.BytesIO(content)
        return UploadFile(filename=filename, file=file_obj)

    return _create


# ==============================================================================
# HOCR Fixtures
# ==============================================================================


@pytest.fixture
def sample_hocr():
    """Valid HOCR XML with page, words, and bounding boxes."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8" />
  <meta name="ocr-system" content="tesseract" />
</head>
<body>
  <div class="ocr_page" id="page_1" title="bbox 0 0 1000 1000">
    <span class="ocrx_word" id="word_1_1" title="bbox 100 100 200 150; x_wconf 95">Hello</span>
    <span class="ocrx_word" id="word_1_2" title="bbox 210 100 300 150; x_wconf 92">World</span>
  </div>
</body>
</html>"""


@pytest.fixture
def sample_hocr_multi_page():
    """Valid HOCR XML with multiple pages."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
  <div class="ocr_page" id="page_1" title="bbox 0 0 1000 1000">
    <span class="ocrx_word" id="word_1_1" title="bbox 100 100 200 150; x_wconf 95">Page</span>
    <span class="ocrx_word" id="word_1_2" title="bbox 210 100 250 150; x_wconf 92">1</span>
  </div>
  <div class="ocr_page" id="page_2" title="bbox 0 0 1000 1000">
    <span class="ocrx_word" id="word_2_1" title="bbox 100 100 200 150; x_wconf 90">Page</span>
    <span class="ocrx_word" id="word_2_2" title="bbox 210 100 250 150; x_wconf 88">2</span>
  </div>
</body>
</html>"""


@pytest.fixture
def invalid_hocr_no_pages():
    """Invalid HOCR (missing ocr_page elements)."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
  <span class="ocrx_word">Invalid</span>
</body>
</html>"""


@pytest.fixture
def invalid_hocr_no_bbox():
    """Invalid HOCR (missing bounding boxes)."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
  <div class="ocr_page" id="page_1">
    <span class="ocrx_word" id="word_1_1">NoBBox</span>
  </div>
</body>
</html>"""


# ==============================================================================
# EasyOCR Result Fixtures
# ==============================================================================


@pytest.fixture
def sample_easyocr_results():
    """Sample EasyOCR detection results (bbox, text, confidence)."""
    return [
        ([[10, 10], [100, 10], [100, 50], [10, 50]], "Hello", 0.95),
        ([[110, 10], [200, 10], [200, 50], [110, 50]], "World", 0.92),
    ]


@pytest.fixture
def sample_easyocr_multiline():
    """Sample EasyOCR results with multiple lines."""
    return [
        # Line 1 (y=10-50)
        ([[10, 10], [100, 10], [100, 50], [10, 50]], "First", 0.95),
        ([[110, 10], [200, 10], [200, 50], [110, 50]], "Line", 0.92),
        # Line 2 (y=60-100)
        ([[10, 60], [100, 60], [100, 100], [10, 100]], "Second", 0.90),
        ([[110, 60], [200, 60], [200, 100], [110, 100]], "Line", 0.88),
    ]


# ==============================================================================
# Temporary Directory Fixtures
# ==============================================================================


@pytest.fixture
def temp_upload_dir(tmp_path):
    """Temporary upload directory for file handler tests."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    return upload_dir


@pytest.fixture
def temp_results_dir(tmp_path):
    """Temporary results directory for file handler tests."""
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    return results_dir


@pytest.fixture
def temp_test_file(tmp_path):
    """Create a temporary test file with content.

    Returns:
        Path to temporary file
    """
    test_file = tmp_path / "test_document.txt"
    test_file.write_text("Test content")
    return test_file


# ==============================================================================
# PIL-Generated Test Images (for E2E tests)
# ==============================================================================


@pytest.fixture
def test_image_with_text(tmp_path):
    """Generate a test image with text using PIL for E2E tests.

    Returns:
        Path: Path to generated image file
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        pytest.skip("PIL not available for image generation")

    # Create white background
    img = Image.new("RGB", (400, 200), color="white")
    draw = ImageDraw.Draw(img)

    # Try to use a basic font, fall back to default if not available
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
    except OSError:
        # Fall back to default font
        font = ImageFont.load_default()

    # Draw text
    text = "Hello World\nTest OCR"
    draw.text((20, 50), text, fill="black", font=font)

    # Save to temporary file
    img_path = tmp_path / "test_image.png"
    img.save(img_path, "PNG")

    return img_path


@pytest.fixture
def test_image_simple_text(tmp_path):
    """Generate simple test image with clear text for OCR.

    Returns:
        Path: Path to generated JPEG image
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        pytest.skip("PIL not available")

    # Create larger image for better OCR accuracy
    img = Image.new("RGB", (800, 400), color="white")
    draw = ImageDraw.Draw(img)

    # Use larger font
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
    except OSError:
        font = ImageFont.load_default()

    # Draw single line of text
    text = "TESTING"
    draw.text((50, 150), text, fill="black", font=font)

    # Save as JPEG
    img_path = tmp_path / "simple_text.jpg"
    img.save(img_path, "JPEG", quality=95)

    return img_path


@pytest.fixture
def test_image_multiline(tmp_path):
    """Generate test image with multiple lines of text.

    Returns:
        Path: Path to generated PNG image
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        pytest.skip("PIL not available")

    img = Image.new("RGB", (600, 400), color="white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except OSError:
        font = ImageFont.load_default()

    # Multiple lines
    lines = ["First Line", "Second Line", "Third Line"]
    y_offset = 50
    for line in lines:
        draw.text((30, y_offset), line, fill="black", font=font)
        y_offset += 60

    img_path = tmp_path / "multiline.png"
    img.save(img_path, "PNG")

    return img_path


# ==============================================================================
# Configuration Fixtures
# ==============================================================================


@pytest.fixture
def test_settings(monkeypatch, temp_upload_dir, temp_results_dir):
    """Override settings for testing with temporary directories."""
    monkeypatch.setenv("UPLOAD_DIR", str(temp_upload_dir))
    monkeypatch.setenv("RESULTS_DIR", str(temp_results_dir))
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "25")
    monkeypatch.setenv("SYNC_MAX_FILE_SIZE_MB", "5")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    # Force reload of settings
    import importlib

    import src.config

    importlib.reload(src.config)

    from src.config import settings

    return settings
