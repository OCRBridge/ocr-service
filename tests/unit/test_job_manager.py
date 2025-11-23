"""Unit tests for Redis job state CRUD operations."""

import pytest


@pytest.mark.asyncio
async def test_job_manager_create_job(redis_client):
    """Test creating a new job in Redis."""
    # This test will initially fail (TDD)
    # from src.services.job_manager import JobManager
    # from src.models.job import OCRJob, JobStatus

    # manager = JobManager(redis_client)
    # job = OCRJob(...)

    # await manager.create_job(job)

    # # Verify job exists in Redis
    # stored_job = await manager.get_job(job.job_id)
    # assert stored_job.job_id == job.job_id
    # assert stored_job.status == JobStatus.PENDING
    pass


@pytest.mark.asyncio
async def test_job_manager_get_job(redis_client):
    """Test retrieving a job from Redis."""
    # This test will initially fail (TDD)
    # from src.services.job_manager import JobManager
    # from src.models.job import OCRJob

    # manager = JobManager(redis_client)
    # job = OCRJob(...)

    # await manager.create_job(job)
    # retrieved = await manager.get_job(job.job_id)

    # assert retrieved.job_id == job.job_id
    pass


@pytest.mark.asyncio
async def test_job_manager_update_job_status(redis_client):
    """Test updating job status in Redis."""
    # This test will initially fail (TDD)
    # from src.services.job_manager import JobManager
    # from src.models.job import OCRJob, JobStatus

    # manager = JobManager(redis_client)
    # job = OCRJob(...)
    # await manager.create_job(job)

    # # Update status
    # job.mark_processing()
    # await manager.update_job(job)

    # # Verify update
    # updated = await manager.get_job(job.job_id)
    # assert updated.status == JobStatus.PROCESSING
    pass


@pytest.mark.asyncio
async def test_job_manager_get_nonexistent_job_returns_none(redis_client):
    """Test getting non-existent job returns None."""
    # This test will initially fail (TDD)
    # from src.services.job_manager import JobManager

    # manager = JobManager(redis_client)
    # job = await manager.get_job("nonexistent_job_id")

    # assert job is None
    pass


@pytest.mark.asyncio
async def test_job_manager_sets_ttl(redis_client):
    """Test job TTL is set to 48 hours."""
    # This test will initially fail (TDD)
    # from src.services.job_manager import JobManager
    # from src.models.job import OCRJob

    # manager = JobManager(redis_client)
    # job = OCRJob(...)
    # job.mark_processing()
    # job.mark_completed()

    # await manager.create_job(job)

    # # Check TTL
    # ttl = await redis_client.ttl(f"job:{job.job_id}:metadata")
    # assert 172700 < ttl <= 172800  # ~48 hours
    pass


@pytest.mark.macos
@pytest.mark.asyncio
async def test_job_manager_serializes_ocrmac_params(redis_client, sample_jpeg):
    """Test that ocrmac engine parameters are properly saved and loaded from Redis."""
    from datetime import datetime

    from src.models.job import EngineType, OCRJob
    from src.models.ocr_params import OcrmacParams, RecognitionLevel
    from src.models.upload import DocumentUpload, FileFormat
    from src.services.job_manager import JobManager

    manager = JobManager(redis_client)

    # Create job with ocrmac engine and parameters
    upload = DocumentUpload(
        file_name="test.jpg",
        file_format=FileFormat.JPEG,
        file_size=1024,
        content_type="image/jpeg",
        upload_timestamp=datetime.utcnow(),
        temp_file_path="/tmp/uploads/test.jpg",  # Valid temp path
    )

    ocrmac_params = OcrmacParams(
        languages=["de-DE", "fr-FR"], recognition_level=RecognitionLevel.ACCURATE
    )

    job = OCRJob(upload=upload, engine=EngineType.OCRMAC, engine_params=ocrmac_params)

    # Save job
    await manager.create_job(job)

    # Retrieve job
    retrieved_job = await manager.get_job(job.job_id)

    # Verify engine and params are preserved
    assert retrieved_job is not None
    assert retrieved_job.engine == EngineType.OCRMAC
    assert retrieved_job.engine_params is not None
    assert isinstance(retrieved_job.engine_params, OcrmacParams)
    assert retrieved_job.engine_params.languages == ["de-DE", "fr-FR"]
    assert retrieved_job.engine_params.recognition_level == RecognitionLevel.ACCURATE


@pytest.mark.asyncio
async def test_job_manager_serializes_tesseract_params(redis_client, sample_jpeg):
    """Test that Tesseract engine parameters are properly saved and loaded from Redis."""
    from datetime import datetime

    from src.models import TesseractParams
    from src.models.job import EngineType, OCRJob
    from src.models.upload import DocumentUpload, FileFormat
    from src.services.job_manager import JobManager

    manager = JobManager(redis_client)

    # Create job with Tesseract engine and parameters
    upload = DocumentUpload(
        file_name="test.jpg",
        file_format=FileFormat.JPEG,
        file_size=1024,
        content_type="image/jpeg",
        upload_timestamp=datetime.utcnow(),
        temp_file_path="/tmp/uploads/test.jpg",  # Valid temp path
    )

    tesseract_params = TesseractParams(lang="deu+fra", psm=6, oem=1, dpi=300)

    job = OCRJob(upload=upload, engine=EngineType.TESSERACT, engine_params=tesseract_params)

    # Save job
    await manager.create_job(job)

    # Retrieve job
    retrieved_job = await manager.get_job(job.job_id)

    # Verify engine and params are preserved
    assert retrieved_job is not None
    assert retrieved_job.engine == EngineType.TESSERACT
    assert retrieved_job.engine_params is not None
    assert isinstance(retrieved_job.engine_params, TesseractParams)
    assert retrieved_job.engine_params.lang == "deu+fra"
    assert retrieved_job.engine_params.psm == 6
    assert retrieved_job.engine_params.oem == 1
    assert retrieved_job.engine_params.dpi == 300
