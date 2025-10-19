# API Contract Changes: Remove Generic Upload Endpoint

**Feature**: Remove Generic Upload Endpoint
**Branch**: `005-remove-generic-upload`
**Date**: 2025-10-19

## Summary

This document describes the breaking API changes introduced by removing the generic `/upload` endpoint.

## Breaking Changes

### Removed Endpoint

**Endpoint**: `POST /upload`
**Status**: REMOVED
**Effective Date**: Upon merge of this feature

**Before**:
```http
POST /upload HTTP/1.1
Content-Type: multipart/form-data

Response: 200 OK (if successful)
```

**After**:
```http
POST /upload HTTP/1.1

Response: 404 Not Found
{
  "detail": "Not Found"
}
```

**Migration Path**:
Clients must migrate to one of the engine-specific endpoints:
- `POST /upload/tesseract`
- `POST /upload/ocrmac` (macOS only)
- `POST /upload/easyocr`

## Stable Endpoints (No Changes)

### 1. Tesseract OCR Upload

**Endpoint**: `POST /upload/tesseract`
**Contract**: STABLE - No changes

**Request**:
```http
POST /upload/tesseract HTTP/1.1
Content-Type: multipart/form-data

file: <binary>
languages: en,fr (optional)
output_format: hocr (optional, default: hocr)
```

**Response** (200 OK):
```json
{
  "job_id": "string",
  "status": "pending",
  "created_at": "2025-10-19T12:00:00Z"
}
```

### 2. OCRMac Upload (macOS only)

**Endpoint**: `POST /upload/ocrmac`
**Contract**: STABLE - No changes

**Request**:
```http
POST /upload/ocrmac HTTP/1.1
Content-Type: multipart/form-data

file: <binary>
languages: en,fr (optional)
output_format: hocr (optional, default: hocr)
```

**Response** (200 OK):
```json
{
  "job_id": "string",
  "status": "pending",
  "created_at": "2025-10-19T12:00:00Z"
}
```

### 3. EasyOCR Upload

**Endpoint**: `POST /upload/easyocr`
**Contract**: STABLE - No changes

**Request**:
```http
POST /upload/easyocr HTTP/1.1
Content-Type: multipart/form-data

file: <binary>
languages: en,fr (optional)
output_format: hocr (optional, default: hocr)
```

**Response** (200 OK):
```json
{
  "job_id": "string",
  "status": "pending",
  "created_at": "2025-10-19T12:00:00Z"
}
```

## Error Responses

### New Error Response

**Scenario**: Client attempts to access removed generic endpoint

**Request**:
```http
POST /upload HTTP/1.1
```

**Response** (404 Not Found):
```json
{
  "detail": "Not Found"
}
```

### Existing Error Responses (Unchanged)

All error responses for engine-specific endpoints remain unchanged:

- **400 Bad Request**: Invalid file format or parameters
- **413 Payload Too Large**: File size exceeds limit
- **415 Unsupported Media Type**: File type not supported
- **422 Unprocessable Entity**: Validation error
- **500 Internal Server Error**: Server-side processing error

## OpenAPI Schema Changes

### Removed Path

```yaml
# REMOVED
/upload:
  post:
    summary: Upload document for OCR processing
    operationId: upload_document
    # ... (entire definition removed)
```

### Preserved Paths (No Changes)

```yaml
# UNCHANGED
/upload/tesseract:
  post:
    summary: Upload document for Tesseract OCR processing
    operationId: upload_document_tesseract
    # ...

/upload/ocrmac:
  post:
    summary: Upload document for OCRMac processing (macOS only)
    operationId: upload_document_ocrmac
    # ...

/upload/easyocr:
  post:
    summary: Upload document for EasyOCR processing
    operationId: upload_document_easyocr
    # ...
```

## Client Migration Guide

### For Existing Clients (None Expected)

According to the feature specification, there are no production clients using the generic endpoint. However, if any clients exist:

**Step 1**: Identify which OCR engine you want to use
- Tesseract: General-purpose, high accuracy
- OCRMac: macOS-optimized (macOS only)
- EasyOCR: Deep learning-based, supports more languages

**Step 2**: Update your endpoint URL
```diff
- POST /upload
+ POST /upload/tesseract  (or /upload/ocrmac or /upload/easyocr)
```

**Step 3**: Verify request parameters are compatible
- All engine-specific endpoints accept the same parameters
- No changes to request structure required

**Step 4**: Test with your client
- Verify 200 OK responses
- Confirm job_id is returned
- Test error handling paths

## Testing Requirements

### Contract Tests

The following contract tests must be updated:

1. **Add test**: Verify `POST /upload` returns 404
2. **Keep existing**: All tests for engine-specific endpoints
3. **Update OpenAPI**: Verify schema no longer includes `/upload`

### Verification Checklist

- [ ] Generic endpoint returns 404 Not Found
- [ ] Engine-specific endpoints return 200 OK for valid requests
- [ ] Error responses maintain consistent format
- [ ] OpenAPI schema is updated (no `/upload` path)
- [ ] API documentation reflects changes

## Rollback Plan

If this change needs to be reverted:

1. Restore `upload_document` function in `src/api/routes/upload.py`
2. Restore `@router.post("/upload")` decorator
3. Restore tests for generic endpoint
4. Restore OpenAPI schema entry
5. Restore documentation

**Note**: Rollback should not be necessary as no clients depend on this endpoint.

## Version Impact

**API Version**: No version bump required (internal cleanup)
**Breaking Change**: Yes, but with zero client impact

If following semantic versioning for the API, this would normally warrant a major version bump. However, since no production clients exist, the project may choose to treat this as a minor or patch version change.
