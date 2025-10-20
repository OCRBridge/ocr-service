"""API response models."""

from datetime import datetime

from pydantic import BaseModel, Field

from src.models.job import ErrorCode, JobStatus


class UploadResponse(BaseModel):
    """Response for successful document upload."""

    job_id: str
    status: JobStatus
    message: str = "Upload successful, processing started"

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_id": "Kj4TY2vN8xQz9wR5pL7mH3fC1sD6aB8nE0gU4tV2iX1",
                "status": "pending",
                "message": "Upload successful, processing started",
            }
        }
    }


class StatusResponse(BaseModel):
    """Response for job status check."""

    job_id: str
    status: JobStatus
    upload_time: datetime
    start_time: datetime | None = None
    completion_time: datetime | None = None
    expiration_time: datetime | None = None
    error_message: str | None = None
    error_code: ErrorCode | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_id": "Kj4TY...",
                "status": "completed",
                "upload_time": "2025-10-18T10:00:00Z",
                "start_time": "2025-10-18T10:00:05Z",
                "completion_time": "2025-10-18T10:00:12Z",
                "expiration_time": "2025-10-20T10:00:12Z",
                "error_message": None,
                "error_code": None,
            }
        }
    }


class ErrorResponse(BaseModel):
    """Standard error response format."""

    detail: str
    error_code: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "Unsupported file format. Supported formats: JPEG, PNG, PDF, TIFF",
                "error_code": "invalid_format",
                "timestamp": "2025-10-18T10:00:00Z",
            }
        }
    }


class SyncOCRResponse(BaseModel):
    """Response model for synchronous OCR processing.

    Returns hOCR content directly in the HTTP response body,
    eliminating the need for job status polling.
    """

    hocr: str = Field(
        ...,
        description="hOCR XML output as escaped string",
        min_length=1,
    )
    processing_duration_seconds: float = Field(
        ...,
        description="Processing time in seconds",
        gt=0,
        le=60.0,  # Should not exceed max timeout
    )
    engine: str = Field(
        ...,
        description="OCR engine used for processing",
        pattern="^(tesseract|easyocr|ocrmac)$",
    )
    pages: int = Field(
        ...,
        description="Number of pages processed",
        ge=1,
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "hocr": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Transitional//EN\" \"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd\"><html xmlns=\"http://www.w3.org/1999/xhtml\" xml:lang=\"en\" lang=\"en\"><head><title></title><meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\" /><meta name='ocr-system' content='tesseract 5.3.0' /><meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocrx_word ocrp_wconf'/></head><body><div class='ocr_page' id='page_1' title='bbox 0 0 2480 3508'><div class='ocr_carea' id='carea_1_1' title='bbox 150 200 2330 400'><p class='ocr_par' id='par_1_1' title='bbox 150 200 2330 400'><span class='ocr_line' id='line_1_1' title='bbox 150 200 2330 400; baseline 0 -10'><span class='ocrx_word' id='word_1_1' title='bbox 150 200 450 390; x_wconf 95'>Sample</span> <span class='ocrx_word' id='word_1_2' title='bbox 500 200 800 390; x_wconf 96'>Text</span></span></p></div></div></body></html>",
                "processing_duration_seconds": 2.34,
                "engine": "tesseract",
                "pages": 1,
            }
        }
    }
