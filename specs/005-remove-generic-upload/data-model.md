# Data Model: Remove Generic Upload Endpoint

**Feature**: Remove Generic Upload Endpoint
**Branch**: `005-remove-generic-upload`
**Date**: 2025-10-19

## Overview

This feature does not introduce any new data models or modify existing ones. It is purely a routing layer change that removes an endpoint without affecting data structures.

## Affected Models

### No New Models

This feature does not create any new data models.

### No Modified Models

This feature does not modify any existing data models. The following models remain unchanged:

- Request models for engine-specific endpoints (TesseractOCRRequest, OCRMacRequest, EasyOCRRequest)
- Response models (OCRResponse, JobResponse)
- Job state models (stored in Redis)

## Entity Relationships

### Current State (Unchanged)

```
┌─────────────────┐
│  Client Request │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Upload Endpoint        │
│  (Engine-Specific Only) │
└────────┬────────────────┘
         │
         ▼
┌─────────────────┐
│   OCR Service   │
│   (Tesseract,   │
│   OCRMac, or    │
│   EasyOCR)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Job State     │
│   (Redis)       │
└─────────────────┘
```

The data flow remains identical to the current implementation, with the only change being the removal of the generic `/upload` entry point.

## API Contracts

### Removed Endpoint

**Endpoint**: `POST /upload`
**Status**: REMOVED (will return 404)

### Preserved Endpoints (No Changes)

1. **Tesseract OCR**
   - Endpoint: `POST /upload/tesseract`
   - Request/Response: Unchanged
   - Contract: Stable

2. **OCRMac** (macOS only)
   - Endpoint: `POST /upload/ocrmac`
   - Request/Response: Unchanged
   - Contract: Stable

3. **EasyOCR**
   - Endpoint: `POST /upload/easyocr`
   - Request/Response: Unchanged
   - Contract: Stable

## Validation Rules

### No Changes

All existing validation rules for engine-specific endpoints remain unchanged:

- File type validation (PDF, image formats)
- File size limits
- Parameter validation (language codes, output formats, etc.)

## State Transitions

### No Changes

Job state transitions managed by Redis remain unchanged:

```
PENDING → PROCESSING → COMPLETED
                    ↓
                  FAILED
```

## Summary

This feature is a pure API surface reduction with:
- **Zero data model changes**
- **Zero validation rule changes**
- **Zero state transition changes**

The only change is the removal of one routing entry point, making this a low-risk refactoring task.
