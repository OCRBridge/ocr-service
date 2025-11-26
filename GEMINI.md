# GEMINI.md

This file serves as a comprehensive context guide for the Gemini AI agent working on the **RESTful OCR API** project.

## Project Overview

**Name:** RESTful OCR API (`restful-ocr`)
**Purpose:** A high-performance, modular RESTful API service for document OCR processing.
**Core Philosophy:** Modular plugin architecture. The core service is engine-agnostic, and OCR capabilities are added via separate Python packages (`ocrbridge-*`) discovered dynamically at runtime.

### Key Features
- **Modular Architecture:** Plugins via `ocrbridge.engines` entry points.
- **Multi-Engine Support:** Tesseract (default), EasyOCR (GPU/Deep Learning), ocrmac (macOS native).
- **Dynamic Endpoints:** API routes are generated based on installed engines (e.g., `/v2/ocr/tesseract/process`).
- **Observability:** Structlog (JSON logs) and Prometheus metrics (`/metrics`).
- **Dependency Management:** Uses `uv` for fast package management.

## Architecture

### Engine Discovery
- **Mechanism:** Python Entry Points (`ocrbridge.engines`).
- **Registry:** `src.services.ocr.registry_v2.EngineRegistry` loads engines on startup.
- **Zero-Code Extension:** Installing a valid `ocrbridge-X` package automatically adds it to the API without changing core code.

### Engine Schema Enhancements (v2.0)
To support rich parameter validation and complex types (e.g., lists of languages), the system now supports v2.0 of the `ocrbridge-*` ecosystem.

- **Requirement:** External engine packages (e.g., `ocrbridge-tesseract`) must export Pydantic v2 models (e.g., `TesseractParams`) defining their configuration.
- **Discovery Priority:** The registry (`src/services/ocr/registry_v2.py`) prioritizes importing these specific models from the installed engine package. If not found, it falls back to the legacy method of inspecting `process()` method type hints.
- **Reference:** See `specs/schemas.py` for the authoritative specification of these parameter models.
- **Complex Types:** The API generation logic correctly maps complex types like `List[str]` to FastAPI `Form` parameters, enabling features like multi-value selection in Swagger UI.

### API Structure
- **Framework:** FastAPI.
- **Routes:**
  - `/health`: Liveness probe.
  - `/metrics`: Prometheus metrics.
  - `/v2/ocr/engines`: List detected engines.
  - `/v2/ocr/<engine>/process`: Dynamic endpoint for processing.
  - `/v2/ocr/process`: Unified endpoint (requires `engine` parameter).

## Development Setup

### Prerequisites
- Python 3.11+
- `uv` (recommended package manager)
- System dependencies: `tesseract-ocr` (for Tesseract engine)

### Installation
```bash
# Install core dependencies + dev tools + all supported engines
uv sync --group dev --all-extras

# Install specific engine only
uv sync --group dev --extra tesseract
```

### Running the Service
```bash
# Development mode (auto-reload)
make dev
# OR
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## Development Workflow

### Testing Strategy
The project uses `pytest` with specific markers for platform/speed.

- **Fast Tests (Default):** `make test` (Skips slow and macOS-only tests).
- **Unit Tests:** `make test-unit` (Isolated, uses mocks, organized by `src` module structure).
- **Integration Tests:** `make test-integration` (API/File I/O, organized by `src` module structure).
- **E2E Tests:** `make test-e2e` (Real engines, excludes slow).
- **Slow Tests:** `make test-slow` (Includes EasyOCR initialization).
- **Full Suite:** `make test-all`.

**Markers:**
- `@pytest.mark.slow`: EasyOCR/heavy tests.
- `@pytest.mark.macos`: `ocrmac` specific tests.

### Code Quality
Automated via `ruff` and `pyright`.

- **Lint:** `make lint`
- **Format:** `make format`
- **Type Check:** `make typecheck`
- **Pre-commit:** `make pre-commit`

## Docker & Deployment

The project supports multi-stage builds for different deployment needs.

- **Lite Image (`ocr-service:lite`):** Tesseract only (~500MB).
  - Build: `make docker-build-lite`
- **Full Image (`ocr-service:full`):** Tesseract + EasyOCR (~2.5GB).
  - Build: `make docker-build-full`

**Docker Compose:**
- `make docker-compose-lite-up`
- `make docker-compose-full-up`

## Project Structure

```text
/home/sneaker15/work/github/OCRBridge/ocr-service/
├── src/
│   ├── api/
│   │   ├── routes/v2/      # Dynamic route generation
│   │   └── middleware/     # Error handling, Logging
│   ├── services/
│   │   ├── ocr/            # Engine registry & discovery logic
│   │   └── cleanup.py      # Background file cleanup
│   ├── models/             # Pydantic models (Request/Response)
│   ├── utils/              # HOCR, Validators, Metrics
│   ├── config.py           # App configuration (Env vars)
│   └── main.py             # App entry point & lifespan
├── tests/
│   ├── unit/
│   │   ├── api/
│   │   ├── services/
│   │   │   ├── ocr/
│   │   │   └── test_cleanup.py
│   │   ├── utils/              # Consolidated utility tests (gpu, hocr, metrics, platform, security, validators)
│   │   └── test_config.py
│   ├── integration/
│   │   ├── api/
│   │   │   ├── v2/             # Dynamic routes and discovery integration tests
│   │   │   └── test_health.py
│   │   └── services/           # File handler integration tests
│   │       └── test_file_handler.py
│   ├── e2e/                # Real engine execution
│   ├── mocks/              # Mock engines for testing
│   └── conftest.py         # Shared fixtures
├── pyproject.toml          # Dependencies & Tool config
├── Makefile                # Command shortcuts
└── Dockerfile              # Multi-stage build definition
```

## Key Files

- `pyproject.toml`: Defines dependencies, entry points, and tool configurations (Ruff, Pytest).
- `Makefile`: The central command hub for dev workflows.
- `src/services/ocr/registry_v2.py`: Core logic for discovering installed OCR engines.
- `src/api/routes/v2/dynamic_routes.py`: Logic for creating API endpoints dynamically.
- `tests/conftest.py`: Critical fixtures including `mock_engine_registry`.

## Critical Constraints & Conventions
- **Imports:** Follow strict ordering enforced by Ruff (isort compatible).
- **Typing:** Strict type hints required (Pyright).
- **Testing:** Prefer mocks for unit tests to avoid binary dependencies. Use `conftest.py` fixtures.
- **State:** The service is stateless; file uploads are temporary and cleaned up via background tasks.
