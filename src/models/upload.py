"""Data models for document uploads."""

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class FileFormat(str, Enum):
    """Supported file formats for OCR processing."""

    JPEG = "image/jpeg"
    PNG = "image/png"
    PDF = "application/pdf"
    TIFF = "image/tiff"


class DocumentUpload(BaseModel):
    """Represents a file submitted by a user for OCR processing."""

    file_name: str = Field(..., max_length=255)
    file_format: FileFormat
    file_size: int = Field(..., gt=0, le=26214400)  # 25MB in bytes
    content_type: str
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    temp_file_path: Path

    @field_validator("file_name")
    @classmethod
    def sanitize_filename(cls, v: str) -> str:
        """Remove path traversal attempts from filename."""
        return Path(v).name

    @field_validator("temp_file_path")
    @classmethod
    def validate_temp_path(cls, v: Path) -> Path:
        """Ensure path is within temp directory."""
        path_str = str(v)
        if not path_str.startswith("/tmp/uploads/"):
            raise ValueError("Invalid temp file path")
        return v
