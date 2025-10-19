"""Upload endpoint for document submission."""

import json
from typing import Optional

import structlog
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from pydantic import ValidationError
from redis import asyncio as aioredis

from src.api.dependencies import get_redis
from src.api.middleware.rate_limit import limiter
from src.models import TesseractParams
from src.models.job import ErrorCode, OCRJob
from src.models.responses import ErrorResponse, UploadResponse
from src.services.file_handler import FileHandler
from src.services.job_manager import JobManager
from src.services.ocr_processor import OCRProcessor, OCRProcessorError
from src.utils import metrics
from src.utils.validators import FileTooLargeError, UnsupportedFormatError

router = APIRouter()
logger = structlog.get_logger()


async def process_ocr_task(
    job_id: str, redis: aioredis.Redis, tesseract_params: Optional[TesseractParams] = None
):
    """
    Background task to process OCR for uploaded document.

    Args:
        job_id: Job identifier
        redis: Redis client
        tesseract_params: Optional Tesseract OCR parameters
    """
    job_manager = JobManager(redis)
    file_handler = FileHandler()
    ocr_processor = OCRProcessor(tesseract_params=tesseract_params)

    try:
        # Get job
        job = await job_manager.get_job(job_id)
        if not job:
            logger.error("job_not_found_in_background", job_id=job_id)
            return

        # Mark as processing
        job.mark_processing()
        await job_manager.update_job(job)

        # Track active jobs (US3 - T099)
        metrics.active_jobs.inc()

        # Track queue duration
        queue_duration = (job.start_time - job.upload.upload_timestamp).total_seconds()
        metrics.job_queue_duration_seconds.observe(queue_duration)

        logger.info("ocr_processing_started", job_id=job_id, queue_duration=queue_duration)

        # Process document
        hocr_content = await ocr_processor.process_document(
            job.upload.temp_file_path, job.upload.file_format
        )

        # Save result
        result_path = await file_handler.save_result(job_id, hocr_content)
        await job_manager.save_result_path(job_id, str(result_path))

        # Mark as completed
        job.mark_completed()
        await job_manager.update_job(job)

        # Track metrics (US3 - T099) - default to tesseract for backward compatibility
        metrics.jobs_completed_total.labels(engine="tesseract").inc()
        metrics.active_jobs.dec()

        # Track processing duration
        processing_duration = (job.completion_time - job.start_time).total_seconds()
        metrics.job_processing_duration_seconds.observe(processing_duration)

        # Track total duration
        total_duration = (job.completion_time - job.upload.upload_timestamp).total_seconds()
        metrics.job_total_duration_seconds.observe(total_duration)

        # Clean up temp upload file
        await file_handler.delete_temp_file(job.upload.temp_file_path)

        logger.info(
            "ocr_processing_completed",
            job_id=job_id,
            processing_duration=processing_duration,
            total_duration=total_duration,
        )

    except OCRProcessorError as e:
        # Mark as failed
        job.mark_failed(e.error_code, str(e))
        await job_manager.update_job(job)

        # Track metrics (US3 - T099) - default to tesseract for backward compatibility
        metrics.jobs_failed_total.labels(error_code=e.error_code.value, engine="tesseract").inc()
        metrics.active_jobs.dec()

        logger.error("ocr_processing_failed", job_id=job_id, error=str(e))

        # Clean up temp file
        await file_handler.delete_temp_file(job.upload.temp_file_path)

    except Exception as e:
        # Mark as failed with internal error
        job.mark_failed(ErrorCode.INTERNAL_ERROR, str(e))
        await job_manager.update_job(job)

        # Track metrics (US3 - T099) - default to tesseract for backward compatibility
        metrics.jobs_failed_total.labels(error_code=ErrorCode.INTERNAL_ERROR.value, engine="tesseract").inc()
        metrics.active_jobs.dec()

        logger.error("ocr_processing_exception", job_id=job_id, error=str(e), engine="tesseract")

        # Clean up temp file
        await file_handler.delete_temp_file(job.upload.temp_file_path)


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        413: {"model": ErrorResponse, "description": "File too large"},
        415: {"model": ErrorResponse, "description": "Unsupported format"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(f"{100}/minute")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Document file to process (JPEG, PNG, PDF, TIFF)"),
    lang: Optional[str] = Form(
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
        pattern=r"^[a-z]{3}(\+[a-z]{3})*$",
        examples=["eng", "eng+fra", "fra"],
    ),
    psm: Optional[int] = Form(
        None,
        description=(
            "Page Segmentation Mode (0-13) - controls how Tesseract segments the page. "
            "Common modes: 3=Fully automatic (default, best for most documents), "
            "6=Single uniform block (best for tables/invoices/forms), "
            "7=Single text line (best for single-line fields), "
            "11=Sparse text (best for receipts with scattered text). "
            "All modes: 0=OSD only, 1=Auto with OSD, 2=Auto (no OSD/OCR), "
            "3=Fully auto, 4=Single column, 5=Single vertical block, 6=Single block, "
            "7=Single line, 8=Single word, 9=Single word (circle), 10=Single char, "
            "11=Sparse text, 12=Sparse text with OSD, 13=Raw line. "
            "Default: 3"
        ),
        ge=0,
        le=13,
        examples=[3, 6, 11],
    ),
    oem: Optional[int] = Form(
        None,
        description=(
            "OCR Engine Mode (0-3) - controls which Tesseract engine to use. "
            "0=Legacy engine (faster, lower accuracy), "
            "1=LSTM neural network (recommended - best accuracy), "
            "2=Legacy+LSTM combined (slower), "
            "3=Default (auto-select based on available traineddata). "
            "Recommendation: Use 1 (LSTM) for modern Tesseract 5.x. "
            "Default: 3"
        ),
        ge=0,
        le=3,
        examples=[1, 3],
    ),
    dpi: Optional[int] = Form(
        None,
        description=(
            "Image resolution (dots per inch) for OCR processing. "
            "Overrides missing or incorrect DPI metadata in image files. "
            "Typical values: 150 (low-res scans), 300 (standard scans - most common), "
            "600 (high-quality scans for small text). "
            "Use when: image lacks DPI metadata, incorrect metadata, "
            "or to standardize processing. "
            "Range: 70-2400. "
            "Default: Auto-detect from image metadata or 70"
        ),
        ge=70,
        le=2400,
        examples=[300, 150, 600],
    ),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Upload a document for OCR processing with optional Tesseract configuration.

    **Default Behavior (no parameters):**
    - Language: English (eng)
    - PSM: 3 (Fully automatic page segmentation)
    - OEM: 3 (Default based on available traineddata)
    - DPI: Auto-detect from image metadata or 70

    **Common Use Cases:**
    - French document: lang=fra
    - Invoice/form: lang=eng, psm=6, oem=1, dpi=300
    - Receipt: lang=eng, psm=11, oem=1, dpi=300
    - Multi-language: lang=eng+fra+deu

    Returns job ID for status polling and result retrieval.
    Processing happens asynchronously in the background.
    """
    file_handler = FileHandler()
    job_manager = JobManager(redis)

    try:
        # Validate Tesseract parameters
        try:
            tesseract_params = TesseractParams(lang=lang, psm=psm, oem=oem, dpi=dpi)
        except ValidationError as e:
            logger.warning("parameter_validation_failed", errors=e.errors())
            # Use e.json() for JSON-serializable error format
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=json.loads(e.json()),
            )

        # Save uploaded file
        upload = await file_handler.save_upload(file)

        # Track metrics (US3 - T099)
        metrics.jobs_created_total.inc()
        metrics.document_size_bytes.observe(upload.file_size)

        # Create job with Tesseract parameters
        job = OCRJob(upload=upload, tesseract_params=tesseract_params)
        await job_manager.create_job(job)

        # Schedule background OCR processing
        background_tasks.add_task(process_ocr_task, job.job_id, redis, tesseract_params)

        logger.info(
            "upload_accepted",
            job_id=job.job_id,
            filename=upload.file_name,
            size=upload.file_size,
        )

        return UploadResponse(
            job_id=job.job_id,
            status=job.status,
        )

    except HTTPException:
        # Re-raise HTTP exceptions (including validation errors)
        raise

    except UnsupportedFormatError as e:
        logger.warning("unsupported_format", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(e),
        )

    except FileTooLargeError as e:
        logger.warning("file_too_large", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(e),
        )

    except Exception as e:
        logger.error("upload_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed",
        )


@router.post(
    "/upload/tesseract",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request or engine not available"},
        413: {"model": ErrorResponse, "description": "File too large"},
        415: {"model": ErrorResponse, "description": "Unsupported format"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(f"{100}/minute")
async def upload_document_tesseract(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Document file to process (JPEG, PNG, PDF, TIFF)"),
    lang: Optional[str] = Form(
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
    psm: Optional[int] = Form(
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
    oem: Optional[int] = Form(
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
    dpi: Optional[int] = Form(
        None,
        description=(
            "Image resolution (dots per inch) for OCR processing. "
            "Typical values: 150 (low-res), 300 (standard), 600 (high-quality). "
            "Range: 70-2400. Default: Auto-detect from image metadata or 70"
        ),
        ge=70,
        le=2400,
        examples=[300, 150, 600],
    ),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Upload a document for OCR processing using Tesseract engine.

    **Tesseract Engine Features:**
    - Cross-platform support (Linux, macOS, Windows)
    - Extensive language support (100+ languages)
    - Highly configurable (PSM, OEM, DPI parameters)
    - LSTM neural network for best accuracy (OEM=1)

    **Common Use Cases:**
    - Invoice/form: lang=eng, psm=6, oem=1, dpi=300
    - Receipt: lang=eng, psm=11, oem=1, dpi=300
    - Multi-language: lang=eng+fra+deu

    Returns job ID for status polling and result retrieval.
    """
    from src.services.ocr.registry import EngineRegistry
    from src.models.job import EngineType

    file_handler = FileHandler()
    job_manager = JobManager(redis)
    registry = EngineRegistry()

    try:
        # Check if Tesseract is available
        if not registry.is_available(EngineType.TESSERACT):
            logger.error("tesseract_not_available")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tesseract engine is not available on this server"
            )

        # Validate Tesseract parameters
        try:
            tesseract_params = TesseractParams(lang=lang, psm=psm, oem=oem, dpi=dpi)
        except ValidationError as e:
            logger.warning("parameter_validation_failed", errors=e.errors())
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=json.loads(e.json()),
            )

        # Save uploaded file
        upload = await file_handler.save_upload(file)

        # Track metrics
        metrics.jobs_created_total.inc()
        metrics.document_size_bytes.observe(upload.file_size)

        # Create job with Tesseract engine
        job = OCRJob(
            upload=upload,
            engine=EngineType.TESSERACT,
            engine_params=tesseract_params
        )
        await job_manager.create_job(job)

        # Schedule background OCR processing
        background_tasks.add_task(process_ocr_task, job.job_id, redis, tesseract_params)

        logger.info(
            "upload_accepted",
            job_id=job.job_id,
            filename=upload.file_name,
            size=upload.file_size,
            engine="tesseract"
        )

        return UploadResponse(
            job_id=job.job_id,
            status=job.status,
        )

    except HTTPException:
        raise

    except UnsupportedFormatError as e:
        logger.warning("unsupported_format", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(e),
        )

    except FileTooLargeError as e:
        logger.warning("file_too_large", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(e),
        )

    except Exception as e:
        logger.error("upload_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed",
        )


@router.post(
    "/upload/ocrmac",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request, engine not available, or platform incompatible"},
        413: {"model": ErrorResponse, "description": "File too large"},
        415: {"model": ErrorResponse, "description": "Unsupported format"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(f"{100}/minute")
async def upload_document_ocrmac(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Document file to process (JPEG, PNG, PDF, TIFF)"),
    languages: Optional[list[str]] = Form(
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
    recognition_level: Optional[str] = Form(
        "balanced",
        description=(
            "Recognition level: 'fast' (faster, fewer languages), "
            "'balanced' (default, good speed/accuracy), "
            "'accurate' (slower, more accurate). "
            "Default: balanced"
        ),
        pattern=r"^(fast|balanced|accurate)$",
        examples=["balanced", "fast", "accurate"],
    ),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Upload a document for OCR processing using ocrmac engine (macOS only).

    **ocrmac Engine Features:**
    - macOS-only (requires macOS 10.15+)
    - Native Apple Vision framework integration
    - GPU-accelerated processing
    - Optimized for Apple Silicon
    - Automatic language detection

    **Common Use Cases:**
    - Fast processing: recognition_level=fast
    - Maximum accuracy: recognition_level=accurate
    - Multi-language: languages=["en-US", "fr-FR"]

    Returns job ID for status polling and result retrieval.

    **Platform Requirement:** macOS only (returns HTTP 400 on other platforms)
    """
    from src.services.ocr.registry import EngineRegistry
    from src.models.job import EngineType
    from src.models.ocr_params import OcrmacParams, RecognitionLevel

    file_handler = FileHandler()
    job_manager = JobManager(redis)
    registry = EngineRegistry()

    try:
        # Check platform compatibility
        is_valid, error_msg = registry.validate_platform(EngineType.OCRMAC)
        if not is_valid:
            logger.warning("platform_incompatible", engine="ocrmac", error=error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # Check if ocrmac is available
        if not registry.is_available(EngineType.OCRMAC):
            logger.error("ocrmac_not_available")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ocrmac engine is not available on this server. Install with: pip install ocrmac"
            )

        # Map recognition_level string to enum
        recognition_level_enum = RecognitionLevel(recognition_level) if recognition_level else RecognitionLevel.BALANCED

        # Validate ocrmac parameters
        try:
            ocrmac_params = OcrmacParams(
                languages=languages,
                recognition_level=recognition_level_enum
            )
        except ValidationError as e:
            logger.warning("parameter_validation_failed", errors=e.errors())
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=json.loads(e.json()),
            )

        # Validate languages against engine capabilities
        if languages:
            is_valid, error_msg = registry.validate_languages(EngineType.OCRMAC, languages)
            if not is_valid:
                logger.warning("language_validation_failed", languages=languages, error=error_msg)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )

        # Save uploaded file
        upload = await file_handler.save_upload(file)

        # Track metrics
        metrics.jobs_created_total.inc()
        metrics.document_size_bytes.observe(upload.file_size)

        # Create job with ocrmac engine
        job = OCRJob(
            upload=upload,
            engine=EngineType.OCRMAC,
            engine_params=ocrmac_params
        )
        await job_manager.create_job(job)

        # Schedule background OCR processing (will use new process_ocr_task_v2)
        background_tasks.add_task(process_ocr_task_v2, job.job_id, redis)

        logger.info(
            "upload_accepted",
            job_id=job.job_id,
            filename=upload.file_name,
            size=upload.file_size,
            engine="ocrmac",
            languages=languages,
            recognition_level=recognition_level
        )

        return UploadResponse(
            job_id=job.job_id,
            status=job.status,
        )

    except HTTPException:
        raise

    except UnsupportedFormatError as e:
        logger.warning("unsupported_format", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(e),
        )

    except FileTooLargeError as e:
        logger.warning("file_too_large", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(e),
        )

    except Exception as e:
        logger.error("upload_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed",
        )


@router.post(
    "/upload/easyocr",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request, engine not available, or invalid parameters"},
        413: {"model": ErrorResponse, "description": "File too large"},
        415: {"model": ErrorResponse, "description": "Unsupported format"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(f"{100}/minute")
async def upload_document_easyocr(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Document file to process (JPEG, PNG, PDF, TIFF)"),
    languages: Optional[list[str]] = Form(
        None,
        description=(
            "Language codes for OCR recognition (EasyOCR naming convention). "
            "Use EasyOCR format (e.g., 'en', 'ch_sim', 'ja', 'ko'). "
            "Max 5 languages. Default: ['en'] if not specified. "
            "Examples: ['en'], ['ch_sim', 'en'], ['ja', 'ko', 'en']"
        ),
        examples=[["en"], ["ch_sim", "en"], ["ja"]],
    ),
    text_threshold: Optional[float] = Form(
        None,
        description=(
            "Confidence threshold for text detection (0.0-1.0). "
            "Lower: more text detected (higher recall). Higher: only high-confidence text (higher precision). "
            "Default: 0.7"
        ),
        ge=0.0,
        le=1.0,
        examples=[0.7, 0.8, 0.5],
    ),
    link_threshold: Optional[float] = Form(
        None,
        description=(
            "Threshold for linking text regions (0.0-1.0). "
            "Controls how text boxes are grouped together. "
            "Default: 0.7"
        ),
        ge=0.0,
        le=1.0,
        examples=[0.7, 0.8],
    ),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Upload a document for OCR processing using EasyOCR engine.

    **EasyOCR Engine Features:**
    - Cross-platform support (Linux, macOS, Windows)
    - Deep learning-based recognition with superior multilingual support (80+ languages)
    - Automatic GPU acceleration when CUDA is available
    - Excellent accuracy for Asian languages (Chinese, Japanese, Korean, Thai, etc.)
    - Automatic graceful fallback to CPU if GPU unavailable

    **GPU Behavior:**
    - GPU is automatically detected and used when available
    - No configuration required - the system automatically optimizes for your hardware
    - Falls back to CPU seamlessly if GPU is not available

    **Common Use Cases:**
    - Chinese document: languages=['ch_sim', 'en']
    - Japanese receipt: languages=['ja'], text_threshold=0.8
    - Korean form: languages=['ko', 'en'], text_threshold=0.7

    Returns job ID for status polling and result retrieval.
    """
    from src.services.ocr.registry import EngineRegistry
    from src.models.job import EngineType
    from src.models.ocr_params import EasyOCRParams

    file_handler = FileHandler()
    job_manager = JobManager(redis)
    registry = EngineRegistry()

    try:
        # Check if EasyOCR is available
        if not registry.is_available(EngineType.EASYOCR):
            logger.error("easyocr_not_available")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="EasyOCR engine is not available on this server. Install with: pip install easyocr torch"
            )

        # Validate EasyOCR parameters
        try:
            easyocr_params = EasyOCRParams(
                languages=languages if languages is not None else ["en"],
                text_threshold=text_threshold if text_threshold is not None else 0.7,
                link_threshold=link_threshold if link_threshold is not None else 0.7,
            )
        except ValidationError as e:
            logger.warning("parameter_validation_failed", errors=e.errors())
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=json.loads(e.json()),
            )

        # Validate languages against engine capabilities
        if languages:
            is_valid, error_msg = registry.validate_languages(EngineType.EASYOCR, languages)
            if not is_valid:
                logger.warning("language_validation_failed", languages=languages, error=error_msg)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )

        # Save uploaded file
        upload = await file_handler.save_upload(file)

        # Track metrics
        metrics.jobs_created_total.inc()
        metrics.document_size_bytes.observe(upload.file_size)

        # Create job with EasyOCR engine
        job = OCRJob(
            upload=upload,
            engine=EngineType.EASYOCR,
            engine_params=easyocr_params
        )
        await job_manager.create_job(job)

        # Schedule background OCR processing (will use process_ocr_task_v2)
        background_tasks.add_task(process_ocr_task_v2, job.job_id, redis)

        logger.info(
            "upload_accepted",
            job_id=job.job_id,
            filename=upload.file_name,
            size=upload.file_size,
            engine="easyocr",
            languages=easyocr_params.languages,
            text_threshold=easyocr_params.text_threshold,
            link_threshold=easyocr_params.link_threshold
        )

        return UploadResponse(
            job_id=job.job_id,
            status=job.status,
        )

    except HTTPException:
        raise

    except UnsupportedFormatError as e:
        logger.warning("unsupported_format", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(e),
        )

    except FileTooLargeError as e:
        logger.warning("file_too_large", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(e),
        )

    except Exception as e:
        logger.error("upload_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed",
        )


async def process_ocr_task_v2(job_id: str, redis: aioredis.Redis):
    """
    Background task to process OCR for uploaded document using engine-specific processing.

    This is the new version that supports multiple engines.

    Args:
        job_id: Job identifier
        redis: Redis client
    """
    from src.services.ocr.tesseract import TesseractEngine
    from src.services.ocr.ocrmac import OcrmacEngine
    from src.services.ocr.easyocr import EasyOCREngine
    from src.models.job import EngineType

    job_manager = JobManager(redis)
    file_handler = FileHandler()

    try:
        # Get job
        job = await job_manager.get_job(job_id)
        if not job:
            logger.error("job_not_found_in_background", job_id=job_id)
            return

        # Mark as processing
        job.mark_processing()
        await job_manager.update_job(job)

        # Track active jobs
        metrics.active_jobs.inc()

        # Track queue duration
        queue_duration = (job.start_time - job.upload.upload_timestamp).total_seconds()
        metrics.job_queue_duration_seconds.observe(queue_duration)

        logger.info(
            "ocr_processing_started",
            job_id=job_id,
            engine=job.engine.value,
            queue_duration=queue_duration
        )

        # Select appropriate engine
        if job.engine == EngineType.TESSERACT:
            engine = TesseractEngine()
        elif job.engine == EngineType.OCRMAC:
            engine = OcrmacEngine()
        elif job.engine == EngineType.EASYOCR:
            engine = EasyOCREngine()
        else:
            raise ValueError(f"Unknown engine type: {job.engine}")

        # Process document with engine-specific parameters
        hocr_content = engine.process(job.upload.temp_file_path, job.engine_params)

        # Save result
        result_path = await file_handler.save_result(job_id, hocr_content)
        await job_manager.save_result_path(job_id, str(result_path))

        # Mark as completed
        job.mark_completed()
        await job_manager.update_job(job)

        # Track metrics with engine label
        metrics.jobs_completed_total.labels(engine=job.engine.value).inc()
        metrics.active_jobs.dec()

        # Track processing duration
        processing_duration = (job.completion_time - job.start_time).total_seconds()
        metrics.job_processing_duration_seconds.observe(processing_duration)

        # Track total duration
        total_duration = (job.completion_time - job.upload.upload_timestamp).total_seconds()
        metrics.job_total_duration_seconds.observe(total_duration)

        # Clean up temp upload file
        await file_handler.delete_temp_file(job.upload.temp_file_path)

        logger.info(
            "ocr_processing_completed",
            job_id=job_id,
            engine=job.engine.value,
            processing_duration=processing_duration,
            total_duration=total_duration,
        )

    except Exception as e:
        # Mark as failed with internal error
        job.mark_failed(ErrorCode.INTERNAL_ERROR, str(e))
        await job_manager.update_job(job)

        # Track metrics with engine label
        engine_label = job.engine.value if job else "unknown"
        metrics.jobs_failed_total.labels(
            error_code=ErrorCode.INTERNAL_ERROR.value,
            engine=engine_label
        ).inc()
        metrics.active_jobs.dec()

        logger.error(
            "ocr_processing_exception",
            job_id=job_id,
            engine=engine_label,
            error=str(e)
        )

        # Clean up temp file
        if job:
            await file_handler.delete_temp_file(job.upload.temp_file_path)
