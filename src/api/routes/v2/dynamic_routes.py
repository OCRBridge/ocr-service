"""Dynamic route generation for OCR engines.

This module dynamically creates engine-specific API routes based on
engines discovered at startup via entry points.
"""

import asyncio
import time
from inspect import Parameter, Signature, signature
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, UploadFile
from ocrbridge.core.exceptions import OCRProcessingError
from pydantic import BaseModel

from src.models.responses import SyncOCRResponse
from src.services.ocr.registry_v2 import EngineRegistry
from src.utils.validators import validate_sync_file_size

logger = structlog.get_logger()


def get_registry() -> EngineRegistry:
    """Dependency to get engine registry from app state."""
    from src.main import app

    return app.state.engine_registry


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
            # Save uploaded file
            suffix = Path(file.filename).suffix if file.filename else ""
            contents = await file.read()
            with NamedTemporaryFile(delete=False, suffix=suffix) as tf:
                tf.write(contents)
                tf.flush()
                temp_file = tf
            temp_file_name = temp_file.name

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
                timeout=30.0,
            )

            duration = time.time() - start_time
            pages = hocr.count('class="ocr_page"') or 1

            logger.info(
                "ocr_processing_completed",
                engine=engine_name,
                duration=duration,
                pages=pages,
            )

            return SyncOCRResponse(
                hocr=hocr,
                processing_duration_seconds=duration,
                engine=engine_name,
                pages=pages,
            )

        except TimeoutError:
            logger.error("ocr_timeout", engine=engine_name)
            raise HTTPException(
                status_code=504,
                detail=f"OCR processing timeout after 30 seconds for {engine_name}",
            )
        except OCRProcessingError as e:
            logger.error("ocr_engine_processing_failed", engine=engine_name, error=str(e))
            raise HTTPException(
                status_code=500,
                detail=f"OCR engine failed to process document: {str(e)}",
            )
        except ValueError as e:
            logger.error("engine_error", engine=engine_name, error=str(e))
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(
                "ocr_processing_failed",
                engine=engine_name,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise HTTPException(
                status_code=500,
                detail=f"OCR processing failed for {engine_name}: {str(e)}",
            )
        finally:
            if temp_file:
                Path(temp_file.name).unlink(missing_ok=True)

    # Create handler based on whether engine has parameters
    if param_model:
        # Generate dynamic parameters from the model
        dynamic_params = create_form_params_from_model(param_model)

        async def handler_with_params(
            file: Annotated[UploadFile, File(description="Document to process")],
            registry: Annotated[EngineRegistry, Depends(get_registry)],
            _validated_file: Annotated[UploadFile, Depends(validate_sync_file_size)],
            **engine_params: Any,
        ) -> SyncOCRResponse:
            """Process document with OCR engine (dynamic params)."""
            try:
                validated_params = registry.validate_params(engine_name, engine_params)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Parameter validation failed: {e}")

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
            file: Annotated[UploadFile, File(description="Document to process")],
            registry: Annotated[EngineRegistry, Depends(get_registry)],
            _validated_file: Annotated[UploadFile, Depends(validate_sync_file_size)],
        ) -> SyncOCRResponse:
            """Process document with OCR engine."""
            return await process_document(file, registry, None)

        handler_no_params.__doc__ = f"Process document with {engine_name} OCR engine."
        return handler_no_params


def create_engine_router(
    engine_name: str, param_model: type[BaseModel] | None, registry: EngineRegistry
) -> APIRouter:
    """Create a dedicated router for a specific engine.

    Args:
        engine_name: Name of the OCR engine
        param_model: Optional Pydantic model for parameter validation
        registry: Engine registry instance

    Returns:
        APIRouter configured for the engine
    """
    router = APIRouter(prefix=f"/v2/ocr/{engine_name}", tags=["OCR", engine_name.capitalize()])

    # Create and register the process endpoint
    handler = create_process_handler(engine_name, param_model)

    router.post(
        "/process",
        response_model=SyncOCRResponse,
        summary=f"Process document with {engine_name}",
        description=(
            f"Process a document using the {engine_name} OCR engine. "
            "Provide engine-specific parameters as individual form fields."
        ),
        operation_id=f"ocr_process_{engine_name}_v2",
    )(handler)

    # Add an info endpoint to expose engine capabilities and params schema
    @router.get(
        "/info",
        summary=f"Get {engine_name} engine info",
        description=(
            "Returns engine metadata including supported formats and a JSON "
            "schema for parameters when available."
        ),
        operation_id=f"ocr_engine_info_{engine_name}_v2",
    )
    async def engine_info(
        _registry: Annotated[EngineRegistry, Depends(get_registry)],
    ) -> dict[str, Any]:
        return registry.get_engine_info(engine_name)

    # Remove local name to avoid unused-function warnings while keeping route registered
    del engine_info

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

            # Create engine-specific router
            engine_router = create_engine_router(engine_name, param_model, registry)

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

    @api_router.get(
        "/engines",
        summary="List available OCR engines",
        description=("Lists all discovered OCR engines with metadata and parameter schemas."),
        operation_id="ocr_engines_list_v2",
    )
    async def list_engines_endpoint() -> list[dict[str, Any]]:
        engines = registry.list_engines()
        return [registry.get_engine_info(name) for name in engines]

    # Remove local name to avoid unused-function warnings while keeping route registered
    del list_engines_endpoint

    # New endpoint: GET /v2/ocr/engines/{engine_name}
    @api_router.get(
        "/engines/{engine_name}",
        summary="Get details for a specific OCR engine",
        description=("Returns metadata and parameter schema for a given OCR engine."),
        operation_id="ocr_engine_details_v2",
    )
    async def get_engine_details_endpoint(
        engine_name: str,
        registry: Annotated[EngineRegistry, Depends(get_registry)],
    ) -> dict[str, Any]:
        try:
            return registry.get_engine_info(engine_name)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # Remove local name to avoid unused-function warnings while keeping route registered
    del get_engine_details_endpoint

    # Avoid duplicate include: check if base path exists
    existing_paths = {getattr(r, "path", None) for r in app.router.routes}
    if "/v2/ocr/engines" not in existing_paths:
        app.include_router(api_router)
