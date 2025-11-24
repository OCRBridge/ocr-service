"""Unified OCR endpoints for v2 API - engine-agnostic processing."""

import asyncio
import tempfile
import time
from pathlib import Path
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from ocrbridge.core import OCRProcessingError, UnsupportedFormatError

from src.models.responses import SyncOCRResponse
from src.services.ocr.registry_v2 import EngineRegistry
from src.utils.validators import validate_sync_file_size

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v2/ocr", tags=["OCR v2"])


def get_registry() -> EngineRegistry:
    """Dependency to get engine registry from app state."""
    from src.main import app

    return app.state.engine_registry


@router.get("/engines")
async def list_engines(
    registry: Annotated[EngineRegistry, Depends(get_registry)]
) -> dict[str, Any]:
    """List all available OCR engines.

    Returns information about all discovered engines including their
    supported formats and available parameters.

    Returns:
        Dictionary with engine list and details
    """
    engines = registry.list_engines()

    engine_details = []
    for engine_name in engines:
        try:
            info = registry.get_engine_info(engine_name)
            engine_details.append(info)
        except Exception as e:
            logger.warning("failed_to_get_engine_info", engine=engine_name, error=str(e))

    return {
        "engines": engines,
        "count": len(engines),
        "details": engine_details,
    }


@router.get("/engines/{engine_name}/schema")
async def get_engine_schema(
    engine_name: str,
    registry: Annotated[EngineRegistry, Depends(get_registry)],
) -> dict[str, Any]:
    """Get JSON schema for engine parameters.

    Returns the Pydantic model schema for the specified engine's parameters,
    which can be used to validate parameters or generate forms.

    Args:
        engine_name: Name of the engine (e.g., 'tesseract', 'easyocr')

    Returns:
        JSON schema for engine parameters

    Raises:
        HTTPException: 404 if engine not found
    """
    if not registry.is_engine_available(engine_name):
        available = ", ".join(registry.list_engines())
        raise HTTPException(
            status_code=404,
            detail=f"Engine '{engine_name}' not found. Available engines: {available}",
        )

    param_model = registry.get_param_model(engine_name)

    if param_model is None:
        return {
            "engine": engine_name,
            "schema": None,
            "message": "This engine does not have configurable parameters",
        }

    # Get Pydantic JSON schema
    schema = param_model.model_json_schema()

    return {
        "engine": engine_name,
        "schema": schema,
    }


@router.post("/process", response_model=SyncOCRResponse)
async def process_document(
    file: Annotated[UploadFile, File(description="Document file (image or PDF)")],
    engine: Annotated[
        str,
        Form(description="OCR engine to use (e.g., 'tesseract', 'easyocr', 'ocrmac')"),
    ],
    registry: Annotated[EngineRegistry, Depends(get_registry)],
    _validated_file: Annotated[UploadFile, Depends(validate_sync_file_size)],
    params: Annotated[
        str | None,
        Form(
            description="Engine parameters as JSON string (optional)",
            example='{"lang": "eng", "psm": 3}',
        ),
    ] = None,
) -> SyncOCRResponse:
    """Process a document using specified OCR engine (synchronous).

    Unified endpoint that works with any installed OCR engine. The engine
    is specified via the 'engine' parameter, and engine-specific parameters
    can be provided as JSON in the 'params' field.

    **Supported Engines:**
    - `tesseract`: Fast, multilingual, supports 100+ languages
    - `easyocr`: Deep learning-based, excellent for Asian scripts
    - `ocrmac`: Apple Vision framework (macOS only)

    **Parameters:**
    Each engine has its own parameter schema. Use the
    `/v2/ocr/engines/{engine}/schema` endpoint to get the schema.

    **Limits:**
    - Maximum file size: 5MB (use async endpoints for larger files)
    - Maximum timeout: 30 seconds

    Args:
        file: Document file to process
        engine: Engine name
        params: Optional JSON string with engine-specific parameters
        registry: Engine registry (injected)

    Returns:
        HOCR XML output with processing metadata

    Raises:
        HTTPException: 400 if engine not found or parameters invalid
        HTTPException: 413 if file too large
        HTTPException: 422 if file format not supported
        HTTPException: 500 if processing fails
    """
    start_time = time.time()

    # Validate engine exists
    if not registry.is_engine_available(engine):
        available = ", ".join(registry.list_engines())
        raise HTTPException(
            status_code=400,
            detail=f"Engine '{engine}' not found. Available engines: {available}",
        )

    # Parse and validate parameters
    validated_params = None
    if params:
        try:
            import json

            params_dict = json.loads(params)
            validated_params = registry.validate_params(engine, params_dict)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON in params field: {e}",
            )
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=str(e),
            )

    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=Path(file.filename or "document").suffix
    ) as tmp_file:
        temp_path = Path(tmp_file.name)
        try:
            # Write file contents
            contents = await file.read()
            tmp_file.write(contents)
            tmp_file.flush()

            logger.info(
                "processing_document_v2",
                engine=engine,
                filename=file.filename,
                size_bytes=len(contents),
            )

            # Get engine and process
            try:
                ocr_engine = registry.get_engine(engine)

                # Run OCR in thread pool to avoid blocking
                hocr_result = await asyncio.wait_for(
                    asyncio.to_thread(ocr_engine.process, temp_path, validated_params),
                    timeout=30.0,
                )

                processing_duration = time.time() - start_time

                # Count pages in HOCR
                page_count = hocr_result.count('class="ocr_page"')
                if page_count == 0:
                    page_count = 1

                logger.info(
                    "document_processed_v2",
                    engine=engine,
                    duration_seconds=processing_duration,
                    pages=page_count,
                )

                return SyncOCRResponse(
                    hocr=hocr_result,
                    processing_duration_seconds=round(processing_duration, 3),
                    engine=engine,
                    pages=page_count,
                )

            except UnsupportedFormatError as e:
                logger.warning("unsupported_format_v2", engine=engine, error=str(e))
                raise HTTPException(
                    status_code=422,
                    detail=str(e),
                )

            except OCRProcessingError as e:
                logger.error("ocr_processing_failed_v2", engine=engine, error=str(e))
                raise HTTPException(
                    status_code=500,
                    detail=f"OCR processing failed: {e}",
                )

            except TimeoutError:
                logger.error("ocr_timeout_v2", engine=engine)
                raise HTTPException(
                    status_code=504,
                    detail="OCR processing timeout (30s). Use async endpoint for large files.",
                )

        finally:
            # Clean up temporary file
            temp_path.unlink(missing_ok=True)
