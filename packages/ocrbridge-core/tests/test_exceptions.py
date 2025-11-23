"""Tests for OCR Bridge exceptions."""

import pytest
from ocrbridge.core import (
    EngineNotAvailableError,
    InvalidParametersError,
    OCRBridgeError,
    OCRProcessingError,
    UnsupportedFormatError,
)


def test_exception_hierarchy():
    """Test exception inheritance hierarchy."""
    # All exceptions should inherit from OCRBridgeError
    assert issubclass(OCRProcessingError, OCRBridgeError)
    assert issubclass(UnsupportedFormatError, OCRBridgeError)
    assert issubclass(EngineNotAvailableError, OCRBridgeError)
    assert issubclass(InvalidParametersError, OCRBridgeError)


def test_ocr_bridge_error():
    """Test base OCRBridgeError exception."""
    with pytest.raises(OCRBridgeError, match="test error"):
        raise OCRBridgeError("test error")


def test_ocr_processing_error():
    """Test OCRProcessingError exception."""
    with pytest.raises(OCRProcessingError, match="processing failed"):
        raise OCRProcessingError("processing failed")


def test_unsupported_format_error():
    """Test UnsupportedFormatError exception."""
    with pytest.raises(UnsupportedFormatError, match="unsupported format"):
        raise UnsupportedFormatError("unsupported format")


def test_engine_not_available_error():
    """Test EngineNotAvailableError exception."""
    with pytest.raises(EngineNotAvailableError, match="engine not found"):
        raise EngineNotAvailableError("engine not found")


def test_invalid_parameters_error():
    """Test InvalidParametersError exception."""
    with pytest.raises(InvalidParametersError, match="invalid params"):
        raise InvalidParametersError("invalid params")
