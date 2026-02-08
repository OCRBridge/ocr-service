"""Unit tests for OCR engine registry v2 with entry point discovery.

HIGHEST PRIORITY - Tests the core plugin architecture.

Tests entry point discovery, lazy loading, parameter model extraction,
and engine validation.
"""

from unittest.mock import patch

import pytest

from src.services.ocr.registry_v2 import EngineRegistry
from tests.mocks.mock_engines import (
    InvalidEngine,
    MockEngineWithoutParams,
    MockTesseractEngine,
)
from tests.mocks.mock_entry_points import (
    create_mock_entry_point,
    mock_entry_points_factory,
    mock_failing_entry_point,
)

# ==============================================================================
# Engine Discovery Tests
# ==============================================================================


def test_discover_engines_success():
    """Test successful engine discovery via entry points."""
    engines = {
        "tesseract": MockTesseractEngine,
    }
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        discovered = registry.list_engines()
        assert "tesseract" in discovered
        assert len(discovered) == 1


def test_discover_engines_empty():
    """Test engine discovery when no engines are installed."""
    mock_ep = mock_entry_points_factory({})

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        discovered = registry.list_engines()
        assert discovered == []


def test_discover_engines_single():
    """Test discovery of single engine."""
    engines = {"tesseract": MockTesseractEngine}
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        discovered = registry.list_engines()
        assert discovered == ["tesseract"]


def test_discover_engines_failed_load():
    """Test graceful handling when engine fails to load."""
    # Create entry point that fails to load
    failing_ep = mock_failing_entry_point("broken", ImportError("Module not found"))
    good_ep = create_mock_entry_point("tesseract", MockTesseractEngine)

    def mock_entry_points(group=None):
        if group == "ocrbridge.engines":
            return [failing_ep, good_ep]
        return []

    with patch("src.services.ocr.registry_v2.entry_points", mock_entry_points):
        registry = EngineRegistry()

        # Should only discover the working engine
        discovered = registry.list_engines()
        assert "tesseract" in discovered
        assert "broken" not in discovered


def test_discover_engines_invalid_class():
    """Test that non-OCREngine classes are rejected."""
    engines = {
        "tesseract": MockTesseractEngine,
        "invalid": InvalidEngine,  # Doesn't subclass OCREngine
    }
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        # Invalid engine should be rejected
        discovered = registry.list_engines()
        assert "tesseract" in discovered
        assert "invalid" not in discovered


# ==============================================================================
# Engine Access Tests
# ==============================================================================


def test_get_engine_lazy_loading():
    """Test that engines are loaded lazily (on first access)."""
    engines = {"tesseract": MockTesseractEngine}
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        # Engine should not be instantiated yet
        assert "tesseract" not in registry.get_engine_instances()

        # First access should instantiate
        engine = registry.get_engine("tesseract")
        assert engine is not None
        assert isinstance(engine, MockTesseractEngine)

        # Should now be cached
        assert "tesseract" in registry.get_engine_instances()


def test_get_engine_caching():
    """Test that engine instances are cached after first load."""
    engines = {"tesseract": MockTesseractEngine}
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        # Get engine twice
        engine1 = registry.get_engine("tesseract")
        engine2 = registry.get_engine("tesseract")

        # Should be the same instance
        assert engine1 is engine2


def test_get_engine_not_found():
    """Test that getting non-existent engine raises ValueError."""
    engines = {"tesseract": MockTesseractEngine}
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        with pytest.raises(ValueError) as exc_info:
            registry.get_engine("nonexistent")

        error_message = str(exc_info.value)
        assert "nonexistent" in error_message
        assert "not found" in error_message.lower()
        assert "tesseract" in error_message  # Shows available engines


def test_get_engine_not_found_empty_registry():
    """Test error message when no engines are available."""
    mock_ep = mock_entry_points_factory({})

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        with pytest.raises(ValueError) as exc_info:
            registry.get_engine("tesseract")

        error_message = str(exc_info.value)
        assert "none" in error_message.lower()


def test_is_engine_available_true():
    """Test checking if engine is available (exists)."""
    engines = {"tesseract": MockTesseractEngine}
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        assert registry.is_engine_available("tesseract") is True


def test_is_engine_available_false():
    """Test checking if engine is available (doesn't exist)."""
    engines = {"tesseract": MockTesseractEngine}
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        assert registry.is_engine_available("easyocr") is False


# ==============================================================================
# Engine Info Tests
# ==============================================================================


def test_get_engine_info():
    """Test getting engine metadata."""
    engines = {"tesseract": MockTesseractEngine}
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        info = registry.get_engine_info("tesseract")

        assert info["name"] == "tesseract"
        assert info["class"] == "MockTesseractEngine"
        assert isinstance(info["supported_formats"], list)
        assert ".jpg" in info["supported_formats"]
        assert info["has_param_model"] is True
        # Should include JSON schema for params
        assert "params_schema" in info
        assert isinstance(info["params_schema"], dict)


def test_get_engine_info_not_found():
    """Test getting info for non-existent engine raises ValueError."""
    engines = {"tesseract": MockTesseractEngine}
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        with pytest.raises(ValueError) as exc_info:
            registry.get_engine_info("nonexistent")

        assert "not found" in str(exc_info.value).lower()


def test_get_engine_info_without_params():
    """Test engine info for engine without parameter model."""
    engines = {"simple": MockEngineWithoutParams}
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        info = registry.get_engine_info("simple")

        assert info["name"] == "simple"
        assert info["has_param_model"] is False
        # Should not include schema when no param model
        assert "params_schema" not in info


# ==============================================================================
# Parameter Model Extraction Tests
# ==============================================================================


def test_extract_param_model_with_optional():
    """Test extracting parameter model from Optional[ParamType] type hint."""
    engines = {"tesseract": MockTesseractEngine}
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        param_model = registry.get_param_model("tesseract")

        assert param_model is not None
        # Should be the MockTesseractParams class
        assert hasattr(param_model, "model_fields")


def test_extract_param_model_none():
    """Test extracting parameter model when engine has no params."""
    engines = {"simple": MockEngineWithoutParams}
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        param_model = registry.get_param_model("simple")

        assert param_model is None


def test_get_param_model_not_found():
    """Test getting parameter model for non-existent engine raises ValueError."""
    engines = {"tesseract": MockTesseractEngine}
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        with pytest.raises(ValueError) as exc_info:
            registry.get_param_model("nonexistent")

        assert "not found" in str(exc_info.value).lower()


# ==============================================================================
# Parameter Validation Tests
# ==============================================================================


def test_validate_params_valid():
    """Test validating valid parameters against engine's parameter model."""
    engines = {"tesseract": MockTesseractEngine}
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        params = {"lang": "eng", "psm": 6, "dpi": 300}
        validated = registry.validate_params("tesseract", params)

        assert validated is not None
        assert validated.lang == "eng"
        assert validated.psm == 6
        assert validated.dpi == 300


def test_validate_params_invalid():
    """Test that invalid parameters raise ValueError with Pydantic details."""
    engines = {"tesseract": MockTesseractEngine}
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        # Invalid PSM value (out of range 0-13)
        params = {"psm": 99}

        with pytest.raises(ValueError) as exc_info:
            registry.validate_params("tesseract", params)

        error_message = str(exc_info.value)
        assert "invalid" in error_message.lower()


def test_validate_params_empty_dict():
    """Test validating empty parameters dict uses defaults."""
    engines = {"tesseract": MockTesseractEngine}
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        validated = registry.validate_params("tesseract", {})

        # Should use default values from MockTesseractParams
        assert validated.lang == "eng"
        assert validated.psm == 3


def test_validate_params_no_model():
    """Test validating params for engine without parameter model returns None."""
    engines = {"simple": MockEngineWithoutParams}
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        result = registry.validate_params("simple", {"any": "value"})

        assert result is None


def test_validate_params_extra_fields_rejected():
    """Test that extra fields in params are rejected (Pydantic forbids extra)."""
    engines = {"tesseract": MockTesseractEngine}
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        params = {"lang": "eng", "unknown_field": "value"}

        # MockTesseractParams uses model_config with extra="forbid"
        with pytest.raises(ValueError):
            registry.validate_params("tesseract", params)


def test_validate_params_type_coercion():
    """Test that parameter validation performs type coercion."""
    engines = {"tesseract": MockTesseractEngine}
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        # Pass string instead of int for psm
        params = {"psm": "6"}  # String that can be coerced to int

        validated = registry.validate_params("tesseract", params)

        # Should be coerced to int
        assert validated.psm == 6
        assert isinstance(validated.psm, int)


def test_validate_params_calls_custom_validation():
    """Test that registry calls validate_config on engine if present."""

    mock_engine_instance = MockTesseractEngine()

    with patch.object(mock_engine_instance, "validate_config") as mock_validate_config:
        # Mock factory to return our custom instance
        def mock_engine_factory():
            return mock_engine_instance

        # Patch the class to return our instance when instantiated
        with patch("tests.mocks.mock_engines.MockTesseractEngine", side_effect=mock_engine_factory):
            engines = {"tesseract": MockTesseractEngine}
            mock_ep = mock_entry_points_factory(engines)

            with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
                registry = EngineRegistry()

                # Force instantiation and injection into registry cache to use our mock instance
                registry.inject_engine_instance("tesseract", mock_engine_instance)
                registry.inject_engine_class(
                    "tesseract", MockTesseractEngine
                )  # Ensure class is present

                # Also need param model
                from typing import Any, cast

                registry.inject_param_model(
                    "tesseract", cast(type[Any], registry.extract_param_model(MockTesseractEngine))
                )

                params = {"lang": "eng"}
                validated = registry.validate_params("tesseract", params)

                # Verify validate_config was called
                mock_validate_config.assert_called_once_with(validated)


def test_validate_params_custom_validation_failure():
    """Test that custom validation failure raises ValueError."""

    mock_engine_instance = MockTesseractEngine()

    with patch.object(
        mock_engine_instance, "validate_config", side_effect=ValueError("Custom validation failed")
    ):
        engines = {"tesseract": MockTesseractEngine}
        mock_ep = mock_entry_points_factory(engines)

        with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
            registry = EngineRegistry()
            registry.inject_engine_instance("tesseract", mock_engine_instance)
            registry.inject_engine_class("tesseract", MockTesseractEngine)
            from typing import Any, cast

            registry.inject_param_model(
                "tesseract", cast(type[Any], registry.extract_param_model(MockTesseractEngine))
            )

            with pytest.raises(ValueError) as exc_info:
                registry.validate_params("tesseract", {"lang": "eng"})

            assert "Custom validation failed" in str(exc_info.value)


# ==============================================================================
# List Engines Tests
# ==============================================================================


def test_list_engines_multiple():
    """Test listing multiple engines returns all names."""
    engines = {
        "tesseract": MockTesseractEngine,
        "simple": MockEngineWithoutParams,
    }
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        engine_list = registry.list_engines()

        assert len(engine_list) == 2
        assert "tesseract" in engine_list
        assert "simple" in engine_list


def test_list_engines_returns_list():
    """Test that list_engines returns a list (not dict keys or other type)."""
    engines = {"tesseract": MockTesseractEngine}
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        engine_list = registry.list_engines()

        assert isinstance(engine_list, list)


# ==============================================================================
# Registry State Tests
# ==============================================================================


def test_registry_internal_state():
    """Test that registry maintains correct internal state."""
    engines = {"tesseract": MockTesseractEngine}
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        # Check internal dictionaries
        assert "tesseract" in registry.get_engine_classes()
        assert "tesseract" in registry.get_param_models()
        # Instance should not exist until first access
        assert "tesseract" not in registry.get_engine_instances()

        # Access engine
        registry.get_engine("tesseract")

        # Now instance should exist
        assert "tesseract" in registry.get_engine_instances()


def test_registry_multiple_instances():
    """Test that multiple registry instances are independent."""
    engines1 = {"tesseract": MockTesseractEngine}
    engines2 = {"simple": MockEngineWithoutParams}

    mock_ep1 = mock_entry_points_factory(engines1)
    mock_ep2 = mock_entry_points_factory(engines2)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep1):
        registry1 = EngineRegistry()

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep2):
        registry2 = EngineRegistry()

    # Each registry should have different engines
    assert registry1.list_engines() == ["tesseract"]
    assert registry2.list_engines() == ["simple"]


# ==============================================================================
# Error Handling Tests
# ==============================================================================


def test_registry_handles_exception_during_discovery():
    """Test that exceptions during discovery don't crash the registry."""

    def mock_failing_entry_points(group=None):
        raise RuntimeError("Entry points discovery failed")

    with patch("src.services.ocr.registry_v2.entry_points", mock_failing_entry_points):
        # Should not raise, just log error
        registry = EngineRegistry()

        # Registry should be empty but functional
        assert registry.list_engines() == []


def test_registry_handles_param_extraction_failure():
    """Test graceful handling when parameter model extraction fails."""

    # First, make it inherit from OCREngine to pass validation
    from ocrbridge.core import OCREngine

    class BrokenOCREngine(OCREngine):
        @property
        def name(self):
            return "broken"

        @property
        def supported_formats(self):
            return {".jpg"}

        def process(self, file_path, params=None):
            return "<html></html>"

    engines = {"broken": BrokenOCREngine}
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        registry = EngineRegistry()

        # Should discover the engine even if param extraction failed
        assert "broken" in registry.list_engines()

        # Should return None for parameter model
        assert registry.get_param_model("broken") is None
