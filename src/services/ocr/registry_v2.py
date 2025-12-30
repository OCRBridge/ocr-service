"""OCR engine registry with entry point discovery for v2 architecture."""

import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from importlib import import_module
from importlib.metadata import entry_points
from typing import Any, get_type_hints

import structlog

from src.config import settings

logger = structlog.get_logger(__name__)


@dataclass
class EngineHealth:
    """Track health status for circuit breaker pattern."""

    failure_count: int = 0
    last_failure: datetime | None = None
    circuit_open: bool = False
    consecutive_successes: int = 0


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
        self._engine_health: dict[str, EngineHealth] = {}
        self._lock = threading.Lock()  # Thread safety for lazy engine instantiation
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

                    # Warn about engine name collision
                    if ep.name in self._engine_classes:
                        logger.warning(
                            "engine_name_collision",
                            name=ep.name,
                            existing_class=self._engine_classes[ep.name].__name__,
                            new_class=engine_class.__name__,
                            message="New engine will override existing one",
                        )

                    self._engine_classes[ep.name] = engine_class

                    # Attempt to resolve the parameter model for this engine.
                    # Strategy:
                    # 1. Try generic naming convention: discover {EngineName}Params from
                    #    the engine's parent module (e.g., TesseractEngine → TesseractParams)
                    # 2. Check for explicit __param_model__ on the engine class.
                    # 3. Fall back to extracting from type hints.

                    param_model = self._discover_param_model_generic(engine_class)

                    # If no model found via generic discovery, fall back to inspection
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

                except ImportError as e:
                    logger.error(
                        "engine_import_failed",
                        name=ep.name,
                        error=str(e),
                        module=ep.value,
                        error_type="ImportError",
                    )
                    if settings.strict_engine_loading:
                        raise
                except AttributeError as e:
                    logger.error(
                        "engine_missing_required_attributes",
                        name=ep.name,
                        error=str(e),
                        error_type="AttributeError",
                    )
                    if settings.strict_engine_loading:
                        raise
                except TypeError as e:
                    logger.error(
                        "engine_invalid_type",
                        name=ep.name,
                        error=str(e),
                        error_type="TypeError",
                    )
                    if settings.strict_engine_loading:
                        raise
                except Exception as e:
                    logger.warning(
                        "unexpected_engine_load_error",
                        name=ep.name,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    if settings.strict_engine_loading:
                        raise

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
            # In strict mode, we want to fail startup if discovery fails
            if settings.strict_engine_loading:
                raise

    def _discover_param_model_generic(self, engine_class: type[Any]) -> type[Any] | None:
        """Discover parameter model using generic naming convention.

        Attempts to find a parameter model class by:
        1. Getting the engine's module (e.g., ocrbridge.engines.tesseract.engine)
        2. Importing the parent module (e.g., ocrbridge.engines.tesseract)
        3. Looking for {EngineName}Params class (e.g., TesseractEngine → TesseractParams)
        4. Verifying it's a subclass of OCREngineParams

        This approach works for any engine without hardcoding names.

        Args:
            engine_class: The OCREngine class

        Returns:
            Parameter model class or None if not found
        """
        try:
            from ocrbridge.core.models import OCREngineParams

            # Get the module where the engine class is defined
            # e.g., "ocrbridge.engines.tesseract.engine"
            engine_module_name = engine_class.__module__

            # Get parent module name (where params are typically exported)
            # e.g., "ocrbridge.engines.tesseract"
            if "." in engine_module_name:
                parent_module_name = engine_module_name.rsplit(".", 1)[0]
            else:
                # Engine is in root module, can't go up
                return None

            # Import parent module
            try:
                parent_module = import_module(parent_module_name)
            except ImportError:
                return None

            # Try naming convention: {EngineName}Params
            # e.g., TesseractEngine → TesseractParams
            engine_class_name = engine_class.__name__
            if engine_class_name.endswith("Engine"):
                params_class_name = engine_class_name.replace("Engine", "Params")
            else:
                # Fallback: append Params to class name
                params_class_name = f"{engine_class_name}Params"

            # Try to get the params class from parent module
            param_model = getattr(parent_module, params_class_name, None)

            # Verify it's a class and subclass of OCREngineParams
            if (
                param_model is not None
                and isinstance(param_model, type)
                and issubclass(param_model, OCREngineParams)
            ):
                logger.debug(
                    "param_model_discovered_via_naming_convention",
                    engine=engine_class.__name__,
                    param_model=params_class_name,
                    module=parent_module_name,
                )
                return param_model

            return None

        except Exception as e:
            logger.debug(
                "generic_param_discovery_failed",
                engine_class=engine_class.__name__,
                error=str(e),
            )
            return None

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
                    if arg is not type(None) and isinstance(arg, type):
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

    # Public helpers for tests and introspection (avoid private access)
    def extract_param_model(self, engine_class: type[Any]) -> type[Any] | None:
        """Public wrapper around param model extraction.

        Args:
            engine_class: Engine class to inspect

        Returns:
            Parameter model class or None
        """
        return self._extract_param_model(engine_class)

    def get_engine_classes(self) -> dict[str, type[Any]]:
        """Return discovered engine classes."""
        return dict(self._engine_classes)

    def get_engine_instances(self) -> dict[str, Any]:
        """Return instantiated engine instances (lazy-loaded)."""
        return dict(self._engine_instances)

    def get_param_models(self) -> dict[str, type[Any]]:
        """Return parameter models mapped by engine name."""
        return dict(self._param_models)

    # Injection helpers specifically for tests
    def inject_engine_instance(self, name: str, instance: Any) -> None:
        """Inject or override an engine instance (testing utility)."""
        self._engine_instances[name] = instance

    def inject_engine_class(self, name: str, cls: type[Any]) -> None:
        """Inject or override an engine class (testing utility)."""
        self._engine_classes[name] = cls

    def inject_param_model(self, name: str, model: type[Any]) -> None:
        """Inject or override a parameter model (testing utility)."""
        self._param_models[name] = model

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

        # Lazy load engine instance with thread-safe double-checked locking
        if name not in self._engine_instances:
            with self._lock:
                # Double-check after acquiring lock to avoid race condition
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
        """Check if an engine is available and healthy (circuit breaker check).

        Args:
            name: Engine name

        Returns:
            True if engine is available and not circuit-broken, False otherwise
        """
        # First check if engine exists
        if name not in self._engine_classes:
            return False

        # If circuit breaker disabled, engine is available
        if not settings.circuit_breaker_enabled:
            return True

        # Check circuit breaker status
        health = self._engine_health.get(name, EngineHealth())

        if not health.circuit_open:
            return True

        # Try to close circuit after timeout
        if health.last_failure and datetime.now() - health.last_failure > timedelta(
            seconds=settings.circuit_breaker_timeout_seconds
        ):
            health.circuit_open = False
            health.failure_count = 0
            logger.info("circuit_breaker_closed", engine=name)
            return True

        return False

    def record_engine_failure(self, name: str) -> None:
        """Record an engine failure for circuit breaker pattern.

        Args:
            name: Engine name
        """
        if not settings.circuit_breaker_enabled:
            return

        health = self._engine_health.setdefault(name, EngineHealth())
        health.failure_count += 1
        health.last_failure = datetime.now()
        health.consecutive_successes = 0

        if health.failure_count >= settings.circuit_breaker_threshold:
            health.circuit_open = True
            logger.warning(
                "circuit_breaker_opened",
                engine=name,
                failure_count=health.failure_count,
                threshold=settings.circuit_breaker_threshold,
            )

    def record_engine_success(self, name: str) -> None:
        """Record an engine success for circuit breaker pattern.

        Args:
            name: Engine name
        """
        if not settings.circuit_breaker_enabled:
            return

        health = self._engine_health.setdefault(name, EngineHealth())
        health.consecutive_successes += 1

        # Reset circuit after consecutive successes
        if health.consecutive_successes >= settings.circuit_breaker_success_threshold:
            health.failure_count = 0
            health.circuit_open = False
            logger.info(
                "circuit_breaker_reset",
                engine=name,
                consecutive_successes=health.consecutive_successes,
                threshold=settings.circuit_breaker_success_threshold,
            )
