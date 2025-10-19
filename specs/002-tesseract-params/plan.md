# Implementation Plan: Configurable Tesseract OCR Parameters

**Branch**: `002-tesseract-params` | **Date**: 2025-10-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-tesseract-params/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature exposes Tesseract OCR configuration parameters (language, page segmentation mode, OCR engine mode, and DPI) as optional API parameters on the document upload endpoint. Users can customize OCR processing for their specific document types and languages, improving recognition accuracy for non-English documents, specialized layouts (receipts, forms, business cards), and various image resolutions. Parameters are validated before processing with clear error messages, maintaining deterministic behavior while extending the API contract to support multilingual and specialized OCR use cases.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI 0.104+, Pydantic 2.5+, pytesseract 0.3+, Tesseract 5.3+
**Storage**: Redis 7.0+ (job state), filesystem (temporary uploaded files)
**Testing**: pytest 7.4+ with pytest-asyncio for async tests, httpx for API contract testing
**Target Platform**: Linux server (Docker containerized), also macOS for development
**Project Type**: Single web API service
**Performance Goals**: <800ms p95 end-to-end latency for 1MP grayscale images, <100ms for parameter validation, <30s for single-page documents
**Constraints**: <512MB memory per request, deterministic output for same input+parameters, parameter validation must occur synchronously during upload
**Scale/Scope**: Extends existing single-endpoint API with 4 new optional parameters (lang, psm, oem, dpi), maintains backward compatibility with existing clients

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle 1: API Contract First ✅ PASS
- OpenAPI contract will be updated to include new optional parameters (lang, psm, oem, dpi) before implementation
- Breaking changes: None - all parameters are optional with backward-compatible defaults
- Contract versioning: Same endpoint path, extended request schema only

### Principle 2: Deterministic & Reproducible Processing ✅ PASS
- Same image + same parameters → identical OCR output
- Parameters (lang, psm, oem, dpi) are deterministic Tesseract configurations
- No random seeds or heuristics introduced
- All parameters logged for reproducibility

### Principle 3: Test-First & Coverage Discipline ✅ PASS
- TDD approach: Write failing tests before implementation for each parameter
- Coverage targets: 90% for parameter validation utilities, 80% overall, 100% for parameter parsing/validation functions
- Contract tests: Cover all parameter combinations, validation edge cases, error paths
- Integration tests: End-to-end with various parameter values

### Principle 4: Performance & Resource Efficiency ✅ PASS
- Parameter validation adds <100ms to upload (in-spec)
- No impact on OCR processing time budget (<800ms p95, <30s single-page)
- Memory: No additional overhead beyond existing job metadata storage
- Validation is lightweight (regex + range checks)

### Principle 5: Observability & Transparency ✅ PASS
- Structured JSON logs will include all parameter values (lang, psm, oem, dpi) with job ID correlation
- Metrics: Track parameter usage distribution, validation errors by type
- No silent failures: All validation errors return explicit HTTP 400 with details

### Principle 6: Security & Data Privacy ✅ PASS
- Parameter validation uses strict whitelist regex patterns (FR-005a)
- Prevents injection attacks through command parameters
- No additional data retention (parameters logged but not persisted beyond job completion)
- Input validation rejects malicious patterns immediately

### Principle 7: Simplicity & Minimal Surface ✅ PASS
- Extends existing upload model with 4 optional fields
- No new abstractions or complex heuristics
- Validation logic is straightforward (regex + range checks + installed language check)
- Reuses existing error handling patterns

### Principle 8: Documentation & Library Reference ✅ PASS
- Will use Context7 for pytesseract API documentation and Tesseract parameter references
- Will consult Pydantic best practices for request validation patterns
- Will reference FastAPI documentation for query parameter handling

**GATE RESULT: ✅ ALL PRINCIPLES PASS - No violations, proceed to Phase 0**

---

**POST-DESIGN RE-EVALUATION (Phase 1 Complete):**

### Principle 1: API Contract First ✅ CONFIRMED
- OpenAPI contract defined in `contracts/openapi-extension.yaml`
- All parameters documented with examples, validation rules, and error responses
- No breaking changes - all parameters optional with backward-compatible defaults
- Contract ready for review before implementation

### Principle 2: Deterministic & Reproducible Processing ✅ CONFIRMED
- Parameters stored in Redis job metadata for reproducibility
- Same document + same parameters → identical HOCR output
- Logged in structured format with job ID correlation
- No non-deterministic behavior introduced

### Principle 3: Test-First & Coverage Discipline ✅ CONFIRMED
- Test strategy defined in data-model.md (validation, integration, contract tests)
- Coverage targets: 90% for validators, 80% overall, 100% for parameter parsing
- Will follow TDD: Write failing tests before implementation

### Principle 4: Performance & Resource Efficiency ✅ CONFIRMED
- Parameter validation overhead: <100ms (within SC-006 budget)
- LRU cache for language detection reduces overhead to ~1ms
- Pydantic Field constraints (Rust-based) for maximum performance
- No impact on OCR processing budget (<800ms p95)

### Principle 5: Observability & Transparency ✅ CONFIRMED
- Structured logging design defined: all parameters logged with job ID
- Log events: validation_started, validation_failed, validation_succeeded, processing_started
- Parameters included in job status response for transparency
- Metrics can track parameter usage distribution, validation errors

### Principle 6: Security & Data Privacy ✅ CONFIRMED
- Strict whitelist validation: regex patterns for lang, Literal for psm, Field constraints for oem/dpi
- Defense in depth: Pydantic validation + pytesseract library sanitization
- No parameters persisted beyond job completion (same as current)
- Attack vectors (injection, path traversal) prevented by validation

### Principle 7: Simplicity & Minimal Surface ✅ CONFIRMED
- Design uses simple composition: TesseractParams embedded in DocumentUpload and OCRJob
- No unnecessary abstractions or complex heuristics
- Validation logic straightforward: type checks + business rules
- Reuses existing patterns for error handling and job management

### Principle 8: Documentation & Library Reference ✅ CONFIRMED
- Research.md documents pytesseract API usage from Context7
- Pydantic validation patterns researched via Context7
- Quickstart.md provides comprehensive usage examples
- OpenAPI contract serves as executable API documentation

**POST-DESIGN GATE RESULT: ✅ ALL PRINCIPLES PASS - Ready for implementation (Phase 2)**

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── upload.py          # Extended: Add OCR parameter fields (lang, psm, oem, dpi)
│   ├── job.py             # Extended: Add parameters to job metadata
│   └── responses.py       # Extended: Include parameters in error messages
├── services/
│   ├── ocr_processor.py   # Modified: Accept and apply Tesseract parameters
│   └── job_manager.py     # Modified: Store parameters in job state
├── api/
│   └── routes/
│       └── upload.py      # Modified: Accept query/form parameters
├── utils/
│   └── validators.py      # New: Parameter validation functions
└── config.py              # Extended: Add Tesseract config validation settings

tests/
├── contract/
│   └── test_api_contract.py    # Extended: Parameter validation scenarios
├── integration/
│   └── test_ocr_params.py      # New: End-to-end parameter tests
└── unit/
    ├── test_validators.py      # New: Parameter validation unit tests
    └── test_ocr_processor.py   # Extended: Test parameter application
```

**Structure Decision**: This is a single-project web API service. The feature extends existing models, services, and routes to support optional Tesseract parameters. No new top-level modules are required - validation utilities are added to the existing `utils/` directory, and parameter handling is integrated into existing upload/processing flows.

## Complexity Tracking

*No violations - this section is empty as all constitution principles pass.*
