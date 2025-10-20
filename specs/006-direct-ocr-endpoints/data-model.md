# Data Model: Direct OCR Processing Endpoints

**Date**: 2025-10-19
**Phase**: 1 (Design & Contracts)

## Overview

This document defines the data entities, validation rules, and state transitions for synchronous OCR endpoints. These models extend the existing codebase without modifying async endpoint models.

---

## Entity Definitions

### 1. SyncOCRResponse

**Purpose**: Represents the successful response from a synchronous OCR processing request.

**Location**: `src/models/responses.py` (new model in existing file)

**Attributes**:
- `hocr` (str, required): The hOCR XML output as an escaped string
- `processing_duration_seconds` (float, required): Time taken to process the document
- `engine` (str, required): OCR engine used ("tesseract", "easyocr", or "ocrmac")
- `pages` (int, required): Number of pages processed in the document

**Validation Rules**:
- `hocr`: Must be valid XML string (validation performed by OCR engines, not Pydantic)
- `processing_duration_seconds`: Must be positive float, typically < 30 (timeout limit)
- `engine`: Must be one of ["tesseract", "easyocr", "ocrmac"]
- `pages`: Must be positive integer >= 1

**Pydantic Model**:
```python
from pydantic import BaseModel, Field, field_validator

class SyncOCRResponse(BaseModel):
    """Response model for synchronous OCR processing.

    Returns hOCR content directly in the HTTP response body,
    eliminating the need for job status polling.
    """
    hocr: str = Field(
        ...,
        description="hOCR XML output as escaped string",
        min_length=1
    )
    processing_duration_seconds: float = Field(
        ...,
        description="Processing time in seconds",
        gt=0,
        le=30.0  # Should not exceed timeout
    )
    engine: str = Field(
        ...,
        description="OCR engine used for processing",
        pattern="^(tesseract|easyocr|ocrmac)$"
    )
    pages: int = Field(
        ...,
        description="Number of pages processed",
        ge=1
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "hocr": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Transitional//EN\" \"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd\"><html xmlns=\"http://www.w3.org/1999/xhtml\" xml:lang=\"en\" lang=\"en\"><head><title></title><meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\" /><meta name='ocr-system' content='tesseract 5.3.0' /><meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocrx_word ocrp_wconf'/></head><body><div class='ocr_page' id='page_1' title='bbox 0 0 2480 3508'><div class='ocr_carea' id='carea_1_1' title='bbox 150 200 2330 400'><p class='ocr_par' id='par_1_1' title='bbox 150 200 2330 400'><span class='ocr_line' id='line_1_1' title='bbox 150 200 2330 400; baseline 0 -10'><span class='ocrx_word' id='word_1_1' title='bbox 150 200 450 390; x_wconf 95'>Sample</span> <span class='ocrx_word' id='word_1_2' title='bbox 500 200 800 390; x_wconf 96'>Text</span></span></p></div></div></body></html>",
                "processing_duration_seconds": 2.34,
                "engine": "tesseract",
                "pages": 1
            }
        }
    }
```

**Relationships**:
- Independent entity (no foreign keys)
- NOT persisted to database/Redis (ephemeral)
- Used only for HTTP response serialization

---

### 2. SyncFileValidation

**Purpose**: Represents file size validation constraints for synchronous endpoints.

**Location**: `src/utils/validators.py` (new constants/function in existing file)

**Attributes**:
- `SYNC_MAX_FILE_SIZE_BYTES` (int, constant): Maximum file size for sync processing (5MB = 5,242,880 bytes)
- `SYNC_FILE_SIZE_ERROR_MESSAGE` (str, constant): User-facing error message template

**Validation Rules**:
- File size must be <= 5MB (5,242,880 bytes)
- File must be readable and not corrupted
- File format must be supported (JPEG, PNG, PDF, TIFF) - reuses existing validation

**Implementation**:
```python
# Constants
SYNC_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB

# Validation function
async def validate_sync_file_size(file: UploadFile) -> UploadFile:
    """Validate file size for synchronous OCR endpoints.

    Args:
        file: Uploaded file from FastAPI

    Returns:
        Same file if valid

    Raises:
        HTTPException: 413 Payload Too Large if file exceeds limit
    """
    # Read file to determine size
    contents = await file.read()
    file_size = len(contents)

    # Reset file pointer for subsequent processing
    await file.seek(0)

    if file_size > SYNC_MAX_FILE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        limit_mb = SYNC_MAX_FILE_SIZE_BYTES / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File size ({size_mb:.2f}MB) exceeds {limit_mb}MB limit. "
                   f"Use async endpoints (/upload/{{engine}}) for larger files."
        )

    return file
```

**Relationships**:
- Used as FastAPI dependency for all sync endpoints
- Reuses existing file format validators from same module

---

### 3. SyncTimeoutConfig

**Purpose**: Represents timeout configuration for synchronous processing.

**Location**: `src/config.py` (new settings in existing Settings class)

**Attributes**:
- `sync_timeout_seconds` (int, default=30): Maximum processing time for sync requests
- `sync_max_file_size_mb` (int, default=5): Maximum file size for sync requests

**Validation Rules**:
- `sync_timeout_seconds`: Must be positive integer, typically between 10-60 seconds
- `sync_max_file_size_mb`: Must be positive integer, typically between 1-10 MB

**Pydantic Settings Extension**:
```python
class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ... existing settings ...

    # Synchronous Endpoint Configuration (NEW)
    sync_timeout_seconds: int = Field(
        default=30,
        description="Maximum processing time for synchronous OCR requests",
        ge=5,
        le=60
    )
    sync_max_file_size_mb: int = Field(
        default=5,
        description="Maximum file size in MB for synchronous OCR requests",
        ge=1,
        le=25  # Must be <= max_upload_size_mb
    )

    @property
    def sync_max_file_size_bytes(self) -> int:
        """Convert sync max file size from MB to bytes."""
        return self.sync_max_file_size_mb * 1024 * 1024
```

**Relationships**:
- Read by sync route handlers to configure `asyncio.wait_for()` timeout
- Used by file size validators
- Environment variable overrides: `SYNC_TIMEOUT_SECONDS`, `SYNC_MAX_FILE_SIZE_MB`

---

### 4. Reused Entities (No Changes)

These existing entities are reused by synchronous endpoints without modification:

#### 4.1 TesseractParams
**Location**: `src/models/ocr_params.py`
**Usage**: Request body for `/sync/tesseract` endpoint (identical to async)
**Attributes**: `lang`, `psm`, `oem`, `dpi`, `config` (all optional with defaults)

#### 4.2 EasyOCRParams
**Location**: `src/models/ocr_params.py`
**Usage**: Request body for `/sync/easyocr` endpoint (identical to async)
**Attributes**: `languages`, `gpu`, `paragraph`, `batch_size` (all optional with defaults)

#### 4.3 OcrmacParams
**Location**: `src/models/ocr_params.py`
**Usage**: Request body for `/sync/ocrmac` endpoint (identical to async)
**Attributes**: `recognition_level`, `languages` (all optional with defaults)

#### 4.4 OCRProcessor
**Location**: `src/services/ocr_processor.py`
**Usage**: Core processing logic reused by sync endpoints
**Methods**: `process_document()` - called by both async and sync endpoints

#### 4.5 FileHandler
**Location**: `src/services/file_handler.py`
**Usage**: Temporary file storage and cleanup
**Methods**: `save_upload()`, `cleanup_file()` - used with context manager pattern

---

## State Transitions

### Synchronous Request Lifecycle

Unlike async endpoints (which have job states: PENDING → PROCESSING → COMPLETED/FAILED), synchronous endpoints have **no persistent state**. The entire lifecycle occurs within a single HTTP request/response.

```
┌─────────────────┐
│ Request Arrives │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ Validate File Size      │ ──❌──> HTTP 413 (Payload Too Large)
│ (SYNC_MAX_FILE_SIZE)    │
└────────┬────────────────┘
         │ ✅
         ▼
┌─────────────────────────┐
│ Check Engine Available  │ ──❌──> HTTP 400 (Engine Unavailable)
│ (OCREngineRegistry)     │
└────────┬────────────────┘
         │ ✅
         ▼
┌─────────────────────────┐
│ Save Temporary File     │
│ (FileHandler)           │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Process with Timeout    │ ──❌──> HTTP 408 (Request Timeout)
│ (asyncio.wait_for 30s)  │         + Cleanup temp file
└────────┬────────────────┘
         │ ✅              │
         │                 └──❌──> HTTP 500 (Processing Error)
         ▼                          + Cleanup temp file
┌─────────────────────────┐
│ Cleanup Temporary File  │
│ (FileHandler.cleanup)   │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Return SyncOCRResponse  │ ──✅──> HTTP 200 (Success)
│ with hOCR content       │         + JSON response body
└─────────────────────────┘
```

**Key Differences from Async Endpoints**:
- **No job creation**: No job ID, no Redis state
- **No polling**: Client gets result in single request
- **Immediate cleanup**: Temp files deleted before response sent
- **Timeout enforced**: 30-second hard limit (async has no timeout)
- **Size restricted**: 5MB limit (async allows up to 25MB)

---

## Validation Summary

### Request Validation
| Validation | Location | Error Response |
|-----------|----------|----------------|
| File size <= 5MB | `validate_sync_file_size()` dependency | HTTP 413 Payload Too Large |
| File format supported | Existing `validate_file_format()` | HTTP 415 Unsupported Media Type |
| Engine available | `OCREngineRegistry.is_available()` | HTTP 400 Bad Request |
| Engine params valid | Pydantic model (TesseractParams, etc.) | HTTP 422 Unprocessable Entity |

### Processing Validation
| Validation | Location | Error Response |
|-----------|----------|----------------|
| Processing timeout | `asyncio.wait_for()` in route handler | HTTP 408 Request Timeout |
| OCR engine error | Exception handling in `OCRProcessor` | HTTP 500 Internal Server Error |

### Response Validation
| Validation | Location | Enforced By |
|-----------|----------|-------------|
| hOCR is non-empty | `SyncOCRResponse` model | Pydantic `min_length=1` |
| Duration > 0 | `SyncOCRResponse` model | Pydantic `gt=0` |
| Engine is valid | `SyncOCRResponse` model | Pydantic `pattern` |
| Pages >= 1 | `SyncOCRResponse` model | Pydantic `ge=1` |

---

## Database/Storage

**Important**: Synchronous endpoints do **NOT** persist any data.

| Entity | Storage | Persistence |
|--------|---------|-------------|
| SyncOCRResponse | None | Ephemeral (response body only) |
| Temporary uploaded file | Filesystem (`/tmp/uploads`) | Deleted before response |
| Processing metrics | Prometheus metrics | Aggregated only |
| Request logs | Structured logs (JSON) | Per logging config |

**Contrast with Async Endpoints**:
- Async: Job metadata in Redis (48-hour TTL)
- Async: Result hOCR in filesystem (`/tmp/results`, 48-hour retention)
- Sync: No persistence, immediate response + cleanup

---

## Error Models

All error responses reuse the existing FastAPI error model (no changes needed):

```python
# Existing error response format (FastAPI default)
{
    "detail": "Error message",
    "status_code": 408
}
```

### Sync-Specific Error Messages

| HTTP Status | Error Scenario | Detail Message Template |
|-------------|----------------|-------------------------|
| 408 | Timeout exceeded | `"Processing exceeded {timeout}s timeout. Document may be too complex. Use async endpoints (/upload/{engine}) for large or multi-page documents."` |
| 413 | File too large | `"File size ({size}MB) exceeds {limit}MB limit. Use async endpoints (/upload/{engine}) for larger files."` |
| 400 | Engine unavailable | `"{engine} engine is unavailable. Platform: {platform}. {engine} requires: {requirements}"` |

---

## Metrics Models

**Location**: `src/utils/metrics.py` (extensions to existing metrics module)

### New Prometheus Metrics

```python
from prometheus_client import Counter, Histogram

# Request counter
sync_ocr_requests_total = Counter(
    'sync_ocr_requests_total',
    'Total synchronous OCR requests',
    ['engine', 'status']  # status: success, timeout, error, rejected
)

# Duration histogram
sync_ocr_duration_seconds = Histogram(
    'sync_ocr_duration_seconds',
    'Synchronous OCR processing duration in seconds',
    ['engine'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0]  # Aligned with timeout
)

# Timeout counter
sync_ocr_timeouts_total = Counter(
    'sync_ocr_timeouts_total',
    'Total synchronous OCR timeout errors',
    ['engine']
)

# File size histogram
sync_ocr_file_size_bytes = Histogram(
    'sync_ocr_file_size_bytes',
    'Synchronous OCR uploaded file sizes in bytes',
    ['engine'],
    buckets=[10240, 102400, 524288, 1048576, 2621440, 5242880]  # 10KB to 5MB
)
```

### Metrics Collection Points

1. **Request start**: Increment `sync_ocr_requests_total{engine="...", status="started"}`
2. **File size validated**: Record `sync_ocr_file_size_bytes{engine="..."}`
3. **Processing complete**: Record `sync_ocr_duration_seconds{engine="..."}`
4. **Timeout occurred**: Increment `sync_ocr_timeouts_total{engine="..."}`
5. **Request end**: Update `sync_ocr_requests_total{engine="...", status="success|error|timeout"}`

---

## Summary

### New Models (3)
1. **SyncOCRResponse**: Response body with hOCR content
2. **SyncFileValidation**: File size validation (5MB limit)
3. **SyncTimeoutConfig**: Timeout configuration (30s default)

### Reused Models (5)
1. **TesseractParams**: Request parameters (unchanged)
2. **EasyOCRParams**: Request parameters (unchanged)
3. **OcrmacParams**: Request parameters (unchanged)
4. **OCRProcessor**: Processing logic (unchanged)
5. **FileHandler**: File management (unchanged)

### Key Design Principles
- **No new abstractions**: Reuse existing OCRProcessor and engines
- **No state persistence**: Entirely request/response based
- **Validation-first**: Reject invalid requests before processing
- **Guaranteed cleanup**: Context manager ensures file cleanup
- **Consistent errors**: Same error format as async endpoints
- **Observable**: Prometheus metrics for all operations

---

## Next Steps

With data models defined, proceed to:
1. Generate OpenAPI contracts using these models
2. Create quickstart.md with example requests/responses
3. Update agent context (CLAUDE.md) with new model information
