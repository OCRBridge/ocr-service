# Gemini Context: OCR Bridge Service

This `GEMINI.md` provides context for the AI agent interacting with the `ocr-service` project.

## Project Overview
**OCR Bridge Service** is a high-performance, RESTful API for document OCR processing. It features a modular architecture where OCR engines (Tesseract, EasyOCR, OCRMac) are loaded as plugins via Python entry points.

*   **Version:** 2.0.0
*   **Core Framework:** FastAPI (Async/Await)
*   **Architecture:** Plugin-based using `ocrbridge-core` and dynamically discovered engine packages.
*   **Package Manager:** `uv` (recommended) or `pip`.

## Key Technologies
*   **Language:** Python 3.10+
*   **Web Framework:** FastAPI, Uvicorn
*   **OCR Engines:** Tesseract (`ocrbridge-tesseract`), EasyOCR (`ocrbridge-easyocr`), Apple Vision (`ocrbridge-ocrmac`).
*   **Testing:** `pytest` (with `pytest-asyncio`, `pytest-cov`)
*   **Linting/Formatting:** `ruff`
*   **Type Checking:** `ty`
*   **Containerization:** Docker (Multi-stage builds: `lite` vs `full`)

## Directory Structure
*   `src/`: Main source code.
    *   `src/api/`: API routes and dependencies (`v2/` contains the unified engine endpoints).
    *   `src/models/`: Pydantic models for requests/responses (`schemas.py` for specs).
    *   `src/services/`: Core logic, including `ocr/registry_v2.py` for engine discovery.
*   `tests/`: Test suite (`unit`, `integration`, `e2e`, `mocks`).
*   `specs/`: API specifications.
*   `samples/`: Sample images/PDFs for testing.

## Development Workflow

### Dependency Management
The project uses `uv` for fast dependency management.
```bash
# Install dependencies
make install
# Or manually: uv sync --group dev --all-extras
```

### Running the Service
```bash
# Run development server (reloads on change)
make dev
# Runs on http://localhost:8000
```

### Code Quality & Testing
Always run these before committing changes.
```bash
# Run core tests (excludes slow/macOS tests)
make test

# Run all tests (if on macOS and have time)
make test-all

# Lint and Fix
make lint

# Format code
make format

# Type check
make typecheck
```

### Docker Operations
The project supports "lite" (Tesseract only) and "full" (Tesseract + EasyOCR) images.
```bash
# Build images
make docker-build-lite
make docker-build-full

# Run with Docker Compose
make docker-compose-lite-up
make docker-compose-full-up
```

## Critical Context for AI Agent
1.  **Modular Engines:** Do not hardcode engine logic in the main API routes. The system relies on `ocrbridge.engines` entry points.
2.  **Unified API:** The `/v2/ocr/process` endpoint is generic. Engine-specific parameters are validated dynamically against schemas provided by the engine packages.
3.  **macOS Specifics:** The `ocrmac` engine and its tests only run on macOS. Use markers (`@pytest.mark.macos`) when writing tests for it.
4.  **Environment:** Respect `.env` configuration (loaded via `pydantic-settings`).
5.  **Dependencies:** When adding packages, remember to update `pyproject.toml` and run `uv sync`.
