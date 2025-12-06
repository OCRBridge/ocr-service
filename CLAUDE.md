# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RESTful OCR API service with **modular plugin architecture**. OCR engines are installed as separate PyPI packages and discovered dynamically via Python entry points. The service automatically adapts to available engines without code changes.

Core architecture:
- **Entry Point Discovery**: Engines register via `ocrbridge.engines` entry points
- **Dynamic Route Generation**: API routes created at runtime for each discovered engine
- **Engine-Agnostic**: Single codebase supports any engine implementing the OCREngine protocol
- **Package-Based**: Engines distributed as independent `ocrbridge-*` packages from datenzar

## Common Commands

### Development
```bash
# Install dependencies with all engines
uv sync --group dev --all-extras

# Run development server
make dev
# Or: uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Run tests (excludes macOS-only and slow EasyOCR tests)
make test
# Or: uv run pytest -m "not ocrmac and not easyocr" -v

# Run single test file
uv run pytest tests/unit/services/ocr/test_registry_v2.py -v

# Run single test function
uv run pytest tests/unit/services/ocr/test_registry_v2.py::test_function_name -v

# Run with markers
make test-tesseract   # Tesseract tests only
make test-easyocr     # EasyOCR tests only (slow, requires GPU)
make test-macos       # macOS-only ocrmac tests
make test-all         # All tests including slow ones

# Coverage
make test-coverage          # Excludes EasyOCR
make test-coverage-full     # Includes all engines
```

### Code Quality
```bash
# Format code
make format
# Or: uv run ruff format

# Lint
make lint
# Or: uv run ruff check --fix

# Type check
make typecheck
# Or: uv run ty check
```

### Docker
```bash
# Multi-stage builds (two flavors)
make docker-build-lite      # Tesseract only (~500MB)
make docker-build-full      # Tesseract + EasyOCR (~2.5GB)
make docker-build-all       # Both images

# Run with docker-compose
make docker-compose-full-up    # Full flavor (default)
make docker-compose-lite-up    # Lite flavor
make docker-up                 # Alias for full
make docker-down
make docker-logs
```

## Architecture Deep Dive

### Plugin Discovery System (`src/services/ocr/registry_v2.py`)

The registry discovers engines at startup:

1. **Entry Point Scan**: Queries `entry_points(group="ocrbridge.engines")`
2. **Class Loading**: Loads each engine class and validates it's an OCREngine subclass
3. **Parameter Model Discovery**:
   - Tries generic naming convention: `{EngineName}Params` from parent module
   - Falls back to `__param_model__` class attribute
   - Falls back to extracting from `process()` method type hints
4. **Lazy Instantiation**: Engine classes stored; instances created on first use

Key methods:
- `get_engine(name)`: Returns engine instance (lazy-loaded)
- `get_param_model(name)`: Returns Pydantic model for engine parameters
- `validate_params(engine, params)`: Validates params against engine's model
- `get_engine_info(name)`: Returns metadata including JSON schema

### Dynamic Route Generation (`src/api/routes/v2/dynamic_routes.py`)

Routes are generated at startup for each discovered engine:

1. **Per-Engine Routers**: Creates `/v2/ocr/{engine}/process` and `/v2/ocr/{engine}/info`
2. **Dynamic Form Parameters**: If engine has parameter model, generates FastAPI Form parameters from Pydantic fields
3. **Signature Injection**: Modifies handler function signature to include dynamic params for OpenAPI schema
4. **Validation**: Uses engine's parameter model for automatic validation

Critical implementation details:
- `create_form_params_from_model()`: Converts Pydantic model to Form parameters
- `create_signature_with_dynamic_params()`: Injects params into function signature
- Form defaults cannot be set in `Form()` (causes errors); set on Parameter object instead
- Dynamic params placed at end of signature to avoid "keyword-only before positional" errors

### Application Lifecycle (`src/main.py`)

Startup sequence:
1. Configure structured logging (structlog with JSON or console renderer)
2. Initialize EngineRegistry (discovers engines via entry points)
3. Register dynamic routes for each engine
4. Start background cleanup task (hourly temp file cleanup)
5. Mount Prometheus metrics at `/metrics`

The `lifespan` context manager handles startup/shutdown orchestration.

## Testing Strategy

### Test Structure
- `tests/unit/`: Pure unit tests with mocks
- `tests/integration/`: Tests with TestClient but mocked engines
- `tests/e2e/`: End-to-end tests with real engines (marked by engine)
- `tests/mocks/`: Mock engines and entry points for testing

### Mock System (`tests/mocks/`)
- `mock_engines.py`: MockTesseractEngine with configurable responses
- `mock_entry_points.py`: `mock_entry_points_factory()` patches entry point discovery
- `conftest.py`: `mock_engine_registry` fixture patches registry initialization

### Test Markers
Defined in `pyproject.toml`:
- `@pytest.mark.tesseract`: Tesseract-specific tests
- `@pytest.mark.easyocr`: EasyOCR tests (slow, GPU, excluded by default)
- `@pytest.mark.ocrmac`: macOS-only tests

### Testing Dynamic Routes
When testing routes, the `client` fixture:
1. Bypasses lifespan (doesn't run real entry point discovery)
2. Injects `mock_engine_registry` into `app.state.engine_registry`
3. Calls `register_engine_routes(app, mock_engine_registry)` to create test routes

## Dependencies and Packages

### Core Service Dependencies
- `ocrbridge-core>=3.1.0`: Base classes (OCREngine, OCREngineParams)
- `fastapi>=0.123.0`: Web framework
- `structlog>=23.2.0`: Structured logging
- `prometheus-client>=0.19.0`: Metrics

### Optional Engine Packages (installed separately)
- `ocrbridge-tesseract>=3.0.0`: Tesseract engine (requires system `tesseract` binary)
- `ocrbridge-easyocr>=3.1.0`: EasyOCR deep learning engine (~2GB with PyTorch)
- `ocrbridge-ocrmac>=2.0.0`: macOS Vision framework (macOS only, incompatible with Docker)

Install engines with: `pip install -e .[tesseract]` or `uv sync --extra tesseract`

## Key Files Reference

- `src/services/ocr/registry_v2.py`: Engine discovery and registry
- `src/api/routes/v2/dynamic_routes.py`: Dynamic route generation
- `src/main.py`: Application entry point and lifecycle
- `tests/conftest.py`: Test fixtures and mocking infrastructure
- `Dockerfile`: Multi-stage builds with `lite` and `full` targets
- `Makefile`: Development commands

## Development Patterns

### Adding a New Engine
Engines are external packages. To add support:
1. Install the engine package (must have `ocrbridge.engines` entry point)
2. Restart the service - routes auto-generate

### Testing with Mock Engines
```python
from tests.mocks.mock_engines import MockTesseractEngine
from tests.mocks.mock_entry_points import mock_entry_points_factory

engines = {"tesseract": MockTesseractEngine}
mock_ep = mock_entry_points_factory(engines)

with patch("src.services.ocr.registry_v2.entry_points", mock_ep):
    registry = EngineRegistry()
```

### Debugging Engine Discovery
Check logs at startup for:
- `discovering_engines`: Initial scan
- `engine_discovered`: Each engine loaded
- `engine_discovery_complete`: Final count
- `route_registered`: Dynamic routes created

### Running Tests with Real Engines
E2E tests require actual engine packages installed:
```bash
# Install Tesseract engine and system binary
uv sync --extra tesseract
# System: brew install tesseract (macOS) or apt-get install tesseract-ocr (Linux)

# Run Tesseract E2E tests
uv run pytest tests/e2e/test_ocr_tesseract.py -v
```

## Environment Variables

Defined in `src/config.py`:
- `MAX_UPLOAD_SIZE_MB`: Max file upload size (default: 5)
- `LOG_LEVEL`: Logging level (default: INFO)
- `LOG_FORMAT`: "json" or "console" (default: json)
