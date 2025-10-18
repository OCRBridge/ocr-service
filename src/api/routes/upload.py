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
    file: UploadFile = File(...),
    lang: Optional[str] = Form(None),
    psm: Optional[int] = Form(None),
    oem: Optional[int] = Form(None),
    dpi: Optional[int] = Form(None),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Upload a document for OCR processing.

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
