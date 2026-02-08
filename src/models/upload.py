"""Upload models for file handling."""

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class FileFormat(str, Enum):
    """Supported file formats with their MIME types."""

    JPEG = "image/jpeg"
    PNG = "image/png"
    PDF = "application/pdf"
    TIFF = "image/tiff"

    @property
    def extension(self) -> str:
        """Get file extension for the format."""
        extensions = {
            FileFormat.JPEG: ".jpg",
            FileFormat.PNG: ".png",
            FileFormat.PDF: ".pdf",
            FileFormat.TIFF: ".tiff",
        }
        return extensions[self]


class DocumentUpload(BaseModel):
    """Model representing an uploaded document."""

    file_name: str = Field(..., description="Original filename")
    file_format: FileFormat = Field(..., description="Detected file format")
    file_size: int = Field(..., description="File size in bytes", gt=0)
    content_type: str = Field(..., description="MIME type")
    temp_file_path: Path = Field(..., description="Path to temporary file")

    model_config = {
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "file_name": "document.pdf",
                "file_format": "application/pdf",
                "file_size": 1024000,
                "content_type": "application/pdf",
                "temp_file_path": "/tmp/uploads/abc-123.pdf",
            }
        },
    }
