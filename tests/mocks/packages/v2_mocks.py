"""Mock structure for ocrbridge packages to simulate v2.0 upgrades."""

import sys
from types import ModuleType
from typing import Any, cast

from specs.schemas import EasyOCRParams, TesseractParams


def create_mock_package(name: str) -> ModuleType:
    """Create a mock package module."""
    mod = ModuleType(name)
    sys.modules[name] = mod
    return mod


def setup_v2_mocks():
    """Setup sys.modules to simulate installed ocrbridge v2 packages."""

    # Mock ocrbridge.engines.tesseract
    tess_mod = cast(Any, create_mock_package("ocrbridge.engines.tesseract"))
    tess_mod.TesseractParams = TesseractParams  # Expose v2 model

    # Mock ocrbridge.engines.easyocr
    easy_mod = cast(Any, create_mock_package("ocrbridge.engines.easyocr"))
    easy_mod.EasyOCRParams = EasyOCRParams  # Expose v2 model

    return tess_mod, easy_mod


def teardown_v2_mocks():
    """Remove mocks from sys.modules."""
    sys.modules.pop("ocrbridge.engines.tesseract", None)
    sys.modules.pop("ocrbridge.engines.easyocr", None)
