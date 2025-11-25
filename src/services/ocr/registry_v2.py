"""OCR engine registry with entry point discovery for v2 architecture."""

from importlib.metadata import entry_points
from typing import Any, get_type_hints

import structlog

logger = structlog.get_logger(__name__)


class EngineRegistry:
    """Registry for OCR engines discovered via entry points.

    Engines are discovered dynamically from installed packages that provide
    entry points in the 'ocrbridge.engines' group. This enables a plugin
    architecture where engines can be installed independently.
    """

    def __init__(self):
        """Initialize the registry and discover engines."""
        self._engine_classes: dict[str, type[Any]] = {}
        self._engine_instances: dict[str, Any] = {}
        self._param_models: dict[str, type[Any]] = {}
        self._discover_engines()

    def _discover_engines(self) -> None:
        """Discover OCR engines via entry points.

        Looks for entry points in the 'ocrbridge.engines' group and loads
        engine classes. Failed engine loads are logged but don't fail startup.
        """
        try:
            # Get entry points for ocrbridge.engines group
            discovered = entry_points(group="ocrbridge.engines")

            # Handle both return types (EntryPoints object or list)
            eps = list(discovered) if hasattr(discovered, "__iter__") else discovered  # type: ignore

            logger.info("discovering_engines", count=len(eps))

            for ep in eps:
                try:
                    engine_class = ep.load()

                    # Validate it's an OCREngine subclass
                    from ocrbridge.core import OCREngine

                    if not issubclass(engine_class, OCREngine):
                        logger.warning(
                            "invalid_engine_class",
                            name=ep.name,
                            class_name=engine_class.__name__,
                            reason="Not a subclass of OCREngine",
                        )
                        continue

                    self._engine_classes[ep.name] = engine_class

                    # Extract parameter model from type hints
                    try:
                        param_model = self._extract_param_model(engine_class)
                        if param_model:
                            self._param_models[ep.name] = param_model
                    except Exception as e:
                        logger.warning(
                            "failed_to_extract_param_model",
                            engine=ep.name,
                            error=str(e),
                        )

                    logger.info(
                        "engine_discovered",
                        name=ep.name,
                        class_name=engine_class.__name__,
                    )

                except Exception as e:
                    logger.warning(
                        "failed_to_load_engine",
                        name=ep.name,
                        error=str(e),
                        error_type=type(e).__name__,
                    )

            logger.info(
                "engine_discovery_complete",
                total_discovered=len(self._engine_classes),
                engines=list(self._engine_classes.keys()),
            )

        except Exception as e:
            logger.error(
                "engine_discovery_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            # Don't fail startup, just log the error

    def _extract_param_model(self, engine_class: type[Any]) -> type[Any] | None:
        """Extract parameter model from engine's process method.

        Args:
            engine_class: The OCREngine class

        Returns:
            Parameter model class or None if not found
        """
        try:
            # Get type hints from the process method
            type_hints = get_type_hints(engine_class.process)

            # Look for 'params' parameter
            if "params" not in type_hints:
                return None

            params_type = type_hints["params"]

            # Handle Optional[ParamType] or ParamType | None
            # In Python 3.10+, Optional[X] is represented as Union[X, None] or X | None
            if hasattr(params_type, "__args__"):
                # Get the first non-None type from Union
                for arg in params_type.__args__:
                    if arg is not type(None):  # noqa: E721
                        return arg

            return params_type

        except Exception as e:
            logger.debug(
                "failed_to_extract_param_model",
                engine_class=engine_class.__name__,
                error=str(e),
            )
            return None

    def get_engine(self, name: str) -> Any:
        """Get engine instance by name (lazy loading).

        Args:
            name: Engine name (e.g., 'tesseract', 'easyocr')

        Returns:
            Engine instance

        Raises:
            ValueError: If engine not found
        """
        if name not in self._engine_classes:
            available = ", ".join(self._engine_classes.keys()) if self._engine_classes else "none"
            raise ValueError(f"Engine '{name}' not found. Available engines: {available}")

        # Lazy load engine instance
        if name not in self._engine_instances:
            engine_class = self._engine_classes[name]
            self._engine_instances[name] = engine_class()
            logger.debug("engine_instantiated", name=name)

        return self._engine_instances[name]

    def list_engines(self) -> list[str]:
        """List all available engine names.

        Returns:
            List of engine names (e.g., ['tesseract', 'easyocr', 'ocrmac'])
        """
        return list(self._engine_classes.keys())

    def get_engine_info(self, name: str) -> dict[str, Any]:
        """Get information about an engine.

        Args:
            name: Engine name

        Returns:
            Dictionary with engine information

        Raises:
            ValueError: If engine not found
        """
        if name not in self._engine_classes:
            raise ValueError(f"Engine '{name}' not found")

        engine = self.get_engine(name)

        return {
            "name": engine.name,
            "class": self._engine_classes[name].__name__,
            "supported_formats": list(engine.supported_formats),
            "has_param_model": name in self._param_models,
        }

    def get_param_model(self, engine_name: str) -> type[Any] | None:
        """Get parameter model class for an engine.

        Args:
            engine_name: Engine name

        Returns:
            Parameter model class or None if not found

        Raises:
            ValueError: If engine not found
        """
        if engine_name not in self._engine_classes:
            raise ValueError(f"Engine '{engine_name}' not found")

        return self._param_models.get(engine_name)

    def validate_params(self, engine_name: str, params: dict[str, Any]) -> Any:
        """Validate parameters against engine's parameter model.

        Args:
            engine_name: Engine name
            params: Parameters dictionary

        Returns:
            Validated parameter model instance

        Raises:
            ValueError: If engine not found or parameters invalid
        """
        param_model = self.get_param_model(engine_name)

        if param_model is None:
            # Engine has no parameter model, return params as-is
            return None

        # Validate using Pydantic
        try:
            return param_model(**params)
        except Exception as e:
            raise ValueError(f"Invalid parameters for {engine_name}: {e}") from e

    def is_engine_available(self, name: str) -> bool:
        """Check if an engine is available.

        Args:
            name: Engine name

        Returns:
            True if engine is available, False otherwise
        """
        return name in self._engine_classes
