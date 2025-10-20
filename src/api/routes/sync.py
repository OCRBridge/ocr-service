"""Synchronous OCR processing endpoints.

This module provides direct request-response OCR processing without job queues.
Clients POST a document and receive hOCR output immediately in the response body.
"""

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from pydantic import ValidationError

from src.config import settings
from src.models import TesseractParams
from src.models.ocr_params import EasyOCRParams, OcrmacParams
from src.models.responses import SyncOCRResponse
from src.services.file_handler import FileHandler
from src.services.ocr.easyocr import EasyOCREngine
from src.services.ocr.ocrmac import OcrmacEngine
from src.services.ocr.registry import EngineRegistry, EngineType
from src.services.ocr_processor import OCRProcessor
from src.utils.hocr import parse_hocr
from src.utils.metrics import (
    sync_ocr_duration_seconds,
    sync_ocr_file_size_bytes,
    sync_ocr_requests_total,
    sync_ocr_timeouts_total,
)
from src.utils.validators import UnsupportedFormatError, validate_sync_file_size

router = APIRouter()
logger = structlog.get_logger()


@asynccontextmanager
async def temporary_upload(file: UploadFile):
    """Context manager for temporary file handling with guaranteed cleanup.

    Args:
        file: Uploaded file from FastAPI

    Yields:
        Tuple of (file_path, file_format) for processing

    Ensures file cleanup regardless of success, timeout, or error.
    """
    file_handler = FileHandler()
    file_path = None

    try:
        # Save uploaded file
        document_upload = await file_handler.save_upload(file)
        file_path = document_upload.temp_file_path
        file_format = document_upload.file_format
        yield file_path, file_format
    finally:
        # Cleanup happens regardless of success, timeout, or error
        if file_path and file_path.exists():
            try:
                file_path.unlink()
                logger.debug(
                    "sync_file_cleanup_success",
                    file_path=str(file_path),
                )
            except Exception as e:
                logger.error(
                    "sync_file_cleanup_failed",
                    file_path=str(file_path),
                    error=str(e),
                )


@router.post(
    "/tesseract",
    response_model=SyncOCRResponse,
    summary="Synchronous Tesseract OCR",
    description="Process a document with Tesseract and receive hOCR output immediately. "
    "Maximum file size: 5MB. Maximum processing time: 30 seconds.",
)
async def sync_tesseract(
    file: UploadFile = Depends(validate_sync_file_size),
    lang: str | None = Form(
        None,
        description=(
            "Language code(s) for OCR recognition. Use 3-letter ISO 639-2/3 codes. "
            "Multiple languages can be specified using '+' separator (max 5). "
            "Common codes: eng (English), fra (French), deu (German), spa (Spanish), "
            "ita (Italian), por (Portuguese), rus (Russian), ara (Arabic), "
            "chi_sim (Simplified Chinese), jpn (Japanese). "
            "Examples: 'eng', 'eng+fra', 'eng+fra+deu'. "
            "Default: eng"
        ),
        pattern=r"^[a-z_]{3,7}(\+[a-z_]{3,7}){0,4}$",
        examples=["eng", "eng+fra", "fra"],
    ),
    psm: int | None = Form(
        None,
        description=(
            "Page Segmentation Mode (0-13) - controls how Tesseract segments the page. "
            "Common modes: 3=Fully automatic (default, best for most documents), "
            "6=Single uniform block (best for tables/invoices/forms), "
            "7=Single text line (best for single-line fields), "
            "11=Sparse text (best for receipts with scattered text). "
            "Default: 3"
        ),
        ge=0,
        le=13,
        examples=[3, 6, 11],
    ),
    oem: int | None = Form(
        None,
        description=(
            "OCR Engine Mode (0-3) - controls which Tesseract engine to use. "
            "0=Legacy engine, 1=LSTM neural network (recommended), "
            "2=Legacy+LSTM combined, 3=Default (auto-select). "
            "Default: 3"
        ),
        ge=0,
        le=3,
        examples=[1, 3],
    ),
    dpi: int | None = Form(
        None,
        description=(
            "Image resolution (dots per inch) for OCR processing. "
            "Typical values: 150 (low-res), 300 (standard), 600 (high-quality). "
            "Range: 70-2400. Default: Auto-detect from image metadata or 70"
        ),
        ge=70,
        le=2400,
        examples=[300],
    ),
) -> SyncOCRResponse:
    """Process document with synchronous Tesseract endpoint.

    Args:
        file: Uploaded document (JPEG, PNG, PDF, TIFF)
        lang: Language code (e.g., 'eng', 'fra+deu')
        psm: Page segmentation mode (0-13)
        oem: OCR engine mode (0-3)
        dpi: Image DPI (70-2400)

    Returns:
        SyncOCRResponse with hOCR content

    Raises:
        HTTPException:
            - 408: Processing timeout exceeded (>30s)
            - 413: File size exceeds 5MB limit
            - 415: Unsupported file format
            - 422: Invalid parameters
            - 500: OCR processing error
    """
    correlation_id = str(uuid.uuid4())
    engine_name = "tesseract"
    start_time = time.time()

    # Get file size for metrics (file already read by validator, need to re-read)
    contents = await file.read()
    file_size = len(contents)
    await file.seek(0)  # Reset for processing

    # Record metrics - request started
    sync_ocr_requests_total.labels(engine=engine_name, status="started").inc()
    sync_ocr_file_size_bytes.labels(engine=engine_name).observe(file_size)

    logger.info(
        "sync_ocr_request_started",
        correlation_id=correlation_id,
        engine=engine_name,
        filename=file.filename,
        file_size_bytes=file_size,
        parameters={"lang": lang, "psm": psm, "oem": oem, "dpi": dpi},
    )

    try:
        # Validate Tesseract parameters
        try:
            params = TesseractParams(lang=lang, psm=psm, oem=oem, dpi=dpi)  # type: ignore
        except ValidationError as e:
            logger.warning("parameter_validation_failed", errors=e.errors())
            sync_ocr_requests_total.labels(engine=engine_name, status="rejected").inc()
            raise HTTPException(
                status_code=422,
                detail=json.loads(e.json()),
            )

        # Process with timeout
        async with temporary_upload(file) as (file_path, file_format):
            try:
                # Create OCR processor instance
                processor = OCRProcessor(tesseract_params=params)

                # Process with timeout enforcement
                hocr_content = await asyncio.wait_for(
                    processor.process_document(file_path, file_format),
                    timeout=settings.sync_timeout_seconds,
                )

                # Count pages from HOCR
                hocr_info = parse_hocr(hocr_content)
                page_count = hocr_info.page_count

                # Calculate duration
                duration = time.time() - start_time

                # Record metrics - success
                sync_ocr_requests_total.labels(engine=engine_name, status="success").inc()
                sync_ocr_duration_seconds.labels(engine=engine_name).observe(duration)

                logger.info(
                    "sync_ocr_request_completed",
                    correlation_id=correlation_id,
                    engine=engine_name,
                    duration_seconds=duration,
                    pages=page_count,
                    status="success",
                )

                return SyncOCRResponse(
                    hocr=hocr_content,
                    processing_duration_seconds=duration,
                    engine=engine_name,
                    pages=page_count,
                )

            except TimeoutError:
                # Record metrics - timeout
                sync_ocr_timeouts_total.labels(engine=engine_name).inc()
                sync_ocr_requests_total.labels(engine=engine_name, status="timeout").inc()

                duration = time.time() - start_time

                logger.warning(
                    "sync_ocr_request_timeout",
                    correlation_id=correlation_id,
                    engine=engine_name,
                    duration_seconds=duration,
                    timeout_limit=settings.sync_timeout_seconds,
                )

                raise HTTPException(
                    status_code=408,
                    detail=f"Processing exceeded {settings.sync_timeout_seconds}s timeout. "
                    f"Document may be too complex. "
                    f"Use async endpoints (/upload/{engine_name}) for large or multi-page documents.",
                )

    except HTTPException:
        # Re-raise HTTP exceptions (timeout, validation errors)
        raise

    except UnsupportedFormatError as e:
        # Handle unsupported file format
        sync_ocr_requests_total.labels(engine=engine_name, status="rejected").inc()

        duration = time.time() - start_time

        logger.warning(
            "unsupported_format",
            correlation_id=correlation_id,
            engine=engine_name,
            duration_seconds=duration,
            error=str(e),
        )

        raise HTTPException(
            status_code=415,
            detail=str(e),
        )

    except Exception as e:
        # Record metrics - error
        sync_ocr_requests_total.labels(engine=engine_name, status="error").inc()

        duration = time.time() - start_time

        logger.error(
            "sync_ocr_request_failed",
            correlation_id=correlation_id,
            engine=engine_name,
            duration_seconds=duration,
            error=str(e),
            error_type=type(e).__name__,
        )

        raise HTTPException(
            status_code=500,
            detail=f"OCR processing failed: {str(e)}",
        )


@router.post(
    "/easyocr",
    response_model=SyncOCRResponse,
    summary="Synchronous EasyOCR",
    description="Process a document with EasyOCR and receive hOCR output immediately. "
    "Maximum file size: 5MB. Maximum processing time: 30 seconds.",
)
async def sync_easyocr(
    file: UploadFile = Depends(validate_sync_file_size),
    languages: list[str] | None = Form(
        None,
        description=(
            "Language codes for OCR recognition (EasyOCR naming convention). "
            "Use EasyOCR format (e.g., 'en', 'ch_sim', 'ja', 'ko'). "
            "Max 5 languages. Default: ['en'] if not specified. "
            "Examples: ['en'], ['ch_sim', 'en'], ['ja', 'ko', 'en']"
        ),
        examples=[["en"], ["ch_sim", "en"], ["ja"]],
    ),
    text_threshold: float | None = Form(
        None,
        description=(
            "Confidence threshold for text detection (0.0-1.0). "
            "Lower values detect more text but may include noise. "
            "Default: 0.7"
        ),
        ge=0.0,
        le=1.0,
        examples=[0.7],
    ),
    link_threshold: float | None = Form(
        None,
        description=(
            "Threshold for linking text regions (0.0-1.0). "
            "Lower values link more regions together. "
            "Default: 0.7"
        ),
        ge=0.0,
        le=1.0,
        examples=[0.7],
    ),
) -> SyncOCRResponse:
    """Process document with synchronous EasyOCR endpoint.

    Args:
        file: Uploaded document (JPEG, PNG, PDF, TIFF)
        languages: Language codes in list format (e.g., ['en'], ['en', 'ch_sim'])
        text_threshold: Text detection confidence threshold (0.0-1.0)
        link_threshold: Text region linking threshold (0.0-1.0)

    Returns:
        SyncOCRResponse with hOCR content

    Raises:
        HTTPException:
            - 408: Processing timeout exceeded (>30s)
            - 413: File size exceeds 5MB limit
            - 415: Unsupported file format
            - 422: Invalid parameters
            - 500: OCR processing error
    """
    correlation_id = str(uuid.uuid4())
    engine_name = "easyocr"
    start_time = time.time()

    # Get file size for metrics
    contents = await file.read()
    file_size = len(contents)
    await file.seek(0)  # Reset for processing

    # Record metrics - request started
    sync_ocr_requests_total.labels(engine=engine_name, status="started").inc()
    sync_ocr_file_size_bytes.labels(engine=engine_name).observe(file_size)

    logger.info(
        "sync_ocr_request_started",
        correlation_id=correlation_id,
        engine=engine_name,
        filename=file.filename,
        file_size_bytes=file_size,
        parameters={
            "languages": languages,
            "text_threshold": text_threshold,
            "link_threshold": link_threshold,
        },
    )

    try:
        # Validate EasyOCR parameters (provide defaults for None values)
        try:
            param_dict = {}
            if languages is not None:
                param_dict["languages"] = languages
            if text_threshold is not None:
                param_dict["text_threshold"] = text_threshold
            if link_threshold is not None:
                param_dict["link_threshold"] = link_threshold

            params = EasyOCRParams(**param_dict)
        except ValidationError as e:
            logger.warning("parameter_validation_failed", errors=e.errors())
            sync_ocr_requests_total.labels(engine=engine_name, status="rejected").inc()
            raise HTTPException(
                status_code=422,
                detail=json.loads(e.json()),
            )

        # Process with timeout
        async with temporary_upload(file) as (file_path, _):
            try:
                # Create EasyOCR engine instance
                engine = EasyOCREngine()

                # Process with timeout enforcement
                hocr_content = await asyncio.wait_for(
                    asyncio.to_thread(engine.process, file_path, params),
                    timeout=settings.sync_timeout_seconds,
                )

                # Count pages from HOCR
                hocr_info = parse_hocr(hocr_content)
                page_count = hocr_info.page_count

                # Calculate duration
                duration = time.time() - start_time

                # Record metrics - success
                sync_ocr_requests_total.labels(engine=engine_name, status="success").inc()
                sync_ocr_duration_seconds.labels(engine=engine_name).observe(duration)

                logger.info(
                    "sync_ocr_request_completed",
                    correlation_id=correlation_id,
                    engine=engine_name,
                    duration_seconds=duration,
                    pages=page_count,
                    status="success",
                )

                return SyncOCRResponse(
                    hocr=hocr_content,
                    processing_duration_seconds=duration,
                    engine=engine_name,
                    pages=page_count,
                )

            except TimeoutError:
                # Record metrics - timeout
                sync_ocr_timeouts_total.labels(engine=engine_name).inc()
                sync_ocr_requests_total.labels(engine=engine_name, status="timeout").inc()

                duration = time.time() - start_time

                logger.warning(
                    "sync_ocr_request_timeout",
                    correlation_id=correlation_id,
                    engine=engine_name,
                    duration_seconds=duration,
                    timeout_limit=settings.sync_timeout_seconds,
                )

                raise HTTPException(
                    status_code=408,
                    detail=f"Processing exceeded {settings.sync_timeout_seconds}s timeout. "
                    f"Document may be too complex. "
                    f"Use async endpoints (/upload/{engine_name}) for large or multi-page documents.",
                )

    except HTTPException:
        # Re-raise HTTP exceptions (timeout, validation errors)
        raise

    except UnsupportedFormatError as e:
        # Handle unsupported file format
        sync_ocr_requests_total.labels(engine=engine_name, status="rejected").inc()

        duration = time.time() - start_time

        logger.warning(
            "unsupported_format",
            correlation_id=correlation_id,
            engine=engine_name,
            duration_seconds=duration,
            error=str(e),
        )

        raise HTTPException(
            status_code=415,
            detail=str(e),
        )

    except Exception as e:
        # Record metrics - error
        sync_ocr_requests_total.labels(engine=engine_name, status="error").inc()

        duration = time.time() - start_time

        logger.error(
            "sync_ocr_request_failed",
            correlation_id=correlation_id,
            engine=engine_name,
            duration_seconds=duration,
            error=str(e),
            error_type=type(e).__name__,
        )

        raise HTTPException(
            status_code=500,
            detail=f"OCR processing failed: {str(e)}",
        )


@router.post(
    "/ocrmac",
    response_model=SyncOCRResponse,
    summary="Synchronous ocrmac (macOS only)",
    description="Process a document with Apple Vision Framework and receive hOCR output immediately. "
    "Maximum file size: 5MB. Maximum processing time: 30 seconds. "
    "Only available on macOS.",
)
async def sync_ocrmac(
    file: UploadFile = Depends(validate_sync_file_size),
    languages: list[str] | None = Form(
        None,
        description=(
            "Language codes for OCR recognition in IETF BCP 47 format. "
            "Supported: en-US, fr-FR, de-DE, es-ES, it-IT, pt-PT, ru, ar, "
            "zh-Hans (Simplified Chinese), zh-Hant (Traditional Chinese), ja-JP, ko-KR. "
            "Max 5 languages. Omit for automatic language detection. "
            "Examples: ['en-US'], ['en-US', 'fr-FR']"
        ),
        examples=[["en-US"], ["en-US", "fr-FR"]],
    ),
    recognition_level: str | None = Form(
        None,
        description=(
            "Recognition level: 'fast' (fewer languages, faster), "
            "'balanced' (default), 'accurate' (slower, more thorough), "
            "'livetext' (Apple LiveText, macOS Sonoma 14.0+). "
            "Default: balanced"
        ),
        pattern="^(fast|balanced|accurate|livetext)$",
        examples=["balanced", "livetext"],
    ),
) -> SyncOCRResponse:
    """Process document with synchronous ocrmac endpoint.

    Args:
        file: Uploaded document (JPEG, PNG, PDF, TIFF)
        languages: Language codes in IETF BCP 47 format (e.g., ['en-US'], ['en-US', 'fr-FR'])
        recognition_level: Recognition level (fast/balanced/accurate)

    Returns:
        SyncOCRResponse with hOCR content

    Raises:
        HTTPException:
            - 400: Engine unavailable (non-macOS platform)
            - 408: Processing timeout exceeded (>30s)
            - 413: File size exceeds 5MB limit
            - 415: Unsupported file format
            - 422: Invalid parameters
            - 500: OCR processing error
    """
    correlation_id = str(uuid.uuid4())
    engine_name = "ocrmac"
    start_time = time.time()

    # Check engine availability BEFORE processing
    engine_registry = EngineRegistry()
    if not engine_registry.is_available(EngineType.OCRMAC):
        _, error_msg = engine_registry.validate_platform(EngineType.OCRMAC)
        logger.warning(
            "engine_unavailable",
            correlation_id=correlation_id,
            engine=engine_name,
            error=error_msg,
        )
        raise HTTPException(
            status_code=400,
            detail=error_msg or f"{engine_name} engine is unavailable",
        )

    # Get file size for metrics
    contents = await file.read()
    file_size = len(contents)
    await file.seek(0)  # Reset for processing

    # Record metrics - request started
    sync_ocr_requests_total.labels(engine=engine_name, status="started").inc()
    sync_ocr_file_size_bytes.labels(engine=engine_name).observe(file_size)

    logger.info(
        "sync_ocr_request_started",
        correlation_id=correlation_id,
        engine=engine_name,
        filename=file.filename,
        file_size_bytes=file_size,
        parameters={"languages": languages, "recognition_level": recognition_level},
    )

    try:
        # Validate ocrmac parameters (provide defaults for None values)
        try:
            param_dict = {}
            if languages is not None:
                param_dict["languages"] = languages
            if recognition_level is not None:
                param_dict["recognition_level"] = recognition_level

            params = OcrmacParams(**param_dict)
        except ValidationError as e:
            logger.warning("parameter_validation_failed", errors=e.errors())
            sync_ocr_requests_total.labels(engine=engine_name, status="rejected").inc()
            raise HTTPException(
                status_code=422,
                detail=json.loads(e.json()),
            )

        # Process with timeout
        async with temporary_upload(file) as (file_path, _):
            try:
                # Create ocrmac engine instance
                engine = OcrmacEngine()

                # Process with timeout enforcement
                hocr_content = await asyncio.wait_for(
                    asyncio.to_thread(engine.process, file_path, params),
                    timeout=settings.sync_timeout_seconds,
                )

                # Count pages from HOCR
                hocr_info = parse_hocr(hocr_content)
                page_count = hocr_info.page_count

                # Calculate duration
                duration = time.time() - start_time

                # Record metrics - success
                sync_ocr_requests_total.labels(engine=engine_name, status="success").inc()
                sync_ocr_duration_seconds.labels(engine=engine_name).observe(duration)

                logger.info(
                    "sync_ocr_request_completed",
                    correlation_id=correlation_id,
                    engine=engine_name,
                    duration_seconds=duration,
                    pages=page_count,
                    status="success",
                )

                return SyncOCRResponse(
                    hocr=hocr_content,
                    processing_duration_seconds=duration,
                    engine=engine_name,
                    pages=page_count,
                )

            except TimeoutError:
                # Record metrics - timeout
                sync_ocr_timeouts_total.labels(engine=engine_name).inc()
                sync_ocr_requests_total.labels(engine=engine_name, status="timeout").inc()

                duration = time.time() - start_time

                logger.warning(
                    "sync_ocr_request_timeout",
                    correlation_id=correlation_id,
                    engine=engine_name,
                    duration_seconds=duration,
                    timeout_limit=settings.sync_timeout_seconds,
                )

                raise HTTPException(
                    status_code=408,
                    detail=f"Processing exceeded {settings.sync_timeout_seconds}s timeout. "
                    f"Document may be too complex. "
                    f"Use async endpoints (/upload/{engine_name}) for large or multi-page documents.",
                )

    except HTTPException:
        # Re-raise HTTP exceptions (timeout, validation errors)
        raise

    except UnsupportedFormatError as e:
        # Handle unsupported file format
        sync_ocr_requests_total.labels(engine=engine_name, status="rejected").inc()

        duration = time.time() - start_time

        logger.warning(
            "unsupported_format",
            correlation_id=correlation_id,
            engine=engine_name,
            duration_seconds=duration,
            error=str(e),
        )

        raise HTTPException(
            status_code=415,
            detail=str(e),
        )

    except Exception as e:
        # Record metrics - error
        sync_ocr_requests_total.labels(engine=engine_name, status="error").inc()

        duration = time.time() - start_time

        logger.error(
            "sync_ocr_request_failed",
            correlation_id=correlation_id,
            engine=engine_name,
            duration_seconds=duration,
            error=str(e),
            error_type=type(e).__name__,
        )

        raise HTTPException(
            status_code=500,
            detail=f"OCR processing failed: {str(e)}",
        )
