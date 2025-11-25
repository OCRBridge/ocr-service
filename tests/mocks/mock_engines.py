"""Mock OCR engine implementations for testing."""

from pathlib import Path

from ocrbridge.core import OCREngine
from ocrbridge.core.models import OCREngineParams
from pydantic import Field


class MockTesseractParams(OCREngineParams):
    """Mock parameters for Tesseract engine."""

    lang: str = Field(default="eng", pattern=r"^[a-z_]{3,7}(\+[a-z_]{3,7})*$")
    psm: int = Field(default=3, ge=0, le=13)
    oem: int = Field(default=1, ge=0, le=3)
    dpi: int = Field(default=300, ge=70, le=2400)


class MockTesseractEngine(OCREngine):
    """Mock Tesseract OCR engine for testing."""

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


class MockEasyOCRParams(OCREngineParams):
    """Mock parameters for EasyOCR engine."""

    languages: list[str] = Field(default=["en"], min_length=1, max_length=5)
    text_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    link_threshold: float = Field(default=0.4, ge=0.0, le=1.0)


class MockEasyOCREngine(OCREngine):
    """Mock EasyOCR engine for testing."""

    @property
    def name(self) -> str:
        return "easyocr"

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
  <meta name="ocr-system" content="easyocr" />
  <meta name="ocr-capabilities" content="ocr_page ocr_line ocrx_word" />
</head>
<body>
  <div class="ocr_page" id="page_1" title="bbox 0 0 200 100">
    <span class="ocr_line" id="line_1_1" title="bbox 10 10 190 50">
      <span class="ocrx_word" id="word_1_1" title="bbox 10 10 90 50; x_wconf 95">EasyOCR</span>
      <span class="ocrx_word" id="word_1_2" title="bbox 100 10 190 50; x_wconf 90">Result</span>
    </span>
  </div>
</body>
</html>"""


class MockEngineWithoutParams(OCREngine):
    """Mock engine without parameter model (for testing optional params)."""

    @property
    def name(self) -> str:
        return "simple"

    @property
    def supported_formats(self) -> set[str]:
        return {".jpg", ".png"}

    def process(self, file_path: Path, params: OCREngineParams | None = None) -> str:
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
