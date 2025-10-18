# Quickstart: EasyOCR Engine Integration

**Date**: 2025-10-19
**Purpose**: Quick reference for developing and testing EasyOCR engine support

## Overview

This feature adds **EasyOCR** as a third OCR engine option alongside Tesseract and ocrmac, enabling superior multilingual support (80+ languages, especially Asian scripts) via deep learning-based recognition.

**Key Addition**: Users can specify `engine=easyocr` with EasyOCR-specific parameters (`languages`, `gpu`, `text_threshold`, `link_threshold`) while maintaining full backward compatibility.

---

## Setup

### 1. Install Dependencies

```bash
# Install EasyOCR and PyTorch
uv add easyocr torch

# Or manually in pyproject.toml
# [project.dependencies]
# easyocr = "^1.7.0"
# torch = "^2.0.0"
```

### 2. Configure Model Storage (Optional)

```bash
# Set custom model directory (default: ~/.EasyOCR/model/)
export EASYOCR_MODEL_DIR="/path/to/models"

# Set model storage limit (default: 5GB)
export EASYOCR_MODEL_SIZE_LIMIT_GB=10
```

### 3. Verify Installation

```python
# Test EasyOCR availability
import easyocr
import torch

# Check GPU availability
print(f"GPU available: {torch.cuda.is_available()}")

# Test basic initialization
reader = easyocr.Reader(['en'], gpu=False)
print("EasyOCR initialized successfully")
```

---

## Development Workflow

### Step 1: Extend Data Models

**File**: `src/models/engine.py`

```python
from enum import Enum

class OCREngine(str, Enum):
    TESSERACT = "tesseract"
    OCRMAC = "ocrmac"
    EASYOCR = "easyocr"  # NEW
```

**File**: `src/models/request.py`

```python
from pydantic import BaseModel, field_validator

class EasyOCRConfig(BaseModel):
    """EasyOCR-specific configuration."""
    languages: list[str] = ["en"]
    gpu: bool = False
    text_threshold: float = 0.7
    link_threshold: float = 0.7

    @field_validator('languages')
    def validate_languages(cls, v):
        if not v or len(v) > 5:
            raise ValueError("EasyOCR requires 1-5 languages")
        # Add language validation
        return v

class UploadRequest(BaseModel):
    engine: str = "tesseract"  # Backward compatible default

    # EasyOCR params (NEW)
    languages: list[str] | None = None
    gpu: bool | None = None
    text_threshold: float | None = None
    link_threshold: float | None = None
```

### Step 2: Implement EasyOCR Engine

**File**: `src/services/engines/easyocr.py`

```python
import easyocr
import torch
from pathlib import Path

class EasyOCREngine:
    """EasyOCR OCR engine implementation."""

    def __init__(self, languages: list[str], use_gpu: bool = False):
        self.languages = languages
        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.reader = easyocr.Reader(languages, gpu=self.use_gpu)

    def process_image(
        self,
        image_path: str,
        text_threshold: float = 0.7,
        link_threshold: float = 0.7
    ) -> list:
        """Process image and return EasyOCR results."""
        results = self.reader.readtext(
            image_path,
            detail=1  # Include bbox and confidence
        )
        return results

    def to_hocr(self, results: list, width: int, height: int) -> str:
        """Convert EasyOCR results to hOCR format."""
        # Implementation in src/utils/hocr.py
        from src.utils.hocr import easyocr_to_hocr
        return easyocr_to_hocr(results, width, height)
```

### Step 3: Add GPU Utilities

**File**: `src/utils/gpu.py` (NEW)

```python
import torch
import logging

logger = logging.getLogger(__name__)

def detect_gpu_availability() -> bool:
    """Detect if CUDA GPU is available."""
    return torch.cuda.is_available()

def get_device(gpu_requested: bool) -> tuple[bool, str]:
    """
    Determine device for EasyOCR.
    Returns: (use_gpu, device_name)
    """
    if gpu_requested and torch.cuda.is_available():
        return True, f"cuda:{torch.cuda.current_device()}"
    elif gpu_requested:
        logger.warning("GPU requested but not available, falling back to CPU")
        return False, "cpu"
    else:
        return False, "cpu"
```

### Step 4: Extend Validation Logic

**File**: `src/services/validators.py`

```python
EASYOCR_SUPPORTED_LANGUAGES = {
    'en', 'ch_sim', 'ch_tra', 'ja', 'ko', 'th', 'vi', 'ar', 'hi',
    'fr', 'de', 'es', 'pt', 'ru', 'it', 'nl', 'pl', 'tr', 'sv',
    # ... (full 80+ language list)
}

def validate_easyocr_params(
    languages: list[str],
    text_threshold: float,
    link_threshold: float
) -> None:
    """Validate EasyOCR parameters."""
    if not languages or len(languages) > 5:
        raise ValueError("EasyOCR requires 1-5 languages")

    invalid = [lang for lang in languages if lang not in EASYOCR_SUPPORTED_LANGUAGES]
    if invalid:
        raise ValueError(f"Unsupported EasyOCR languages: {invalid}")

    if not 0.0 <= text_threshold <= 1.0:
        raise ValueError("text_threshold must be between 0.0 and 1.0")

    if not 0.0 <= link_threshold <= 1.0:
        raise ValueError("link_threshold must be between 0.0 and 1.0")
```

### Step 5: Register Engine

**File**: `src/services/engine_registry.py`

```python
def detect_easyocr_availability() -> tuple[bool, bool]:
    """Detect EasyOCR availability at startup."""
    try:
        import easyocr
        import torch

        # Test basic initialization
        reader = easyocr.Reader(['en'], gpu=False)
        gpu_available = torch.cuda.is_available()

        return True, gpu_available
    except Exception as e:
        logger.warning(f"EasyOCR unavailable: {e}")
        return False, False

# At application startup
engine_registry = {
    "tesseract": detect_tesseract_availability(),
    "ocrmac": detect_ocrmac_availability(),
    "easyocr": detect_easyocr_availability()[0],  # NEW
}
```

---

## Testing Strategy

### Unit Tests

**File**: `tests/unit/test_validators.py`

```python
import pytest
from src.services.validators import validate_easyocr_params

def test_easyocr_valid_languages():
    """Test valid EasyOCR language codes."""
    validate_easyocr_params(['en'], 0.7, 0.7)  # Should pass
    validate_easyocr_params(['ch_sim', 'en'], 0.7, 0.7)  # Should pass

def test_easyocr_invalid_language_code():
    """Test rejection of Tesseract language format."""
    with pytest.raises(ValueError, match="Unsupported EasyOCR languages"):
        validate_easyocr_params(['eng'], 0.7, 0.7)  # 'eng' is Tesseract format

def test_easyocr_too_many_languages():
    """Test maximum language limit."""
    with pytest.raises(ValueError, match="1-5 languages"):
        validate_easyocr_params(['en', 'ch_sim', 'ja', 'ko', 'th', 'vi'], 0.7, 0.7)

def test_easyocr_invalid_threshold():
    """Test threshold validation."""
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        validate_easyocr_params(['en'], 1.5, 0.7)
```

**File**: `tests/unit/test_easyocr_engine.py` (NEW)

```python
import pytest
from src.services.engines.easyocr import EasyOCREngine

def test_easyocr_initialization():
    """Test EasyOCR engine initialization."""
    engine = EasyOCREngine(languages=['en'], use_gpu=False)
    assert engine.languages == ['en']
    assert engine.use_gpu == False

def test_easyocr_gpu_fallback(monkeypatch):
    """Test graceful GPU fallback when unavailable."""
    monkeypatch.setattr('torch.cuda.is_available', lambda: False)
    engine = EasyOCREngine(languages=['en'], use_gpu=True)
    assert engine.use_gpu == False  # Fell back to CPU
```

### Contract Tests

**File**: `tests/contract/test_api_contract.py`

```python
import pytest
from fastapi.testclient import TestClient

def test_upload_with_easyocr_engine(client: TestClient, sample_image):
    """Test EasyOCR engine selection."""
    response = client.post(
        "/upload",
        files={"file": sample_image},
        data={
            "engine": "easyocr",
            "languages": ["en"],
            "gpu": False
        }
    )
    assert response.status_code == 202
    data = response.json()
    assert data["engine"] == "easyocr"
    assert "job_id" in data

def test_upload_easyocr_multilingual(client: TestClient, chinese_image):
    """Test EasyOCR with multiple languages."""
    response = client.post(
        "/upload",
        files={"file": chinese_image},
        data={
            "engine": "easyocr",
            "languages": ["ch_sim", "en"],
            "gpu": False,
            "text_threshold": 0.8
        }
    )
    assert response.status_code == 202

def test_upload_easyocr_with_tesseract_params_returns_400(client: TestClient):
    """Test parameter isolation - reject Tesseract params with EasyOCR."""
    response = client.post(
        "/upload",
        files={"file": sample_image},
        data={
            "engine": "easyocr",
            "psm": 6  # Tesseract-only parameter
        }
    )
    assert response.status_code == 400
    assert "not valid for EasyOCR" in response.json()["detail"]

def test_upload_tesseract_lang_with_easyocr_returns_400(client: TestClient):
    """Test rejection of Tesseract language format with EasyOCR."""
    response = client.post(
        "/upload",
        files={"file": sample_image},
        data={
            "engine": "easyocr",
            "lang": ["eng"]  # Should be 'languages' with 'en' for EasyOCR
        }
    )
    assert response.status_code == 400
    assert "Use 'languages'" in response.json()["detail"]
```

### Integration Tests

**File**: `tests/integration/test_easyocr.py` (NEW)

```python
import pytest
from pathlib import Path

def test_easyocr_end_to_end(sample_english_image):
    """Test complete EasyOCR workflow."""
    from src.services.engines.easyocr import EasyOCREngine

    engine = EasyOCREngine(languages=['en'], use_gpu=False)
    results = engine.process_image(str(sample_english_image))

    assert len(results) > 0
    assert all(len(r) == 3 for r in results)  # bbox, text, confidence

def test_easyocr_to_hocr_conversion(sample_english_image):
    """Test EasyOCR output to hOCR conversion."""
    from src.services.engines.easyocr import EasyOCREngine

    engine = EasyOCREngine(languages=['en'], use_gpu=False)
    results = engine.process_image(str(sample_english_image))
    hocr = engine.to_hocr(results, width=800, height=600)

    assert '<?xml version="1.0"' in hocr
    assert 'ocr-system' in hocr
    assert 'easyocr' in hocr
```

---

## API Usage Examples

### Example 1: Basic EasyOCR Request

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@document.jpg" \
  -F "engine=easyocr" \
  -F "languages=en"
```

**Response**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "engine": "easyocr",
  "engine_config": {
    "languages": ["en"],
    "gpu": false,
    "text_threshold": 0.7,
    "link_threshold": 0.7
  }
}
```

### Example 2: Multilingual with GPU

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@chinese_document.jpg" \
  -F "engine=easyocr" \
  -F "languages=ch_sim" \
  -F "languages=en" \
  -F "gpu=true" \
  -F "text_threshold=0.8"
```

### Example 3: Get Results

```bash
curl http://localhost:8000/jobs/550e8400-e29b-41d4-a716-446655440000
```

**Response**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "engine": "easyocr",
  "created_at": "2025-10-19T10:30:00Z",
  "updated_at": "2025-10-19T10:30:15Z",
  "result": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>...",
  "metadata": {
    "gpu_used": true,
    "model_load_time_ms": 2500,
    "processing_time_ms": 12000,
    "queue_wait_time_ms": 3000,
    "languages_used": ["ch_sim", "en"]
  }
}
```

---

## Common Pitfalls

### 1. Language Code Confusion

**Problem**: Using Tesseract language codes with EasyOCR
```bash
# WRONG - 'eng' is Tesseract format
curl -F "engine=easyocr" -F "languages=eng" ...

# CORRECT - 'en' is EasyOCR format
curl -F "engine=easyocr" -F "languages=en" ...
```

### 2. Cross-Engine Parameters

**Problem**: Mixing engine parameters
```bash
# WRONG - psm is Tesseract-only
curl -F "engine=easyocr" -F "psm=6" ...

# CORRECT - Use EasyOCR-specific params
curl -F "engine=easyocr" -F "text_threshold=0.8" ...
```

### 3. GPU Expectations

**Problem**: Assuming GPU always used when requested
```python
# GPU requested but may fall back to CPU if unavailable
# Check metadata.gpu_used in response to confirm
```

---

## Performance Tips

1. **Model Caching**: First request loads models (~2-5s), subsequent requests faster
2. **GPU Acceleration**: 50%+ speedup for complex documents when GPU available
3. **Language Selection**: Fewer languages = faster processing
4. **Threshold Tuning**: Higher thresholds = fewer detections = faster processing

---

## Troubleshooting

### EasyOCR Not Available

```bash
# Check installation
python -c "import easyocr; print('OK')"

# Re-install if needed
pip uninstall easyocr torch
pip install easyocr torch
```

### Model Download Issues

```bash
# Clear model cache
rm -rf ~/.EasyOCR/model/

# Re-initialize (will re-download)
python -c "import easyocr; easyocr.Reader(['en'], gpu=False)"
```

### GPU Not Detected

```bash
# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available())"

# If False, install CUDA toolkit and PyTorch with CUDA support
```

---

## Next Steps

1. Run `/speckit.tasks` to generate implementation task list
2. Follow TDD workflow: write failing tests first
3. Implement engine following existing Tesseract/ocrmac patterns
4. Update documentation and OpenAPI spec
5. Performance testing and optimization

---

## Reference Links

- **EasyOCR Documentation**: https://github.com/JaidedAI/EasyOCR
- **Supported Languages**: https://github.com/JaidedAI/EasyOCR#supported-languages
- **PyTorch CUDA**: https://pytorch.org/get-started/locally/
- **Feature Spec**: `spec.md`
- **Data Model**: `data-model.md`
- **API Contract**: `contracts/openapi-easyocr-extension.yaml`
