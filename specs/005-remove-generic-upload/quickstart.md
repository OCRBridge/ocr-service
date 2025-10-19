# Quickstart: Remove Generic Upload Endpoint

**Feature**: Remove Generic Upload Endpoint
**Branch**: `005-remove-generic-upload`
**Date**: 2025-10-19

## Overview

This guide provides a quick reference for implementing the removal of the generic `/upload` endpoint from the RESTful OCR API.

## Prerequisites

- Feature branch checked out: `005-remove-generic-upload`
- Development environment set up (see main README.md)
- Redis running locally or via Docker Compose
- All existing tests passing before changes

## Quick Implementation Steps

### Step 1: Update Tests (Test-First Approach)

Following TDD principles from the project constitution:

```bash
# Create test for removed endpoint
# Edit: tests/unit/api/routes/test_upload.py
```

Add this test:
```python
async def test_generic_upload_endpoint_returns_404(client):
    """Verify that the generic /upload endpoint returns 404 after removal."""
    # Arrange
    files = {"file": ("test.pdf", b"fake pdf content", "application/pdf")}

    # Act
    response = await client.post("/upload", files=files)

    # Assert
    assert response.status_code == 404
    assert "detail" in response.json()
```

### Step 2: Run Failing Test

```bash
# This test should fail initially
uv run pytest tests/unit/api/routes/test_upload.py::test_generic_upload_endpoint_returns_404 -v
```

Expected output: Test fails because `/upload` still exists

### Step 3: Remove the Generic Endpoint

Edit `src/api/routes/upload.py`:

```python
# REMOVE THIS FUNCTION AND ITS DECORATOR:
# @router.post("/upload", response_model=JobResponse)
# async def upload_document(...):
#     ...
```

**What to keep:**
- All engine-specific functions (`upload_document_tesseract`, `upload_document_ocrmac`, `upload_document_easyocr`)
- Helper functions (if any)
- Imports and router definition

**What to remove:**
- Only the `upload_document` function and its `@router.post("/upload")` decorator

### Step 4: Verify Test Passes

```bash
# Test should now pass
uv run pytest tests/unit/api/routes/test_upload.py::test_generic_upload_endpoint_returns_404 -v
```

Expected output: Test passes (404 returned)

### Step 5: Update Existing Tests

Remove any tests that specifically test the generic `/upload` endpoint:

```bash
# Review and remove old tests
# Edit: tests/unit/api/routes/test_upload.py
# Remove: test_upload_document_generic() or similar
```

### Step 6: Run Full Test Suite

```bash
# Ensure all tests pass
uv run pytest tests/ -v

# Check coverage
uv run pytest --cov=src --cov-report=term
```

Expected outcome:
- All tests pass
- Coverage remains ≥80% overall, ≥90% for utilities

### Step 7: Update Documentation

#### Update API Docs

If there's an OpenAPI schema file or documentation:
```bash
# The FastAPI app auto-generates OpenAPI schema
# Verify at http://localhost:8000/docs after starting the server
# Ensure /upload is not listed
```

#### Update README (if applicable)

Search for any references to `/upload`:
```bash
grep -r "POST /upload" README.md
```

Replace with engine-specific endpoint examples.

### Step 8: Verify Locally

Start the application:
```bash
# Start Redis
docker compose up -d redis

# Start API
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Test manually:
```bash
# Should return 404
curl -X POST http://localhost:8000/upload \
  -F "file=@samples/invoice-sample.pdf"

# Should return 200
curl -X POST http://localhost:8000/upload/tesseract \
  -F "file=@samples/invoice-sample.pdf"
```

Expected results:
- `/upload` returns 404
- `/upload/tesseract` returns job_id and 200 status

## Verification Checklist

Before pushing changes:

- [ ] Test for 404 on `/upload` passes
- [ ] All engine-specific endpoint tests pass
- [ ] Full test suite passes
- [ ] Code coverage meets thresholds (≥80% overall)
- [ ] Manual testing confirms 404 on `/upload`
- [ ] Manual testing confirms engine-specific endpoints work
- [ ] OpenAPI docs at `/docs` no longer show `/upload`
- [ ] No references to generic endpoint in README or docs

## Common Issues & Solutions

### Issue 1: Tests Still Reference Generic Endpoint

**Symptom**: Tests fail because they try to use `/upload`

**Solution**:
```bash
# Find all references
grep -r "POST /upload" tests/

# Update to use engine-specific endpoints
# Replace: client.post("/upload", ...)
# With: client.post("/upload/tesseract", ...)
```

### Issue 2: Import Errors After Removal

**Symptom**: Other files import the removed function

**Solution**:
```bash
# Search for imports
grep -r "from.*upload_document" src/

# Remove or update imports
```

### Issue 3: Coverage Drops

**Symptom**: Coverage falls below 80% threshold

**Solution**: Ensure removed tests are replaced with equivalent coverage for engine-specific endpoints

## Next Steps

After completing the implementation:

1. Run `/speckit.tasks` to generate the detailed task breakdown
2. Implement tasks in order
3. Create a PR following the project's PR template
4. Ensure CI passes all gates (lint, tests, coverage, security scan)

## Time Estimate

- **Test writing**: 15 minutes
- **Code removal**: 10 minutes
- **Documentation update**: 15 minutes
- **Verification**: 10 minutes
- **Total**: ~50 minutes

This is a low-complexity change with minimal risk.

## References

- [Specification](./spec.md)
- [Implementation Plan](./plan.md)
- [Research](./research.md)
- [API Contract Changes](./contracts/api-changes.md)
- [Project Constitution](../../.specify/memory/constitution.md)
