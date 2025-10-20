# Research: Direct OCR Processing Endpoints

**Date**: 2025-10-19
**Phase**: 0 (Outline & Research)

## Overview

This document consolidates research findings for implementing synchronous OCR endpoints. All technical unknowns from the planning phase have been investigated and resolved.

## 1. FastAPI Timeout Implementation

### Decision
Use `asyncio.wait_for()` to enforce request-level timeouts for synchronous OCR processing.

### Rationale
- **Native asyncio support**: Python's standard library provides `asyncio.wait_for(coro, timeout)` which raises `asyncio.TimeoutError` after the specified duration
- **FastAPI compatibility**: Works seamlessly with FastAPI's async path operations without requiring additional dependencies
- **Clean error handling**: Timeout exceptions can be caught and converted to HTTP 408 responses using FastAPI's exception handling
- **No middleware overhead**: Timeout is enforced at the route level, providing fine-grained control per endpoint

### Implementation Pattern
```python
import asyncio
from fastapi import HTTPException

@app.post("/sync/tesseract")
async def sync_tesseract(file: UploadFile):
    try:
        # Enforce 30-second timeout
        result = await asyncio.wait_for(
            process_document_async(file),
            timeout=30.0
        )
        return {"hocr": result}
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=408,
            detail="Processing timeout exceeded. Use async endpoints for large documents."
        )
```

### Alternatives Considered
1. **Starlette BackgroundTasks with threading.Timer**: Rejected because it doesn't integrate well with async operations and requires manual thread management
2. **Third-party timeout libraries (async-timeout)**: Rejected because `asyncio.wait_for()` is part of the standard library (Python 3.11+) and sufficient for our needs
3. **Uvicorn/Gunicorn timeout settings**: Rejected because these are worker-level timeouts, not request-level; too coarse-grained for this feature
4. **FastAPI middleware timeout**: Rejected because it would affect all endpoints, including async ones; we need per-route control

### References
- FastAPI async operations: https://fastapi.tiangolo.com/async/
- Python asyncio.wait_for: https://docs.python.org/3/library/asyncio-task.html#asyncio.wait_for

---

## 2. File Size Validation Strategy

### Decision
Validate file size **before** processing using `UploadFile.size` attribute and custom dependency injection.

### Rationale
- **Early rejection**: Prevents wasting resources on files that will timeout
- **FastAPI dependencies**: Can create a reusable `Depends()` validator for all sync endpoints
- **Consistent error messages**: Returns HTTP 413 (Payload Too Large) immediately, before any processing
- **Reuses existing patterns**: The codebase already has file validators in `src/utils/validators.py`

### Implementation Pattern
```python
from fastapi import Depends, HTTPException, UploadFile
from src.config import settings

SYNC_MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

async def validate_sync_file_size(file: UploadFile) -> UploadFile:
    """Validate file size for synchronous endpoints (5MB limit)."""
    # Read file in chunks to get size without loading entire file
    contents = await file.read()
    file_size = len(contents)

    # Reset file pointer for later processing
    await file.seek(0)

    if file_size > SYNC_MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File size {file_size} exceeds {SYNC_MAX_FILE_SIZE} byte limit. Use async endpoints for large files."
        )

    return file

@app.post("/sync/tesseract")
async def sync_tesseract(file: UploadFile = Depends(validate_sync_file_size)):
    # File is already validated, proceed with processing
    ...
```

### Alternatives Considered
1. **Check file size during processing**: Rejected because resources are already committed; timeout is less informative than size limit error
2. **Streaming validation**: Rejected because OCRProcessor needs the full file; streaming adds complexity without benefit
3. **Client-side size limits only**: Rejected because client can be bypassed; server must enforce limits

### References
- FastAPI file uploads: https://fastapi.tiangolo.com/tutorial/request-files/
- UploadFile API: https://fastapi.tiangolo.com/reference/uploadfile/

---

## 3. Response Format for hOCR Content

### Decision
Return hOCR as an **escaped XML string** within a JSON response body, not as raw XML.

### Rationale
- **API consistency**: All existing endpoints return JSON (job status, errors, health checks); mixing JSON and XML responses complicates client code
- **Error response compatibility**: Error responses are JSON; having success responses also as JSON maintains uniform error handling logic
- **Content negotiation**: No need for `Accept` header handling or multiple response formats
- **Specification requirement**: FR-003 explicitly requires "hOCR content in a JSON response body with the hOCR XML as an escaped string field"
- **Easy parsing**: Clients can parse JSON first, then extract and parse hOCR XML separately if needed

### Response Schema
```python
from pydantic import BaseModel

class SyncOCRResponse(BaseModel):
    """Response model for synchronous OCR processing."""
    hocr: str  # Escaped XML string
    processing_duration_seconds: float
    engine: str  # "tesseract" | "easyocr" | "ocrmac"
    pages: int  # Number of pages processed
```

### Example Response
```json
{
  "hocr": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Transitional//EN\" \"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd\"><html>...</html>",
  "processing_duration_seconds": 2.34,
  "engine": "tesseract",
  "pages": 1
}
```

### Alternatives Considered
1. **Return raw XML with Content-Type: application/xml**: Rejected due to API inconsistency (all other responses are JSON)
2. **Base64-encode hOCR**: Rejected because it's unnecessary; JSON string escaping is sufficient and more human-readable
3. **Separate metadata endpoint**: Rejected because it reintroduces the multi-request pattern we're trying to avoid

### References
- Pydantic models: https://docs.pydantic.dev/latest/
- FastAPI response models: https://fastapi.tiangolo.com/tutorial/response-model/

---

## 4. Temporary File Cleanup Strategy

### Decision
Reuse existing `FileHandler` cleanup logic with **context manager pattern** to ensure cleanup on success, timeout, or error.

### Rationale
- **Existing infrastructure**: `src/services/file_handler.py` already handles temporary file storage and cleanup for async endpoints
- **Guaranteed cleanup**: Python context managers (`with` / `finally`) ensure cleanup even if exceptions occur
- **No job persistence**: Unlike async endpoints, sync endpoints don't need to persist files for later retrieval; immediate cleanup is correct
- **Memory efficiency**: Cleanup within 1 second of request completion (requirement FR-016)

### Implementation Pattern
```python
from src.services.file_handler import FileHandler
from contextlib import asynccontextmanager

@asynccontextmanager
async def temporary_upload(file: UploadFile):
    """Context manager for temporary file handling with guaranteed cleanup."""
    file_handler = FileHandler()
    file_path = None

    try:
        # Save uploaded file
        file_path = await file_handler.save_upload(file)
        yield file_path
    finally:
        # Cleanup happens regardless of success, timeout, or error
        if file_path:
            await file_handler.cleanup_file(file_path)

@app.post("/sync/tesseract")
async def sync_tesseract(file: UploadFile):
    async with temporary_upload(file) as file_path:
        # Process document (cleanup guaranteed on exit)
        result = await asyncio.wait_for(
            processor.process_document(file_path),
            timeout=30.0
        )
    return {"hocr": result}
```

### Alternatives Considered
1. **Background tasks cleanup**: Rejected because cleanup should be immediate, not deferred
2. **Manual try/finally in each endpoint**: Rejected to avoid code duplication; context manager is reusable
3. **Shared cleanup with async endpoints**: Considered but rejected; async endpoints need persistent storage until job completion, sync endpoints should cleanup immediately

### References
- Python context managers: https://docs.python.org/3/library/contextlib.html#contextlib.asynccontextmanager
- Existing FileHandler: `src/services/file_handler.py`

---

## 5. Metrics and Observability

### Decision
Extend existing `src/utils/metrics.py` with Prometheus-style counters and histograms for sync endpoint observability.

### Rationale
- **Existing infrastructure**: The codebase already uses structured logging and metrics collection
- **Prometheus compatibility**: Industry-standard metrics format, compatible with Grafana dashboards
- **Requirements alignment**: FR-014a requires tracking request count, latency percentiles (p50, p95, p99), timeout rate, and per-engine success rate
- **Minimal overhead**: Metrics collection is fast and doesn't impact request latency

### Metrics Schema
```python
# New metrics to add to src/utils/metrics.py

sync_ocr_requests_total = Counter(
    'sync_ocr_requests_total',
    'Total synchronous OCR requests',
    ['engine', 'status']  # status: success, timeout, error
)

sync_ocr_duration_seconds = Histogram(
    'sync_ocr_duration_seconds',
    'Synchronous OCR processing duration',
    ['engine'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0]  # Aligned with timeout budget
)

sync_ocr_timeouts_total = Counter(
    'sync_ocr_timeouts_total',
    'Total synchronous OCR timeouts',
    ['engine']
)

sync_ocr_file_size_bytes = Histogram(
    'sync_ocr_file_size_bytes',
    'Synchronous OCR file sizes',
    ['engine'],
    buckets=[1024, 10240, 102400, 1048576, 5242880]  # 1KB to 5MB
)
```

### Alternatives Considered
1. **Logging only (no metrics)**: Rejected because logs don't provide aggregated statistics like p95 latency
2. **Third-party APM (DataDog, New Relic)**: Out of scope; Prometheus metrics are sufficient and vendor-neutral
3. **Custom metrics database**: Rejected due to complexity; Prometheus is industry standard

### References
- Prometheus Python client: https://github.com/prometheus/client_python
- Existing metrics: `src/utils/metrics.py`

---

## 6. Error Response Consistency

### Decision
Reuse existing FastAPI exception handlers to ensure sync and async endpoints return identical error formats.

### Rationale
- **Requirement FR-022**: "System MUST return error responses in the same JSON format as async endpoints for consistency"
- **Existing infrastructure**: `src/api/middleware/error_handler.py` already handles HTTP exceptions uniformly
- **Client simplification**: Clients can use the same error parsing logic for both sync and async endpoints
- **No new code**: Just ensure sync endpoints raise standard `HTTPException` instances

### Error Response Format (Existing)
```json
{
  "detail": "Error message here",
  "status_code": 408
}
```

### Error Mapping for Sync Endpoints
| Scenario | HTTP Status | Detail Message |
|----------|-------------|----------------|
| Timeout exceeded | 408 Request Timeout | "Processing timeout exceeded. Use async endpoints for large documents." |
| File size too large | 413 Payload Too Large | "File size exceeds 5MB limit. Use async endpoints for large files." |
| Invalid file format | 415 Unsupported Media Type | "Unsupported file format. Supported: JPEG, PNG, PDF, TIFF" |
| Engine unavailable | 400 Bad Request | "OCR engine 'ocrmac' is unavailable on this platform" |
| Processing error | 500 Internal Server Error | "OCR processing failed: {error details}" |

### Alternatives Considered
1. **Custom error format for sync endpoints**: Rejected due to FR-022 requirement for consistency
2. **Include stack traces in errors**: Rejected for security; only include user-facing error details

### References
- FastAPI error handling: https://fastapi.tiangolo.com/tutorial/handling-errors/
- Existing error handler: `src/api/middleware/error_handler.py`

---

## 7. Engine Availability Validation

### Decision
Check engine availability **before** file upload using existing `OCREngineRegistry` pattern.

### Rationale
- **Fast failure**: Reject requests immediately if engine is unavailable (e.g., ocrmac on Linux)
- **Existing pattern**: `src/services/ocr/registry.py` already tracks engine availability
- **Platform-specific logic**: ocrmac availability is checked at startup and cached
- **Clear error messages**: HTTP 400 with details about platform requirements

### Implementation Pattern
```python
from src.services.ocr.registry import engine_registry

@app.post("/sync/ocrmac")
async def sync_ocrmac(file: UploadFile):
    # Check availability before processing
    if not engine_registry.is_available("ocrmac"):
        raise HTTPException(
            status_code=400,
            detail="ocrmac engine is only available on macOS with Apple Vision framework"
        )
    # Proceed with processing...
```

### Alternatives Considered
1. **Check availability after file upload**: Rejected because it wastes resources on doomed requests
2. **Remove unavailable endpoints at startup**: Rejected because it complicates documentation; better to return 400 error
3. **Automatic fallback to Tesseract**: Rejected as out of scope (per spec); users must explicitly choose engine

### References
- Existing engine registry: `src/services/ocr/registry.py`
- Platform detection: `src/utils/platform.py`

---

## 8. Backward Compatibility Verification

### Decision
No changes to existing async endpoints; sync endpoints are **additive only**.

### Rationale
- **Requirement FR-020**: "System MUST preserve all existing async endpoint functionality without modification or performance degradation"
- **Separate routes**: Sync endpoints use new route prefix (`/sync/`) to avoid path conflicts
- **No shared state modification**: Sync endpoints don't use job queue (Redis) at all
- **Independent testing**: Existing async endpoint tests remain unchanged; new tests for sync endpoints

### Verification Strategy
1. Run existing test suite without modification → 100% pass rate required
2. Add new sync endpoint tests in separate test files
3. Performance tests to ensure async endpoint metrics unchanged

### Routes Separation
```
Existing (unchanged):
- POST /upload/tesseract
- POST /upload/easyocr
- POST /upload/ocrmac
- GET /jobs/{job_id}
- GET /jobs/{job_id}/result

New (additive):
- POST /sync/tesseract
- POST /sync/easyocr
- POST /sync/ocrmac
```

### Alternatives Considered
1. **Optional query parameter `?sync=true` on existing routes**: Rejected due to higher risk of breaking changes
2. **Version prefix `/v2/upload/`**: Rejected because functionality is different, not a version upgrade
3. **Deprecate async endpoints**: Rejected; async endpoints remain recommended for multi-page/large documents

### References
- Existing routes: `src/api/routes/upload.py`, `src/api/routes/jobs.py`
- Backward compatibility requirement: spec.md FR-020

---

## Summary of Technical Decisions

| Area | Decision | Key Technology/Pattern |
|------|----------|----------------------|
| Timeout enforcement | `asyncio.wait_for()` at route level | Python stdlib asyncio |
| File size validation | Custom FastAPI dependency with `UploadFile.size` | FastAPI Depends() |
| Response format | JSON with escaped hOCR XML string | Pydantic BaseModel |
| File cleanup | Context manager with `finally` block | asynccontextmanager |
| Metrics | Prometheus counters/histograms | Existing metrics.py |
| Error handling | Reuse existing HTTPException handlers | FastAPI middleware |
| Engine validation | Check `OCREngineRegistry` before processing | Existing registry.py |
| Backward compatibility | Separate `/sync/` routes, no changes to async | Additive-only approach |

---

## Open Questions Resolved

✅ **Q1**: How to enforce request timeout in FastAPI?
**A**: Use `asyncio.wait_for()` with 30-second timeout, catch `asyncio.TimeoutError`, return HTTP 408

✅ **Q2**: When to validate file size?
**A**: Before processing using FastAPI dependency injection; return HTTP 413 immediately

✅ **Q3**: How to return hOCR in HTTP response?
**A**: JSON response with escaped XML string field (matches spec FR-003, FR-003a)

✅ **Q4**: How to ensure file cleanup on timeout/error?
**A**: Context manager pattern with `finally` block; guaranteed cleanup

✅ **Q5**: What metrics to track?
**A**: Request count, duration histogram (p50/p95/p99), timeout counter, file size histogram per engine (matches FR-014a)

✅ **Q6**: How to maintain error format consistency?
**A**: Reuse existing FastAPI exception handlers; raise standard HTTPException

✅ **Q7**: How to check engine availability?
**A**: Use existing `OCREngineRegistry.is_available()` before processing

✅ **Q8**: How to ensure backward compatibility?
**A**: Additive-only changes; new `/sync/` routes; no modifications to async endpoints

---

## Next Steps

Phase 1 (Design & Contracts) can proceed with all technical unknowns resolved:
- Generate `data-model.md` with `SyncOCRResponse` and validation models
- Generate OpenAPI contracts for three sync endpoints
- Generate `quickstart.md` with curl examples for sync vs async usage
- Update agent context (CLAUDE.md) with new technologies/patterns
