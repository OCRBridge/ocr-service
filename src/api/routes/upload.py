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

        # Track metrics (US3 - T099)
        metrics.jobs_completed_total.inc()
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

        # Track metrics (US3 - T099)
        metrics.jobs_failed_total.labels(error_code=e.error_code.value).inc()
        metrics.active_jobs.dec()

        logger.error("ocr_processing_failed", job_id=job_id, error=str(e))

        # Clean up temp file
        await file_handler.delete_temp_file(job.upload.temp_file_path)

    except Exception as e:
        # Mark as failed with internal error
        job.mark_failed(ErrorCode.INTERNAL_ERROR, str(e))
        await job_manager.update_job(job)

        # Track metrics (US3 - T099)
        metrics.jobs_failed_total.labels(error_code=ErrorCode.INTERNAL_ERROR.value).inc()
        metrics.active_jobs.dec()

        logger.error("ocr_processing_exception", job_id=job_id, error=str(e))

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
