"""Upload endpoint for document submission."""

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from redis import asyncio as aioredis

from src.api.dependencies import get_redis
from src.api.middleware.rate_limit import limiter
from src.models.job import ErrorCode, OCRJob
from src.models.responses import ErrorResponse, UploadResponse
from src.services.file_handler import FileHandler
from src.services.job_manager import JobManager
from src.services.ocr_processor import OCRProcessor, OCRProcessorError
from src.utils.validators import FileTooLargeError, UnsupportedFormatError

router = APIRouter()
logger = structlog.get_logger()


async def process_ocr_task(job_id: str, redis: aioredis.Redis):
    """
    Background task to process OCR for uploaded document.

    Args:
        job_id: Job identifier
        redis: Redis client
    """
    job_manager = JobManager(redis)
    file_handler = FileHandler()
    ocr_processor = OCRProcessor()

    try:
        # Get job
        job = await job_manager.get_job(job_id)
        if not job:
            logger.error("job_not_found_in_background", job_id=job_id)
            return

        # Mark as processing
        job.mark_processing()
        await job_manager.update_job(job)

        logger.info("ocr_processing_started", job_id=job_id)

        # Process document
        hocr_content = await ocr_processor.process_document(
            job.upload.temp_file_path,
            job.upload.file_format
        )

        # Save result
        result_path = await file_handler.save_result(job_id, hocr_content)
        await job_manager.save_result_path(job_id, str(result_path))

        # Mark as completed
        job.mark_completed()
        await job_manager.update_job(job)

        # Clean up temp upload file
        await file_handler.delete_temp_file(job.upload.temp_file_path)

        logger.info("ocr_processing_completed", job_id=job_id)

    except OCRProcessorError as e:
        # Mark as failed
        job.mark_failed(e.error_code, str(e))
        await job_manager.update_job(job)

        logger.error("ocr_processing_failed", job_id=job_id, error=str(e))

        # Clean up temp file
        await file_handler.delete_temp_file(job.upload.temp_file_path)

    except Exception as e:
        # Mark as failed with internal error
        job.mark_failed(ErrorCode.INTERNAL_ERROR, str(e))
        await job_manager.update_job(job)

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
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
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
        # Save uploaded file
        upload = await file_handler.save_upload(file)

        # Create job
        job = OCRJob(upload=upload)
        await job_manager.create_job(job)

        # Schedule background OCR processing
        background_tasks.add_task(process_ocr_task, job.job_id, redis)

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
