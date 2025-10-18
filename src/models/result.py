"""Data models for OCR results."""

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class HOCRResult(BaseModel):
    """Represents the output of OCR processing in HOCR format."""

    job_id: str
    hocr_content: str
    file_path: Path
    file_size: int = Field(..., gt=0)
    page_count: int = Field(..., ge=1)
    word_count: int = Field(..., ge=0)
    confidence_avg: float | None = Field(None, ge=0.0, le=1.0)
    creation_time: datetime = Field(default_factory=datetime.utcnow)
    expiration_time: datetime

    @field_validator("hocr_content")
    @classmethod
    def validate_hocr_xml(cls, v: str) -> str:
        """Validate HOCR content is well-formed XML."""
        try:
            root = ET.fromstring(v)
            # Check for HOCR namespace/class markers
            if not (root.tag in ["html", "{http://www.w3.org/1999/xhtml}html"] or "ocr_page" in v):
                raise ValueError("Not a valid HOCR document")
            return v
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML: {e}")

    @field_validator("file_path")
    @classmethod
    def validate_result_path(cls, v: Path) -> Path:
        """Ensure path is within results directory."""
        if not str(v).startswith("/tmp/results/"):
            raise ValueError("Invalid result file path")
        return v

    @property
    def has_bounding_boxes(self) -> bool:
        """Check if HOCR contains bbox coordinates."""
        return "bbox" in self.hocr_content
