"""Data models for OCR job management."""

import secrets
from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from src.models.upload import DocumentUpload


class JobStatus(str, Enum):
    """Job processing states."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ErrorCode(str, Enum):
    """Machine-readable error types."""

    INVALID_FORMAT = "invalid_format"
    CORRUPTED_FILE = "corrupted_file"
    OCR_ENGINE_ERROR = "ocr_engine_error"
    TIMEOUT = "timeout"
    MEMORY_LIMIT = "memory_limit"
    INTERNAL_ERROR = "internal_error"


class OCRJob(BaseModel):
    """Represents a processing task for a document with lifecycle tracking."""

    job_id: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    status: JobStatus = JobStatus.PENDING
    upload: DocumentUpload
    start_time: datetime | None = None
    completion_time: datetime | None = None
    expiration_time: datetime | None = None
    error_message: str | None = Field(None, max_length=500)
    error_code: ErrorCode | None = None

    @field_validator("expiration_time", mode="before")
    @classmethod
    def calculate_expiration(cls, v, info):
        """Auto-calculate expiration time as completion + 48h."""
        if v is None and info.data.get("completion_time"):
            return info.data["completion_time"] + timedelta(hours=48)
        return v

    def mark_processing(self):
        """Transition to PROCESSING state."""
        if self.status != JobStatus.PENDING:
            raise ValueError(f"Cannot start processing from {self.status} state")
        self.status = JobStatus.PROCESSING
        self.start_time = datetime.utcnow()

    def mark_completed(self):
        """Transition to COMPLETED state."""
        if self.status != JobStatus.PROCESSING:
            raise ValueError(f"Cannot complete from {self.status} state")
        self.status = JobStatus.COMPLETED
        self.completion_time = datetime.utcnow()
        self.expiration_time = self.completion_time + timedelta(hours=48)

    def mark_failed(self, error_code: ErrorCode, error_message: str):
        """Transition to FAILED state."""
        if self.status not in [JobStatus.PENDING, JobStatus.PROCESSING]:
            raise ValueError(f"Cannot fail from {self.status} state")
        self.status = JobStatus.FAILED
        self.completion_time = datetime.utcnow()
        self.expiration_time = self.completion_time + timedelta(hours=48)
        self.error_code = error_code
        self.error_message = error_message[:500]  # Truncate if too long
