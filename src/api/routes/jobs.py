"""Job status and result retrieval endpoints."""

from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from redis import asyncio as aioredis

from src.api.dependencies import get_redis
from src.api.middleware.rate_limit import limiter
from src.models.job import JobStatus
from src.models.responses import ErrorResponse, StatusResponse
from src.services.job_manager import JobManager

router = APIRouter()
logger = structlog.get_logger()


@router.get(
    "/jobs/{job_id}/status",
    response_model=StatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Job not found"},
    },
)
@limiter.limit(f"{100}/minute")  # type: ignore[reportUntypedFunctionDecorator]
async def get_job_status(
    request: Request,
    job_id: str,
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Get processing status for a job.

    Returns job metadata including current status, timestamps, and error details if applicable.
    """
    job_manager = JobManager(redis)

    job = await job_manager.get_job(job_id)

    if not job:
        logger.warning("status_check_job_not_found", job_id=job_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    logger.info("status_checked", job_id=job_id, status=job.status.value)

    return StatusResponse(
        job_id=job.job_id,
        status=job.status,
        upload_time=job.upload.upload_timestamp,
        start_time=job.start_time,
        completion_time=job.completion_time,
        expiration_time=job.expiration_time,
        error_message=job.error_message,
        error_code=job.error_code,
    )


@router.get(
    "/jobs/{job_id}/result",
    responses={
        200: {"content": {"text/html": {}}, "description": "HOCR result"},
        400: {"model": ErrorResponse, "description": "Job not completed"},
        404: {"model": ErrorResponse, "description": "Job or result not found"},
    },
)
@limiter.limit(f"{100}/minute")  # type: ignore[reportUntypedFunctionDecorator]
async def get_job_result(
    request: Request,
    job_id: str,
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Download HOCR result for a completed job.

    Returns HOCR XML file with bounding boxes and text hierarchy.
    """
    job_manager = JobManager(redis)

    # Get job
    job = await job_manager.get_job(job_id)

    if not job:
        logger.warning("result_check_job_not_found", job_id=job_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    # Check job status
    if job.status != JobStatus.COMPLETED:
        logger.warning("result_check_not_completed", job_id=job_id, status=job.status.value)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is {job.status.value}, result not available",
        )

    # Get result path
    result_path_str = await job_manager.get_result_path(job_id)

    if not result_path_str:
        logger.error("result_path_not_found", job_id=job_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result file not found",
        )

    result_path = Path(result_path_str)

    if not result_path.exists():
        logger.error("result_file_missing", job_id=job_id, path=result_path_str)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result file has been deleted or expired",
        )

    logger.info("result_retrieved", job_id=job_id)

    # Return HOCR file
    return FileResponse(
        path=result_path,
        media_type="text/html",
        filename=f"{job_id}.hocr",
    )
