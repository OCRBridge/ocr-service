# Data Model: Multi-Engine OCR Support

**Feature**: 003-multi-engine-ocr
**Date**: 2025-10-18

## Overview

This document defines the data entities and their relationships for the multi-engine OCR feature. All models use Pydantic for validation and FastAPI integration.

## Core Entities

### 1. OCR Engine

**Purpose**: Represents an available OCR processing engine with its capabilities.

**Location**: `src/services/ocr/registry.py`

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Set

class EngineType(str, Enum):
    """Supported OCR engine types."""
    TESSERACT = "tesseract"
    OCRMAC = "ocrmac"

@dataclass
class EngineCapabilities:
    """Cached capabilities for an OCR engine."""
    available: bool                       # Whether engine is currently available
    version: Optional[str]                # Engine version (e.g., "5.3.0", "0.1.0")
    supported_languages: Set[str]         # Set of supported language codes
    platform_requirement: Optional[str]   # Required platform (e.g., "darwin" for macOS)
```

**Validation Rules**:
- `available`: Boolean indicating runtime availability after startup detection
- `version`: String version identifier, None if not available
- `supported_languages`: Non-empty set if available, empty set if not
- `platform_requirement`: None for cross-platform engines (Tesseract), "darwin" for macOS-only (ocrmac)

**State Transitions**:
- Set at application startup during engine registry initialization
- Read-only after initialization (cache-only)
- Refreshes on application restart

**Related Entities**: Used by EngineRegistry to validate upload requests

---

### 2. Engine Configuration (Abstract)

**Purpose**: Base type for engine-specific parameter sets.

**Implementations**:
- `TesseractParams` (existing, extended)
- `OcrmacParams` (new)

---

### 3. Tesseract Configuration

**Purpose**: Tesseract-specific OCR parameters.

**Location**: `src/models/upload.py` (existing, no changes needed)

**Schema**:
```python
class TesseractParams(BaseModel):
    """Tesseract OCR engine parameters."""

    lang: Optional[str] = Field(
        None,
        description="Language code(s) in ISO 639-3 format (e.g., eng, fra, deu). Multiple: eng+fra. Max 5.",
        pattern=r"^[a-z_]{3,7}(\+[a-z_]{3,7}){0,4}$"
    )

    psm: Optional[int] = Field(
        None,
        description="Page Segmentation Mode (0-13)",
        ge=0,
        le=13
    )

    oem: Optional[int] = Field(
        None,
        description="OCR Engine Mode (0-3)",
        ge=0,
        le=3
    )

    dpi: Optional[int] = Field(
        None,
        description="Image DPI for processing (70-2400)",
        ge=70,
        le=2400
    )
```

**Validation Rules**:
- `lang`: ISO 639-3 format (3-7 chars to support codes like "chi_sim"), max 5 languages via `+` separator
- `psm`: Integer 0-13 (Tesseract page segmentation modes)
- `oem`: Integer 0-3 (Tesseract engine modes)
- `dpi`: Integer 70-2400 (reasonable DPI range)
- All fields optional (use defaults from settings)

**Defaults** (from `src/config.py`):
- `lang`: "eng" (English)
- `psm`: 3 (Fully automatic page segmentation)
- `oem`: 3 (Default based on available traineddata)
- `dpi`: Auto-detect from image metadata or 70

**Related Entities**: Used in OCRJob, passed to Tesseract processor

---

### 4. ocrmac Configuration

**Purpose**: ocrmac-specific OCR parameters.

**Location**: `src/models/ocr_params.py` (new file)

**Schema**:
```python
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re

class RecognitionLevel(str, Enum):
    """ocrmac recognition level options."""
    FAST = "fast"
    BALANCED = "balanced"
    ACCURATE = "accurate"

class OcrmacParams(BaseModel):
    """ocrmac OCR engine parameters."""

    languages: Optional[list[str]] = Field(
        None,
        description="Language codes in IETF BCP 47 format (e.g., en-US, fr-FR, zh-Hans). Max 5.",
        min_length=1,
        max_length=5,
        examples=[["en-US"], ["en-US", "fr-FR"], ["zh-Hans"]]
    )

    recognition_level: RecognitionLevel = Field(
        RecognitionLevel.BALANCED,
        description="Recognition level: fast (fewer languages, faster), balanced (default), accurate (slower)"
    )

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate IETF BCP 47 language code format."""
        if v is None:
            return v

        if len(v) > 5:
            raise ValueError("Maximum 5 languages allowed")

        # IETF BCP 47 format: language[-Script][-Region]
        # Examples: en, en-US, zh-Hans, zh-Hans-CN
        pattern = r"^[a-z]{2,3}(-[A-Z][a-z]{3})?(-[A-Z]{2})?$"

        for lang in v:
            if not re.match(pattern, lang, re.IGNORECASE):
                raise ValueError(
                    f"Invalid IETF BCP 47 language code: '{lang}'. "
                    f"Expected format: 'en-US', 'fr-FR', 'zh-Hans'"
                )

        return v
```

**Validation Rules**:
- `languages`: List of IETF BCP 47 codes, max 5 languages, case-insensitive validation
- `recognition_level`: Enum value (fast/balanced/accurate)
- Automatic language detection when `languages` is None or empty

**Defaults**:
- `languages`: None (automatic language detection)
- `recognition_level`: "balanced"

**Related Entities**: Used in OCRJob, passed to ocrmac processor

---

### 5. OCR Job (Extended)

**Purpose**: Represents an OCR processing job with engine selection.

**Location**: `src/models/job.py` (extended)

**Schema Extensions**:
```python
from enum import Enum
from typing import Optional, Union
from pydantic import BaseModel, Field
from src.models.upload import DocumentUpload, TesseractParams
from src.models.ocr_params import OcrmacParams

class EngineType(str, Enum):
    """OCR engine types."""
    TESSERACT = "tesseract"
    OCRMAC = "ocrmac"

class OCRJob(BaseModel):
    """OCR processing job."""

    job_id: str
    upload: DocumentUpload
    status: JobStatus
    error_code: Optional[ErrorCode] = None
    error_message: Optional[str] = None

    # NEW: Engine selection
    engine: EngineType = Field(
        default=EngineType.TESSERACT,
        description="OCR engine used for processing"
    )

    # MODIFIED: Engine-specific parameters (union type)
    engine_params: Optional[Union[TesseractParams, OcrmacParams]] = Field(
        None,
        description="Engine-specific processing parameters"
    )

    # Existing fields
    upload_timestamp: datetime
    start_time: Optional[datetime] = None
    completion_time: Optional[datetime] = None
```

**Validation Rules**:
- `engine`: Must be valid EngineType enum value
- `engine_params`: Type must match `engine` value
  - If `engine == TESSERACT`: `engine_params` must be `TesseractParams` or None
  - If `engine == OCRMAC`: `engine_params` must be `OcrmacParams` or None

**State Transitions**:
```
pending -> processing -> completed
pending -> processing -> failed
```

**Field Constraints**:
- `job_id`: Unique identifier (UUID4)
- `status`: Must follow state transition rules
- `error_code` and `error_message`: Set only when `status == failed`
- `engine`: Immutable after job creation (reproducibility)
- `engine_params`: Immutable after job creation (reproducibility)

**Related Entities**:
- Contains `DocumentUpload` (file metadata)
- Contains `TesseractParams` or `OcrmacParams` (engine configuration)
- Used by `JobManager` for state management

---

### 6. Document Upload

**Purpose**: Represents uploaded file metadata.

**Location**: `src/models/upload.py` (existing, no changes)

**Schema**: (unchanged from current implementation)
```python
class DocumentUpload(BaseModel):
    file_name: str
    file_format: FileFormat  # JPEG, PNG, PDF, TIFF
    file_size: int
    content_type: str
    upload_timestamp: datetime
    temp_file_path: Path
```

---

### 7. Upload Response

**Purpose**: API response for upload endpoint.

**Location**: `src/models/responses.py` (existing, no changes needed)

**Schema**: (unchanged)
```python
class UploadResponse(BaseModel):
    job_id: str
    status: JobStatus
```

---

### 8. Engine Registry (Singleton)

**Purpose**: Central registry for engine discovery and capability caching.

**Location**: `src/services/ocr/registry.py` (new)

**Schema**:
```python
class EngineRegistry:
    """Singleton registry for OCR engine discovery and capability caching."""

    _instance: Optional['EngineRegistry'] = None
    _capabilities: dict[EngineType, EngineCapabilities]
    _initialized: bool = False

    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize registry and detect engines (once)."""
        if not self._initialized:
            self._capabilities = {}
            self._detect_all_engines()
            self._initialized = True

    def _detect_all_engines(self):
        """Detect all supported engines at startup."""
        self._detect_tesseract()
        self._detect_ocrmac()

    def is_available(self, engine: EngineType) -> bool:
        """Check if engine is available."""
        return self._capabilities[engine].available

    def get_capabilities(self, engine: EngineType) -> EngineCapabilities:
        """Get cached capabilities for engine."""
        return self._capabilities[engine]

    def validate_platform(self, engine: EngineType) -> tuple[bool, Optional[str]]:
        """
        Validate platform compatibility for engine.

        Returns:
            (is_valid, error_message)
        """
        caps = self._capabilities[engine]
        if caps.platform_requirement is None:
            return (True, None)

        import platform
        current_platform = platform.system().lower()
        if current_platform != caps.platform_requirement:
            return (
                False,
                f"{engine.value} engine is only available on {caps.platform_requirement} systems. "
                f"Current platform: {current_platform}"
            )
        return (True, None)

    def validate_languages(
        self, engine: EngineType, languages: list[str]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate language codes against engine capabilities.

        Returns:
            (is_valid, error_message)
        """
        caps = self._capabilities[engine]
        if not caps.available:
            return (False, f"{engine.value} engine is not available")

        unsupported = [
            lang for lang in languages
            if lang not in caps.supported_languages
        ]

        if unsupported:
            return (
                False,
                f"Unsupported language codes for {engine.value}: {', '.join(unsupported)}. "
                f"Supported: {', '.join(sorted(caps.supported_languages))}"
            )

        return (True, None)
```

**Lifecycle**:
- Created at application startup (in `src/main.py` lifespan)
- Singleton pattern ensures single instance
- Capabilities cached for entire application lifetime
- No runtime refresh (requires app restart)

---

## Entity Relationships

```
┌─────────────────────┐
│  EngineRegistry     │  Singleton, initialized at startup
│  (Singleton)        │
├─────────────────────┤
│ + _capabilities     │────┐
│ + is_available()    │    │
│ + validate_*()      │    │
└─────────────────────┘    │
                           │ owns
                           ▼
               ┌─────────────────────────┐
               │  EngineCapabilities     │
               ├─────────────────────────┤
               │ + available: bool       │
               │ + version: str          │
               │ + supported_languages   │
               │ + platform_requirement  │
               └─────────────────────────┘
                           ▲
                           │ describes
                           │
               ┌───────────┴───────────┐
               │                       │
    ┌──────────┴──────────┐ ┌─────────┴──────────┐
    │  TesseractParams    │ │  OcrmacParams      │
    ├─────────────────────┤ ├────────────────────┤
    │ + lang: str         │ │ + languages: list  │
    │ + psm: int          │ │ + recognition_level│
    │ + oem: int          │ └────────────────────┘
    │ + dpi: int          │
    └─────────────────────┘
               ▲                       ▲
               │                       │
               └───────┬───────────────┘
                       │ uses (union type)
                       │
               ┌───────┴────────┐
               │   OCRJob       │
               ├────────────────┤
               │ + job_id       │
               │ + engine       │───> EngineType enum
               │ + engine_params│
               │ + status       │
               │ + upload       │────> DocumentUpload
               └────────────────┘
```

## Validation Matrix

| Entity | Field | Validation | Error Message |
|--------|-------|------------|---------------|
| TesseractParams | lang | ISO 639-3 pattern, max 5 | "Invalid language format: {lang}. Expected ISO 639-3 (e.g., eng, fra)" |
| TesseractParams | psm | 0-13 range | "PSM must be between 0 and 13" |
| TesseractParams | oem | 0-3 range | "OEM must be between 0 and 3" |
| TesseractParams | dpi | 70-2400 range | "DPI must be between 70 and 2400" |
| OcrmacParams | languages | IETF BCP 47, max 5 | "Invalid IETF BCP 47 format: {lang}. Expected: en-US, fr-FR, zh-Hans" |
| OcrmacParams | languages | Length <= 5 | "Maximum 5 languages allowed" |
| OcrmacParams | recognition_level | Enum value | "Invalid recognition level. Allowed: fast, balanced, accurate" |
| OCRJob | engine | EngineType enum | "Invalid engine type. Allowed: tesseract, ocrmac" |
| OCRJob | engine_params | Type matches engine | "Parameter type mismatch for engine {engine}" |
| EngineRegistry | platform | Platform check | "ocrmac is only available on darwin systems. Current: {platform}" |
| EngineRegistry | languages | Capability check | "Unsupported languages: {langs}. Supported: {supported}" |

## Database/Storage Schema

**Redis Keys** (for job state):
```
job:{job_id}              # OCRJob JSON (includes engine and engine_params)
job:{job_id}:result_path  # Path to HOCR result file
```

**Filesystem** (temporary files):
```
/tmp/uploads/{job_id}_{filename}    # Uploaded document (deleted after processing)
/tmp/results/{job_id}.hocr          # HOCR result (both engines produce HOCR)
```

**Serialization**:
- All models use Pydantic's `.model_dump_json()` for Redis storage
- Engine-specific params stored as nested JSON in OCRJob
- Deserialization uses `OCRJob.model_validate_json()`

## Migration from Current Schema

### Changes Required:

1. **OCRJob model** (`src/models/job.py`):
   - Add `engine: EngineType` field (default: TESSERACT for backward compatibility)
   - Rename `tesseract_params` → `engine_params` (Union type)
   - Migration: existing jobs without `engine` field default to TESSERACT

2. **New files**:
   - `src/models/ocr_params.py` - OcrmacParams and RecognitionLevel
   - `src/services/ocr/registry.py` - EngineRegistry and EngineCapabilities

3. **No breaking changes**:
   - TesseractParams unchanged (fully backward compatible)
   - DocumentUpload unchanged
   - API responses unchanged

### Backward Compatibility:

- Existing `/upload` endpoint continues to work (defaults to Tesseract)
- Existing jobs in Redis can be deserialized (engine defaults to TESSERACT)
- No changes to result format (all engines produce HOCR)
