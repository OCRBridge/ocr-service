"""Mock entry points for testing engine discovery."""

from collections.abc import Callable
from typing import Any
from unittest.mock import Mock


def create_mock_entry_point(name: str, engine_class: Any) -> Mock:
    """Create a mock entry point that loads an engine class.

    Args:
        name: Entry point name (e.g., 'tesseract')
        engine_class: Engine class to return when load() is called

    Returns:
        Mock entry point object with name and load() method
    """
    ep = Mock()
    ep.name = name
    ep.load = Mock(return_value=engine_class)
    return ep


def mock_entry_points_factory(engines: dict[str, Any]) -> Callable[[str | None], list[Mock]]:
    """Create mock entry_points function.

    This factory creates a mock function that can replace importlib.metadata.entry_points().
    It returns a list of mock entry points for the 'ocrbridge.engines' group.

    Args:
        engines: Dict mapping engine names to engine classes
                 e.g., {"tesseract": MockTesseractEngine}

    Returns:
        Mock function that returns entry points when called with group="ocrbridge.engines"

    Example:
        >>> from tests.mocks.mock_engines import MockTesseractEngine
        >>> engines = {"tesseract": MockTesseractEngine}
        >>> mock_ep = mock_entry_points_factory(engines)
        >>> with patch("importlib.metadata.entry_points", mock_ep):
        ...     registry = EngineRegistry()  # Will discover mock engines
    """

    def mock_entry_points(group: str | None = None) -> list[Mock]:
        """Mock implementation of importlib.metadata.entry_points()."""
        if group == "ocrbridge.engines":
            return [create_mock_entry_point(name, cls) for name, cls in engines.items()]
        return []

    return mock_entry_points


def mock_failing_entry_point(name: str, error: Exception) -> Mock:
    """Create a mock entry point that fails to load.

    Args:
        name: Entry point name
        error: Exception to raise when load() is called

    Returns:
        Mock entry point that raises an exception on load()

    Example:
        >>> ep = mock_failing_entry_point("broken", ImportError("Module not found"))
        >>> eps = [ep]
    """
    ep = Mock()
    ep.name = name
    ep.load = Mock(side_effect=error)
    return ep
