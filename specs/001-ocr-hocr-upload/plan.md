# Implementation Plan: OCR Document Upload with HOCR Output

**Branch**: `001-ocr-hocr-upload` | **Date**: 2025-10-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-ocr-hocr-upload/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build a RESTful API service that accepts document uploads (JPEG, PNG, PDF, TIFF), performs OCR processing, and returns results in HOCR format. The service is public (no authentication), uses job-based async processing with polling for status, implements rate limiting (100 requests/min per IP), and auto-expires results after 24-48 hours. The implementation follows TDD principles using sample documents in the `samples/` directory as test fixtures.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**:
- FastAPI 0.104+ (web framework)
- Pydantic 2.5+ (type validation)
- Pydantic-settings (environment config)
- Starlette (ASGI server components)
- Uvicorn 0.24+ (ASGI server)
- Tesseract 5.3+ (OCR engine, via pytesseract wrapper)
- pdf2image 1.16+ (PDF to image conversion)
- Redis 7.0+ (job state storage with TTL)
- slowapi 0.1+ (rate limiting)
- structlog 23.2+ (structured logging)
- prometheus-client 0.19+ (metrics)

**Storage**:
- File system: Temporary document uploads (/tmp/uploads) and HOCR results (/tmp/results)
- Redis: Job state metadata, rate limiting counters, TTL-based auto-expiration

**Testing**: pytest 7.4+ with TDD approach using samples/ directory fixtures, pytest-asyncio 0.21+, httpx 0.25+ for client testing

**Target Platform**: Linux server (containerized deployment via Docker)

**Project Type**: Single web API service (FastAPI + Uvicorn multi-worker)

**Performance Goals**:
- OCR processing: <30 seconds for single-page documents <5MB
- Status endpoint: <800ms p95 latency
- Retrieval endpoint: <800ms p95 latency
- Throughput: 100 requests/min per IP (rate limited)
- Concurrency: 10+ simultaneous users

**Constraints**:
- Memory: <512MB peak per request (constitution requirement)
- Security: Cryptographically secure job IDs (secrets.token_urlsafe)
- Data retention: 48h auto-expiration via Redis TTL
- Coverage: 90% for utilities, 80% overall (constitution requirement)

**Scale/Scope**:
- Public API (no authentication)
- Multi-format support: JPEG, PNG, PDF, TIFF
- HOCR output with bounding boxes and text hierarchy
- Async job processing with polling-based status checks

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Design Check (Phase 0 Gate)

| Principle | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| **1. API Contract First** | OpenAPI spec before implementation | ✅ PASS | Will generate OpenAPI contract in Phase 1 before implementation |
| **2. Deterministic Processing** | Same input → same output | ✅ PASS | OCR engine selection will prioritize determinism; seeding documented |
| **3. Test-First (NON-NEGOTIABLE)** | TDD with 90%/80% coverage | ✅ PASS | Explicit TDD requirement using samples/ fixtures; coverage gates enforced |
| **4. Performance & Efficiency** | p95 ≤800ms, memory <512MB | ✅ PASS | Technical Context defines budgets aligned with constitution |
| **5. Observability** | Structured logs, metrics, tracing | ✅ PASS | Will implement request_id, correlation_id, stage tracking |
| **6. Security & Privacy** | No data retention beyond processing | ✅ PASS | 24-48h auto-expiration per spec; no auth simplifies privacy scope |
| **7. Simplicity** | Simplest algorithm first | ✅ PASS | Will select proven OCR library vs custom ML; remove dead code in same PR |

**Security & Performance Requirements Check:**

| Requirement | Status | Implementation Plan |
|-------------|--------|-------------------|
| Input Validation | ✅ PASS | Pydantic models validate formats, FastAPI returns 415/400 with JSON errors |
| Rate Limiting | ✅ PASS | 100 req/min per IP (spec clarification Q4) |
| Resource Isolation | ✅ PASS | Async processing with file streaming, memory budget per request |
| Accuracy Benchmarks | ✅ PASS | TDD with samples/ directory provides baseline test corpus |
| Dependency Hygiene | ✅ PASS | uv lock file + weekly security scans (to be configured in CI) |

**Development Workflow Check:**

| Gate | Status | Notes |
|------|--------|-------|
| Design/Contract | ✅ PASS | Phase 1 will produce OpenAPI + performance budgets |
| Tests First | ✅ PASS | TDD approach mandated by user input |
| Type Checks | ✅ PASS | Pydantic enforces runtime type safety |
| Observability Hooks | ✅ PASS | Will add structured logging to all endpoints |
| CI Gates | ⚠️ DEFERRED | Ruff formatting specified; coverage/security scans to be configured |

**Overall Gate Status**: ✅ **PASS** - Proceed to Phase 0 Research

*Note: CI pipeline configuration (lint, coverage, security scan) will be included in implementation tasks but doesn't block planning phase.*

### Post-Design Check (Phase 1 Complete)

| Principle | Requirement | Status | Implementation Notes |
|-----------|-------------|--------|---------------------|
| **1. API Contract First** | OpenAPI spec before implementation | ✅ PASS | contracts/openapi.yaml complete with all endpoints, schemas, examples |
| **2. Deterministic Processing** | Same input → same output | ✅ PASS | Tesseract with fixed PSM/OEM config; Redis for deterministic job IDs |
| **3. Test-First (NON-NEGOTIABLE)** | TDD with samples/ fixtures | ✅ PASS | Test structure defined in quickstart.md; 80%/90% coverage gates |
| **4. Performance & Efficiency** | Budgets met | ✅ PASS | Redis <1ms, streaming uploads, background tasks for OCR |
| **5. Observability** | Structured logs + metrics | ✅ PASS | structlog JSON format; prometheus_client for metrics |
| **6. Security & Privacy** | 48h auto-expiration | ✅ PASS | Redis TTL + cleanup task; cryptographically secure job IDs |
| **7. Simplicity** | Simplest working solution | ✅ PASS | FastAPI BackgroundTasks initially (not Celery); Tesseract (not custom ML) |

**Overall Gate Status**: ✅ **PASS** - Ready for `/speckit.tasks` (task generation)

*No violations requiring justification. All design decisions align with constitution.*

## Project Structure

### Documentation (this feature)

```
specs/001-ocr-hocr-upload/
├── spec.md              # Feature specification (user requirements)
├── plan.md              # This file - implementation plan
├── research.md          # Phase 0 - technology decisions & rationale
├── data-model.md        # Phase 1 - Pydantic models & validation rules
├── quickstart.md        # Phase 1 - developer setup & TDD workflow
├── contracts/           # Phase 1 - API contracts
│   └── openapi.yaml     # OpenAPI 3.1 specification
├── checklists/          # Validation checklists
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 - NOT YET CREATED (run /speckit.tasks)
```

### Source Code (repository root)

**Selected Structure**: Single web API service (Option 1)

```
restful-ocr/
├── src/                           # Application source code
│   ├── main.py                    # FastAPI app entry point + lifespan
│   ├── config.py                  # Pydantic Settings (loads .env)
│   ├── models/                    # Pydantic data models
│   │   ├── __init__.py
│   │   ├── job.py                 # OCRJob, JobStatus, ErrorCode enums
│   │   ├── upload.py              # DocumentUpload, FileFormat enum
│   │   ├── result.py              # HOCRResult
│   │   └── responses.py           # UploadResponse, StatusResponse, ErrorResponse
│   ├── api/                       # API layer
│   │   ├── __init__.py
│   │   ├── routes/                # Endpoint implementations
│   │   │   ├── __init__.py
│   │   │   ├── upload.py          # POST /upload
│   │   │   ├── jobs.py            # GET /jobs/{id}/status, /result
│   │   │   └── health.py          # GET /health, /metrics
│   │   ├── middleware/            # Request/response middleware
│   │   │   ├── __init__.py
│   │   │   ├── rate_limit.py      # slowapi integration (100/min per IP)
│   │   │   ├── logging.py         # structlog request logging
│   │   │   └── error_handler.py   # Exception → JSON error response
│   │   └── dependencies.py        # FastAPI Depends() providers (Redis, config)
│   ├── services/                  # Business logic
│   │   ├── __init__.py
│   │   ├── ocr_processor.py       # Tesseract wrapper (pytesseract + pdf2image)
│   │   ├── job_manager.py         # Redis job state CRUD + TTL management
│   │   ├── file_handler.py        # Streaming upload, temp file management
│   │   └── cleanup.py             # Background task: delete expired files
│   └── utils/                     # Shared utilities
│       ├── __init__.py
│       ├── validators.py          # File magic byte validation, size checks
│       ├── hocr.py                 # HOCR XML parsing & validation
│       └── security.py            # secrets.token_urlsafe() job ID generation
│
├── tests/                         # Test suite (TDD)
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures (client, Redis, temp dirs)
│   ├── unit/                      # Unit tests (90% coverage target)
│   │   ├── __init__.py
│   │   ├── test_models.py         # Pydantic validation, state transitions
│   │   ├── test_validators.py     # File format detection, size limits
│   │   ├── test_security.py       # Job ID uniqueness, entropy
│   │   ├── test_hocr.py            # HOCR XML parsing
│   │   └── test_job_manager.py    # Redis operations, TTL logic
│   ├── integration/               # Integration tests (80% coverage target)
│   │   ├── __init__.py
│   │   ├── test_upload_samples.py # End-to-end with samples/ fixtures
│   │   ├── test_expiration.py     # 48h TTL enforcement (mocked time)
│   │   └── test_rate_limiting.py  # 100/min enforcement
│   ├── contract/                  # OpenAPI contract compliance
│   │   ├── __init__.py
│   │   ├── test_upload_endpoint.py    # POST /upload schema validation
│   │   ├── test_status_endpoint.py    # GET /jobs/{id}/status
│   │   ├── test_result_endpoint.py    # GET /jobs/{id}/result
│   │   └── test_error_responses.py    # 400/404/413/415/429 schemas
│   └── performance/               # Performance budget validation
│       ├── __init__.py
│       ├── test_endpoint_latency.py   # p95 <800ms for status/result
│       └── test_memory_usage.py       # <512MB per request (profiler)
│
├── samples/                       # TDD fixtures (committed to repo)
│   ├── numbers_gs150.jpg          # Low DPI grayscale test
│   ├── stock_gs200.jpg            # Medium DPI grayscale test
│   └── mietvertrag.pdf            # Multi-page PDF test
│
├── specs/                         # Design documentation (this directory)
│   └── 001-ocr-hocr-upload/       # Current feature
│
├── .specify/                      # Speckit governance
│   ├── memory/
│   │   └── constitution.md        # Project principles (v1.0.0)
│   └── [other speckit files]
│
├── pyproject.toml                 # Project metadata, dependencies, tool config
├── uv.lock                        # Locked dependency versions
├── .env.example                   # Environment variable template
├── .env                           # Local config (gitignored)
├── .python-version                # Python 3.11
├── .gitignore                     # Git ignore rules
├── ruff.toml                      # Ruff formatter/linter config
├── docker-compose.yml             # Local dev stack (API + Redis)
├── Dockerfile                     # API container image
├── README.md                      # Project overview & setup
└── CLAUDE.md                      # Agent context (auto-generated)
```

**Structure Decision**:

Selected **Option 1: Single web API service** because:
- No frontend required (spec clarification Q2: API-only)
- Single Python service with FastAPI
- Traditional src/tests separation
- Scales to multiple workers via Uvicorn
- Simple Docker deployment

## Complexity Tracking

**Status**: No violations requiring justification

All design decisions comply with the constitution. No complexity tracking needed.
