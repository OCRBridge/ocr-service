"""Tests for Registry v2 model loading."""

from unittest.mock import patch

from src.services.ocr.registry_v2 import EngineRegistry
from tests.mocks.mock_engines import MockTesseractEngine
from tests.mocks.mock_entry_points import mock_entry_points_factory
from tests.mocks.packages.v2_mocks import setup_v2_mocks, teardown_v2_mocks


def test_registry_loads_v2_models():
    """Test that registry prefers v2 models from package imports."""

    # Setup mocks for ocrbridge.engines.*
    setup_v2_mocks()

    try:
        engines = {"tesseract": MockTesseractEngine}
        mock_ep = mock_entry_points_factory(engines)

        with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
            registry = EngineRegistry()

            # Check Tesseract
            tess_model = registry.get_param_model("tesseract")
            assert tess_model is not None
            assert tess_model.__name__ == "TesseractParams"
            assert "oem" in tess_model.model_fields  # Field from spec/v2 model

    finally:
        teardown_v2_mocks()
