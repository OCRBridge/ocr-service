# Data Model: EasyOCR Engine Support

**Date**: 2025-10-19
**Purpose**: Define data entities, relationships, and validation rules for EasyOCR engine integration

## Core Entities

### 1. OCR Engine (Extended)

**Description**: Represents an OCR processing engine available in the system

**Attributes**:
- `name`: String - Engine identifier ("tesseract", "ocrmac", "easyocr")
- `platform_requirements`: List[String] - Required platform(s) for engine
- `supported_parameters`: Set[String] - Parameters valid for this engine
- `available`: Boolean - Whether engine is available in current environment
- `gpu_support`: Boolean - Whether engine supports GPU acceleration

**State**:
- Detected at application startup
- Cached in memory for request validation

**New Values for EasyOCR**:
```python
{
    "name": "easyocr",
    "platform_requirements": ["linux", "darwin", "win32"],  # Cross-platform
    "supported_parameters": {"languages", "gpu", "text_threshold", "link_threshold"},
    "available": True/False,  # Detected at startup
    "gpu_support": True
}
```

---

### 2. EasyOCR Configuration (New)

**Description**: Configuration parameters specific to EasyOCR engine

**Attributes**:
- `languages`: List[String] - Language codes for recognition (EasyOCR naming convention)
  - Validation: Non-empty list, max 5 items, values in EASYOCR_SUPPORTED_LANGUAGES
  - Default: ["en"]
  - Examples: ["en"], ["ch_sim", "en"], ["ja", "ko", "en"]

- `gpu`: Boolean - Enable GPU acceleration
  - Validation: Must be boolean
  - Default: False (conservative default)
  - Note: Graceful fallback to CPU if GPU requested but unavailable

- `text_threshold`: Float - Confidence threshold for text detection
  - Validation: 0.0 <= value <= 1.0
  - Default: 0.7
  - Lower = more text detected (higher recall), Higher = fewer but more confident detections (higher precision)

- `link_threshold`: Float - Threshold for linking text regions
  - Validation: 0.0 <= value <= 1.0
  - Default: 0.7
  - Controls how text boxes are grouped together

**Validation Rules**:
```python
class EasyOCRConfig(BaseModel):
    languages: list[str] = ["en"]
    gpu: bool = False
    text_threshold: float = 0.7
    link_threshold: float = 0.7

    @field_validator('languages')
    def validate_languages(cls, v):
        if not v:
            raise ValueError("At least one language required")
        if len(v) > 5:
            raise ValueError("Maximum 5 languages allowed for EasyOCR")
        invalid = [lang for lang in v if lang not in EASYOCR_SUPPORTED_LANGUAGES]
        if invalid:
            raise ValueError(f"Unsupported EasyOCR languages: {invalid}")
        return v

    @field_validator('text_threshold', 'link_threshold')
    def validate_threshold(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        return v
```

**State Transitions**:
1. User provides parameters in upload request
2. System validates against EasyOCR rules
3. System checks EasyOCR availability
4. Configuration passed to EasyOCR engine for processing

---

### 3. Engine Configuration (Extended)

**Description**: Union type representing configuration for any OCR engine

**Attributes**:
- `engine_type`: Enum["tesseract", "ocrmac", "easyocr"]
- `tesseract_config`: TesseractConfig | None
- `ocrmac_config`: OcrmacConfig | None
- `easyocr_config`: EasyOCRConfig | None

**Validation Rules**:
- Exactly one engine config must be non-null based on engine_type
- Engine-specific parameters validated independently
- Cross-engine parameter usage rejected with HTTP 400

**Example Instances**:
```python
# EasyOCR configuration
{
    "engine_type": "easyocr",
    "easyocr_config": {
        "languages": ["ch_sim", "en"],
        "gpu": True,
        "text_threshold": 0.7,
        "link_threshold": 0.7
    },
    "tesseract_config": None,
    "ocrmac_config": None
}

# Tesseract configuration (existing)
{
    "engine_type": "tesseract",
    "tesseract_config": {
        "lang": ["eng"],
        "psm": 6,
        "oem": 3
    },
    "easyocr_config": None,
    "ocrmac_config": None
}
```

---

### 4. OCR Job (Extended)

**Description**: Represents an OCR processing job with engine-specific configuration

**Attributes** (additions/changes):
- `job_id`: String (UUID) - Unique job identifier
- `engine`: String - Engine used ("tesseract", "ocrmac", "easyocr")
- `engine_config`: EngineConfiguration - Engine-specific parameters
- `status`: Enum["pending", "processing", "completed", "failed"]
- `created_at`: DateTime
- `updated_at`: DateTime
- `result_path`: String | None - Path to hOCR output
- `error_message`: String | None

**New Fields for EasyOCR**:
- `gpu_used`: Boolean | None - Whether GPU was used for processing (EasyOCR only)
- `model_load_time_ms`: Integer | None - Time to load models (EasyOCR metrics)
- `processing_time_ms`: Integer - Time to process document
- `queue_wait_time_ms`: Integer | None - Time waiting in GPU queue

**State Transitions**:
```
pending → processing → completed
pending → processing → failed
pending → failed (validation error, engine unavailable)
```

**Storage**:
- Stored in Redis with TTL
- Key format: `job:{job_id}`
- Includes all engine configuration for reproducibility

**Example EasyOCR Job**:
```python
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "engine": "easyocr",
    "engine_config": {
        "engine_type": "easyocr",
        "easyocr_config": {
            "languages": ["ja", "en"],
            "gpu": True,
            "text_threshold": 0.8,
            "link_threshold": 0.7
        }
    },
    "status": "completed",
    "created_at": "2025-10-19T10:30:00Z",
    "updated_at": "2025-10-19T10:30:15Z",
    "result_path": "/tmp/results/550e8400-e29b-41d4-a716-446655440000.hocr",
    "gpu_used": True,
    "model_load_time_ms": 2500,
    "processing_time_ms": 12000,
    "queue_wait_time_ms": 3000,
    "error_message": None
}
```

---

### 5. GPU Job Queue (New)

**Description**: Manages concurrent GPU-enabled EasyOCR jobs to prevent memory exhaustion

**Attributes**:
- `active_jobs`: Set[String] - Currently processing GPU job IDs
- `max_concurrent`: Integer - Maximum concurrent GPU jobs (default: 2)
- `queued_jobs`: Queue[String] - Job IDs waiting for GPU slot
- `job_start_times`: Dict[String, DateTime] - Tracking for timeout enforcement

**Operations**:
- `acquire_gpu_slot(job_id)`: Returns True if slot available, False if must queue
- `release_gpu_slot(job_id)`: Frees slot and processes next queued job
- `get_queue_position(job_id)`: Returns position in queue (0-indexed)

**Validation Rules**:
- Active jobs count never exceeds max_concurrent
- Queued jobs processed in FIFO order
- Jobs timeout if waiting in queue exceeds overall job timeout

**Storage**:
- In-memory for performance (or Redis for distributed systems)
- Atomic operations for concurrency safety

**Example State**:
```python
{
    "active_jobs": {"job-abc", "job-def"},  # 2 jobs actively using GPU
    "max_concurrent": 2,
    "queued_jobs": ["job-ghi", "job-jkl"],  # 2 jobs waiting
    "job_start_times": {
        "job-abc": "2025-10-19T10:30:00Z",
        "job-def": "2025-10-19T10:30:05Z"
    }
}
```

---

### 6. Engine Availability Status (Extended)

**Description**: System-wide engine availability cache, updated at startup

**Attributes**:
- `tesseract_available`: Boolean
- `tesseract_version`: String | None
- `ocrmac_available`: Boolean
- `easyocr_available`: Boolean (new)
- `easyocr_gpu_available`: Boolean (new)
- `easyocr_model_storage_bytes`: Integer (new)
- `last_check`: DateTime

**Detection Logic**:
```python
@dataclass
class EngineAvailability:
    tesseract_available: bool
    tesseract_version: str | None
    ocrmac_available: bool
    easyocr_available: bool
    easyocr_gpu_available: bool
    easyocr_model_storage_bytes: int
    last_check: datetime

async def detect_engine_availability() -> EngineAvailability:
    """Detect all engine availability at startup."""
    tesseract_check = await detect_tesseract()
    ocrmac_check = await detect_ocrmac()
    easyocr_check, gpu_check = await detect_easyocr_availability()
    storage_check = validate_model_storage()

    return EngineAvailability(
        tesseract_available=tesseract_check[0],
        tesseract_version=tesseract_check[1],
        ocrmac_available=ocrmac_check,
        easyocr_available=easyocr_check,
        easyocr_gpu_available=gpu_check,
        easyocr_model_storage_bytes=storage_check["size_bytes"],
        last_check=datetime.utcnow()
    )
```

**Usage**:
- Cached at application startup
- Referenced during upload request validation
- Returns HTTP 400 if requested engine unavailable

---

### 7. Upload Request (Extended)

**Description**: API request model for OCR upload endpoint

**Attributes** (with EasyOCR additions):
```python
class UploadRequest(BaseModel):
    """OCR upload request with multi-engine support."""

    # File upload
    file: UploadFile

    # Engine selection (backward compatible default)
    engine: Literal["tesseract", "ocrmac", "easyocr"] = "tesseract"

    # Tesseract-specific parameters
    lang: list[str] | None = None  # Tesseract 3-letter codes
    psm: int | None = None
    oem: int | None = None
    dpi: int | None = None

    # Ocrmac-specific parameters
    recognition_level: Literal["fast", "balanced", "accurate"] | None = None

    # EasyOCR-specific parameters (NEW)
    languages: list[str] | None = None  # EasyOCR language codes
    gpu: bool | None = None
    text_threshold: float | None = None
    link_threshold: float | None = None

    @field_validator('*', mode='after')
    def validate_engine_parameter_isolation(cls, v, info):
        """Validate that parameters match selected engine."""
        engine = info.data.get('engine', 'tesseract')
        field_name = info.field_name

        # Define parameter sets per engine
        tesseract_params = {'lang', 'psm', 'oem', 'dpi'}
        ocrmac_params = {'recognition_level'}
        easyocr_params = {'languages', 'gpu', 'text_threshold', 'link_threshold'}

        # Check for invalid parameter usage
        if engine == 'easyocr':
            if field_name in tesseract_params and v is not None:
                raise ValueError(
                    f"Parameter '{field_name}' is not valid for EasyOCR engine. "
                    f"Use 'languages' instead of 'lang' for EasyOCR."
                )
            if field_name in ocrmac_params and v is not None:
                raise ValueError(f"Parameter '{field_name}' is not valid for EasyOCR engine")

        elif engine == 'tesseract':
            if field_name in easyocr_params and v is not None:
                raise ValueError(f"Parameter '{field_name}' is not valid for Tesseract engine")
            if field_name in ocrmac_params and v is not None:
                raise ValueError(f"Parameter '{field_name}' is not valid for Tesseract engine")

        elif engine == 'ocrmac':
            if field_name in tesseract_params and v is not None:
                raise ValueError(f"Parameter '{field_name}' is not valid for ocrmac engine")
            if field_name in easyocr_params and v is not None:
                raise ValueError(f"Parameter '{field_name}' is not valid for ocrmac engine")

        return v

    def to_engine_config(self) -> EngineConfiguration:
        """Convert request to engine configuration."""
        if self.engine == "easyocr":
            return EngineConfiguration(
                engine_type="easyocr",
                easyocr_config=EasyOCRConfig(
                    languages=self.languages or ["en"],
                    gpu=self.gpu if self.gpu is not None else False,
                    text_threshold=self.text_threshold or 0.7,
                    link_threshold=self.link_threshold or 0.7
                )
            )
        # ... existing tesseract/ocrmac logic
```

---

## Entity Relationships

```
UploadRequest
    ├─> validates against EngineAvailability
    └─> creates OCRJob
            ├─> contains EngineConfiguration
            │       └─> contains EasyOCRConfig (if engine=easyocr)
            └─> may queue in GPUJobQueue (if gpu=True)
                    └─> acquires slot for processing
```

---

## Validation Rules Summary

### Language Validation
- **Tesseract**: 3-letter codes (eng, spa, fra), validated against installed languages
- **Ocrmac**: 2-letter codes (en, de, ja), validated against macOS supported languages
- **EasyOCR**: Specific naming (en, ch_sim, ja), validated against EASYOCR_SUPPORTED_LANGUAGES constant

### Parameter Validation
- **Engine Selection**: Must be "tesseract", "ocrmac", or "easyocr"
- **Parameter Isolation**: Engine-specific parameters rejected for other engines with HTTP 400
- **Threshold Values**: Must be 0.0 <= value <= 1.0 for text_threshold and link_threshold
- **Language Count**: Maximum 5 languages for EasyOCR
- **GPU Availability**: Graceful fallback if GPU requested but unavailable (warning logged)

### Backward Compatibility
- Default engine remains "tesseract" (unchanged behavior)
- Existing requests without engine parameter work identically
- No breaking changes to existing Tesseract or ocrmac functionality

---

## Storage Patterns

### Redis Keys
- `job:{job_id}`: OCR job state and configuration
- `gpu_queue:active`: Set of active GPU job IDs
- `gpu_queue:pending`: Ordered queue of pending GPU job IDs
- `engine_availability`: Cached engine detection results

### Filesystem
- `/tmp/uploads/{job_id}_{filename}`: Temporary uploaded file
- `/tmp/results/{job_id}.hocr`: Processing results (hOCR format)
- `~/.EasyOCR/model/`: EasyOCR model files (persistent volume)

---

## Performance Characteristics

### Memory Usage
- EasyOCR models: ~100-200MB per language loaded
- GPU memory: ~2-4GB per active job (limit: 2 concurrent)
- CPU memory: ~500MB per job

### Processing Time Estimates
- Single page, English, CPU: ~5-10 seconds
- Single page, English, GPU: ~2-5 seconds
- Single page, multilingual (3 languages), GPU: ~8-15 seconds
- First request (model loading): +2-5 seconds overhead

### Concurrency Limits
- GPU jobs: Maximum 2 concurrent
- CPU jobs: No specific limit (constrained by system resources)
- Queue depth: Unlimited (but timeout applies to queued jobs)
