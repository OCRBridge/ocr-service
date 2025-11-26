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

                    # Attempt to resolve the best parameter model for this engine.
                    # Strategy:
                    # 1. Check for engine-specific v2.0 models (TesseractParams, EasyOCRParams)
                    #    exported by the engine package itself.
                    # 2. Check for explicit __param_model__ on the engine class.
                    # 3. Fall back to extracting from type hints (v1 behavior).

                    param_model = None
                    try:
                        import importlib
                        if ep.name == "tesseract":
                            mod = importlib.import_module("ocrbridge.engines.tesseract")
                            param_model = getattr(mod, "TesseractParams", None)
                        elif ep.name == "easyocr":
                            mod = importlib.import_module("ocrbridge.engines.easyocr")
                            param_model = getattr(mod, "EasyOCRParams", None)
                        elif ep.name == "ocrmac":
                            mod = importlib.import_module("ocrbridge.engines.ocrmac")
                            param_model = getattr(mod, "OCRMacParams", None)
                    except ImportError:
                        # Engine package installed but maybe not the submodule we expect
                        pass
                    except Exception as e:
                        logger.debug("v2_model_import_failed", engine=ep.name, error=str(e))

                    # If no v2 model found, fall back to v1 inspection logic
                    if param_model is None:
                        param_model = self._extract_param_model(engine_class)

                    if param_model:
                        self._param_models[ep.name] = param_model

                    logger.info(
                        "engine_discovered",
                        name=ep.name,
                        class_name=engine_class.__name__,
                        has_param_model=param_model is not None,
                        param_model_name=param_model.__name__ if param_model else None,
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
        """Extract parameter model from engine class.

        First checks for explicit __param_model__ class attribute.
        Falls back to extracting from process() method type hints.

        Args:
            engine_class: The OCREngine class

        Returns:
            Parameter model class or None if not found
        """
        try:
            # Check for explicit param model declaration (preferred method)
            if hasattr(engine_class, "__param_model__"):
                param_model = engine_class.__param_model__  # type: ignore[attr-defined]
                # Validate it's a class (not instance) and not None
                if param_model is not None and isinstance(param_model, type):
                    return param_model

            # Fall back to type hint extraction
            type_hints = get_type_hints(engine_class.process)

            # Look for 'params' parameter
            if "params" not in type_hints:
                return None

            params_type = type_hints["params"]

            # Handle Optional[ParamType] or ParamType | None
            # In Python 3.10+, Optional[X] is represented as Union[X, None] or X | None
            # Import kept for type resolution in get_type_hints; refer in comment to avoid unused warnings.
            # from ocrbridge.core.models import OCREngineParams

            if hasattr(params_type, "__args__"):
                # Get the first non-None type from Union
                for arg in params_type.__args__:
                    if arg is not type(None) and isinstance(arg, type):  # noqa: E721
                        # Accept base OCREngineParams as a valid model to expose
                        return arg
            else:
                # Direct annotation without Union/Optional
                if isinstance(params_type, type):
                    # Accept base OCREngineParams as a valid model to expose
                    return params_type

            return None

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

        info: dict[str, Any] = {
            "name": engine.name,
            "class": self._engine_classes[name].__name__,
            "supported_formats": list(engine.supported_formats),
            "has_param_model": name in self._param_models,
        }

        # Include JSON schema for parameter model when available
        param_model = self._param_models.get(name)
        if param_model is not None:
            try:
                # Pydantic v2: model_json_schema provides JSON-schema of the model
                if hasattr(param_model, "model_json_schema"):
                    info["params_schema"] = param_model.model_json_schema()
                # Fallback for Pydantic v1 if ever present
                elif hasattr(param_model, "schema"):
                    info["params_schema"] = param_model.schema()  # type: ignore[attr-defined]
            except Exception as e:
                logger.warning(
                    "failed_to_generate_param_schema",
                    engine=name,
                    error=str(e),
                )

        return info

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

        If the engine has a 'validate_config' method, it will be called
        with the validated parameter model (or None) for additional checks.

        Args:
            engine_name: Engine name
            params: Parameters dictionary

        Returns:
            Validated parameter model instance

        Raises:
            ValueError: If engine not found or parameters invalid
        """
        param_model = self.get_param_model(engine_name)

        # Initial validation via Pydantic model
        validated_params = None
        if param_model is not None:
            try:
                validated_params = param_model(**params)
            except Exception as e:
                raise ValueError(f"Invalid parameters for {engine_name}: {e}") from e

        # Extended validation via engine protocol
        # If the engine implements validate_config(params), call it.
        try:
            engine = self.get_engine(engine_name)
            if hasattr(engine, "validate_config"):
                engine.validate_config(validated_params)  # type: ignore
        except Exception as e:
            # Re-raise ValueErrors as-is (validation failures)
            if isinstance(e, ValueError):
                raise
            # Wrap other errors
            logger.error(
                "engine_custom_validation_failed",
                engine=engine_name,
                error=str(e),
            )
            raise ValueError(f"Engine validation failed for {engine_name}: {e}") from e

        return validated_params

    def is_engine_available(self, name: str) -> bool:
        """Check if an engine is available.

        Args:
            name: Engine name

        Returns:
            True if engine is available, False otherwise
        """
        return name in self._engine_classes
