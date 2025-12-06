# Agents Context: OCR Service

## Project Overview

**Name:** RESTful OCR API
**Description:** A high-performance, modular RESTful API service for document OCR processing. It uses a plugin-based architecture to support multiple OCR engines (Tesseract, EasyOCR, Apple Vision) via a unified API.

**Key Features:**
*   **Modular Architecture:** Engines are separate Python packages (`ocrbridge-tesseract`, `ocrbridge-easyocr`, `ocrbridge-ocrmac`) that register via entry points.
*   **Unified API:** A single `/v2/ocr/process` endpoint works with any installed engine.
*   **Format Support:** Handles JPEG, PNG, PDF, and TIFF.
*   **Output:** Standard HOCR (HTML-based OCR) with bounding boxes and text hierarchy.
*   **Observability:** JSON logging (structlog) and Prometheus metrics.

**Tech Stack:**
*   **Language:** Python 3.10+
*   **Framework:** FastAPI, Uvicorn
*   **Dependency Management:** `uv`
*   **Linting/Formatting:** `ruff`
*   **Type Checking:** `ty`
*   **Testing:** `pytest`
*   **Containerization:** Docker

## Building and Running

The project uses `make` and `uv` for most tasks.

### Installation
```bash
# Install dependencies (including dev and all engines)
make install
# OR directly with uv
uv sync --group dev --all-extras
```

### Running Locally
```bash
# Start development server with reload
make dev
# OR
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Run standard tests (skips EasyOCR and Ocrmac)
make test

# Run all tests
make test-all

# Run specific test types
make test-unit
make test-integration
make test-e2e
make test-contract
```

### Docker
```bash
# Build specific flavors
make docker-build-lite  # Tesseract only (~500MB)
make docker-build-full  # Tesseract + EasyOCR (~2.5GB)

# Run with Docker Compose
make docker-up
make docker-down
```

## Development Conventions

*   **Code Style:** Strict adherence to `ruff` for linting and formatting. Run `make lint` and `make format` before committing.
*   **Type Safety:** 100% type compliance required via `ty`. Run `make typecheck`.
*   **Commits:** Follow Conventional Commits. Use `make commit` to use the Commitizen CLI.
*   **Architecture:**
    *   **Core:** `src/` contains the API service.
    *   **Packages:** Managed via `uv` and `pyproject.toml`. Engines are installed as separate packages.
    *   **Entry Points:** Engines are discovered via `project.entry-points."ocrbridge.engines"` in `pyproject.toml`.
*   **Testing:**
    *   Unit tests for logic.
    *   Integration tests for API endpoints.
    *   E2E tests for full flow with engines.
    *   Contract tests for API schema validation.
    *   Use markers (`@pytest.mark.tesseract`, `@pytest.mark.easyocr`, `@pytest.mark.ocrmac`) for conditional execution.

## Directory Structure
*   `src/`: Main application source code.
    *   `api/`: FastAPI routes and dependencies.
    *   `models/`: Pydantic models.
    *   `services/`: Business logic (file handling, engine registry).
*   `tests/`: Comprehensive test suite.
*   `samples/`: Sample images/PDFs for testing.

Always use context7 when I need code generation, setup or configuration steps, or
library/API documentation. This means you should automatically use the Context7 MCP
tools to resolve library id and get library docs without me having to explicitly ask.
