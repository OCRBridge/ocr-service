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
