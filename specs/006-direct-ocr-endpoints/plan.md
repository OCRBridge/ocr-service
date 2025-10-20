# Implementation Plan: Direct OCR Processing Endpoints

**Branch**: `006-direct-ocr-endpoints` | **Date**: 2025-10-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-direct-ocr-endpoints/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add synchronous OCR processing endpoints for Tesseract, EasyOCR, and ocrmac engines to enable direct request-response processing. Clients can POST a document and receive hOCR output immediately in the HTTP response body, eliminating the need for job queue polling. This simplifies integration for single-page or quick-processing documents while maintaining existing async endpoints for complex/long-running jobs.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI 0.104+, Pydantic 2.5+, pytesseract 0.3+, EasyOCR (latest), PyTorch (EasyOCR dependency), Redis 7.0+ (for async jobs - NOT used by sync endpoints)
**Storage**: Filesystem (temporary uploaded files - cleaned up immediately after sync processing), Redis 7.0+ (job state for async endpoints only)
**Testing**: pytest 7.4+, pytest-cov for coverage tracking
**Target Platform**: Linux server (Docker), macOS (local development)
**Project Type**: Single web service (FastAPI backend)
**Performance Goals**: 95% of single-page documents complete in <5 seconds, 100 concurrent requests without timeout/degradation, p95 latency <5s for sync endpoints
**Constraints**: 30-second request timeout (hard limit), 5MB file size limit (sync endpoints), no job queue overhead, temporary file cleanup within 1 second
**Scale/Scope**: New synchronous endpoints alongside existing async endpoints, reuse OCRProcessor and engine implementations, minimal code duplication

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle 1: API Contract First
**Status**: ✅ PASS
- OpenAPI contracts will be defined in Phase 1 (contracts/ directory)
- New synchronous endpoints will have explicit path + method + schema before implementation
- Existing async endpoint contracts remain unchanged (backward compatibility)

### Principle 2: Deterministic & Reproducible Processing
**Status**: ✅ PASS
- Synchronous endpoints will reuse existing OCRProcessor implementation
- Same document + parameters → identical hOCR output (requirement FR-013)
- No new processing logic, only new HTTP endpoints wrapping existing deterministic processing

### Principle 3: Test-First & Coverage Discipline
**Status**: ✅ PASS
- Tests required for each new synchronous endpoint before implementation
- Contract tests for OpenAPI spec compliance
- Integration tests for end-to-end sync processing
- Unit tests for timeout handling, file size validation, error responses
- Target: 90% coverage for new endpoint code, 80% overall maintained

### Principle 4: Performance & Resource Efficiency
**Status**: ✅ PASS with monitoring
- Performance budgets defined: p95 <5s, 95% complete in <5s, 100 concurrent requests
- 30-second timeout prevents resource exhaustion
- 5MB file size limit prevents memory issues
- Immediate file cleanup prevents disk bloat
- SUCCESS CRITERIA SC-003: 100 concurrent requests without degradation
- Will require performance tests to validate budgets

### Principle 5: Observability & Transparency
**Status**: ✅ PASS
- Structured JSON logging with correlation IDs (requirement FR-014)
- Metrics: request_count, latency_histogram (p50, p95, p99), timeout_rate, per-engine success_rate (requirement FR-014a)
- Existing logging/metrics infrastructure will be extended for sync endpoints
- Error responses include clear messages (timeout → suggest async, size → suggest async)

### Principle 6: Security & Data Privacy
**Status**: ✅ PASS
- Temporary files deleted immediately after processing (requirement FR-016)
- No job state persistence (requirement FR-015)
- Same rate limiting as async endpoints (requirement FR-019)
- Same CORS/middleware as async endpoints (requirement FR-021)
- File size validation prevents DoS (requirement FR-006, FR-007)

### Principle 7: Simplicity & Minimal Surface
**Status**: ✅ PASS
- Reuses existing OCRProcessor, engines, validators, file handlers
- No new abstractions - only new HTTP routes calling existing services
- Minimal code duplication (sync endpoints call same processor.process_document())
- No premature optimization - simple timeout + size validation

### Principle 8: Documentation & Library Reference
**Status**: ✅ PASS
- Phase 1 will generate quickstart.md with usage examples
- OpenAPI contracts will document sync vs. async endpoint selection
- Will reference FastAPI async best practices and timeout handling patterns
- Context7 will be used for FastAPI timeout implementation patterns

### Overall Gate Decision
**✅ PROCEED TO PHASE 0**

All constitution principles align with feature design. No violations requiring justification.

## Project Structure

### Documentation (this feature)

```
specs/006-direct-ocr-endpoints/
├── spec.md              # Feature specification (already exists)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── sync-tesseract-openapi.yaml
│   ├── sync-easyocr-openapi.yaml
│   └── sync-ocrmac-openapi.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
src/
├── models/              # Pydantic models
│   ├── ocr_params.py    # [EXISTING] Engine-specific parameters (reused)
│   ├── upload.py        # [EXISTING] File upload models (reused)
│   ├── responses.py     # [NEW] Add SyncOCRResponse model for sync endpoints
│   └── job.py           # [EXISTING] Job models (NOT used by sync endpoints)
├── services/
│   ├── ocr_processor.py # [EXISTING] OCRProcessor class (reused by sync endpoints)
│   ├── file_handler.py  # [EXISTING] File upload/cleanup (reused)
│   └── ocr/             # [EXISTING] Engine implementations (reused)
│       ├── tesseract.py
│       ├── easyocr.py
│       └── ocrmac.py
├── api/
│   ├── routes/
│   │   ├── upload.py    # [EXISTING] Async upload endpoints (unchanged)
│   │   ├── jobs.py      # [EXISTING] Job status endpoints (unchanged)
│   │   ├── sync.py      # [NEW] Synchronous OCR endpoints (Tesseract, EasyOCR, ocrmac)
│   │   └── health.py    # [EXISTING] Health check (unchanged)
│   ├── middleware/      # [EXISTING] Logging, rate limiting, error handling (reused)
│   └── dependencies.py  # [EXISTING] FastAPI dependencies (reused)
├── utils/
│   ├── validators.py    # [EXISTING] File format, size validation (reused)
│   ├── hocr.py          # [EXISTING] hOCR utilities (reused)
│   └── metrics.py       # [MODIFIED] Add sync endpoint metrics tracking
└── main.py              # [MODIFIED] Register sync.py router

tests/
├── contract/
│   └── test_sync_openapi.py    # [NEW] Contract tests for sync endpoints
├── integration/
│   └── test_sync_endpoints.py  # [NEW] End-to-end sync processing tests
└── unit/
    ├── test_sync_routes.py     # [NEW] Unit tests for sync endpoint logic
    └── test_sync_validation.py # [NEW] Timeout, file size validation tests
```

**Structure Decision**: Single project structure (Option 1). This feature adds new synchronous API routes (`src/api/routes/sync.py`) and a new response model (`src/models/responses.py`) while reusing existing OCRProcessor, engines, validators, and middleware. No new services or abstractions are needed - synchronous endpoints are thin wrappers calling the same processing logic as async endpoints.

## Complexity Tracking

*No violations - section not needed*

---

## Post-Design Constitution Check

*Re-evaluation after Phase 1 design completion*

### Principle 1: API Contract First
**Status**: ✅ PASS
- ✅ OpenAPI contracts generated in `contracts/` directory:
  - `sync-tesseract-openapi.yaml`
  - `sync-easyocr-openapi.yaml`
  - `sync-ocrmac-openapi.yaml`
- ✅ All endpoints have explicit path + method + request/response schemas
- ✅ Error responses documented (400, 408, 413, 415, 422, 429, 500, 503)
- ✅ Backward compatibility maintained (no changes to async endpoints)

### Principle 2: Deterministic & Reproducible Processing
**Status**: ✅ PASS
- ✅ Reuses existing `OCRProcessor.process_document()` - same logic as async endpoints
- ✅ Data model confirms: "System MUST return error responses in the same JSON format as async endpoints" (FR-022)
- ✅ Research confirms: Same document + parameters → identical hOCR output (FR-013)

### Principle 3: Test-First & Coverage Discipline
**Status**: ✅ PASS (design complete, implementation pending)
- ✅ Test structure defined in project structure:
  - `tests/contract/test_sync_openapi.py` (OpenAPI contract validation)
  - `tests/integration/test_sync_endpoints.py` (end-to-end processing)
  - `tests/unit/test_sync_routes.py` (route handler logic)
  - `tests/unit/test_sync_validation.py` (timeout, file size validation)
- ✅ Coverage targets: 90% for new endpoint code, 80% overall maintained
- Note: Tests will be written BEFORE implementation (TDD approach confirmed)

### Principle 4: Performance & Resource Efficiency
**Status**: ✅ PASS
- ✅ Performance budgets defined:
  - p95 latency < 5 seconds (success criteria SC-001)
  - 95% of single-page docs complete in < 5 seconds (SC-001)
  - 100 concurrent requests without degradation (SC-003)
- ✅ Resource constraints enforced:
  - 30-second timeout prevents runaway processing
  - 5MB file size limit prevents memory issues
  - Immediate file cleanup (< 1 second, requirement FR-016)
- ✅ Metrics defined: `sync_ocr_duration_seconds` histogram tracks latency percentiles
- Note: Performance tests will validate budgets during implementation

### Principle 5: Observability & Transparency
**Status**: ✅ PASS
- ✅ Structured logging with correlation IDs (requirement FR-014)
- ✅ Prometheus metrics defined in `data-model.md`:
  - `sync_ocr_requests_total{engine, status}`
  - `sync_ocr_duration_seconds{engine}` (histogram for p50/p95/p99)
  - `sync_ocr_timeouts_total{engine}`
  - `sync_ocr_file_size_bytes{engine}`
- ✅ Error messages clear and actionable (e.g., timeout → suggest async endpoints)
- ✅ All error scenarios documented in OpenAPI specs

### Principle 6: Security & Data Privacy
**Status**: ✅ PASS
- ✅ Temporary files deleted immediately (FR-016, context manager pattern in research.md)
- ✅ No job state persistence (FR-015) - ephemeral processing only
- ✅ Rate limiting reused from async endpoints (FR-019)
- ✅ File size validation prevents DoS (FR-006, FR-007)
- ✅ Same CORS/middleware as async endpoints (FR-021)
- ✅ No sensitive data logged (existing logging infrastructure)

### Principle 7: Simplicity & Minimal Surface
**Status**: ✅ PASS
- ✅ Zero new abstractions - only new HTTP routes
- ✅ Reuses existing components:
  - `OCRProcessor` (processing logic)
  - `FileHandler` (file management)
  - `OCREngineRegistry` (engine availability)
  - `TesseractParams`, `EasyOCRParams`, `OcrmacParams` (validation)
- ✅ Minimal new code: 3 new models (SyncOCRResponse, validation constants, config settings)
- ✅ No premature optimization: Simple timeout + size validation (asyncio.wait_for)

### Principle 8: Documentation & Library Reference
**Status**: ✅ PASS
- ✅ `quickstart.md` generated with usage examples (curl, Python, JavaScript)
- ✅ OpenAPI specs document all endpoints comprehensively
- ✅ Research.md references FastAPI documentation for timeout implementation
- ✅ Decision flowchart for sync vs async endpoint selection
- ✅ Error handling examples provided
- ✅ FAQ section addresses common questions

### Overall Post-Design Gate Decision
**✅ ALL PRINCIPLES SATISFIED**

Design artifacts confirm constitution compliance:
- **Contracts-first**: OpenAPI specs complete before implementation
- **Deterministic**: Reuses existing OCRProcessor (proven deterministic)
- **Test-ready**: Test structure defined, TDD approach documented
- **Performance-conscious**: Budgets defined, metrics instrumented
- **Observable**: Full metrics + logging coverage
- **Secure**: Ephemeral processing, immediate cleanup, validation
- **Simple**: Zero new abstractions, maximum reuse
- **Documented**: Comprehensive quickstart + OpenAPI + research

**READY TO PROCEED TO PHASE 2 (Implementation via /speckit.tasks)**
