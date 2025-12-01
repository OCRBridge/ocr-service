"""Mock OCR engine implementations for testing."""

from pathlib import Path

from ocrbridge.core import OCREngine
from ocrbridge.core.models import OCREngineParams

from specs.schemas import TesseractParams

"""Mock OCR engine implementations for testing."""


class MockTesseractEngine(OCREngine):
    """Mock Tesseract OCR engine for testing."""

    __param_model__: type[OCREngineParams] | None = TesseractParams

    @property
    def name(self) -> str:
        return "tesseract"

    @property
    def supported_formats(self) -> set[str]:
        return {".jpg", ".jpeg", ".png", ".pdf", ".tiff", ".tif"}

    def process(self, file_path: Path, params: OCREngineParams | None = None) -> str:
        """Return mock HOCR output."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8" />
  <meta name="ocr-system" content="tesseract" />
  <meta name="ocr-capabilities" content="ocr_page ocr_carea ocr_par ocr_line ocrx_word" />
</head>
<body>
  <div class="ocr_page" id="page_1" title="bbox 0 0 100 100">
    <span class="ocrx_word" id="word_1_1" title="bbox 10 10 50 50; x_wconf 95">Mock</span>
    <span class="ocrx_word" id="word_1_2" title="bbox 55 10 90 50; x_wconf 92">Text</span>
  </div>
</body>
</html>"""

    def validate_config(self, params: OCREngineParams | None) -> None:  # pragma: no cover
        """Optional custom validation hook used by registry tests."""
        return None


class MockEngineWithoutParams(OCREngine):
    """Mock engine without parameter model (for testing optional params)."""

    @property
    def name(self) -> str:
        return "simple"

    @property
    def supported_formats(self) -> set[str]:
        return {".jpg", ".png"}

    def process(self, file_path: Path, params=None) -> str:
        """Return minimal HOCR output."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
  <div class="ocr_page" id="page_1" title="bbox 0 0 100 100">
    <span class="ocrx_word" id="word_1_1" title="bbox 10 10 50 50; x_wconf 95">Test</span>
  </div>
</body>
</html>"""


class InvalidEngine:
    """Invalid engine class (doesn't subclass OCREngine) for testing validation."""

    def process(self, file_path: Path) -> str:
        return "Not an OCREngine"
