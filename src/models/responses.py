"""API response models."""

import xml.etree.ElementTree as ET

from pydantic import BaseModel, Field, field_validator


class ErrorResponse(BaseModel):
    """Standard error response model for API errors.

    Used in OpenAPI documentation to describe error responses.
    """

    detail: str = Field(
        ...,
        description="Human-readable error message",
    )
    error_code: str | None = Field(
        default=None,
        description="Machine-readable error code for programmatic handling",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "detail": "Invalid parameters. Please check your request.",
                    "error_code": "validation_error",
                },
                {
                    "detail": "Engine 'unknown' not found. Check /v2/ocr/engines for available engines.",
                    "error_code": "not_found",
                },
                {
                    "detail": "OCR engine 'tesseract' is temporarily unavailable due to repeated failures.",
                    "error_code": "service_unavailable",
                },
                {
                    "detail": "OCR processing timeout after 30 seconds.",
                    "error_code": "timeout",
                },
            ]
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

    @field_validator("hocr")
    @classmethod
    def validate_hocr_xml(cls, v: str) -> str:
        """Validate that HOCR content is well-formed XML."""
        try:
            # Basic XML well-formedness check
            ET.fromstring(v)
        except ET.ParseError as e:
            raise ValueError(f"HOCR content is not valid XML: {e}") from e
        return v
    processing_duration_seconds: float = Field(
        ...,
        description="Processing time in seconds",
        gt=0,
        le=60.0,  # Should not exceed max timeout
    )
    engine: str = Field(
        ...,
        description="OCR engine used for processing",
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
