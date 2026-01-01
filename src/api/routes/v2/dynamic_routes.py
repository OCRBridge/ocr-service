"""Dynamic route generation for OCR engines.

This module dynamically creates engine-specific API routes based on
engines discovered at startup via entry points.
"""

import asyncio
import re
import time
from inspect import Parameter, Signature, signature
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from ocrbridge.core.exceptions import OCRProcessingError
from pydantic import BaseModel

from src.api.dependencies import verify_api_key
from src.config import settings
from src.models.responses import ErrorResponse, SyncOCRResponse
from src.services.ocr.registry_v2 import EngineRegistry
from src.utils.metrics import (
    sync_ocr_duration_seconds,
    sync_ocr_file_size_bytes,
    sync_ocr_requests_total,
    sync_ocr_timeouts_total,
)
from src.utils.validators import validate_sync_file_size

logger = structlog.get_logger()

# Allowed file extensions for security
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".tiff", ".tif"}


def get_safe_suffix(filename: str | None) -> str:
    """Extract and validate file extension from filename.

    Args:
        filename: Original filename from upload

    Returns:
        Validated file extension

    Raises:
        HTTPException: If filename contains invalid characters or unsupported extension
    """
    if not filename:
        return ""

    # Get only basename to prevent path traversal
    safe_name = Path(filename).name

    # Validate filename length to prevent excessively long paths
    if len(safe_name) > 255:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename: exceeds maximum length of 255 characters",
        )

    # Validate: only alphanumeric + allowed chars (prevent path traversal, null bytes, etc.)
    if not re.match(r"^[a-zA-Z0-9._-]+$", safe_name):
        raise HTTPException(
            status_code=400,
            detail="Invalid filename: contains unsupported characters",
        )

    # Extract and validate extension
    suffix = Path(safe_name).suffix.lower()
    if suffix and suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    return suffix


def get_registry(request: Request) -> EngineRegistry:
    """Dependency to get engine registry from app state."""
    return request.app.state.engine_registry


def create_form_params_from_model(param_model: type[BaseModel]) -> dict[str, Parameter]:
    """Create FastAPI Form parameters from a Pydantic model.

    Converts each field in the Pydantic model to a FastAPI Form parameter
    with proper type annotations and default values.

    Args:
        param_model: Pydantic model class

    Returns:
        Dictionary mapping field names to Parameter objects
    """
    params: dict[str, Parameter] = {}

    for field_name, field_info in param_model.model_fields.items():
        # Get the field type annotation
        field_type = field_info.annotation

        # Create Form metadata.
        # We intentionally do NOT pass the default value to Form() here because:
        # 1. Passing mutable defaults (like lists) to Form() causes "unhashable type" errors.
        # 2. Passing defaults to Form() inside Annotated AND having a function default
        #    causes "Form default value cannot be set in Annotated" errors.
        # Instead, we set the default on the Parameter object below.
        form_info = Form(..., description=field_info.description)

        # Create annotated type: Annotated[field_type, Form(...)]
        annotated_type = Annotated[field_type, form_info]

        # Determine parameter default
        default_val = Parameter.empty if field_info.is_required() else field_info.default

        # Create Parameter object
        params[field_name] = Parameter(
            field_name,
            Parameter.KEYWORD_ONLY,
            default=default_val,
            annotation=annotated_type,
        )

    return params


def create_signature_with_dynamic_params(
    original_sig: Signature, dynamic_params: dict[str, Parameter]
) -> Signature:
    """Add dynamic parameters to a function signature.

    Inserts dynamic params after 'file' and 'params_json' but before
    'registry' and other dependencies.

    Args:
        original_sig: Original function signature
        dynamic_params: Parameters to insert

    Returns:
        Modified signature with dynamic parameters
    """
    original_params = list(original_sig.parameters.values())

    # Append dynamic params at the end to preserve valid order.
    # Python signature order must be: positional-or-keyword params first,
    # then keyword-only params (our Form fields). Placing them last avoids
    # "keyword-only parameter before positional or keyword parameter" errors.
    insertion_index = len(original_params)

    # Build new parameter list
    new_params = (
        original_params[:insertion_index]
        + list(dynamic_params.values())
        + original_params[insertion_index:]
    )

    # Remove **engine_params since we're replacing it with explicit params
    new_params = [p for p in new_params if p.name != "engine_params"]

    return original_sig.replace(parameters=new_params)


def create_process_handler(engine_name: str, param_model: type[BaseModel] | None) -> Any:
    """Create the /process endpoint handler for a specific engine.

    Args:
        engine_name: Name of the OCR engine
        param_model: Optional Pydantic model for parameter validation

    Returns:
        Async route handler function
    """

    # Helper function for common OCR processing logic
    async def process_document(
        file: UploadFile,
        registry: EngineRegistry,
        validated_params: Any,
    ) -> SyncOCRResponse:
        """Common OCR processing logic."""
        temp_file = None
        try:
            # Save uploaded file with validated filename
            suffix = get_safe_suffix(file.filename)
            contents = await file.read()

            # Ensure upload directory exists
            upload_dir = Path(settings.upload_dir)
            upload_dir.mkdir(parents=True, exist_ok=True)

            # Create temp file in configured directory (not system /tmp)
            with NamedTemporaryFile(delete=False, suffix=suffix, dir=upload_dir) as tf:
                tf.write(contents)
                tf.flush()
                temp_file = tf
            temp_file_name = temp_file.name

            # Record file size metric
            sync_ocr_file_size_bytes.labels(engine=engine_name).observe(len(contents))

            # Check circuit breaker before processing
            if not registry.is_engine_available(engine_name):
                logger.warning(
                    "engine_circuit_open",
                    engine=engine_name,
                    reason="Circuit breaker is open due to repeated failures",
                )
                raise HTTPException(
                    status_code=503,
                    detail=f"OCR engine '{engine_name}' is temporarily unavailable due to repeated failures. "
                    "Please try again later or use a different engine.",
                )

            # Get engine and process
            start_time = time.time()
            ocr_engine = registry.get_engine(engine_name)

            logger.info(
                "ocr_processing_started",
                engine=engine_name,
                file_size=len(contents),
                has_params=validated_params is not None,
            )

            hocr = await asyncio.wait_for(
                asyncio.to_thread(ocr_engine.process, Path(temp_file_name), validated_params),
                timeout=float(settings.sync_timeout_seconds),
            )

            duration = time.time() - start_time
            pages = hocr.count('class="ocr_page"') or 1

            logger.info(
                "ocr_processing_completed",
                engine=engine_name,
                duration=duration,
                pages=pages,
            )

            # Record success for circuit breaker
            registry.record_engine_success(engine_name)

            # Record success metrics
            sync_ocr_requests_total.labels(engine=engine_name, status="success").inc()
            sync_ocr_duration_seconds.labels(engine=engine_name).observe(duration)

            return SyncOCRResponse(
                hocr=hocr,
                processing_duration_seconds=duration,
                engine=engine_name,
                pages=pages,
            )

        except asyncio.TimeoutError:
            logger.error(
                "ocr_timeout",
                engine=engine_name,
                timeout_seconds=settings.sync_timeout_seconds,
            )
            # Record failure for circuit breaker
            registry.record_engine_failure(engine_name)
            # Record timeout metrics
            sync_ocr_requests_total.labels(engine=engine_name, status="timeout").inc()
            sync_ocr_timeouts_total.labels(engine=engine_name).inc()
            raise HTTPException(
                status_code=504,
                detail=f"OCR processing timeout after {settings.sync_timeout_seconds} seconds. "
                "Try reducing image size or complexity.",
            )
        except OCRProcessingError as e:
            logger.error(
                "ocr_engine_processing_failed",
                engine=engine_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            # Record failure for circuit breaker
            registry.record_engine_failure(engine_name)
            # Record error metric
            sync_ocr_requests_total.labels(engine=engine_name, status="error").inc()
            raise HTTPException(
                status_code=500,
                detail="OCR processing failed. Please check your document and try again.",
            )
        except ValueError as e:
            logger.error("parameter_validation_error", engine=engine_name, error=str(e))
            # Don't record parameter validation as engine failure
            # Record rejected metric
            sync_ocr_requests_total.labels(engine=engine_name, status="rejected").inc()
            raise HTTPException(
                status_code=400,
                detail="Invalid parameters. Please check your request.",
            )
        except HTTPException:
            # Re-raise HTTP exceptions (like 503 from circuit breaker) as-is
            raise
        except Exception as e:
            logger.error(
                "ocr_processing_failed",
                engine=engine_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            # Record failure for circuit breaker
            registry.record_engine_failure(engine_name)
            # Record error metric
            sync_ocr_requests_total.labels(engine=engine_name, status="error").inc()
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred during OCR processing.",
            )
        finally:
            if temp_file:
                Path(temp_file.name).unlink(missing_ok=True)

    # Create handler based on whether engine has parameters
    if param_model:
        # Generate dynamic parameters from the model
        dynamic_params = create_form_params_from_model(param_model)

        async def handler_with_params(
            request: Request,
            file: Annotated[UploadFile, File(description="Document to process")],
            registry: Annotated[EngineRegistry, Depends(get_registry)],
            _validated_file: Annotated[UploadFile, Depends(validate_sync_file_size)],
            _api_key: Annotated[str, Depends(verify_api_key)],
            **engine_params: Any,
        ) -> SyncOCRResponse:
            """Process document with OCR engine (dynamic params)."""
            try:
                validated_params = registry.validate_params(engine_name, engine_params)
            except ValueError as e:
                # Log detailed validation error internally
                logger.error(
                    "parameter_validation_failed",
                    engine=engine_name,
                    error=str(e),
                )
                # Return generic message (security: don't expose validation internals)
                raise HTTPException(
                    status_code=400,
                    detail="Parameter validation failed. Please check engine parameter requirements.",
                )

            return await process_document(file, registry, validated_params)

        # Update signature to include dynamic parameters
        sig = signature(handler_with_params)
        # create_signature_with_dynamic_params expects "engine_params" to be present in sig
        # to remove it and replace with dynamic params
        new_sig = create_signature_with_dynamic_params(sig, dynamic_params)
        handler_with_params.__signature__ = new_sig  # type: ignore

        handler_with_params.__doc__ = f"Process document with {engine_name} OCR engine."
        return handler_with_params

    else:
        # Engine without parameters
        async def handler_no_params(
            request: Request,
            file: Annotated[UploadFile, File(description="Document to process")],
            registry: Annotated[EngineRegistry, Depends(get_registry)],
            _validated_file: Annotated[UploadFile, Depends(validate_sync_file_size)],
            _api_key: Annotated[str, Depends(verify_api_key)],
        ) -> SyncOCRResponse:
            """Process document with OCR engine."""
            return await process_document(file, registry, None)

        handler_no_params.__doc__ = f"Process document with {engine_name} OCR engine."
        return handler_no_params


def create_engine_router(
    engine_name: str,
    param_model: type[BaseModel] | None,
    registry: EngineRegistry,
    app: FastAPI | None = None,
) -> APIRouter:
    """Create a dedicated router for a specific engine.

    Args:
        engine_name: Name of the OCR engine
        param_model: Optional Pydantic model for parameter validation
        registry: Engine registry instance
        app: FastAPI application instance (for rate limiter access)

    Returns:
        APIRouter configured for the engine
    """
    router = APIRouter(prefix=f"/v2/ocr/{engine_name}", tags=["OCR", engine_name.capitalize()])

    # Create and register the process endpoint
    handler = create_process_handler(engine_name, param_model)

    # Apply rate limiting if enabled
    if app and settings.rate_limit_enabled and hasattr(app.state, "limiter"):
        limiter = app.state.limiter
        # Apply rate limit decorator for expensive OCR processing
        handler = limiter.limit(settings.rate_limit_ocr_process)(handler)

    router.post(
        "/process",
        response_model=SyncOCRResponse,
        summary=f"Process document with {engine_name}",
        description=(
            f"Process a document using the {engine_name} OCR engine. "
            "Provide engine-specific parameters as individual form fields."
        ),
        operation_id=f"ocr_process_{engine_name}_v2",
        responses={
            400: {
                "model": ErrorResponse,
                "description": "Invalid request - bad parameters, unsupported file format, or file too large",
            },
            401: {
                "model": ErrorResponse,
                "description": "Unauthorized - missing or invalid API key",
            },
            404: {
                "model": ErrorResponse,
                "description": "Engine not found",
            },
            413: {
                "model": ErrorResponse,
                "description": "File too large for synchronous processing",
            },
            500: {
                "model": ErrorResponse,
                "description": "Internal server error during OCR processing",
            },
            503: {
                "model": ErrorResponse,
                "description": "Engine temporarily unavailable (circuit breaker open)",
            },
            504: {
                "model": ErrorResponse,
                "description": "OCR processing timeout",
            },
        },
    )(handler)

    # Add an info endpoint to expose engine capabilities and params schema
    async def engine_info_handler(
        request: Request,
        _registry: Annotated[EngineRegistry, Depends(get_registry)],
        _api_key: Annotated[str, Depends(verify_api_key)],
    ) -> dict[str, Any]:
        return registry.get_engine_info(engine_name)

    # Apply rate limiting if enabled (lighter limit for info endpoints)
    if app and settings.rate_limit_enabled and hasattr(app.state, "limiter"):
        limiter = app.state.limiter
        engine_info_handler = limiter.limit(settings.rate_limit_ocr_info)(engine_info_handler)

    router.get(
        "/info",
        summary=f"Get {engine_name} engine info",
        description=(
            "Returns engine metadata including supported formats and a JSON "
            "schema for parameters when available."
        ),
        operation_id=f"ocr_engine_info_{engine_name}_v2",
    )(engine_info_handler)

    return router


def register_engine_routes(app: FastAPI, registry: EngineRegistry) -> None:
    """Register a router for each discovered engine.

    Args:
        app: FastAPI application instance
        registry: Engine registry with discovered engines
    """
    discovered_engines = registry.list_engines()

    if not discovered_engines:
        logger.warning("no_engines_to_register", message="No OCR engines discovered")
        return

    for engine_name in discovered_engines:
        try:
            # Get parameter model (might be None)
            param_model = registry.get_param_model(engine_name)

            # Create engine-specific router with rate limiting
            engine_router = create_engine_router(engine_name, param_model, registry, app)

            # Avoid duplicate registration (e.g., tests calling register twice)
            existing_paths = {getattr(r, "path", None) for r in app.router.routes}
            process_path = f"/v2/ocr/{engine_name}/process"
            if process_path in existing_paths:
                logger.debug(
                    "route_already_registered",
                    engine=engine_name,
                    path=process_path,
                )
                continue

            # Register with main app
            app.include_router(engine_router)

            logger.info(
                "route_registered",
                engine=engine_name,
                path=f"/v2/ocr/{engine_name}/process",
                has_param_model=param_model is not None,
            )
        except Exception as e:
            # Log error but don't fail startup if one engine fails
            logger.error(
                "route_registration_failed",
                engine=engine_name,
                error=str(e),
                error_type=type(e).__name__,
            )

    logger.info(
        "dynamic_routes_registered",
        count=len(discovered_engines),
        engines=discovered_engines,
    )

    # Add a global listing endpoint if not already present
    api_router = APIRouter(prefix="/v2/ocr", tags=["OCR"])

    # List all engines endpoint
    async def list_engines_handler(
        request: Request,
        _api_key: Annotated[str, Depends(verify_api_key)],
    ) -> list[dict[str, Any]]:
        engines = registry.list_engines()
        return [registry.get_engine_info(name) for name in engines]

    # Apply rate limiting if enabled
    if settings.rate_limit_enabled and hasattr(app.state, "limiter"):
        limiter = app.state.limiter
        list_engines_handler = limiter.limit(settings.rate_limit_ocr_info)(list_engines_handler)

    api_router.get(
        "/engines",
        summary="List available OCR engines",
        description=("Lists all discovered OCR engines with metadata and parameter schemas."),
        operation_id="ocr_engines_list_v2",
    )(list_engines_handler)

    # New endpoint: GET /v2/ocr/engines/{engine_name}
    async def get_engine_details_handler(
        request: Request,
        engine_name: str,
        registry: Annotated[EngineRegistry, Depends(get_registry)],
        _api_key: Annotated[str, Depends(verify_api_key)],
    ) -> dict[str, Any]:
        try:
            return registry.get_engine_info(engine_name)
        except ValueError as e:
            # Log detailed error internally
            logger.error("engine_not_found", engine=engine_name, error=str(e))
            # Return generic message (security: don't list available engines)
            raise HTTPException(
                status_code=404,
                detail=f"Engine '{engine_name}' not found. Check /v2/ocr/engines for available engines.",
            )

    # Apply rate limiting if enabled
    if settings.rate_limit_enabled and hasattr(app.state, "limiter"):
        limiter = app.state.limiter
        get_engine_details_handler = limiter.limit(settings.rate_limit_ocr_info)(
            get_engine_details_handler
        )

    api_router.get(
        "/engines/{engine_name}",
        summary="Get details for a specific OCR engine",
        description=("Returns metadata and parameter schema for a given OCR engine."),
        operation_id="ocr_engine_details_v2",
    )(get_engine_details_handler)

    # Avoid duplicate include: check if base path exists
    existing_paths = {getattr(r, "path", None) for r in app.router.routes}
    if "/v2/ocr/engines" not in existing_paths:
        app.include_router(api_router)
