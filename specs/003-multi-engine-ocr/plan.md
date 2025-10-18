# Implementation Plan: Multi-Engine OCR Support

**Branch**: `003-multi-engine-ocr` | **Date**: 2025-10-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-multi-engine-ocr/spec.md`
**User Direction**: Implement the additional engine using a separate endpoint for processing

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature adds support for multiple OCR engines (Tesseract and ocrmac) with engine-specific parameter validation and processing. The architectural approach creates separate API endpoints for each OCR engine (`/upload/tesseract` and `/upload/ocrmac`) to provide clear API contracts and maintain parameter isolation between engines.

**Primary Requirement**: Enable users to choose between Tesseract and ocrmac OCR engines, with each engine supporting its own specific parameters (Tesseract: lang/psm/oem/dpi; ocrmac: languages/recognition_level).

**Technical Approach**: Separate endpoint pattern - creates dedicated endpoints per engine for clear API boundaries, explicit parameter contracts per engine, easier versioning and deprecation, and natural backward compatibility via existing `/upload` endpoint defaulting to Tesseract.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI 0.104+, Pydantic 2.5+, pytesseract 0.3+ (Tesseract), ocrmac (macOS-only, NEEDS CLARIFICATION on version/installation)
**Storage**: Redis 7.0+ (job state), filesystem (temporary uploaded files, results)
**Testing**: pytest 7.4+ (unit, integration, contract tests with 80% overall, 90% utility coverage)
**Target Platform**: Linux/macOS servers (ocrmac macOS 10.15+ only)
**Project Type**: Web API (single FastAPI application)
**Performance Goals**: 95% of single-page documents in <30s, 60s hard timeout per page (SC-004a)
**Constraints**: <100ms engine validation (SC-008), <512MB memory per request, deterministic processing (Constitution Principle 2)
**Scale/Scope**: Multi-engine support (2 engines: Tesseract, ocrmac), engine-specific parameter sets, separate endpoints per engine

**Architecture Decision**: Separate endpoints pattern (`/upload/tesseract`, `/upload/ocrmac`) rather than single parametric endpoint
- **Rationale**: Clearer API contracts per engine, explicit parameter validation per engine, easier to version/deprecate engines independently
- **Trade-off**: More endpoints to maintain vs. simpler parameter validation and documentation
- **Backward Compatibility**: Existing `/upload` endpoint remains, defaults to Tesseract with all current parameters

**Engine Discovery**: NEEDS CLARIFICATION - How to detect ocrmac availability, version, and capabilities at runtime?
**ocrmac Integration**: NEEDS CLARIFICATION - ocrmac Python library availability, API documentation, HOCR output format compatibility
**Language Code Mapping**: Tesseract uses ISO 639-3 (eng, fra), ocrmac uses ISO 639-1 (en, fr) - requires validation per engine
**Engine Capabilities Cache**: Detect at startup via engine queries, cache in memory (FR-016a) - NEEDS CLARIFICATION on implementation pattern

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle 1: API Contract First
**Status**: ✅ PASS
**Evidence**: Separate endpoint approach requires OpenAPI contract definition before implementation. Contract will include `/upload/tesseract` and `/upload/ocrmac` endpoints with engine-specific parameters.
**Action**: Phase 1 will generate OpenAPI contracts in `/contracts/` directory.

### Principle 2: Deterministic & Reproducible Processing
**Status**: ✅ PASS
**Evidence**: FR-012 ensures same document + engine + parameters = identical results. Each job stores engine type and all parameters for reproducibility.
**Action**: Job model will be extended to include engine type and engine-specific configuration.

### Principle 3: Test-First & Coverage Discipline (NON-NEGOTIABLE)
**Status**: ✅ PASS
**Evidence**: Feature spec includes comprehensive acceptance scenarios for each user story. Test coverage targets: 80% overall, 90% utilities, 100% critical validation logic.
**Action**: TDD approach - write tests before implementation. Contract tests for each endpoint, unit tests for engine-specific validators.

### Principle 4: Performance & Resource Efficiency
**Status**: ✅ PASS
**Evidence**: SC-004a defines performance budget (95% under 30s, 60s hard timeout). FR-017b enforces 60s timeout per page. SC-008 requires <100ms validation.
**Concern**: ocrmac performance unknown - need benchmarking against Tesseract.
**Action**: Phase 0 research will investigate ocrmac performance characteristics.

### Principle 5: Observability & Transparency
**Status**: ✅ PASS
**Evidence**: FR-010 requires engine type in job metadata, FR-011 requires structured logging with job ID correlation. Existing metrics infrastructure will be extended for per-engine tracking.
**Action**: Add engine-specific labels to existing Prometheus metrics (jobs_completed_total, jobs_failed_total).

### Principle 6: Security & Data Privacy
**Status**: ✅ PASS
**Evidence**: No new data retention introduced. Existing temporary file cleanup applies to both engines. No sensitive data logging.
**Concern**: ocrmac platform detection must not leak system information.
**Action**: Platform detection will use standard Python `platform.system()` only.

### Principle 7: Simplicity & Minimal Surface
**Status**: ⚠️ NEEDS JUSTIFICATION
**Concern**: Adding separate endpoints increases API surface vs. single parametric endpoint with `engine` parameter.
**Justification**: Separate endpoints provide:
- Clearer parameter validation (each endpoint validates only its engine's parameters)
- Better OpenAPI documentation (parameters scoped to relevant endpoint)
- Easier versioning/deprecation per engine
- Natural backward compatibility (existing `/upload` unchanged)
- Reduced complexity in validation logic (no cross-engine parameter checking)
**Alternative Rejected**: Single `/upload?engine=tesseract` endpoint would require complex conditional parameter validation, unclear OpenAPI schema (all parameters listed but only subset valid per engine), risk of breaking existing `/upload` contract.

### Principle 8: Documentation & Library Reference
**Status**: ⚠️ NEEDS ACTION
**Evidence**: ocrmac library integration requires Context7 reference for API usage, configuration, and best practices.
**Action**: Phase 0 research will use Context7 to:
- Verify ocrmac Python library availability and version
- Document ocrmac API usage patterns
- Identify HOCR output format compatibility
- Document platform detection and capability discovery

### Security & Performance Requirements Check
- **Input Validation**: ✅ Engine-specific validators per endpoint (Pydantic models)
- **Rate Limiting**: ✅ Existing limiter applies to all upload endpoints
- **Resource Isolation**: ✅ Existing file handling patterns, 60s timeout per page
- **Accuracy Benchmarks**: ⚠️ NEEDS ACTION - Phase 0 research must establish ocrmac accuracy baseline
- **Dependency Hygiene**: ✅ Existing weekly scan process applies to ocrmac

### Development Workflow & Quality Gates Check
- **Design/Contract**: Phase 1 generates OpenAPI contracts ✅
- **Tests First**: TDD approach per User Stories ✅
- **Implementation**: Phase 2 (not in this command scope) ✅
- **Observability Hooks**: Extend existing structured logging ✅
- **Review Checklist**: PR template includes all principles ✅
- **CI Gates**: Existing gates apply (lint, tests, coverage, security) ✅

### Pre-Research Gate Decision
**GATE RESULT**: ✅ PASS WITH ACTIONS
**Required Actions Before Phase 0**:
1. None - all concerns will be resolved in Phase 0 research

**Required Actions During Phase 0**:
1. Research ocrmac library availability, API, performance (Principle 8) ✅ COMPLETED
2. Establish ocrmac accuracy baseline vs Tesseract (Performance Requirements) ⚠️ DEFERRED TO PHASE 2
3. Document engine capability discovery pattern (Technical Context unknowns) ✅ COMPLETED
4. Verify HOCR output format compatibility (Technical Context unknown) ✅ COMPLETED

---

### Post-Design Gate Re-Evaluation
**Date**: 2025-10-18
**Status**: Phase 0 and Phase 1 complete, re-evaluating all principles

#### Principle 1: API Contract First
**Status**: ✅ PASS - IMPROVED
**Evidence**:
- Generated OpenAPI contracts: `contracts/upload-tesseract.openapi.yaml`, `contracts/upload-ocrmac.openapi.yaml`
- Both contracts fully specify request/response schemas, validation rules, error cases
- Contracts versioned with feature spec in `specs/003-multi-engine-ocr/`
**Conclusion**: Fully compliant. Contracts defined before implementation starts.

#### Principle 2: Deterministic & Reproducible Processing
**Status**: ⚠️ REQUIRES IMPLEMENTATION VERIFICATION
**Evidence**:
- research.md documents HOCR conversion layer to standardize output format
- data-model.md extends OCRJob with `engine` and `engine_params` fields for reproducibility
- Critical finding: ocrmac does NOT natively output HOCR, requires custom conversion
**Action Required in Phase 2**:
- Implement HOCR converter using `xml.etree.ElementTree`
- Test conversion produces identical HOCR for same ocrmac input
- Validate determinism: same image + params = same HOCR output
**Conclusion**: Design supports principle, implementation required for full compliance.

#### Principle 3: Test-First & Coverage Discipline
**Status**: ✅ PASS
**Evidence**:
- data-model.md documents test requirements: unit tests for validators, contract tests for endpoints
- plan.md specifies TDD approach, coverage targets (80% overall, 90% utilities)
- quickstart.md provides examples for manual testing scenarios
**Phase 2 Requirements**:
- Write tests BEFORE implementation
- Unit tests: `test_validators.py`, `test_platform.py`, `test_engine_registry.py`, `test_ocrmac_processor.py`
- Contract tests: `test_api_contract.py` (extend for new endpoints)
- Integration tests: `test_ocrmac_integration.py`
**Conclusion**: Design includes test strategy, tests to be written in Phase 2.

#### Principle 4: Performance & Resource Efficiency
**Status**: ⚠️ BENCHMARKING DEFERRED TO PHASE 2
**Evidence**:
- research.md identifies expected 20% performance improvement for ocrmac (GPU acceleration)
- plan.md defines 60s hard timeout per page, 95% under 30s target
- EngineRegistry startup detection <100ms (cached)
- Unknown: Actual ocrmac performance, HOCR conversion overhead
**Phase 2 Requirements**:
- Benchmark ocrmac vs Tesseract on test corpus (50 documents)
- Measure HOCR conversion latency
- Validate SC-005 (20% faster), SC-006 (5% accuracy difference)
**Conclusion**: Design supports principle, benchmarking required in Phase 2.

#### Principle 5: Observability & Transparency
**Status**: ✅ PASS
**Evidence**:
- data-model.md extends OCRJob with engine type and engine_params (FR-010, FR-011)
- Existing structured logging infrastructure extends to new engines
- plan.md specifies engine-specific labels for Prometheus metrics
**Phase 2 Requirements**:
- Add engine field to all OCR-related log entries
- Extend metrics with engine label: `jobs_completed_total{engine="ocrmac"}`
**Conclusion**: Design fully supports observability requirements.

#### Principle 6: Security & Data Privacy
**Status**: ✅ PASS
**Evidence**:
- research.md documents platform detection using standard `platform.system()` only
- No new data retention (existing cleanup applies to both engines)
- No sensitive data logging (engine type and params are not sensitive)
- Platform requirement validation prevents unauthorized access attempts
**Conclusion**: Fully compliant, no security concerns.

#### Principle 7: Simplicity & Minimal Surface
**Status**: ✅ PASS - JUSTIFIED
**Evidence**:
- Complexity Tracking table documents justification for separate endpoints
- Alternative (parametric endpoint) rejected for valid architectural reasons
- Separate endpoints reduce validation complexity despite increasing API surface
- quickstart.md demonstrates clear, simple API usage per engine
**Conclusion**: Complexity justified and documented. Design prioritizes clarity over minimal surface.

#### Principle 8: Documentation & Library Reference
**Status**: ✅ PASS - COMPLETED
**Evidence**:
- research.md used Context7 to document ocrmac library (version, API, usage patterns)
- Critical HOCR compatibility finding documented via library research
- Language code format (IETF BCP 47) identified through Context7 documentation
**Conclusion**: Fully compliant. Context7 used as primary reference source.

#### Security & Performance Requirements Check
- **Input Validation**: ✅ Pydantic models per engine (data-model.md)
- **Rate Limiting**: ✅ Existing limiter applies (no changes)
- **Resource Isolation**: ✅ Existing patterns + 60s timeout (plan.md)
- **Accuracy Benchmarks**: ⚠️ DEFERRED TO PHASE 2 (research.md)
- **Dependency Hygiene**: ✅ ocrmac added to weekly scan process

#### Development Workflow & Quality Gates Check
- **Design/Contract**: ✅ COMPLETED (contracts/, data-model.md)
- **Tests First**: ⚠️ PENDING PHASE 2 (test strategy documented)
- **Implementation**: ⚠️ PENDING PHASE 2 (out of scope for /speckit.plan)
- **Observability Hooks**: ✅ DESIGNED (extends existing infrastructure)
- **Review Checklist**: ✅ PR template will include all principles
- **CI Gates**: ✅ Existing gates apply (no changes needed)

### Post-Design Gate Decision
**GATE RESULT**: ✅ PASS - READY FOR PHASE 2
**Outstanding Items for Phase 2 Implementation**:
1. Implement HOCR conversion layer (research.md section 9)
2. Implement EngineRegistry with startup detection (research.md section 4)
3. Write all tests BEFORE implementation (Principle 3)
4. Benchmark performance: ocrmac vs Tesseract (research.md section 5)
5. Extend structured logging with engine field (data-model.md)
6. Validate determinism of HOCR conversion (Principle 2)

**No Blockers**: All design decisions made, all unknowns resolved, ready to proceed with implementation.

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
│   ├── upload.py            # Extended: Add engine-specific param models
│   ├── job.py               # Extended: Add engine type field
│   └── ocr_params.py        # NEW: OcrmacParams model
├── services/
│   ├── ocr/                 # NEW: Engine abstraction layer
│   │   ├── base.py         # NEW: Base OCR engine interface
│   │   ├── tesseract.py    # REFACTORED: From ocr_processor.py
│   │   ├── ocrmac.py       # NEW: ocrmac engine implementation
│   │   └── registry.py     # NEW: Engine discovery & capability cache
│   ├── ocr_processor.py     # REFACTORED: Use engine registry
│   ├── file_handler.py      # No change
│   ├── job_manager.py       # No change
│   └── cleanup.py           # No change
├── api/
│   └── routes/
│       ├── upload.py        # REFACTORED: Add /upload/tesseract, /upload/ocrmac
│       ├── health.py        # Extended: Add engine availability status
│       └── jobs.py          # No change
├── utils/
│   ├── validators.py        # Extended: Add ocrmac validators
│   └── platform.py          # NEW: Platform detection utilities
└── main.py                  # Extended: Initialize engine registry at startup

tests/
├── contract/
│   ├── test_api_contract.py           # Extended: Tests for new endpoints
│   └── test_tesseract_params.py       # Existing
├── integration/
│   ├── test_tesseract_params.py       # Existing
│   └── test_ocrmac_integration.py     # NEW: ocrmac end-to-end tests
└── unit/
    ├── test_validators.py             # Extended: ocrmac validators
    ├── test_platform.py               # NEW: Platform detection tests
    ├── test_ocrmac_processor.py       # NEW: ocrmac unit tests
    └── test_engine_registry.py        # NEW: Registry tests
```

**Structure Decision**: Single project (FastAPI web API). Using Option 1 structure with engine abstraction layer in `src/services/ocr/` to isolate engine-specific logic. This enables clean separation of concerns and easy addition of future engines.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Separate endpoints per engine (Principle 7) | Clear API contracts per engine, explicit parameter validation, easier versioning | Single parametric endpoint would require complex conditional validation, unclear OpenAPI schema (all params listed but only subset valid), risk of breaking existing `/upload` contract |

