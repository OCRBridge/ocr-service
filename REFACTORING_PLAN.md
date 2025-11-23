# OCR Service Modular Engine Architecture Refactoring Plan

## Overview

This document outlines the plan to refactor the OCR service into a modular architecture where each OCR engine is implemented as a standalone Python package. This refactoring will enable dynamic engine discovery via Python entry points and provide a clean, extensible architecture for adding new OCR engines.

## Architecture Decisions

Based on requirements and project discussions:

1. **Repository Structure**: Separate repositories for each component
2. **Shared Code**: Create `ocrbridge-core` package with base classes and utilities
3. **Dependencies**: Each engine package declares its own dependencies
4. **API Compatibility**: Redesign API to be engine-agnostic (breaking change, v2.0.0)

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│         OCR Bridge Service (v2.0.0)             │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │      Engine Registry                     │  │
│  │  (Entry Point Discovery)                 │  │
│  └──────────────────────────────────────────┘  │
│                    │                            │
│       ┌────────────┼────────────┐              │
│       ▼            ▼            ▼              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │Tesseract│ │ EasyOCR │ │ ocrmac  │          │
│  │ Engine  │ │ Engine  │ │ Engine  │          │
│  └─────────┘ └─────────┘ └─────────┘          │
│       │            │            │              │
│       └────────────┴────────────┘              │
│                    │                            │
│                    ▼                            │
│         ┌──────────────────────┐               │
│         │   ocrbridge-core     │               │
│         │  (Abstract Base)     │               │
│         └──────────────────────┘               │
└─────────────────────────────────────────────────┘
```

## Phase 1: Create ocrbridge-core Package

### Repository: `ocrbridge-core`

#### Directory Structure

```
ocrbridge-core/
├── src/
│   └── ocrbridge/
│       └── core/
│           ├── __init__.py
│           ├── base.py              # OCREngine abstract base class
│           ├── models.py             # Shared parameter base classes
│           ├── exceptions.py        # Common exceptions
│           └── utils/
│               ├── __init__.py
│               ├── hocr.py          # HOCR utilities
│               └── validators.py    # Base validators
├── tests/
│   ├── __init__.py
│   ├── test_base.py
│   └── test_utils.py
├── pyproject.toml
├── README.md
├── LICENSE
└── .gitignore
```

#### Key Components

**1. Abstract Base Class (`base.py`)**

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TypeVar

from .models import OCREngineParams

T = TypeVar('T', bound=OCREngineParams)

class OCREngine(ABC):
    """Abstract base class for OCR engines."""

    @abstractmethod
    def process(
        self,
        file_path: Path,
        params: T | None = None
    ) -> str:
        """
        Process a document and return HOCR XML output.

        Args:
            file_path: Path to the image or PDF file
            params: Engine-specific parameters

        Returns:
            HOCR XML as a string

        Raises:
            OCRProcessingError: If processing fails
            UnsupportedFormatError: If file format is not supported
            TimeoutError: If processing exceeds timeout
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the engine name (e.g., 'tesseract', 'easyocr')."""
        pass

    @property
    @abstractmethod
    def supported_formats(self) -> set[str]:
        """Return set of supported file extensions (e.g., {'.jpg', '.png', '.pdf'})."""
        pass
```

**2. Base Models (`models.py`)**

```python
from pydantic import BaseModel

class OCREngineParams(BaseModel):
    """Base class for all engine-specific parameters."""

    class Config:
        extra = "forbid"  # Reject unknown parameters
```

**3. Exceptions (`exceptions.py`)**

```python
class OCRBridgeError(Exception):
    """Base exception for ocrbridge."""
    pass

class OCRProcessingError(OCRBridgeError):
    """Raised when OCR processing fails."""
    pass

class UnsupportedFormatError(OCRBridgeError):
    """Raised when file format is not supported by engine."""
    pass

class EngineNotAvailableError(OCRBridgeError):
    """Raised when requested engine is not installed or available."""
    pass

class InvalidParametersError(OCRBridgeError):
    """Raised when engine parameters are invalid."""
    pass
```

**4. HOCR Utilities (`utils/hocr.py`)**

Extract HOCR helper functions from current codebase:
- `create_hocr_page()`
- `create_hocr_line()`
- `create_hocr_word()`
- HOCR document wrapper functions

#### pyproject.toml

```toml
[project]
name = "ocrbridge-core"
version = "0.1.0"
description = "Core interfaces and utilities for OCR Bridge engine packages"
authors = [{name = "Your Name", email = "your.email@example.com"}]
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.11"

dependencies = [
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
    "pyright>=1.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pyright]
typeCheckingMode = "strict"
pythonVersion = "3.11"
```

#### README.md

Include:
- Purpose of the package
- Installation instructions
- How to implement a new engine
- Entry point registration guide
- API reference

#### Tasks

- [ ] Create GitHub repository `ocrbridge-core`
- [ ] Set up project structure and boilerplate
- [ ] Implement abstract base class with comprehensive docstrings
- [ ] Define exception hierarchy
- [ ] Extract and refactor HOCR utilities from main service
- [ ] Write unit tests (target: 90%+ coverage)
- [ ] Set up CI/CD (GitHub Actions)
- [ ] Write comprehensive README with examples
- [ ] Publish v0.1.0 to PyPI

---

## Phase 2: Create Engine Packages

### 2.1 ocrbridge-tesseract

#### Repository: `ocrbridge-tesseract`

**Directory Structure:**

```
ocrbridge-tesseract/
├── src/
│   └── ocrbridge/
│       └── engines/
│           └── tesseract/
│               ├── __init__.py
│               ├── engine.py        # TesseractEngine class
│               ├── models.py         # TesseractParams
│               └── converter.py     # PDF to image conversion
├── tests/
│   ├── __init__.py
│   ├── test_engine.py
│   ├── test_params.py
│   └── fixtures/
│       ├── sample.jpg
│       ├── sample.pdf
│       └── sample.png
├── pyproject.toml
├── README.md
├── LICENSE
└── .gitignore
```

**Key Implementation:**

```python
# engine.py
from pathlib import Path
from ocrbridge.core import OCREngine
from ocrbridge.core.exceptions import OCRProcessingError
from .models import TesseractParams

class TesseractEngine(OCREngine):
    """Tesseract OCR engine implementation."""

    @property
    def name(self) -> str:
        return "tesseract"

    @property
    def supported_formats(self) -> set[str]:
        return {".jpg", ".jpeg", ".png", ".pdf", ".tiff", ".tif"}

    def process(
        self,
        file_path: Path,
        params: TesseractParams | None = None
    ) -> str:
        """Process document using Tesseract OCR."""
        # Implementation from current src/services/ocr/tesseract.py
        pass
```

```python
# models.py
from ocrbridge.core.models import OCREngineParams
from pydantic import Field, field_validator

class TesseractParams(OCREngineParams):
    """Tesseract-specific parameters."""

    lang: str | None = Field(
        default="eng",
        description="Language codes (e.g., 'eng', 'eng+fra'). Max 5 languages.",
    )
    psm: int | None = Field(
        default=3,
        ge=0,
        le=13,
        description="Page segmentation mode",
    )
    oem: int | None = Field(
        default=1,
        ge=0,
        le=3,
        description="OCR engine mode",
    )
    dpi: int | None = Field(
        default=300,
        ge=70,
        le=2400,
        description="DPI for PDF conversion",
    )

    @field_validator("lang")
    @classmethod
    def validate_languages(cls, v: str | None) -> str | None:
        if v is None:
            return v
        langs = v.split("+")
        if len(langs) > 5:
            raise ValueError("Maximum 5 languages allowed")
        return v
```

**pyproject.toml:**

```toml
[project]
name = "ocrbridge-tesseract"
version = "0.1.0"
description = "Tesseract OCR engine for OCR Bridge"
dependencies = [
    "ocrbridge-core>=0.1.0",
    "pytesseract>=0.3.13",
    "pdf2image>=1.17.0",
    "Pillow>=10.0.0",
]

[project.entry-points."ocrbridge.engines"]
tesseract = "ocrbridge.engines.tesseract:TesseractEngine"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Tasks:**

- [ ] Create GitHub repository `ocrbridge-tesseract`
- [ ] Extract Tesseract engine from main service
- [ ] Implement TesseractEngine class inheriting from OCREngine
- [ ] Define TesseractParams model
- [ ] Configure entry point in pyproject.toml
- [ ] Write comprehensive tests
- [ ] Document Tesseract-specific features
- [ ] Publish v0.1.0 to PyPI

---

### 2.2 ocrbridge-easyocr

#### Repository: `ocrbridge-easyocr`

**Directory Structure:**

```
ocrbridge-easyocr/
├── src/
│   └── ocrbridge/
│       └── engines/
│           └── easyocr/
│               ├── __init__.py
│               ├── engine.py        # EasyOCREngine class
│               ├── models.py         # EasyOCRParams
│               └── converter.py     # HOCR conversion
├── tests/
│   ├── __init__.py
│   ├── test_engine.py
│   ├── test_gpu.py
│   └── fixtures/
├── pyproject.toml
├── README.md
├── LICENSE
└── .gitignore
```

**Key Features:**

- GPU auto-detection and fallback
- Reader instance caching for performance
- 80+ language support
- Deep learning-based detection

**pyproject.toml:**

```toml
[project]
name = "ocrbridge-easyocr"
version = "0.1.0"
description = "EasyOCR engine for OCR Bridge"
dependencies = [
    "ocrbridge-core>=0.1.0",
    "easyocr>=1.7.2",
    "torch>=2.1.0",
    "pdf2image>=1.17.0",
    "Pillow>=10.0.0",
]

[project.entry-points."ocrbridge.engines"]
easyocr = "ocrbridge.engines.easyocr:EasyOCREngine"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Tasks:**

- [ ] Create GitHub repository `ocrbridge-easyocr`
- [ ] Extract EasyOCR engine from main service
- [ ] Implement EasyOCREngine with GPU support
- [ ] Define EasyOCRParams model
- [ ] Implement HOCR conversion from EasyOCR results
- [ ] Configure entry point
- [ ] Write tests including GPU detection
- [ ] Document GPU usage and language support
- [ ] Publish v0.1.0 to PyPI

---

### 2.3 ocrbridge-ocrmac

#### Repository: `ocrbridge-ocrmac`

**Directory Structure:**

```
ocrbridge-ocrmac/
├── src/
│   └── ocrbridge/
│       └── engines/
│           └── ocrmac/
│               ├── __init__.py
│               ├── engine.py        # OcrmacEngine class
│               ├── models.py         # OcrmacParams
│               └── converter.py     # HOCR conversion
├── tests/
│   ├── __init__.py
│   ├── test_engine.py
│   └── fixtures/
├── pyproject.toml
├── README.md
├── LICENSE
└── .gitignore
```

**Platform Requirements:**

- macOS only
- Apple Vision Framework
- Platform validation in engine initialization

**pyproject.toml:**

```toml
[project]
name = "ocrbridge-ocrmac"
version = "0.1.0"
description = "ocrmac (Apple Vision) engine for OCR Bridge"
dependencies = [
    "ocrbridge-core>=0.1.0",
    "ocrmac>=0.2.2",
    "pdf2image>=1.17.0",
    "Pillow>=10.0.0",
]

[project.entry-points."ocrbridge.engines"]
ocrmac = "ocrbridge.engines.ocrmac:OcrmacEngine"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

# Platform-specific marker
[tool.hatch.build.targets.wheel]
only-include = ["src"]

[tool.hatch.metadata]
# Note: Platform restriction enforced at runtime in engine initialization
```

**Tasks:**

- [ ] Create GitHub repository `ocrbridge-ocrmac`
- [ ] Extract ocrmac engine from main service
- [ ] Implement OcrmacEngine with platform validation
- [ ] Define OcrmacParams with RecognitionLevel enum
- [ ] Implement coordinate system conversion (bottom-left to top-left)
- [ ] Configure entry point
- [ ] Write tests with macOS markers
- [ ] Document macOS requirements and LiveText features
- [ ] Publish v0.1.0 to PyPI

---

## Phase 3: Refactor Main OCR Service

### 3.1 Update Dependencies

**Current pyproject.toml → Updated:**

```toml
[project]
name = "ocrbridge-service"
version = "2.0.0"  # BREAKING CHANGE
description = "OCR Bridge Service with pluggable engine architecture"
requires-python = ">=3.11"

dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.4.0",
    "pydantic-settings>=2.0.0",
    "redis>=5.0.0",
    "structlog>=23.2.0",
    "prometheus-client>=0.19.0",
    "python-multipart>=0.0.6",
    "python-magic>=0.4.27",
    "ocrbridge-core>=0.1.0",  # NEW: Core package
]

[project.optional-dependencies]
# Engine installations
tesseract = ["ocrbridge-tesseract>=0.1.0"]
easyocr = ["ocrbridge-easyocr>=0.1.0"]
ocrmac = ["ocrbridge-ocrmac>=0.1.0"]
all-engines = [
    "ocrbridge-tesseract>=0.1.0",
    "ocrbridge-easyocr>=0.1.0",
    "ocrbridge-ocrmac>=0.1.0",
]

# Development
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "httpx>=0.25.0",
    "ruff>=0.1.0",
    "pyright>=1.1.0",
]
```

### 3.2 Implement Dynamic Engine Discovery

**New: `src/services/ocr/registry.py`**

```python
from importlib.metadata import entry_points
from typing import Type
from ocrbridge.core import OCREngine
from ocrbridge.core.exceptions import EngineNotAvailableError

class EngineRegistry:
    """Discovers and manages OCR engines via entry points."""

    def __init__(self):
        self._engines: dict[str, Type[OCREngine]] = {}
        self._instances: dict[str, OCREngine] = {}
        self._discover_engines()

    def _discover_engines(self) -> None:
        """Discover engines from entry points."""
        discovered = entry_points(group="ocrbridge.engines")

        for ep in discovered:
            try:
                engine_class = ep.load()
                if not issubclass(engine_class, OCREngine):
                    continue
                self._engines[ep.name] = engine_class
            except Exception as e:
                # Log but don't fail if an engine can't be loaded
                logger.warning(f"Failed to load engine {ep.name}: {e}")

    def get_engine(self, name: str) -> OCREngine:
        """Get engine instance by name (lazy loading)."""
        if name not in self._engines:
            raise EngineNotAvailableError(f"Engine '{name}' not found")

        if name not in self._instances:
            self._instances[name] = self._engines[name]()

        return self._instances[name]

    def list_engines(self) -> list[str]:
        """List all available engine names."""
        return list(self._engines.keys())

    def get_param_model(self, engine_name: str) -> Type:
        """Get parameter model class for an engine."""
        engine_class = self._engines.get(engine_name)
        if not engine_class:
            raise EngineNotAvailableError(f"Engine '{engine_name}' not found")

        # Extract from type hints
        process_method = engine_class.process
        type_hints = get_type_hints(process_method)
        return type_hints.get("params").__args__[0]  # Extract from Optional[ParamType]
```

### 3.3 Redesign API (v2)

**Remove Files:**
- `src/api/routes/sync.py` (old engine-specific endpoints)
- `src/services/ocr/tesseract.py`
- `src/services/ocr/easyocr.py`
- `src/services/ocr/ocrmac.py`
- `src/models/ocr_params.py`

**New: `src/api/routes/v2/ocr.py`**

```python
from fastapi import APIRouter, UploadFile, Query, Depends
from typing import Annotated
from pydantic import BaseModel, create_model

router = APIRouter(prefix="/v2/ocr", tags=["OCR v2"])

@router.post("/process")
async def process_document(
    file: UploadFile,
    engine: Annotated[str, Query(description="OCR engine to use")],
    registry: Annotated[EngineRegistry, Depends(get_registry)],
    params: dict | None = None,
) -> OCRResponse:
    """
    Process a document using specified OCR engine.

    - **engine**: tesseract, easyocr, or ocrmac
    - **params**: Engine-specific parameters (validated against engine's param model)
    """
    # Get engine
    ocr_engine = registry.get_engine(engine)

    # Validate params
    param_model = registry.get_param_model(engine)
    validated_params = param_model(**params) if params else None

    # Process
    result = await asyncio.wait_for(
        asyncio.to_thread(ocr_engine.process, file_path, validated_params),
        timeout=30.0
    )

    return OCRResponse(hocr=result, engine=engine)

@router.post("/jobs")
async def create_job(
    file: UploadFile,
    engine: str,
    params: dict | None = None,
) -> JobResponse:
    """Create async OCR job."""
    # Similar to /process but enqueues to Redis
    pass

@router.get("/engines")
async def list_engines(
    registry: Annotated[EngineRegistry, Depends(get_registry)]
) -> list[EngineInfo]:
    """List all available OCR engines."""
    engines = registry.list_engines()
    return [
        EngineInfo(
            name=name,
            available=True,
            supported_formats=registry.get_engine(name).supported_formats,
        )
        for name in engines
    ]

@router.get("/engines/{engine}/schema")
async def get_engine_schema(
    engine: str,
    registry: Annotated[EngineRegistry, Depends(get_registry)],
) -> dict:
    """Get JSON schema for engine parameters."""
    param_model = registry.get_param_model(engine)
    return param_model.model_json_schema()
```

**New: `src/api/routes/v2/jobs.py`**

```python
# Updated job management for v2
# Similar to current implementation but engine-agnostic
```

### 3.4 Update Main Application

**`src/main.py`:**

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
from .api.routes.v2 import ocr, jobs
from .services.ocr.registry import EngineRegistry

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.engine_registry = EngineRegistry()
    logger.info(f"Discovered engines: {app.state.engine_registry.list_engines()}")

    yield

    # Shutdown
    pass

app = FastAPI(
    title="OCR Bridge Service",
    version="2.0.0",  # Breaking change
    lifespan=lifespan,
)

app.include_router(ocr.router)
app.include_router(jobs.router)
```

### 3.5 Update Tests

**Test Structure:**

```
tests/
├── unit/
│   ├── test_registry.py              # NEW: Entry point discovery
│   ├── test_api_v2.py                # NEW: v2 endpoints
│   └── (remove engine-specific tests)
├── integration/
│   ├── test_v2_endpoints.py          # NEW: Integration tests
│   ├── test_engine_discovery.py      # NEW: Mock entry points
│   └── test_job_workflow_v2.py       # Updated for v2
├── contract/
│   └── test_api_v2_contract.py       # NEW: OpenAPI validation
└── performance/
    └── test_v2_latency.py             # Updated for v2
```

**Tasks:**

- [ ] Update pyproject.toml with new dependencies
- [ ] Implement EngineRegistry with entry point discovery
- [ ] Create v2 API routes (engine-agnostic)
- [ ] Update main.py with registry initialization
- [ ] Remove old engine implementations
- [ ] Remove old API routes
- [ ] Write tests for engine discovery
- [ ] Write integration tests for v2 API
- [ ] Update contract tests
- [ ] Update performance tests
- [ ] Update Prometheus metrics for v2

---

## Phase 4: Documentation

### 4.1 Engine Developer Guide

**Create: `docs/ENGINE_DEVELOPMENT.md`**

Topics:
- Creating a new engine package
- Implementing the OCREngine interface
- Defining parameter models with Pydantic
- Registering via entry points
- Testing guidelines
- Publishing to PyPI
- Example: Complete minimal engine implementation

### 4.2 Migration Guide

**Create: `docs/MIGRATION_V1_TO_V2.md`**

Topics:
- Breaking changes summary
- API endpoint mapping (v1 → v2)
- Parameter format changes
- Code examples (before/after)
- Installation changes
- Deprecation timeline

### 4.3 API Documentation

**Update: `docs/API.md`**

- v2 endpoint reference
- Engine discovery endpoints
- Dynamic parameter validation
- Error responses
- OpenAPI schema

### 4.4 Deployment Guide

**Update: `docs/DEPLOYMENT.md`**

Topics:
- Installing specific engines
- Docker multi-stage builds
- Platform-specific deployments (macOS for ocrmac)
- Engine discovery in containerized environments
- Production recommendations

### 4.5 README Updates

**Update: `README.md`**

- Quick start with v2 API
- Engine installation instructions
- Available engines and their features
- Links to detailed documentation

**Tasks:**

- [ ] Write comprehensive engine development guide
- [ ] Create migration guide from v1 to v2
- [ ] Document v2 API with examples
- [ ] Update deployment documentation
- [ ] Update main README
- [ ] Add architecture diagrams
- [ ] Create troubleshooting guide

---

## Implementation Order

### Recommended Sequence

1. **ocrbridge-core** (1-2 days)
   - Foundation for all other packages
   - Must be published to PyPI first
   - Enables parallel development of engines

2. **ocrbridge-tesseract** (1-2 days)
   - Simplest engine (no GPU, no platform restrictions)
   - Validates the approach
   - Reference implementation for other engines

3. **ocrbridge-easyocr** (2-3 days)
   - GPU detection adds complexity
   - Stateful Reader caching
   - Tests the approach with heavier dependencies

4. **ocrbridge-ocrmac** (1-2 days)
   - Platform-specific constraints
   - Validates conditional availability
   - Coordinate system conversion

5. **Main Service Refactor** (3-4 days)
   - Entry point discovery implementation
   - v2 API design and implementation
   - Remove old code
   - Integration testing

6. **Documentation** (2-3 days)
   - Engine development guide
   - Migration guide
   - API documentation
   - Deployment guide

**Total Estimated Time: 10-16 days**

---

## Testing Strategy

### Unit Tests

**Per-Package Testing:**
- Each engine package: Isolated unit tests with mocked dependencies
- ocrbridge-core: Test abstract interface, utilities, exceptions
- Main service: Test registry, API routes, job management

**Coverage Targets:**
- Core package: 95%+
- Engine packages: 90%+
- Main service: 85%+

### Integration Tests

**Cross-Package Testing:**
- Main service with real engine packages installed
- Entry point discovery with multiple engines
- Parameter validation across engines
- Error handling and exceptions

### Contract Tests

**API Validation:**
- OpenAPI schema compliance
- Request/response format validation
- Error response format consistency
- Backward compatibility checks (ensure v1 is fully removed)

### Platform Tests

**Platform-Specific:**
- macOS-only tests for ocrmac
- GPU detection tests for EasyOCR
- Platform markers in pytest

**Markers:**
```python
@pytest.mark.macos  # macOS only
@pytest.mark.gpu    # Requires GPU
@pytest.mark.slow   # Slow tests
```

### Performance Tests

**Benchmarks:**
- Endpoint latency (v2)
- Engine loading time (lazy vs eager)
- Memory usage with multiple engines
- Concurrent request handling

---

## Rollout Considerations

### Breaking Changes

**API Version Bump: 1.x → 2.0.0**

**Removed:**
- `/sync/tesseract` → Use `/v2/ocr/process?engine=tesseract`
- `/sync/easyocr` → Use `/v2/ocr/process?engine=easyocr`
- `/sync/ocrmac` → Use `/v2/ocr/process?engine=ocrmac`
- `/upload/tesseract` → Use `/v2/ocr/jobs` with `engine` field
- `/upload/easyocr` → Use `/v2/ocr/jobs` with `engine` field
- `/upload/ocrmac` → Use `/v2/ocr/jobs` with `engine` field

**Added:**
- `/v2/ocr/process` - Unified sync endpoint
- `/v2/ocr/jobs` - Unified async job creation
- `/v2/engines` - Engine discovery
- `/v2/engines/{engine}/schema` - Parameter schema

### Deployment Strategy

**Option 1: Big Bang (Recommended for this refactor)**
- Deploy v2.0.0 with all breaking changes
- Update all clients before deployment
- No backward compatibility
- Clean break, simpler codebase

**Option 2: Gradual Migration (Not recommended)**
- Run v1 and v2 endpoints side-by-side
- Adds complexity
- Longer transition period
- Requires maintaining old code

### Client Migration

**Required Client Changes:**

```python
# Before (v1)
response = requests.post(
    "http://api/sync/tesseract",
    files={"file": open("doc.pdf", "rb")},
    data={"lang": "eng", "psm": 3}
)

# After (v2)
response = requests.post(
    "http://api/v2/ocr/process",
    files={"file": open("doc.pdf", "rb")},
    params={"engine": "tesseract"},
    json={"lang": "eng", "psm": 3}
)
```

### Installation Changes

**Before (v1):**
```bash
pip install ocrbridge-service[easyocr]
```

**After (v2):**
```bash
pip install ocrbridge-service[easyocr]
# OR
pip install ocrbridge-service ocrbridge-easyocr
```

### Docker Considerations

**Multi-stage Build Example:**

```dockerfile
# Build stage for Tesseract-only
FROM python:3.11-slim AS tesseract
RUN apt-get update && apt-get install -y tesseract-ocr
COPY requirements.txt .
RUN pip install ocrbridge-service[tesseract]

# Build stage for EasyOCR (larger, with PyTorch)
FROM python:3.11 AS easyocr
RUN pip install ocrbridge-service[easyocr]

# Final stage - choose your engine(s)
FROM tesseract AS final
# OR: FROM easyocr AS final
# OR: Install multiple engines
```

---

## Risk Mitigation

### Technical Risks

**1. Entry Point Discovery Failures**
- **Risk**: Engines not discovered at runtime
- **Mitigation**: Comprehensive logging, fallback to manual registration
- **Testing**: Mock entry points in tests

**2. Dependency Conflicts**
- **Risk**: PyTorch vs other packages
- **Mitigation**: Optional dependencies, clear documentation
- **Testing**: Test with different engine combinations

**3. Performance Regression**
- **Risk**: Lazy loading overhead
- **Mitigation**: Benchmark before/after, optimize hot paths
- **Testing**: Performance tests in CI

**4. Platform-Specific Issues**
- **Risk**: ocrmac fails on non-macOS
- **Mitigation**: Runtime platform validation, graceful degradation
- **Testing**: Platform markers, CI on multiple platforms

### Operational Risks

**1. Breaking Changes Impact**
- **Risk**: Client applications break
- **Mitigation**: Clear migration guide, versioned API
- **Communication**: Release notes, deprecation warnings

**2. Deployment Complexity**
- **Risk**: New dependency management
- **Mitigation**: Detailed deployment guide, Docker examples
- **Testing**: Test deployment scenarios

**3. Package Publishing**
- **Risk**: PyPI publishing issues
- **Mitigation**: Test on TestPyPI first, CI/CD automation
- **Documentation**: Publishing checklist

---

## Success Criteria

### Technical Metrics

- [ ] All engine packages published to PyPI
- [ ] Main service successfully discovers engines via entry points
- [ ] v2 API functional with all engines
- [ ] Test coverage >85% across all packages
- [ ] CI/CD pipelines green for all repositories
- [ ] No performance regression (within 10% of v1)

### Documentation Metrics

- [ ] Engine development guide complete
- [ ] Migration guide published
- [ ] API documentation updated
- [ ] Deployment guide includes Docker examples
- [ ] README updated with v2 examples

### Operational Metrics

- [ ] Successful deployment to staging
- [ ] All test clients migrated to v2
- [ ] Monitoring and metrics functional
- [ ] Error rates within acceptable limits

---

## Appendix

### Repository URLs

To be created:
- `https://github.com/yourusername/ocrbridge-core`
- `https://github.com/yourusername/ocrbridge-tesseract`
- `https://github.com/yourusername/ocrbridge-easyocr`
- `https://github.com/yourusername/ocrbridge-ocrmac`

### PyPI Packages

To be published:
- `ocrbridge-core` (0.1.0)
- `ocrbridge-tesseract` (0.1.0)
- `ocrbridge-easyocr` (0.1.0)
- `ocrbridge-ocrmac` (0.1.0)
- `ocrbridge-service` (2.0.0)

### Key Dependencies

**Core:**
- Python 3.11+
- Pydantic 2.0+

**Tesseract:**
- pytesseract 0.3.13+
- pdf2image 1.17.0+

**EasyOCR:**
- easyocr 1.7.2+
- torch 2.1.0+

**ocrmac:**
- ocrmac 0.2.2+
- macOS 12+ (runtime requirement)

### Contact and Support

- **Issues**: GitHub Issues on respective repositories
- **Discussions**: GitHub Discussions for architecture questions
- **Security**: security@yourdomain.com

---

## Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2025-11-23 | 1.0 | Initial refactoring plan |

---

**Last Updated**: 2025-11-23
**Plan Version**: 1.0
**Status**: Draft
