# Research: EasyOCR Engine Integration

**Date**: 2025-10-19
**Purpose**: Resolve technical unknowns and establish implementation patterns for EasyOCR engine support

## Research Questions Addressed

### 1. EasyOCR Installation and Dependencies

**Decision**: Install EasyOCR via pip with PyTorch as primary dependency

**Rationale**:
- EasyOCR provides stable pip package: `pip install easyocr`
- PyTorch is required dependency (used for deep learning models)
- Installation pattern matches existing approach (pytesseract via pip)
- Development version available from GitHub if needed: `pip install git+https://github.com/JaidedAI/EasyOCR.git`

**Implementation Details**:
```python
# pyproject.toml dependencies
easyocr = "^1.7.0"  # Latest stable version
torch = "^2.0.0"    # PyTorch dependency for EasyOCR
```

**Alternatives Considered**:
- Building from source: Rejected - unnecessary complexity for standard use case
- Using conda: Rejected - project uses pip/uv for dependency management

---

### 2. GPU Detection and Management with PyTorch

**Decision**: Use `torch.cuda.is_available()` for GPU detection and implement concurrency limiting for GPU jobs

**Rationale**:
- PyTorch provides robust CUDA availability checking via `torch.cuda.is_available()`
- Context7 documentation shows standard pattern for device selection
- GPU graceful fallback: if `gpu=True` requested but unavailable, fall back to CPU with warning
- Memory management: limit concurrent GPU jobs to prevent OOM errors

**Implementation Pattern**:
```python
import torch

def detect_gpu_availability() -> bool:
    """Detect if CUDA GPU is available for EasyOCR."""
    return torch.cuda.is_available()

def get_easyocr_device(gpu_requested: bool) -> tuple[bool, str]:
    """
    Determine device for EasyOCR based on request and availability.
    Returns: (use_gpu, device_name)
    """
    if gpu_requested and torch.cuda.is_available():
        return True, f"cuda:{torch.cuda.current_device()}"
    elif gpu_requested and not torch.cuda.is_available():
        logger.warning("GPU requested but not available, falling back to CPU")
        return False, "cpu"
    else:
        return False, "cpu"
```

**GPU Concurrency Management**:
- Use semaphore or queue to limit concurrent GPU jobs to 2 maximum
- Track active GPU jobs in Redis or in-memory counter
- Queue additional GPU requests when limit reached

**Alternatives Considered**:
- Manual CUDA detection: Rejected - PyTorch abstracts this reliably
- Automatic GPU selection: Rejected - explicit user control preferred per requirements

---

### 3. EasyOCR Reader Initialization and Configuration

**Decision**: Initialize EasyOCR Reader per-job with specified parameters, cache model loading

**Rationale**:
- Reader initialization: `easyocr.Reader(lang_list, gpu=True/False)`
- Models load once into memory on first Reader creation for given languages
- Supports 80+ languages with specific naming convention (e.g., 'en', 'ch_sim', 'ja', 'ko')
- GPU parameter controls CUDA usage explicitly

**Implementation Pattern**:
```python
import easyocr

def create_easyocr_reader(
    languages: list[str],
    use_gpu: bool = False
) -> easyocr.Reader:
    """
    Create EasyOCR Reader instance with specified configuration.
    Note: First call downloads/loads models (cached for subsequent calls).
    """
    return easyocr.Reader(languages, gpu=use_gpu)

def perform_easyocr(
    image_path: str,
    languages: list[str],
    use_gpu: bool,
    text_threshold: float = 0.7,
    link_threshold: float = 0.7
) -> list:
    """Execute EasyOCR text recognition."""
    reader = create_easyocr_reader(languages, use_gpu)

    # readtext returns: [([[x1,y1], [x2,y2], [x3,y3], [x4,y4]], text, confidence), ...]
    results = reader.readtext(
        image_path,
        detail=1  # Include bounding boxes and confidence
    )

    return results
```

**Configuration Parameters**:
- `languages`: List of language codes (EasyOCR naming: 'en', 'ch_sim', 'ch_tra', 'ja', 'ko', 'th', etc.)
- `gpu`: Boolean flag for CUDA usage
- `text_threshold`: Confidence threshold for text detection (0.0-1.0, default 0.7)
- `link_threshold`: Threshold for linking text regions (0.0-1.0, default 0.7)

**Alternatives Considered**:
- Singleton Reader instance: Rejected - different language combinations require different readers
- Pre-loading all languages: Rejected - memory intensive, 5GB storage limit

---

### 4. EasyOCR Language Support and Validation

**Decision**: Maintain hardcoded list of supported EasyOCR languages for validation

**Rationale**:
- EasyOCR supports 80+ languages with specific naming convention
- Language codes differ from Tesseract (3-letter) and ocrmac (2-letter)
- Validation must reject Tesseract/ocrmac language formats when EasyOCR selected
- Maximum 5 languages per request to manage memory and performance

**Supported Language Examples**:
```python
EASYOCR_SUPPORTED_LANGUAGES = {
    'en', 'ch_sim', 'ch_tra', 'ja', 'ko', 'th', 'vi', 'ar', 'hi',
    'fr', 'de', 'es', 'pt', 'ru', 'it', 'nl', 'pl', 'tr', 'sv',
    # ... (full list ~80 languages)
}

def validate_easyocr_languages(languages: list[str]) -> None:
    """Validate EasyOCR language codes."""
    if len(languages) > 5:
        raise ValueError("EasyOCR supports maximum 5 languages per request")

    invalid = [lang for lang in languages if lang not in EASYOCR_SUPPORTED_LANGUAGES]
    if invalid:
        raise ValueError(f"Unsupported EasyOCR languages: {invalid}")
```

**Alternatives Considered**:
- Dynamic language detection from EasyOCR: Rejected - no reliable API for this
- Unlimited languages: Rejected - memory/performance constraints

---

### 5. EasyOCR Output to hOCR Conversion

**Decision**: Convert EasyOCR bounding box output to hOCR format for consistency

**Rationale**:
- EasyOCR returns: `[([[x1,y1], [x2,y2], [x3,y3], [x4,y4]], text, confidence), ...]`
- Need to convert to hOCR XML format to match Tesseract/ocrmac output
- hOCR provides standard format for OCR results with bounding boxes and confidence

**Implementation Pattern**:
```python
def easyocr_to_hocr(
    easyocr_results: list,
    image_width: int,
    image_height: int
) -> str:
    """
    Convert EasyOCR results to hOCR XML format.

    EasyOCR output: [([[x1,y1], [x2,y2], [x3,y3], [x4,y4]], text, confidence), ...]
    hOCR format: XML with bbox coordinates and confidence (x_wconf)
    """
    hocr_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"',
        '    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">',
        '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">',
        '<head><meta http-equiv="content-type" content="text/html; charset=utf-8" />',
        '<meta name="ocr-system" content="easyocr" /></head>',
        f'<body><div class="ocr_page" title="bbox 0 0 {image_width} {image_height}">',
    ]

    for idx, (bbox, text, confidence) in enumerate(easyocr_results):
        # EasyOCR bbox: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        # Convert to hOCR bbox: x_min y_min x_max y_max
        x_coords = [point[0] for point in bbox]
        y_coords = [point[1] for point in bbox]
        x_min, x_max = int(min(x_coords)), int(max(x_coords))
        y_min, y_max = int(min(y_coords)), int(max(y_coords))

        # Convert confidence (0.0-1.0) to percentage (0-100)
        conf_percent = int(confidence * 100)

        hocr_lines.append(
            f'<span class="ocrx_word" title="bbox {x_min} {y_min} {x_max} {y_max}; '
            f'x_wconf {conf_percent}">{text}</span>'
        )

    hocr_lines.append('</div></body></html>')
    return '\n'.join(hocr_lines)
```

**Alternatives Considered**:
- Native EasyOCR format output: Rejected - breaks consistency with other engines
- JSON format: Rejected - hOCR is established standard in OCR domain

---

### 6. Model Storage and Checksum Validation

**Decision**: Store EasyOCR models in configurable persistent volume with checksum validation at startup

**Rationale**:
- EasyOCR downloads models to `~/.EasyOCR/model/` by default
- Models average 100-200MB per language, 5GB total storage budget adequate
- Checksums validate model integrity to prevent corruption issues
- Model path configurable via environment variable

**Implementation Pattern**:
```python
import os
import hashlib
from pathlib import Path

# Configuration
EASYOCR_MODEL_DIR = os.getenv('EASYOCR_MODEL_DIR', str(Path.home() / '.EasyOCR/model'))
EASYOCR_MODEL_SIZE_LIMIT = int(os.getenv('EASYOCR_MODEL_SIZE_LIMIT_GB', '5')) * 1024**3

def get_model_directory_size(path: Path) -> int:
    """Calculate total size of EasyOCR model directory."""
    return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())

def validate_model_storage() -> dict:
    """
    Validate EasyOCR model storage at startup.
    Returns: {"available": bool, "size_bytes": int, "message": str}
    """
    model_path = Path(EASYOCR_MODEL_DIR)

    if not model_path.exists():
        model_path.mkdir(parents=True, exist_ok=True)

    size_bytes = get_model_directory_size(model_path)

    if size_bytes > EASYOCR_MODEL_SIZE_LIMIT:
        return {
            "available": False,
            "size_bytes": size_bytes,
            "message": f"Model storage exceeds {EASYOCR_MODEL_SIZE_LIMIT / 1024**3}GB limit"
        }

    return {
        "available": True,
        "size_bytes": size_bytes,
        "message": "Model storage within limits"
    }
```

**Checksum Validation**:
- EasyOCR models include checksums in download process
- Model corruption detected automatically during Reader initialization
- Return HTTP 500 with re-download instructions if validation fails

**Alternatives Considered**:
- No storage limits: Rejected - unbounded disk usage risk
- Pre-download all models: Rejected - exceeds 5GB limit, most languages unused

---

### 7. Performance Optimization and Timeouts

**Decision**: Implement 60-second per-page timeout with model caching for performance

**Rationale**:
- EasyOCR deep learning models slower than Tesseract (expected tradeoff for accuracy)
- GPU acceleration provides 50%+ speedup for complex documents
- Model loading cached after first use (subsequent calls faster)
- Timeout prevents hung jobs on problematic documents

**Implementation Pattern**:
```python
import signal
from contextlib import contextmanager

class TimeoutError(Exception):
    pass

@contextmanager
def timeout(seconds: int):
    """Context manager for timeout enforcement."""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation exceeded {seconds} second timeout")

    # Set the signal handler
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)  # Disable alarm

def process_page_with_easyocr(
    image_path: str,
    config: EasyOCRConfig,
    timeout_seconds: int = 60
) -> str:
    """Process single page with timeout."""
    try:
        with timeout(timeout_seconds):
            reader = create_easyocr_reader(config.languages, config.gpu)
            results = reader.readtext(image_path)
            return easyocr_to_hocr(results, config.image_width, config.image_height)
    except TimeoutError:
        raise ValueError(f"EasyOCR processing exceeded {timeout_seconds}s timeout")
```

**Performance Metrics to Track**:
- Per-job processing time (logged)
- GPU vs CPU mode used (logged)
- Model load time (first call vs cached)
- Queue wait time for GPU jobs
- Language count impact on performance

**Alternatives Considered**:
- No timeout: Rejected - risk of infinite hangs
- Shorter timeout (<30s): Rejected - insufficient for complex multilingual documents

---

### 8. Parameter Isolation and Validation

**Decision**: Extend existing engine parameter validation pattern to reject cross-engine parameters

**Rationale**:
- Existing codebase validates Tesseract vs ocrmac parameters separately
- EasyOCR introduces third parameter set: gpu, text_threshold, link_threshold
- Must reject Tesseract params (psm, oem, dpi, lang) when engine=easyocr
- Must reject ocrmac params (recognition_level) when engine=easyocr
- Must reject EasyOCR params when engine=tesseract or engine=ocrmac

**Implementation Pattern**:
```python
from pydantic import BaseModel, field_validator

TESSERACT_ONLY_PARAMS = {'psm', 'oem', 'dpi'}
OCRMAC_ONLY_PARAMS = {'recognition_level'}
EASYOCR_ONLY_PARAMS = {'gpu', 'text_threshold', 'link_threshold'}

class UploadRequest(BaseModel):
    engine: str = "tesseract"  # Default to Tesseract for backward compatibility
    languages: list[str] | None = None

    # Engine-specific parameters
    # Tesseract
    psm: int | None = None
    oem: int | None = None
    dpi: int | None = None

    # Ocrmac
    recognition_level: str | None = None

    # EasyOCR
    gpu: bool | None = None
    text_threshold: float | None = None
    link_threshold: float | None = None

    @field_validator('*', mode='before')
    def validate_engine_params(cls, v, info):
        """Validate parameter compatibility with selected engine."""
        engine = info.data.get('engine', 'tesseract')
        field_name = info.field_name

        if engine == 'easyocr':
            if field_name in TESSERACT_ONLY_PARAMS:
                raise ValueError(f"Parameter '{field_name}' is not valid for EasyOCR engine")
            if field_name in OCRMAC_ONLY_PARAMS:
                raise ValueError(f"Parameter '{field_name}' is not valid for EasyOCR engine")

        elif engine == 'tesseract':
            if field_name in EASYOCR_ONLY_PARAMS:
                raise ValueError(f"Parameter '{field_name}' is not valid for Tesseract engine")

        elif engine == 'ocrmac':
            if field_name in TESSERACT_ONLY_PARAMS:
                raise ValueError(f"Parameter '{field_name}' is not valid for ocrmac engine")
            if field_name in EASYOCR_ONLY_PARAMS:
                raise ValueError(f"Parameter '{field_name}' is not valid for ocrmac engine")

        return v
```

**Alternatives Considered**:
- Automatic parameter mapping: Rejected - engines fundamentally different, no reliable mapping
- Separate endpoints per engine: Rejected - violates backward compatibility and API simplicity

---

### 9. Startup Detection and Graceful Degradation

**Decision**: Detect EasyOCR availability at startup; start service even if EasyOCR unavailable

**Rationale**:
- Service availability prioritized over individual engine availability
- EasyOCR detection may fail due to: missing installation, model corruption, GPU driver issues
- Other engines (Tesseract, ocrmac) should continue functioning
- Log warning if EasyOCR unavailable, return HTTP 400 for easyocr engine requests

**Implementation Pattern**:
```python
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class EngineAvailability:
    tesseract: bool
    ocrmac: bool
    easyocr: bool
    easyocr_gpu: bool

def detect_easyocr_availability() -> tuple[bool, bool]:
    """
    Detect EasyOCR availability at startup.
    Returns: (easyocr_available, gpu_available)
    """
    try:
        import easyocr
        import torch

        # Validate model storage
        storage_check = validate_model_storage()
        if not storage_check["available"]:
            logger.warning(f"EasyOCR storage issue: {storage_check['message']}")
            return False, False

        # Test basic initialization (CPU mode)
        reader = easyocr.Reader(['en'], gpu=False)

        # Check GPU availability
        gpu_available = torch.cuda.is_available()

        logger.info(f"EasyOCR available: CPU=True, GPU={gpu_available}")
        return True, gpu_available

    except ImportError as e:
        logger.warning(f"EasyOCR not installed: {e}")
        return False, False
    except Exception as e:
        logger.warning(f"EasyOCR initialization failed: {e}")
        return False, False

# At application startup
engine_availability = EngineAvailability(
    tesseract=detect_tesseract_availability(),
    ocrmac=detect_ocrmac_availability(),
    easyocr=detect_easyocr_availability()[0],
    easyocr_gpu=detect_easyocr_availability()[1]
)

if not engine_availability.easyocr:
    logger.warning("Starting service with EasyOCR unavailable")
```

**Alternatives Considered**:
- Fail startup if EasyOCR missing: Rejected - breaks existing Tesseract/ocrmac functionality
- Auto-install EasyOCR: Rejected - installation should be explicit deployment step

---

## Summary of Key Decisions

1. **Installation**: pip install easyocr + torch dependencies
2. **GPU Management**: PyTorch CUDA detection, graceful fallback, 2-job concurrency limit
3. **Reader Initialization**: Per-job with language-specific model caching
4. **Language Support**: Hardcoded 80+ language list, EasyOCR naming convention, 5-language max
5. **Output Format**: Convert EasyOCR bounding boxes to hOCR XML for consistency
6. **Model Storage**: Configurable persistent volume, 5GB limit, checksum validation
7. **Performance**: 60s per-page timeout, GPU acceleration, model caching, metrics tracking
8. **Parameter Validation**: Extend existing pattern, strict engine-parameter isolation
9. **Startup Behavior**: Detect availability, graceful degradation, warning logs

All technical unknowns from the planning phase have been resolved with concrete implementation approaches.
