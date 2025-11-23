"""Job state management service using Redis."""

import json
from datetime import datetime

import structlog
from redis import asyncio as aioredis

from src.models.job import EngineType, ErrorCode, JobStatus, OCRJob
from src.models.ocr_params import OcrmacParams, TesseractParams
from src.models.upload import DocumentUpload, FileFormat

logger = structlog.get_logger()


class JobManager:
    """Manages OCR job state in Redis with TTL support."""

    def __init__(self, redis: aioredis.Redis):
        """Initialize job manager with Redis client."""
        self.redis = redis

    async def create_job(self, job: OCRJob) -> None:
        """
        Create a new job in Redis.

        Args:
            job: OCRJob instance to store
        """
        key = f"job:{job.job_id}:metadata"

        # Serialize job to dict
        job_data = {
            "job_id": job.job_id,
            "status": job.status.value,
            "file_name": job.upload.file_name,
            "file_format": job.upload.file_format.value,
            "file_size": job.upload.file_size,
            "upload_time": job.upload.upload_timestamp.isoformat(),
            "temp_file_path": str(job.upload.temp_file_path),
        }

        # Serialize engine type
        job_data["engine"] = job.engine.value

        # Serialize engine-specific parameters
        if job.engine_params:
            job_data["engine_params"] = job.engine_params.model_dump()
            # Store type for deserialization
            if isinstance(job.engine_params, TesseractParams):
                job_data["engine_params_type"] = "tesseract"
            elif isinstance(job.engine_params, OcrmacParams):
                job_data["engine_params_type"] = "ocrmac"

        # Add Tesseract parameters if provided (legacy field for backward compatibility)
        if job.tesseract_params:
            job_data["tesseract_params"] = job.tesseract_params.model_dump()

        # Store in Redis as JSON
        await self.redis.set(key, json.dumps(job_data))

        logger.info("job_created", job_id=job.job_id, status=job.status.value)

    async def get_job(self, job_id: str) -> OCRJob | None:
        """
        Retrieve a job from Redis.

        Args:
            job_id: Job identifier

        Returns:
            OCRJob instance or None if not found
        """
        key = f"job:{job_id}:metadata"
        data = await self.redis.get(key)

        if not data:
            logger.warning("job_not_found", job_id=job_id)
            return None

        job_data = json.loads(data)

        # Reconstruct OCRJob
        upload = DocumentUpload(
            file_name=job_data["file_name"],
            file_format=FileFormat(job_data["file_format"]),
            file_size=job_data["file_size"],
            content_type=job_data["file_format"],
            upload_timestamp=datetime.fromisoformat(job_data["upload_time"]),
            temp_file_path=job_data["temp_file_path"],
        )

        # Reconstruct engine type (default to TESSERACT for backward compatibility)
        engine = EngineType(job_data.get("engine", "tesseract"))

        # Reconstruct engine-specific parameters
        engine_params = None
        if job_data.get("engine_params"):
            params_type = job_data.get("engine_params_type")
            if params_type == "tesseract":
                engine_params = TesseractParams(**job_data["engine_params"])
            elif params_type == "ocrmac":
                engine_params = OcrmacParams(**job_data["engine_params"])

        # Reconstruct Tesseract parameters if present (legacy field for backward compatibility)
        tesseract_params = None
        if job_data.get("tesseract_params"):
            tesseract_params = TesseractParams(**job_data["tesseract_params"])

        job = OCRJob(
            job_id=job_data["job_id"],
            status=JobStatus(job_data["status"]),
            upload=upload,
            engine=engine,
            engine_params=engine_params,
            tesseract_params=tesseract_params,
            start_time=datetime.fromisoformat(job_data["start_time"])
            if job_data.get("start_time")
            else None,
            completion_time=datetime.fromisoformat(job_data["completion_time"])
            if job_data.get("completion_time")
            else None,
            expiration_time=datetime.fromisoformat(job_data["expiration_time"])
            if job_data.get("expiration_time")
            else None,
            error_message=job_data.get("error_message"),
            error_code=ErrorCode(job_data["error_code"]) if job_data.get("error_code") else None,
        )

        return job

    async def update_job(self, job: OCRJob) -> None:
        """
        Update job state in Redis.

        Args:
            job: OCRJob instance with updated state
        """
        key = f"job:{job.job_id}:metadata"

        # Serialize job to dict
        job_data = {
            "job_id": job.job_id,
            "status": job.status.value,
            "file_name": job.upload.file_name,
            "file_format": job.upload.file_format.value,
            "file_size": job.upload.file_size,
            "upload_time": job.upload.upload_timestamp.isoformat(),
            "temp_file_path": str(job.upload.temp_file_path),
        }

        # Serialize engine type
        job_data["engine"] = job.engine.value

        # Serialize engine-specific parameters
        if job.engine_params:
            job_data["engine_params"] = job.engine_params.model_dump()
            # Store type for deserialization
            if isinstance(job.engine_params, TesseractParams):
                job_data["engine_params_type"] = "tesseract"
            elif isinstance(job.engine_params, OcrmacParams):
                job_data["engine_params_type"] = "ocrmac"

        # Add Tesseract parameters if provided (legacy field for backward compatibility)
        if job.tesseract_params:
            job_data["tesseract_params"] = job.tesseract_params.model_dump()

        # Add optional fields
        if job.start_time:
            job_data["start_time"] = job.start_time.isoformat()
        if job.completion_time:
            job_data["completion_time"] = job.completion_time.isoformat()
        if job.expiration_time:
            job_data["expiration_time"] = job.expiration_time.isoformat()
        if job.error_message:
            job_data["error_message"] = job.error_message
        if job.error_code:
            job_data["error_code"] = job.error_code.value

        # Update in Redis
        await self.redis.set(key, json.dumps(job_data))

        # Set TTL if job is completed or failed
        if job.expiration_time:
            ttl_seconds = int((job.expiration_time - datetime.utcnow()).total_seconds())
            if ttl_seconds > 0:
                await self.redis.expire(key, ttl_seconds)

        logger.info("job_updated", job_id=job.job_id, status=job.status.value)

    async def save_result_path(self, job_id: str, result_path: str) -> None:
        """
        Save result file path for a job.

        Args:
            job_id: Job identifier
            result_path: Path to HOCR result file
        """
        key = f"job:{job_id}:result"
        await self.redis.set(key, result_path)

        # Set same TTL as job metadata
        metadata_key = f"job:{job_id}:metadata"
        ttl = await self.redis.ttl(metadata_key)
        if ttl > 0:
            await self.redis.expire(key, ttl)

        logger.info("result_path_saved", job_id=job_id, path=result_path)

    async def get_result_path(self, job_id: str) -> str | None:
        """
        Get result file path for a job.

        Args:
            job_id: Job identifier

        Returns:
            Path string or None if not found
        """
        key = f"job:{job_id}:result"
        return await self.redis.get(key)
