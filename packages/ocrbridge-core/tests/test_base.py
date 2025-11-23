"""Tests for OCREngine base class."""

from pathlib import Path

import pytest
from ocrbridge.core import OCREngine, OCREngineParams


class MockParams(OCREngineParams):
    """Mock parameters for testing."""

    test_param: str = "default"


class MockEngine(OCREngine):
    """Mock engine implementation for testing."""

    @property
    def name(self) -> str:
        return "mock"

    @property
    def supported_formats(self) -> set[str]:
        return {".jpg", ".png", ".pdf"}

    def process(self, file_path: Path, params: MockParams | None = None) -> str:
        return '<html><body><div class="ocr_page">Mock HOCR</div></body></html>'


def test_engine_name():
    """Test engine name property."""
    engine = MockEngine()
    assert engine.name == "mock"


def test_engine_supported_formats():
    """Test supported formats property."""
    engine = MockEngine()
    assert engine.supported_formats == {".jpg", ".png", ".pdf"}


def test_engine_process():
    """Test process method."""
    engine = MockEngine()
    result = engine.process(Path("/tmp/test.jpg"))
    assert "ocr_page" in result
    assert "Mock HOCR" in result


def test_engine_process_with_params():
    """Test process method with parameters."""
    engine = MockEngine()
    params = MockParams(test_param="custom")
    result = engine.process(Path("/tmp/test.jpg"), params)
    assert isinstance(result, str)


def test_params_extra_forbid():
    """Test that unknown parameters are rejected."""
    with pytest.raises(ValueError):
        MockParams(test_param="valid", unknown_param="invalid")
