# Research & Technology Decisions

**Feature**: OCR Document Upload with HOCR Output
**Date**: 2025-10-18
**Status**: Phase 0 Complete

## Overview

This document resolves all "NEEDS CLARIFICATION" items from the Technical Context and documents technology choices, rationales, and alternatives considered for the OCR RESTful API service.

## Decision 1: OCR Engine Selection

### Decision
**Tesseract OCR 5.x** via `pytesseract` Python wrapper

### Rationale
1. **HOCR Support**: Tesseract has native HOCR output format support via `--output-format hocr` flag
2. **Determinism**: Tesseract produces deterministic results given same input and configuration (satisfies Constitution Principle 2)
3. **Maturity**: Industry-standard, actively maintained by Google, extensive documentation
4. **Performance**: Meets <30s processing target for typical documents
5. **Multi-format**: Handles JPEG, PNG, TIFF, PDF (via pdf2image preprocessing)
6. **License**: Apache 2.0 - permissive for commercial use
7. **TDD-friendly**: Well-tested library with predictable behavior using samples/ fixtures

### Alternatives Considered
- **EasyOCR**: Better accuracy for some Asian languages, but slower and no native HOCR support (would require custom formatting)
- **PaddleOCR**: Fast and accurate, but HOCR conversion not native, adds complexity
- **AWS Textract/Google Vision API**: Cloud services would add cost, latency, and external dependencies; against simplicity principle

### Configuration
- Language: `eng` (English) default, configurable via environment
- PSM (Page Segmentation Mode): Auto-detect (3) for general documents
- OEM (OCR Engine Mode): LSTM-only (1) for best speed/accuracy balance

## Decision 2: Job State Storage

### Decision
**Redis** for job state and result metadata, with file system for HOCR output files

### Rationale
1. **TTL Support**: Redis native key expiration perfectly matches 24-48h auto-deletion requirement (FR-012)
2. **Atomic Operations**: INCR for rate limiting, SETEX for job creation with expiration
3. **Performance**: In-memory operations meet <800ms p95 latency budget for status endpoints
4. **Scalability**: Supports multi-worker deployments without shared file system complexity
5. **Simplicity**: Single dependency vs. full database (PostgreSQL/SQLite) for simple key-value needs
6. **Rate Limiting**: Native support for sliding window rate limiting per IP

### Alternatives Considered
- **In-memory (dict)**: Loses state on restart, no multi-worker support, fails scalability requirement
- **SQLite**: File-based persistence unnecessary (results are temporary), no native TTL, slower than Redis
- **PostgreSQL**: Over-engineered for key-value job state, higher resource usage, violates simplicity principle

### Schema Design
```
Keys:
- job:{uuid}:status → "pending"|"processing"|"completed"|"failed"
- job:{uuid}:result_path → "/tmp/results/{uuid}.hocr"
- job:{uuid}:metadata → JSON(filename, format, upload_time, completion_time, error)
- ratelimit:{ip}:{minute} → request count (TTL: 60s)
- uploads:{ip} → sorted set for sliding window rate limiting

TTL: 48 hours on all job:* keys
```

## Decision 3: Async Processing Strategy

### Decision
**FastAPI BackgroundTasks** for initial implementation, with migration path to Celery if needed

### Rationale
1. **Simplicity First**: Constitution Principle 7 - start with simplest solution
2. **Zero Additional Infrastructure**: No message broker required initially
3. **FastAPI Native**: Tight integration with framework, minimal boilerplate
4. **Sufficient for Scale**: Handles 10 concurrent users requirement with async workers
5. **TDD-Friendly**: Easy to test with `pytest-asyncio`

### Migration Path
If load exceeds capacity:
1. Introduce **Celery** with Redis as broker
2. Replace `background_tasks.add_task()` with `process_document.delay()`
3. Add flower for monitoring
4. Update observability to track celery task states

### Alternatives Considered
- **Celery (immediately)**: Adds complexity (broker, workers, monitoring) before proven necessary
- **FastAPI async routes only**: Blocks worker thread during OCR, doesn't meet <30s SLA for status endpoints
- **AWS Lambda/Cloud Functions**: Vendor lock-in, cold start latency, against self-hosted simplicity

## Decision 4: File Upload Handling

### Decision
**Streaming upload with size validation** using FastAPI `UploadFile` with chunk processing

### Rationale
1. **Memory Efficiency**: Stream to disk without loading entire file in memory (<512MB budget per Constitution)
2. **Early Rejection**: Validate file size and magic bytes before full upload (fail fast)
3. **Security**: Prevents zip bombs and malformed files from consuming resources
4. **FastAPI Native**: Built-in `UploadFile` uses `python-multipart` efficiently

### Implementation
```python
async def upload_document(file: UploadFile = File(...)):
    # Validate magic bytes (first 12 bytes)
    chunk = await file.read(12)
    validate_file_format(chunk)  # JPEG/PNG/PDF/TIFF magic
    await file.seek(0)

    # Stream to temp file with size limit (25MB)
    temp_path = f"/tmp/uploads/{uuid4()}.{ext}"
    async with aiofiles.open(temp_path, 'wb') as f:
        while chunk := await file.read(8192):  # 8KB chunks
            if f.tell() > MAX_SIZE:
                raise HTTPException(413, "File too large")
            await f.write(chunk)
```

## Decision 5: PDF to Image Conversion

### Decision
**pdf2image** library (wraps `pdftoppm` from poppler-utils)

### Rationale
1. **Tesseract Compatibility**: Tesseract processes images, not PDFs directly
2. **Quality Control**: Specify DPI (300) for optimal OCR accuracy
3. **Multi-page Support**: Automatically handles page iteration
4. **Memory Efficient**: Can process pages one at a time
5. **Proven**: Standard solution in Python OCR pipelines

### Configuration
```python
from pdf2image import convert_from_path
images = convert_from_path(pdf_path, dpi=300, thread_count=2)
```

### Alternatives Considered
- **PyMuPDF (fitz)**: Fast but license concerns (AGPL), overkill for just image extraction
- **Direct Tesseract PDF**: Tesseract can process PDFs but less control over preprocessing

## Decision 6: Job ID Generation

### Decision
**UUID v4** generated via Python's `secrets.token_urlsafe(32)`

### Rationale
1. **Cryptographically Secure**: Meets FR-016 requirement for non-guessable job IDs
2. **Collision Resistance**: 128-bit UUID v4 has negligible collision probability
3. **URL-safe**: `token_urlsafe` generates base64url encoding without padding
4. **Standard Library**: No external dependency

### Format
`job_id = secrets.token_urlsafe(32)` → 43 character URL-safe string
Example: `Kj4TY2vN8xQz9wR5pL7mH3fC1sD6aB8nE0gU4tV2iX1`

### Alternatives Considered
- **UUID v4 (uuid.uuid4())**: Standard but not cryptographically secure random source by default
- **ULID**: Sortable and time-embedded, but reveals upload time (minor privacy concern)
- **Hashids**: Reversible encoding, not suitable for security-critical IDs

## Decision 7: Rate Limiting Implementation

### Decision
**slowapi** library with Redis backend

### Rationale
1. **FastAPI Integration**: Decorator-based rate limiting for endpoints
2. **Redis Native**: Uses Redis INCR and EXPIRE for atomic sliding window
3. **Per-IP Limiting**: Extracts client IP from `X-Forwarded-For` or `X-Real-IP` headers
4. **Configurable**: `@limiter.limit("100/minute")` matches requirement exactly
5. **HTTP 429 Response**: Automatic `Too Many Requests` with `Retry-After` header

### Implementation
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379")

@app.post("/upload")
@limiter.limit("100/minute")
async def upload_endpoint(...):
    ...
```

### Alternatives Considered
- **Custom middleware**: Reinventing the wheel, error-prone
- **NGINX rate limiting**: Requires infrastructure config, less granular per-endpoint control
- **Token bucket in-memory**: Loses state on restart, no multi-worker coordination

## Decision 8: Structured Logging

### Decision
**structlog** with JSON formatter

### Rationale
1. **Constitution Requirement**: Principle 5 mandates structured logs with request_id, correlation_id, stage, latency
2. **JSON Output**: Machine-parseable for log aggregation (ELK, Splunk, CloudWatch)
3. **Context Binding**: Thread-local context automatically includes request metadata
4. **Performance**: Fast C-based JSON encoding

### Configuration
```python
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

log = structlog.get_logger()
```

### Log Format
```json
{
  "timestamp": "2025-10-18T10:30:45.123Z",
  "level": "info",
  "event": "ocr_completed",
  "request_id": "req_abc123",
  "correlation_id": "corr_xyz789",
  "job_id": "Kj4TY...",
  "stage": "hocr_generation",
  "latency_ms": 245.67,
  "status": "success"
}
```

## Decision 9: Metrics & Observability

### Decision
**Prometheus** metrics via `prometheus-fastapi-instrumentator`

### Rationale
1. **Constitution Requirement**: Principle 5 requires request_count, latency_histogram, error_type counters
2. **FastAPI Native**: Auto-instruments all endpoints with minimal code
3. **Standard**: Prometheus is de facto standard for metrics in cloud-native apps
4. **Grafana Integration**: Pre-built dashboards available

### Metrics Exposed
```
http_requests_total{method, path, status}
http_request_duration_seconds{method, path}
ocr_processing_duration_seconds{status}
ocr_pages_processed_total
rate_limit_exceeded_total{endpoint}
```

### Alternatives Considered
- **OpenTelemetry**: More complex, overkill for current scope (future migration path)
- **StatsD**: Less powerful query language than PromQL
- **Custom metrics**: Reinventing the wheel

## Decision 10: Development Environment

### Decision
**uv** for dependency management and virtual environment

### Rationale
1. **User Specification**: Explicitly requested "uses uv with fastAPI"
2. **Speed**: 10-100x faster than pip for installs
3. **Lock File**: Deterministic builds with `uv.lock`
4. **PEP 621**: Native support for `pyproject.toml` standard

### Project Structure
```
pyproject.toml (dependencies, tool config for ruff/pytest)
uv.lock (locked dependencies)
.python-version (3.11)
```

### Alternatives Considered
- **Poetry**: Slower resolver, not requested by user
- **pip + venv**: Manual lock file management, slower installs

## Summary of Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.11+ |
| Web Framework | FastAPI | 0.104+ |
| Validation | Pydantic | 2.5+ |
| ASGI Server | Uvicorn | 0.24+ |
| OCR Engine | Tesseract | 5.3+ |
| OCR Wrapper | pytesseract | 0.3+ |
| PDF Processing | pdf2image | 1.16+ |
| Job Store | Redis | 7.0+ |
| Rate Limiting | slowapi | 0.1+ |
| Logging | structlog | 23.2+ |
| Metrics | prometheus-client | 0.19+ |
| Testing | pytest | 7.4+ |
| Async Testing | pytest-asyncio | 0.21+ |
| HTTP Client (tests) | httpx | 0.25+ |
| Code Formatting | ruff | 0.1+ |
| Package Manager | uv | 0.1+ |

## Performance Budget Validation

| Requirement | Target | Implementation Validation |
|-------------|--------|--------------------------|
| OCR Processing | <30s for 5MB single-page | Tesseract benchmarks: ~2-5s for 1MP @ 300 DPI |
| Status Endpoint Latency | <800ms p95 | Redis GET: <1ms, total roundtrip <50ms |
| Retrieval Endpoint Latency | <800ms p95 | File read + transfer: <100ms for typical HOCR (50-200KB) |
| Memory per Request | <512MB | Tesseract: ~100-200MB, pdf2image: ~50MB per page |
| Concurrent Users | 10+ | FastAPI async: hundreds of concurrent connections, OCR is background task |
| Rate Limit | 100 req/min per IP | slowapi + Redis: <1ms overhead per request |

## Security Considerations

| Threat | Mitigation |
|--------|-----------|
| File Upload Bomb | Size limit (25MB), magic byte validation, streaming |
| Path Traversal | UUID-based temp files, no user-controlled paths |
| Job ID Guessing | Cryptographically secure 256-bit IDs |
| DoS via Rate Limit | 100/min per IP, 429 responses with Retry-After |
| Memory Exhaustion | Per-request 512MB budget, streaming uploads, temp file cleanup |
| Dependency Vulnerabilities | uv lock file, weekly security scans (to be configured) |
| Data Leakage | Auto-expire results (48h), no logging of file content, temp cleanup |

## Testing Strategy

### Test Fixtures (samples/ directory)
- `numbers_gs150.jpg` - Low DPI grayscale test
- `stock_gs200.jpg` - Medium DPI grayscale test
- `mietvertrag.pdf` - Multi-page PDF test

### Test Coverage Plan
1. **Unit Tests** (90% coverage target):
   - File format validation
   - Job ID generation uniqueness
   - Rate limiting logic
   - HOCR parsing/validation

2. **Integration Tests** (80% coverage target):
   - End-to-end: upload → status → retrieve for each fixture
   - Error paths: invalid format, oversized file, corrupted image
   - Rate limit enforcement
   - Job expiration

3. **Contract Tests**:
   - OpenAPI spec validation
   - Request/response schema validation
   - HTTP status code correctness

4. **Performance Tests**:
   - Latency benchmarks (p95 <800ms for status/retrieval)
   - Memory profiling (<512MB per request)
   - Concurrent user simulation (10+ users)

## Open Questions / Future Enhancements

1. **Multi-language OCR**: Currently English-only; expand to configurable language packs
2. **Confidence Scores**: Expose Tesseract confidence metrics in HOCR output
3. **Image Preprocessing**: Auto-rotation, de-skewing, noise reduction (out of scope per spec)
4. **Result Formats**: Support additional formats beyond HOCR (plain text, searchable PDF)
5. **Batch Processing**: Multiple documents in single request (out of scope per spec)
6. **Webhooks**: Push notifications on completion (rejected in clarification Q5)

## References

- Tesseract OCR: https://github.com/tesseract-ocr/tesseract
- HOCR Specification: https://github.com/kba/hocr-spec
- FastAPI Documentation: https://fastapi.tiangolo.com
- Redis TTL Documentation: https://redis.io/commands/expire
- Prometheus Best Practices: https://prometheus.io/docs/practices/naming
