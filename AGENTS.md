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
*   **Task Runner:** `mise`
*   **Dependency Management:** `uv` (via mise tasks)
*   **Linting/Formatting:** `ruff`
*   **Type Checking:** `ty`
*   **Testing:** `pytest`
*   **Containerization:** Docker

## Building and Running

The project uses `mise` tasks for all developer workflows.

### Installation
```bash
# Install pinned tools from mise.toml
mise install

# Install dependencies (including dev and all engines)
mise run install:all
```

### Running Locally
```bash
# Start development server with reload
mise run run
```

### Testing
```bash
# Run all tests
mise run test:all

# Run specific test types
mise run test:unit
mise run test:integration
mise run test:e2e
mise run test:contract
```

## Development Conventions

*   **Code Style:** Strict adherence to `ruff` for linting and formatting. Run `mise run lint:lint` and `mise run lint:format` before committing.
*   **Type Safety:** 100% type compliance required via `ty`. Run `mise run lint:typecheck`.
*   **Commits:** Follow Conventional Commits. Use `mise run release:commit` to open Commitizen CLI.
*   **Architecture:**
    *   **Core:** `src/` contains the API service.
    *   **Packages:** Managed via `pyproject.toml`; dependencies are installed through mise tasks.
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
