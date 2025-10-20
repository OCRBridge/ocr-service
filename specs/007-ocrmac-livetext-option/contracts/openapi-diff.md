# OpenAPI Schema Changes: LiveText Recognition Level

**Feature**: Add LiveText Recognition Level to ocrmac Engine
**Date**: 2025-10-20
**API Version**: 1.1.0 → 1.2.0 (minor version bump - new functionality, backward compatible)

## Summary

This document outlines the OpenAPI schema changes required to support the `livetext` recognition level. All changes are additive and backward compatible. No existing endpoints, parameters, or responses are modified except for enum extensions.

---

## Schema Components

### RecognitionLevel Enum (Modified)

**Location**: `#/components/schemas/RecognitionLevel`

**Before**:
```yaml
RecognitionLevel:
  type: string
  enum:
    - fast
    - balanced
    - accurate
  description: |
    OCR recognition quality level:
    - fast: Fewer languages, faster processing
    - balanced: Default, good balance of speed and accuracy
    - accurate: Slower, highest accuracy
```

**After**:
```yaml
RecognitionLevel:
  type: string
  enum:
    - fast
    - balanced
    - accurate
    - livetext
  description: |
    OCR recognition quality level:
    - fast: Fewer languages, faster processing (~131ms)
    - balanced: Default, good balance of speed and accuracy
    - accurate: Slower, highest accuracy (~207ms)
    - livetext: Apple LiveText framework, requires macOS Sonoma 14.0+ (~174ms)
  example: balanced
```

**Changes**:
- ✅ Added `livetext` to enum values
- ✅ Enhanced descriptions with performance characteristics
- ✅ Added platform requirement note for livetext
- ⚠️  No default value change (remains `balanced`)

---

## Affected Endpoints

### 1. POST /sync/ocrmac

**Before**:
```yaml
/sync/ocrmac:
  post:
    summary: Synchronous ocrmac (macOS only)
    parameters:
      - name: recognition_level
        in: formData
        required: false
        schema:
          $ref: '#/components/schemas/RecognitionLevel'
        default: balanced
```

**After**:
```yaml
/sync/ocrmac:
  post:
    summary: Synchronous ocrmac (macOS only)
    description: |
      Process a document with Apple Vision Framework or LiveText and receive hOCR output immediately.
      Maximum file size: 5MB. Maximum processing time: 30 seconds.
      Only available on macOS. LiveText requires macOS Sonoma (14.0) or later.
    parameters:
      - name: recognition_level
        in: formData
        required: false
        schema:
          $ref: '#/components/schemas/RecognitionLevel'
        default: balanced
        description: |
          Recognition quality level. LiveText option requires macOS Sonoma 14.0+.
```

**Changes**:
- ✅ Enhanced description to mention LiveText
- ✅ Added platform requirement clarification
- ⚠️  RecognitionLevel enum automatically includes `livetext` via schema reference

---

### 2. POST /upload/ocrmac

**Before**:
```yaml
/upload/ocrmac:
  post:
    summary: Upload document for ocrmac OCR processing (macOS only)
    parameters:
      - name: recognition_level
        in: formData
        required: false
        schema:
          $ref: '#/components/schemas/RecognitionLevel'
        default: balanced
```

**After**:
```yaml
/upload/ocrmac:
  post:
    summary: Upload document for ocrmac OCR processing (macOS only)
    description: |
      Upload a document for OCR processing using ocrmac engine (macOS only).
      Supports Vision Framework (fast, balanced, accurate) and LiveText (macOS Sonoma 14.0+).
    parameters:
      - name: recognition_level
        in: formData
        required: false
        schema:
          $ref: '#/components/schemas/RecognitionLevel'
        default: balanced
        description: |
          Recognition quality level. LiveText option requires macOS Sonoma 14.0+.
```

**Changes**:
- ✅ Enhanced description to mention LiveText
- ✅ Added platform requirement clarification
- ⚠️  RecognitionLevel enum automatically includes `livetext` via schema reference

---

## Error Responses (New/Updated)

### HTTP 400: Platform Incompatibility

**New Error Response for Pre-Sonoma macOS**:

```yaml
400:
  description: Bad Request - LiveText not available on this macOS version
  content:
    application/json:
      schema:
        type: object
        properties:
          detail:
            type: string
            example: "LiveText recognition requires macOS Sonoma (14.0) or later. Available recognition levels: fast, balanced, accurate"
```

**When Triggered**:
- User requests `recognition_level=livetext` on macOS < 14.0
- User requests `recognition_level=livetext` on non-macOS platform

---

### HTTP 422: Validation Error

**Existing Error (Enhanced Documentation)**:

```yaml
422:
  description: Validation Error - Invalid recognition level value
  content:
    application/json:
      schema:
        type: object
        properties:
          detail:
            type: array
            items:
              type: object
              properties:
                loc:
                  type: array
                  items:
                    type: string
                  example: ["body", "recognition_level"]
                msg:
                  type: string
                  example: "value is not a valid enumeration member; permitted: 'fast', 'balanced', 'accurate', 'livetext'"
                type:
                  type: string
                  example: "value_error.enum"
```

**When Triggered**:
- User provides invalid recognition_level value (e.g., `"livetextt"` with typo)
- Pydantic automatically validates against RecognitionLevel enum

---

### HTTP 500: Library Incompatibility

**New Error Response for Unsupported ocrmac Version**:

```yaml
500:
  description: Internal Server Error - ocrmac library version incompatibility
  content:
    application/json:
      schema:
        type: object
        properties:
          detail:
            type: string
            example: "ocrmac library version does not support LiveText framework. Please upgrade to a newer version of ocrmac that supports the framework parameter."
```

**When Triggered**:
- User requests `recognition_level=livetext` but ocrmac library doesn't support `framework` parameter
- Backend cannot initialize `ocrmac.OCR(..., framework="livetext")`

---

### HTTP 500: Unexpected Output Format

**New Error Response for LiveText Processing Errors**:

```yaml
500:
  description: Internal Server Error - Unexpected LiveText output format
  content:
    application/json:
      schema:
        type: object
        properties:
          detail:
            type: string
            example: "LiveText processing returned unexpected output format"
```

**When Triggered**:
- LiveText returns annotations in unexpected structure
- Annotation validation fails before hOCR conversion

---

## Response Schemas

### SyncOCRResponse (No Changes)

**Schema**:
```yaml
SyncOCRResponse:
  type: object
  properties:
    hocr:
      type: string
      description: hOCR XML output (metadata includes framework type)
    engine:
      type: string
      pattern: ^(tesseract|easyocr|ocrmac)$
      example: ocrmac
    pages:
      type: integer
      minimum: 1
    processing_duration_seconds:
      type: number
      minimum: 0
```

**Changes**:
- ⚠️  No schema changes
- ℹ️  `hocr` content includes framework type in metadata (`<meta name="ocr-system">`)
- ℹ️  `engine` value remains `"ocrmac"` for both Vision and LiveText (framework is internal detail)

---

### UploadResponse (No Changes)

**Schema**:
```yaml
UploadResponse:
  type: object
  properties:
    job_id:
      type: string
      format: uuid
    status:
      type: string
      enum: [pending]
    message:
      type: string
```

**Changes**: None - async responses unaffected by recognition level

---

## Backward Compatibility

### Client Compatibility

**Old Client → New API**:
- ✅ Clients using `fast`, `balanced`, `accurate` → No changes required
- ✅ Clients omitting `recognition_level` → Default remains `balanced`
- ✅ Old clients unaware of `livetext` → Continue working unchanged

**New Client → Old API**:
- ⚠️  Clients sending `recognition_level=livetext` to old API → HTTP 422 (enum validation failure)
- ℹ️  Error message clearly indicates unsupported value with permitted options

### API Versioning

- **Version Bump**: 1.1.0 → 1.2.0 (minor version - new functionality, backward compatible)
- **Versioning Strategy**: No breaking changes; enum extension follows semantic versioning
- **Migration Path**: None required - clients adopt `livetext` as needed

---

## OpenAPI Specification Diff

**Full Diff** (generated from Pydantic models):

```diff
  components:
    schemas:
      RecognitionLevel:
        type: string
        enum:
          - fast
          - balanced
          - accurate
+         - livetext
        description: |
-         OCR recognition quality level:
-         - fast: Fewer languages, faster processing
-         - balanced: Default, good balance of speed and accuracy
-         - accurate: Slower, highest accuracy
+         OCR recognition quality level:
+         - fast: Fewer languages, faster processing (~131ms)
+         - balanced: Default, good balance of speed and accuracy
+         - accurate: Slower, highest accuracy (~207ms)
+         - livetext: Apple LiveText framework, requires macOS Sonoma 14.0+ (~174ms)

  paths:
    /sync/ocrmac:
      post:
        description: |
-         Process a document with Apple Vision Framework and receive hOCR output immediately.
+         Process a document with Apple Vision Framework or LiveText and receive hOCR output immediately.
          Maximum file size: 5MB. Maximum processing time: 30 seconds.
-         Only available on macOS.
+         Only available on macOS. LiveText requires macOS Sonoma (14.0) or later.

    /upload/ocrmac:
      post:
        description: |
-         Upload a document for OCR processing using ocrmac engine (macOS only).
+         Upload a document for OCR processing using ocrmac engine (macOS only).
+         Supports Vision Framework (fast, balanced, accurate) and LiveText (macOS Sonoma 14.0+).
```

---

## Validation & Testing

### Contract Tests Required

1. **Enum Validation**:
   - ✅ `recognition_level=livetext` accepted (HTTP 200/202)
   - ✅ `recognition_level=livetextt` rejected (HTTP 422)
   - ✅ Default value remains `balanced` when omitted

2. **Error Response Formats**:
   - ✅ HTTP 400 for pre-Sonoma macOS (correct error message)
   - ✅ HTTP 500 for library incompatibility (correct error message)
   - ✅ HTTP 500 for unexpected output (correct error message)

3. **Backward Compatibility**:
   - ✅ `recognition_level=fast` still works (HTTP 200/202)
   - ✅ `recognition_level=balanced` still works (HTTP 200/202)
   - ✅ `recognition_level=accurate` still works (HTTP 200/202)
   - ✅ Omitting `recognition_level` defaults to `balanced` (HTTP 200/202)

4. **OpenAPI Schema**:
   - ✅ `/openapi.json` includes `livetext` in RecognitionLevel enum
   - ✅ Endpoint descriptions mention LiveText requirements
   - ✅ Error response schemas documented

---

## Implementation Checklist

- [ ] Update `src/models/ocr_params.py`: Add `LIVETEXT = "livetext"` to RecognitionLevel enum
- [ ] Update RecognitionLevel enum docstring with platform requirements
- [ ] Verify OpenAPI schema auto-generation includes new enum value
- [ ] Add contract tests for livetext parameter validation
- [ ] Add contract tests for error responses (HTTP 400/500)
- [ ] Verify backward compatibility with existing recognition levels
- [ ] Update API documentation with LiveText requirements

---

## Related Artifacts

- **Data Model**: [data-model.md](../data-model.md) - RecognitionLevel enum definition
- **Research**: [research.md](../research.md) - Platform requirements and error handling
- **Specification**: [spec.md](../spec.md) - Functional requirements FR-001 through FR-014

---

## Notes

- OpenAPI schema is auto-generated from Pydantic models - manual schema files not required
- All enum changes propagate automatically through FastAPI's OpenAPI generation
- Error response formats follow existing patterns in the codebase
- Platform requirements documented in both endpoint descriptions and enum descriptions for clarity
