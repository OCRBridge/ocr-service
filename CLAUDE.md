# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RESTful OCR API service with a modular plugin architecture powered by datenzar OCR Bridge packages. The service uses Python entry points for dynamic engine discovery, allowing OCR engines to be installed independently as PyPI packages.

**Key Architecture Principles:**
- **Plugin-based engines**: OCR engines (Tesseract, EasyOCR, ocrmac) are separate PyPI packages discovered via Python entry points in the `ocrbridge.engines` group
- **Dynamic engine routes**: Per-engine endpoints like `/v2/ocr/<engine>/process` are generated at startup
- **Zero-code engine addition**: Installing a new engine package automatically makes it available in the API
- **Parameter validation**: Each engine provides its own Pydantic model for parameter validation via type hints or `__param_model__` class attribute

## Development Commands

### Package Management
This project uses `uv` for dependency management (faster than pip):

```bash
# Install all dependencies including dev tools
uv sync --group dev --all-extras

# Install with specific engine only
uv sync --group dev --extra tesseract
```

### Running the Service
```bash
# Development server with auto-reload
make dev
# or
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing

**Important**: Tests are marked with two custom markers:
- `@pytest.mark.slow` - Slow tests (EasyOCR integration, skipped by default in CI)
- `@pytest.mark.macos` - macOS-only tests (ocrmac engine, skipped on Linux)

```bash
# Run fast tests only (excluding slow and macOS-only)
make test              # Uses: pytest -m "not macos and not slow"

# Run specific test types
make test-unit         # Unit tests only
make test-integration  # Integration tests only
make test-e2e          # E2E tests (excluding slow)
make test-e2e-slow     # Slow E2E tests (EasyOCR)

# Run all tests including slow ones
make test-slow         # Uses: pytest --run-slow
make test-all          # All tests including macOS (if on macOS)

# Coverage reports
make test-coverage      # HTML + XML coverage (excludes slow tests)
make test-coverage-full # Full coverage including slow tests

# Run a single test file
uv run pytest tests/unit/services/ocr/test_registry_v2.py -v

# Run a single test function
uv run pytest tests/unit/services/ocr/test_registry_v2.py::test_discover_engines -v

# Run with verbose output and stop on first failure
uv run pytest tests/path/to/test.py -xvs
```

### Code Quality
```bash
make lint           # Check code with ruff
make format         # Auto-format code with ruff
make format-check   # Check if code is formatted (CI)
make lint-fix       # Auto-fix linting issues
make typecheck      # Run ty type checker
make pre-commit     # Run all pre-commit hooks
```

### Docker
The project uses multi-stage Docker builds with two targets:
- **lite**: Tesseract only (~500MB)
- **full**: Tesseract + EasyOCR (~2.5GB, includes PyTorch)

```bash
# Build both flavors
make docker-build-lite   # Build lite image
make docker-build-full   # Build full image (default)
make docker-build-all    # Build both

# Run with docker-compose (combines base + flavor-specific config)
make docker-compose-lite-up    # Start lite flavor
make docker-compose-full-up    # Start full flavor (default)
make docker-compose-lite-down  # Stop lite
make docker-compose-full-down  # Stop full

# Standard docker commands
make docker-up      # Start services (uses full flavor)
make docker-down    # Stop services
make docker-logs    # View logs
```

## Project Structure

```
src/
├── api/
│   ├── routes/
│   │   └── v2/
│   │       └── dynamic_routes.py   # V2 dynamic per-engine OCR endpoints
│   └── middleware/
│       ├── error_handler.py        # Global error handling
│       └── logging.py              # Request/response logging
├── services/
│   ├── ocr/
│   │   └── registry_v2.py          # Engine discovery via entry points
│   ├── file_handler.py             # Temporary file management
│   └── cleanup.py                  # Background cleanup task
├── models/
│   ├── responses.py                # API response models
│   └── upload.py                   # File upload models
├── utils/
│   ├── hocr.py                     # HOCR validation and utilities
│   ├── validators.py               # File size/type validation
│   └── metrics.py                  # Prometheus metrics
└── main.py                         # FastAPI app with lifespan management

tests/
├── conftest.py                     # Shared fixtures (mock engines, file bytes)
├── mocks/
│   ├── mock_engines.py             # Mock engine implementations
│   └── mock_entry_points.py        # Mock entry point factory
├── unit/                           # Pure unit tests (no I/O)
├── integration/                    # Integration tests (API, file I/O)
├── e2e/                            # End-to-end tests (real engines)
└── fixtures/                       # Sample images and expected outputs
```

## Core Architecture Patterns

### 1. Engine Discovery (registry_v2.py)

The `EngineRegistry` class discovers engines via Python entry points with **zero hardcoded engine names**:

```python
# On startup, EngineRegistry calls _discover_engines()
# which loads all entry points from group "ocrbridge.engines"
discovered = entry_points(group="ocrbridge.engines")

# Each entry point provides an OCREngine subclass
engine_class = entry_point.load()  # e.g., TesseractEngine

# Parameter models discovered via GENERIC naming convention:
# 1. Get engine's module (e.g., ocrbridge.engines.tesseract.engine)
# 2. Import parent module (e.g., ocrbridge.engines.tesseract)
# 3. Look for {EngineName}Params (e.g., TesseractEngine → TesseractParams)
# 4. Verify it's a subclass of OCREngineParams
# 5. Fallback to __param_model__ class attribute
# 6. Fallback to type hints on process() method

# This works for ANY new engine without code changes!
```

**Key methods:**
- `get_engine(name)` - Lazy loads engine instance
- `list_engines()` - Returns available engine names
- `validate_params(engine, params)` - Validates using engine's Pydantic model
- `get_param_model(engine)` - Returns parameter model class or None

**Architecture Principle**: The registry never imports or checks for specific engine names. All discovery is generic and works for any conforming engine package.

### 2. Dynamic OCR Endpoints (api/routes/v2/dynamic_routes.py)

Per-engine endpoints are generated for each discovered OCR engine, with parameters exposed directly in the OpenAPI schema:

```python
POST /v2/ocr/<engine>/process
- file: UploadFile (required)
- **dynamic_params**: Individual Form fields matching engine's Pydantic model
```

**Flow:**
1. Discover engines via entry points at startup
2. Register `/v2/ocr/<engine>/process` for each engine
3. Use `inspect` module to dynamically generate the route handler signature
4. Convert engine's Pydantic model fields into `Annotated[T, Form()]` parameters
5. Validates incoming form data against the engine's model automatically via FastAPI
6. Process in thread pool with a 30s timeout
7. Return HOCR + metadata
8. Cleanup temp file

### 3. Testing with Mock Engines

Tests use mock engines to avoid requiring actual OCR binaries:

```python
# conftest.py provides mock_engine_registry fixture
# which patches entry_points to return MockTesseractEngine and MockEasyOCREngine

@pytest.fixture
def mock_engine_registry():
    engines = {"tesseract": MockTesseractEngine, "easyocr": MockEasyOCREngine}
    mock_ep = mock_entry_points_factory(engines)

    with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
        yield EngineRegistry()

# Usage in tests
def test_endpoint(client, mock_engine_registry):
    # client fixture injects mock_engine_registry into app.state
    response = client.post("/v2/ocr/process", ...)
```

**Important**: Tests bypass the lifespan startup to inject a mock registry and explicitly call `register_engine_routes(app, registry)` to include dynamic routes.

### 4. Background Cleanup Task

The `CleanupService` runs hourly to remove expired temporary files:

```python
# Started in lifespan context (main.py)
cleanup_task = asyncio.create_task(cleanup_task_runner())
app.state.cleanup_task = cleanup_task

# Cancelled gracefully on shutdown
cleanup_task.cancel()
```

## Clean Architecture: Core vs. Engine Responsibilities

### **ocrbridge-core (Base Abstractions)**
- **Defines contracts**: `OCREngine` base class, `OCREngineParams` base model
- **Provides generic HOCR utilities**: `parse_hocr()`, `validate_hocr()`, `extract_bbox()`
- **NO engine-specific code**: No imports from engine packages, no engine name checks
- **HOCR validation only**: Core validates HOCR output but doesn't generate it

### **Engine Packages (Implementations)**
- **HOCR generation**: Each engine is responsible for producing valid HOCR XML from its native output
- **Parameter validation**: Each engine defines its own `{EngineName}Params` model
- **Self-contained**: Engines may have internal utilities (e.g., EasyOCR's `hocr.py` for format conversion)

**Example**: EasyOCR's native output is `[(bbox, text, confidence), ...]`. The EasyOCR engine package contains `hocr.to_hocr()` to convert this to HOCR. Tesseract natively outputs HOCR, so it needs no conversion.

## Engine Development

To add a new OCR engine:

1. Create package depending on `ocrbridge-core>=2.0.0`
2. Implement `OCREngine` from `ocrbridge.core`:
   ```python
   from ocrbridge.core import OCREngine, OCREngineParams
   from pathlib import Path

   class MyEngineParams(OCREngineParams):
       """Parameters for MyEngine."""
       param1: str
       param2: int = 100

   class MyEngine(OCREngine):
       """MyEngine OCR implementation."""

       @property
       def name(self) -> str:
           return "myengine"

       @property
       def supported_formats(self) -> set[str]:
           return {".jpg", ".png", ".pdf"}

       def process(self, file_path: Path, params: OCREngineParams | None = None) -> str:
           """Process document and return HOCR XML.

           This method MUST return valid HOCR XML. Use ocrbridge.core.utils
           for validation, but conversion from native format is engine's job.
           """
           # Your OCR processing logic here
           # Must return HOCR XML string
           return hocr_xml
   ```

3. Export both classes from package's `__init__.py`:
   ```python
   # src/ocrbridge/engines/myengine/__init__.py
   from .engine import MyEngine
   from .models import MyEngineParams

   __all__ = ["MyEngine", "MyEngineParams"]
   ```

4. Add entry point in `pyproject.toml`:
   ```toml
   [project.entry-points."ocrbridge.engines"]
   myengine = "ocrbridge.engines.myengine:MyEngine"
   ```

5. **Naming Convention**: Export `{EngineName}Params` from package root for automatic discovery
   - `TesseractEngine` → `TesseractParams`
   - `EasyOCREngine` → `EasyOCRParams`
   - `MyEngine` → `MyParams`

The service will automatically discover and register the engine on startup with zero code changes!

## Configuration

Environment variables (see `src/config.py`):

```bash
# API
MAX_UPLOAD_SIZE_MB=25             # Max file size for uploads
SYNC_MAX_FILE_SIZE_MB=5           # Max file size for sync endpoints
SYNC_TIMEOUT_SECONDS=30           # Timeout for sync OCR requests

# Logging
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json                   # json or console

# Storage
JOB_EXPIRATION_HOURS=48           # How long to keep job results
```

**Note**: Engine-specific parameters (e.g., Tesseract lang/psm) are NOT in config. They're passed per-request via the API and validated against each engine's Pydantic model.

## Important Development Notes

### Testing Guidelines
- **Mock by default**: Unit and integration tests use mock engines to avoid binary dependencies
- **E2E for real engines**: E2E tests use real engines but are marked `@pytest.mark.slow`
- **Mark platform-specific tests**: Use `@pytest.mark.macos` for ocrmac tests
- **File fixtures**: Use `sample_jpeg_bytes`, `sample_png_bytes`, `sample_pdf_bytes` from conftest.py
- **Client fixture**: Automatically injects mock registry into app state

### Code Quality Standards
- **Line length**: 100 characters (ruff config)
- **Type hints**: Required for all function signatures (ty enforces)
- **Import order**: Ruff enforces isort-compatible ordering (E, F, I, N, W rules)
- **Async patterns**: Use `asyncio.to_thread()` for blocking OCR operations
- **Structured logging**: Use structlog with JSON output in production

### Common Patterns
- **Temporary files**: Always use context managers and `missing_ok=True` for cleanup
- **Registry access**: Use `Depends(get_registry)` in route handlers
- **Error handling**: Raise HTTPException with appropriate status codes
- **Background tasks**: Use asyncio.create_task() and cancel gracefully in lifespan

### Anti-patterns to Avoid
- Don't access `_engine_classes`, `_engine_instances`, `_param_models` directly (use public methods)
- Don't skip file validation in endpoints (security issue)
- Don't block async endpoints with synchronous I/O (use thread pool)
- **Don't hardcode engine names** anywhere outside tests (use registry.list_engines())
- **Don't add engine-specific code to ocrbridge-core** (violates plugin architecture)
- **Don't put engine-specific utilities in service layer** (belongs in engine packages)
- Don't commit test output files (add to .gitignore)

### Clean Architecture Checklist
✅ Registry uses generic naming convention for param model discovery
✅ Core package has no engine-specific imports or logic
✅ HOCR generation is each engine's responsibility
✅ Service layer doesn't know about specific engines
✅ Config has no engine-specific parameters
✅ Adding a new engine requires ZERO service code changes

## API Endpoints

```bash
# Health check
GET /health

# Prometheus metrics
GET /metrics

# List available engines
GET /v2/ocr/engines
# Returns: {"engines": ["tesseract", "easyocr"], "count": 2, "details": [...]}

# Get engine parameter schema
GET /v2/ocr/engines/{engine_name}/schema
# Returns: JSON schema for engine's Pydantic parameter model

# Per-engine processing
POST /v2/ocr/tesseract/process
    form: file=<UploadFile>, lang="eng", psm=6

POST /v2/ocr/easyocr/process
    form: file=<UploadFile>, languages=["en"], text_threshold=0.7

# Notes
- Parameters are passed as standard `multipart/form-data` fields.
- Validated against the engine's model (exposed in OpenAPI).
- Response: {"hocr": "...", "processing_duration_seconds": 2.5, "engine": "tesseract", "pages": 1}
```

## Deployment

### Production Considerations
- Service is **fully stateless** - safe for horizontal scaling
- Install only needed engines to minimize image size
- Use GPU-enabled base image for EasyOCR performance
- Health endpoint: `/health` (liveness/readiness probes)
- Metrics endpoint: `/metrics` (Prometheus scraping)
- **ocrmac not compatible with Docker** (requires native macOS, not Linux containers)

### Multi-stage Docker Strategy
- **lite target**: Production deployments with Tesseract only (minimal footprint)
- **full target**: Deployments requiring EasyOCR (GPU-accelerated environments)
- Base + flavor-specific docker-compose files for flexibility

## Troubleshooting

**No engines detected:**
```bash
# Check installed packages
pip list | grep ocrbridge

# Check logs for discovery errors
# Look for: "ocr_engines_discovered" with count=0
```

**Import errors:**
```bash
# For Tesseract: ensure binary installed
which tesseract

# For ocrmac: only works on macOS
uname -s  # Should return "Darwin"
```

**Protected member access warnings in tests:**
These are expected in test files that need to verify internal state (e.g., `registry._engine_instances`). Tests are allowed to access protected members for validation.
