from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from ocrbridge.core import OCREngine
from ocrbridge.core.models import OCREngineParams

from src.services.ocr.registry_v2 import EngineRegistry

# ==============================================================================
# Strict Mode & Error Handling Tests
# ==============================================================================


def test_strict_mode_raises_on_import_error():
    """Test that strict mode raises ImportError instead of logging it."""
    mock_ep = Mock()
    mock_ep.name = "broken"
    mock_ep.load.side_effect = ImportError("Import failed")
    with (
        patch("src.services.ocr.registry_v2.entry_points", return_value=[mock_ep]) as _,
        patch("src.services.ocr.registry_v2.settings") as mock_settings,
    ):
        mock_settings.strict_engine_loading = True

        with pytest.raises(ImportError):
            EngineRegistry()


def test_strict_mode_raises_on_attribute_error():
    """Test that strict mode raises AttributeError."""
    mock_ep = Mock()
    mock_ep.name = "broken"
    mock_ep.load.side_effect = AttributeError("Missing attribute")

    with (
        patch("src.services.ocr.registry_v2.entry_points", return_value=[mock_ep]) as _,
        patch("src.services.ocr.registry_v2.settings") as mock_settings,
    ):
        mock_settings.strict_engine_loading = True

        with pytest.raises(AttributeError):
            EngineRegistry()


def test_strict_mode_raises_on_type_error():
    """Test that strict mode raises TypeError."""
    mock_ep = Mock()
    mock_ep.name = "broken"
    mock_ep.load.side_effect = TypeError("Bad type")

    with (
        patch("src.services.ocr.registry_v2.entry_points", return_value=[mock_ep]) as _,
        patch("src.services.ocr.registry_v2.settings") as mock_settings,
    ):
        mock_settings.strict_engine_loading = True

        with pytest.raises(TypeError):
            EngineRegistry()


def test_unexpected_error_handling():
    """Test handling of unexpected exceptions during load."""
    mock_ep = Mock()
    mock_ep.name = "broken"
    mock_ep.load.side_effect = RuntimeError("Unexpected boom")

    with patch("src.services.ocr.registry_v2.entry_points", return_value=[mock_ep]):
        # Non-strict mode should just log and continue
        registry = EngineRegistry()
        assert "broken" not in registry.list_engines()


# ==============================================================================
# Generic Parameter Model Discovery Tests
# ==============================================================================


def test_discover_param_model_generic_naming_convention():
    """Test discovering param model via {Engine}Params naming convention."""

    # Define a dummy engine class
    class MyCustomEngine(OCREngine):
        name = "my_custom"
        supported_formats = {".jpg"}

        def process(self, file_path, params=None):
            return ""

    # Mock the module structure
    MyCustomEngine.__module__ = "some.package.engine"

    # Define a dummy params class
    class MyCustomParams(OCREngineParams):
        pass

    # Mock parent module containing the params class
    mock_parent_module = Mock()
    mock_parent_module.MyCustomParams = MyCustomParams

    # Mock entry point
    mock_ep = Mock()
    mock_ep.name = "my_custom"
    mock_ep.load.return_value = MyCustomEngine

    with (
        patch("src.services.ocr.registry_v2.entry_points", return_value=[mock_ep]) as _,
        patch("src.services.ocr.registry_v2.import_module") as mock_import,
    ):

        def side_effect(name):
            if name == "some.package":
                return mock_parent_module
            raise ImportError(f"No module named {name}")

        mock_import.side_effect = side_effect

        registry = EngineRegistry()

        # Should have discovered the params model
        param_model = registry.get_param_model("my_custom")
        assert param_model is MyCustomParams


def test_discover_param_model_generic_root_module():
    """Test that generic discovery handles root modules gracefully (no parent)."""

    class RootEngine(OCREngine):
        name = "root"
        supported_formats = {".jpg"}

        def process(self, file_path, params=None):
            return ""

    RootEngine.__module__ = "root_module"

    mock_ep = Mock()
    mock_ep.name = "root"
    mock_ep.load.return_value = RootEngine

    with patch("src.services.ocr.registry_v2.entry_points", return_value=[mock_ep]):
        registry = EngineRegistry()
        assert registry.get_param_model("root") is None


# ==============================================================================
# Circuit Breaker Tests
# ==============================================================================


def test_circuit_breaker_logic():
    """Test the full circuit breaker lifecycle."""

    # Define a mock engine class
    class MockEngine(OCREngine):
        name = "test_engine"
        supported_formats = {".jpg"}

        def process(self, file_path, params=None):
            return ""

    # Setup registry with a mock engine
    mock_ep = Mock()
    mock_ep.name = "test_engine"
    mock_ep.load.return_value = MockEngine

    with (
        patch("src.services.ocr.registry_v2.entry_points", return_value=[mock_ep]) as _,
        patch("src.services.ocr.registry_v2.settings") as mock_settings,
    ):
        # Configure settings
        mock_settings.circuit_breaker_enabled = True
        mock_settings.circuit_breaker_threshold = 2
        mock_settings.circuit_breaker_timeout_seconds = 10
        mock_settings.circuit_breaker_success_threshold = 3

        registry = EngineRegistry()

        # 1. Initially available
        assert registry.is_engine_available("test_engine") is True

        # 2. Record failure (count = 1) -> still available
        registry.record_engine_failure("test_engine")
        assert registry.is_engine_available("test_engine") is True

        # 3. Record failure (count = 2) -> circuit opens
        registry.record_engine_failure("test_engine")
        assert registry.is_engine_available("test_engine") is False

        # 4. Check again immediately -> still closed
        assert registry.is_engine_available("test_engine") is False

        # 5. Simulate timeout expiration
        # We need to manipulate the stored health object directly since we can't mock datetime.now() easily across the module
        # without patching it everywhere.
        # registry._engine_health["test_engine"].last_failure = datetime.now() - timedelta(seconds=11)
        # Or better, use freezegun or just patch datetime in the module

        with patch("src.services.ocr.registry_v2.datetime") as mock_datetime:
            # Setup current time
            now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = now

            # Reset failure time to be old
            registry._engine_health["test_engine"].last_failure = now - timedelta(seconds=11)

            # Should now be available (circuit half-open/closed test)
            assert registry.is_engine_available("test_engine") is True

            # 6. Record success -> should reset failure count
            registry.record_engine_success("test_engine")  # 1
            registry.record_engine_success("test_engine")  # 2
            registry.record_engine_success("test_engine")  # 3 (reset threshold)

            health = registry._engine_health["test_engine"]
            assert health.failure_count == 0
            assert health.circuit_open is False


def test_circuit_breaker_disabled():
    """Test that circuit breaker does nothing when disabled."""

    # Define a mock engine class
    class MockEngine(OCREngine):
        name = "test_engine"
        supported_formats = {".jpg"}

        def process(self, file_path, params=None):
            return ""

    mock_ep = Mock()
    mock_ep.name = "test_engine"
    mock_ep.load.return_value = MockEngine

    with (
        patch("src.services.ocr.registry_v2.entry_points", return_value=[mock_ep]) as _,
        patch("src.services.ocr.registry_v2.settings") as mock_settings,
    ):
        mock_settings.circuit_breaker_enabled = False

        registry = EngineRegistry()

        # Even with many failures
        for _ in range(10):
            registry.record_engine_failure("test_engine")

        assert registry.is_engine_available("test_engine") is True
