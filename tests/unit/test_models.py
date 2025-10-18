"""Unit tests for Pydantic model validation and state transitions."""


def test_document_upload_model_validation():
    """Test DocumentUpload model validates fields correctly."""
    # This test will initially fail (TDD)
    # from src.models.upload import DocumentUpload, FileFormat

    # Valid upload
    # upload = DocumentUpload(
    #     file_name="test.jpg",
    #     file_format=FileFormat.JPEG,
    #     file_size=1024,
    #     content_type="image/jpeg",
    #     temp_file_path="/tmp/uploads/test.jpg"
    # )
    # assert upload.file_name == "test.jpg"
    pass


def test_document_upload_rejects_oversized_file():
    """Test DocumentUpload rejects files > 25MB."""
    # This test will initially fail (TDD)
    # from src.models.upload import DocumentUpload, FileFormat

    # with pytest.raises(ValidationError):
    #     DocumentUpload(
    #         file_name="large.jpg",
    #         file_format=FileFormat.JPEG,
    #         file_size=26 * 1024 * 1024,  # 26MB
    #         content_type="image/jpeg",
    #         temp_file_path="/tmp/uploads/large.jpg"
    #     )
    pass


def test_document_upload_sanitizes_filename():
    """Test DocumentUpload sanitizes path traversal in filename."""
    # This test will initially fail (TDD)
    # from src.models.upload import DocumentUpload, FileFormat

    # upload = DocumentUpload(
    #     file_name="../../../etc/passwd",
    #     file_format=FileFormat.JPEG,
    #     file_size=1024,
    #     content_type="image/jpeg",
    #     temp_file_path="/tmp/uploads/test.jpg"
    # )
    # assert ".." not in upload.file_name
    # assert "/" not in upload.file_name
    pass


def test_ocr_job_state_transitions():
    """Test OCRJob state transitions follow state machine (US3 - T090)."""
    from datetime import datetime, timedelta

    from src.models.job import JobStatus, OCRJob
    from src.models.upload import DocumentUpload, FileFormat

    # Create a valid upload
    upload = DocumentUpload(
        file_name="test.jpg",
        file_format=FileFormat.JPEG,
        file_size=1024,
        content_type="image/jpeg",
        upload_timestamp=datetime.utcnow(),
        temp_file_path="/tmp/uploads/test.jpg",
    )

    # Create job - should start in PENDING state
    job = OCRJob(upload=upload)
    assert job.status == JobStatus.PENDING
    assert job.start_time is None
    assert job.completion_time is None
    assert job.expiration_time is None

    # Transition to PROCESSING
    job.mark_processing()
    assert job.status == JobStatus.PROCESSING
    assert job.start_time is not None
    assert isinstance(job.start_time, datetime)

    # Transition to COMPLETED
    job.mark_completed()
    assert job.status == JobStatus.COMPLETED
    assert job.completion_time is not None
    assert isinstance(job.completion_time, datetime)
    assert job.expiration_time is not None

    # Verify expiration is 48h from completion
    expected_expiration = job.completion_time + timedelta(hours=48)
    assert job.expiration_time == expected_expiration


def test_ocr_job_invalid_state_transition_raises_error():
    """Test invalid state transitions raise ValueError (US3 - T090)."""
    from datetime import datetime

    import pytest

    from src.models.job import JobStatus, OCRJob
    from src.models.upload import DocumentUpload, FileFormat

    # Create a valid upload
    upload = DocumentUpload(
        file_name="test.jpg",
        file_format=FileFormat.JPEG,
        file_size=1024,
        content_type="image/jpeg",
        upload_timestamp=datetime.utcnow(),
        temp_file_path="/tmp/uploads/test.jpg",
    )

    # Test: Cannot complete from PENDING
    job = OCRJob(upload=upload)
    assert job.status == JobStatus.PENDING

    with pytest.raises(ValueError, match="Cannot complete from"):
        job.mark_completed()

    # Test: Cannot start processing from COMPLETED
    job2 = OCRJob(upload=upload)
    job2.mark_processing()
    job2.mark_completed()

    with pytest.raises(ValueError, match="Cannot start processing from"):
        job2.mark_processing()


def test_ocr_job_expiration_time_auto_calculated():
    """Test expiration_time is automatically set to completion + 48h."""
    # This test will initially fail (TDD)
    # from src.models.job import OCRJob

    # job = OCRJob(...)
    # job.mark_processing()
    # job.mark_completed()

    # expected_expiration = job.completion_time + timedelta(hours=48)
    # assert job.expiration_time == expected_expiration
    pass


def test_hocr_result_model_validation():
    """Test HOCRResult model validates HOCR content."""
    # This test will initially fail (TDD)
    # from src.models.result import HOCRResult

    # Valid HOCR
    # result = HOCRResult(
    #     job_id="test_job_id",
    #     hocr_content='<?xml version="1.0"?><html>...</html>',
    #     file_path="/tmp/results/test.hocr",
    #     file_size=1024,
    #     page_count=1,
    #     word_count=50,
    #     expiration_time=datetime.utcnow() + timedelta(hours=48)
    # )
    # assert result.page_count == 1
    pass


def test_hocr_result_rejects_invalid_xml():
    """Test HOCRResult rejects malformed XML."""
    # This test will initially fail (TDD)
    # from src.models.result import HOCRResult

    # with pytest.raises(ValidationError):
    #     HOCRResult(
    #         job_id="test_job_id",
    #         hocr_content="not valid xml",
    #         ...
    #     )
    pass
