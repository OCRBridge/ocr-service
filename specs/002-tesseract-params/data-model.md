# Data Model: Configurable Tesseract OCR Parameters

**Feature**: 002-tesseract-params
**Date**: 2025-10-18

## Overview

This document defines the data entities and their relationships for the Tesseract parameter configuration feature. The feature extends existing entities (DocumentUpload, OCRJob) with optional parameter fields and adds new validation entities.

---

## Entity Definitions

### 1. TesseractParams (New)

**Purpose**: Encapsulates OCR configuration parameters for validation and processing.

**Attributes**:

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `lang` | `Optional[str]` | No | `None` | Pattern: `^[a-z]{3}(\+[a-z]{3})*$`<br>Max 5 languages<br>Must be installed | Language code(s) for OCR (e.g., "eng", "eng+fra") |
| `psm` | `Optional[Literal[0..13]]` | No | `None` | Integer 0-13 | Page segmentation mode |
| `oem` | `Optional[int]` | No | `None` | Integer 0-3 | OCR engine mode (0=Legacy, 1=LSTM, 2=Both, 3=Default) |
| `dpi` | `Optional[int]` | No | `None` | Integer 70-2400 | Image resolution for processing |

**Validation Rules**:
1. If `lang` provided: Must match pattern, each code must be installed, max 5 languages
2. If `psm` provided: Must be 0-13 (Literal type ensures this)
3. If `oem` provided: Must be 0-3
4. If `dpi` provided: Must be 70-2400
5. All fields optional - `None` means use Tesseract defaults

**Relationships**:
- Embedded in `DocumentUpload` (request)
- Embedded in `OCRJob` (metadata)

**Pydantic Implementation**:
```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal

class TesseractParams(BaseModel):
    """OCR configuration parameters with validation."""

    lang: Optional[str] = Field(
        default=None,
        pattern=r'^[a-z]{3}(\+[a-z]{3})*$',
        description="Language code(s): 'eng', 'fra', 'eng+fra' (max 5)",
        examples=["eng", "eng+fra", "eng+fra+deu"]
    )

    psm: Optional[Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]] = Field(
        default=None,
        description="Page segmentation mode (0-13)"
    )

    oem: Optional[int] = Field(
        default=None,
        ge=0,
        le=3,
        description="OCR Engine mode: 0=Legacy, 1=LSTM, 2=Both, 3=Default"
    )

    dpi: Optional[int] = Field(
        default=None,
        ge=70,
        le=2400,
        description="Image DPI (70-2400, typical: 300)"
    )

    @field_validator('lang', mode='after')
    @classmethod
    def validate_language(cls, v: Optional[str]) -> Optional[str]:
        """Validate language count and availability."""
        if v is None:
            return v

        # Max 5 languages
        langs = v.split('+')
        if len(langs) > 5:
            raise ValueError(f"Maximum 5 languages allowed, got {len(langs)}")

        # Check installed (cached)
        from src.utils.validators import get_installed_languages
        installed = get_installed_languages()
        invalid = [lang for lang in langs if lang not in installed]

        if invalid:
            available_sample = ', '.join(sorted(installed)[:10])
            raise ValueError(
                f"Language(s) not installed: {', '.join(invalid)}. "
                f"Available: {available_sample}..."
            )

        return v
```

---

### 2. DocumentUpload (Extended)

**Purpose**: Request model for document upload with optional OCR parameters.

**Changes**:
- Add optional parameter fields from TesseractParams
- Maintain backward compatibility (all new fields optional)

**Attributes** (New/Modified):

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `file` | `UploadFile` | Yes | - | **Existing**: Document file to process |
| `lang` | `Optional[str]` | No | `None` | **New**: Language code(s) |
| `psm` | `Optional[int]` | No | `None` | **New**: Page segmentation mode |
| `oem` | `Optional[int]` | No | `None` | **New**: OCR engine mode |
| `dpi` | `Optional[int]` | No | `None` | **New**: Image DPI |

**Validation Rules**:
- Inherits TesseractParams validation via composition or field reuse
- File validation remains unchanged (format, size limits)

**Pydantic Implementation**:
```python
from fastapi import UploadFile, File, Form
from typing import Optional, Annotated

class DocumentUploadRequest(BaseModel):
    """Document upload with optional Tesseract parameters."""

    # Existing field
    file: UploadFile

    # New optional parameters
    lang: Optional[str] = None
    psm: Optional[int] = None
    oem: Optional[int] = None
    dpi: Optional[int] = None

    def to_tesseract_params(self) -> TesseractParams:
        """Convert to TesseractParams for validation."""
        return TesseractParams(
            lang=self.lang,
            psm=self.psm,
            oem=self.oem,
            dpi=self.dpi
        )

# FastAPI endpoint signature
async def upload_document(
    file: Annotated[UploadFile, File(description="Document file")],
    lang: Annotated[Optional[str], Form()] = None,
    psm: Annotated[Optional[int], Form()] = None,
    oem: Annotated[Optional[int], Form()] = None,
    dpi: Annotated[Optional[int], Form()] = None,
) -> JobResponse:
    # Validate parameters
    params = TesseractParams(lang=lang, psm=psm, oem=oem, dpi=dpi)
    ...
```

---

### 3. OCRJob (Extended)

**Purpose**: Represents an OCR processing job with full context for reproducibility.

**Changes**:
- Add `parameters` field containing TesseractParams
- Store for reproducibility and debugging

**Attributes** (New/Modified):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `job_id` | `str` | Yes | **Existing**: Unique job identifier (UUID) |
| `status` | `JobStatus` | Yes | **Existing**: Job state (pending, processing, completed, failed) |
| `file_path` | `Path` | Yes | **Existing**: Temporary file location |
| `parameters` | `dict` | Yes | **New**: Tesseract parameters used for this job |
| `created_at` | `datetime` | Yes | **Existing**: Job creation timestamp |
| `updated_at` | `datetime` | Yes | **Existing**: Last update timestamp |

**Parameters Dict Structure**:
```python
{
    "lang": "eng+fra",  # or None
    "psm": 6,           # or None
    "oem": 1,           # or None
    "dpi": 300          # or None
}
```

**Pydantic Implementation**:
```python
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path
from typing import Optional

class OCRJob(BaseModel):
    """OCR job with processing parameters."""

    job_id: str
    status: str  # "pending", "processing", "completed", "failed"
    file_path: Path
    parameters: dict  # Tesseract parameters
    created_at: datetime
    updated_at: datetime
    result_path: Optional[Path] = None
    error: Optional[str] = None
```

**Redis Storage Format**:
```python
# Key: job:{job_id}
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "processing",
    "file_path": "/tmp/uploads/550e8400-e29b-41d4-a716-446655440000.jpg",
    "parameters": {
        "lang": "eng+fra",
        "psm": 6,
        "oem": 1,
        "dpi": 300
    },
    "created_at": "2025-10-18T14:23:45.123Z",
    "updated_at": "2025-10-18T14:23:46.789Z"
}
```

---

### 4. ParameterValidationError (New)

**Purpose**: Structured error information for parameter validation failures.

**Attributes**:

| Field | Type | Description |
|-------|------|-------------|
| `field` | `str` | Parameter name that failed validation |
| `message` | `str` | Human-readable error message |
| `type` | `str` | Error type (e.g., "value_error", "pattern_mismatch") |
| `input` | `Any` | The invalid input value provided |
| `context` | `Optional[dict]` | Additional context (e.g., available options) |

**Pydantic Implementation**:
```python
from pydantic import BaseModel
from typing import Any, Optional

class ParameterValidationError(BaseModel):
    """Validation error details."""

    field: str
    message: str
    type: str
    input: Any
    context: Optional[dict] = None

class ValidationErrorResponse(BaseModel):
    """API error response for validation failures."""

    detail: list[ParameterValidationError]
```

**Example Response**:
```json
{
  "detail": [
    {
      "field": "lang",
      "message": "Language(s) not installed: xyz. Available: ara, chi_sim, deu, eng, fra...",
      "type": "value_error",
      "input": "eng+xyz",
      "context": {
        "available": ["ara", "chi_sim", "deu", "eng", "fra", "hin", "ita", "jpn", "por", "rus"]
      }
    }
  ]
}
```

---

### 5. TesseractConfig (Service Layer)

**Purpose**: Internal configuration builder for pytesseract calls.

**Attributes**:

| Field | Type | Description |
|-------|------|-------------|
| `lang` | `str` | Resolved language (never None, defaults to 'eng') |
| `config_string` | `str` | Tesseract CLI config (e.g., "--psm 6 --oem 1 --dpi 300") |

**Not a Pydantic model** - simple dataclass or tuple:

```python
from dataclasses import dataclass

@dataclass
class TesseractConfig:
    """Resolved Tesseract configuration for processing."""

    lang: str                # Never None, defaults to 'eng'
    config_string: str       # CLI config string

def build_tesseract_config(params: TesseractParams) -> TesseractConfig:
    """Build config from validated parameters."""
    # Default language to English if not specified
    lang = params.lang or 'eng'

    # Build config string from non-None parameters
    config_parts = []
    if params.psm is not None:
        config_parts.append(f'--psm {params.psm}')
    if params.oem is not None:
        config_parts.append(f'--oem {params.oem}')
    if params.dpi is not None:
        config_parts.append(f'--dpi {params.dpi}')

    config_string = ' '.join(config_parts)

    return TesseractConfig(lang=lang, config_string=config_string)
```

---

## Entity Relationships

```
┌─────────────────────┐
│ DocumentUpload      │
│ (API Request)       │
│ ─────────────────   │
│ - file              │
│ - lang?             │
│ - psm?              │
│ - oem?              │
│ - dpi?              │
└──────────┬──────────┘
           │ validates to
           ▼
┌─────────────────────┐
│ TesseractParams     │
│ (Validation Model)  │
│ ─────────────────   │
│ - lang?             │
│ - psm?              │
│ - oem?              │
│ - dpi?              │
└──────────┬──────────┘
           │ stored in
           ▼
┌─────────────────────┐
│ OCRJob              │
│ (Job State)         │
│ ─────────────────   │
│ - job_id            │
│ - status            │
│ - parameters        │◄────┐
│ - file_path         │     │
│ - created_at        │     │ reproduces with
│ - updated_at        │     │
└──────────┬──────────┘     │
           │ processed by   │
           ▼                │
┌─────────────────────┐     │
│ TesseractConfig     │─────┘
│ (Service Config)    │
│ ─────────────────   │
│ - lang (resolved)   │
│ - config_string     │
└─────────────────────┘
```

---

## State Transitions

### Job Lifecycle with Parameters

```
[User Upload] + [Parameters]
    │
    ▼
[Validate Parameters] ────► [Validation Error] ──► HTTP 400
    │ (lang, psm, oem, dpi)
    │
    ▼ [PASS]
[Create Job]
    │ status: "pending"
    │ parameters: stored
    │
    ▼
[Process OCR]
    │ status: "processing"
    │ applies parameters to Tesseract
    │
    ├──► [Success] ──► status: "completed"
    │                  result: HOCR output
    │
    └──► [Failure] ──► status: "failed"
                       error: details
```

---

## Validation Flow

### Parameter Validation Sequence

```
1. Type Validation (Pydantic Field)
   ├─ lang: str matches pattern?
   ├─ psm: Literal[0..13]?
   ├─ oem: 0 <= int <= 3?
   └─ dpi: 70 <= int <= 2400?
        │
        ▼ [PASS]
2. Business Rules (field_validator)
   ├─ lang: count <= 5?
   ├─ lang: all codes installed?
   └─ (no additional rules for psm/oem/dpi)
        │
        ▼ [PASS]
3. Configuration Build
   ├─ Resolve defaults (None → Tesseract defaults)
   ├─ Build config string
   └─ Return TesseractConfig
```

---

## Data Persistence

### Redis Schema

**Job State** (key: `job:{uuid}`):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "file_path": "/tmp/uploads/550e8400.jpg",
  "parameters": {
    "lang": "eng+fra",
    "psm": 6,
    "oem": 1,
    "dpi": 300
  },
  "created_at": "2025-10-18T14:23:45.123Z",
  "updated_at": "2025-10-18T14:23:46.789Z",
  "result_path": null,
  "error": null
}
```

**TTL**: 3600 seconds (1 hour) - same as existing jobs

### Filesystem

**Temporary Files** (no changes):
- Uploaded files: `/tmp/uploads/{job_id}.{ext}`
- HOCR results: `/tmp/results/{job_id}.hocr`

**Cleanup** (no changes):
- Files deleted after job completion/expiry
- Parameters not stored on filesystem, only in Redis

---

## Logging Schema

### Structured Log Entry

```json
{
  "event": "ocr_processing_started",
  "timestamp": "2025-10-18T14:23:45.123Z",
  "level": "info",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "parameters": {
    "lang": "eng+fra",
    "psm": 6,
    "oem": 1,
    "dpi": 300
  },
  "file_format": "jpeg",
  "file_size_bytes": 2458240
}
```

**Log Events**:
- `ocr_parameter_validation_started` - Before validation
- `ocr_parameter_validation_failed` - Validation error details
- `ocr_parameter_validation_succeeded` - Validated parameters
- `ocr_processing_started` - Processing begins with parameters
- `ocr_processing_completed` - Success with parameters
- `ocr_processing_failed` - Failure with parameters

---

## Backward Compatibility

### Data Model Migration

**Before** (Current):
```python
# Upload endpoint
async def upload(file: UploadFile) -> JobResponse:
    ...

# OCR processing
def process_ocr(image_path: Path) -> str:
    lang = config.tesseract_lang  # 'eng' from config
    config_str = f"--psm {config.tesseract_psm} --oem {config.tesseract_oem}"
    ...
```

**After** (With Parameters):
```python
# Upload endpoint
async def upload(
    file: UploadFile,
    lang: Optional[str] = None,
    psm: Optional[int] = None,
    oem: Optional[int] = None,
    dpi: Optional[int] = None
) -> JobResponse:
    params = TesseractParams(lang=lang, psm=psm, oem=oem, dpi=dpi)
    ...

# OCR processing
def process_ocr(image_path: Path, params: TesseractParams) -> str:
    config = build_tesseract_config(params)
    # config.lang defaults to 'eng' if params.lang is None
    # config.config_string includes only specified parameters
    ...
```

**Migration Strategy**:
- All new fields are optional
- Default behavior (no parameters) matches current behavior
- Existing clients continue to work without changes

---

## Example Usage Scenarios

### Scenario 1: Default Behavior (Existing Clients)

**Request**:
```http
POST /api/v1/upload
Content-Type: multipart/form-data

file=@document.jpg
```

**Parameters**:
```python
TesseractParams(lang=None, psm=None, oem=None, dpi=None)
```

**Resolved Config**:
```python
TesseractConfig(
    lang='eng',           # Default
    config_string=''      # Tesseract uses defaults
)
```

### Scenario 2: French Document

**Request**:
```http
POST /api/v1/upload
Content-Type: multipart/form-data

file=@document.jpg
lang=fra
```

**Parameters**:
```python
TesseractParams(lang='fra', psm=None, oem=None, dpi=None)
```

**Resolved Config**:
```python
TesseractConfig(
    lang='fra',
    config_string=''
)
```

### Scenario 3: Invoice with Optimal Settings

**Request**:
```http
POST /api/v1/upload
Content-Type: multipart/form-data

file=@invoice.jpg
lang=eng
psm=6
oem=1
dpi=300
```

**Parameters**:
```python
TesseractParams(lang='eng', psm=6, oem=1, dpi=300)
```

**Resolved Config**:
```python
TesseractConfig(
    lang='eng',
    config_string='--psm 6 --oem 1 --dpi 300'
)
```

### Scenario 4: Validation Error

**Request**:
```http
POST /api/v1/upload
Content-Type: multipart/form-data

file=@document.jpg
lang=eng+xyz
psm=99
```

**Response**:
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "detail": [
    {
      "field": "lang",
      "message": "Language(s) not installed: xyz. Available: ara, chi_sim, deu, eng, fra...",
      "type": "value_error",
      "input": "eng+xyz"
    },
    {
      "field": "psm",
      "message": "Input should be 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 or 13",
      "type": "literal_error",
      "input": 99
    }
  ]
}
```

---

## Summary

**New Entities**:
- `TesseractParams` - Validation model for OCR parameters
- `ParameterValidationError` - Structured error response
- `TesseractConfig` - Internal config builder

**Extended Entities**:
- `DocumentUpload` - Add optional parameter fields
- `OCRJob` - Add `parameters` dict field

**Key Design Principles**:
1. All parameters are optional (backward compatibility)
2. Validation happens at API boundary (fail fast)
3. Parameters stored in job state (reproducibility)
4. Defaults resolved in service layer (separation of concerns)
5. Structured errors guide users to correct usage
