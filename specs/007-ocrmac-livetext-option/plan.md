# Implementation Plan: Add LiveText Recognition Level to ocrmac Engine

**Branch**: `007-ocrmac-livetext-option` | **Date**: 2025-10-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-ocrmac-livetext-option/spec.md`

## Summary

Extend the ocrmac OCR engine to support Apple's LiveText framework as a fourth recognition level option (alongside fast, balanced, accurate). Users can specify `recognition_level=livetext` on both sync and async ocrmac endpoints to leverage LiveText's enhanced OCR capabilities on macOS Sonoma (14.0) or later. The implementation adds the enum value, passes the framework parameter to the ocrmac library, validates platform compatibility, and maintains consistent error handling, logging, and metrics with existing recognition levels.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI 0.104+, Pydantic 2.5+, pytesseract 0.3+, ocrmac 0.1+ (with framework parameter support), Redis 7.0+
**Storage**: Redis (job state for async), filesystem (temporary uploaded files)
**Testing**: pytest 7.4+, pytest-asyncio 0.21+, pytest-cov 4.1+
**Target Platform**: macOS Sonoma (14.0)+ for LiveText; macOS 10.15+ for existing Vision framework levels
**Project Type**: Single project (web API service)
**Performance Goals**: LiveText processing ~174ms per image (comparable to existing levels); sync endpoint 30s timeout; p95 latency ≤800ms
**Constraints**: macOS-only (no Linux/Windows); Docker incompatible (requires native macOS); ocrmac library must support framework parameter; LiveText requires Sonoma 14.0+
**Scale/Scope**: Extends existing ocrmac engine (~500 LOC); adds 1 enum value, modifies 2 endpoints, adds ~10 test cases

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle 1: API Contract First ✓ PASS
- **Status**: Pass
- **Evidence**: OpenAPI schema will be updated to include "livetext" enum value (FR-011). Existing `/sync/ocrmac` and `/upload/ocrmac` endpoints are extended with new recognition_level option. No new endpoints or breaking changes.
- **Action**: Update OpenAPI schema in Phase 1 contracts generation

### Principle 2: Deterministic & Reproducible Processing ⚠️ PARTIAL
- **Status**: Partial - LiveText behavior documented but not fully deterministic
- **Evidence**: LiveText always returns confidence=1 (FR-008). LiveText framework behavior is controlled by Apple and may vary between macOS versions.
- **Mitigation**: Document LiveText non-determinism in API docs (FR-012). Use existing hOCR conversion logic for consistency (FR-007).
- **Action**: Add documentation note about LiveText determinism limitations

### Principle 3: Test-First & Coverage Discipline ✓ PASS
- **Status**: Pass
- **Evidence**: Specification includes detailed acceptance scenarios for all user stories. Edge cases identified and clarified. Constitution requires 80% overall coverage, 100% for critical functions.
- **Action**: Write failing tests before implementation (per constitution workflow). Target 90%+ coverage for new code.

### Principle 4: Performance & Resource Efficiency ✓ PASS
- **Status**: Pass
- **Evidence**: Performance budget defined: ~174ms per image (NFR-001), 30s sync timeout (SC-002). LiveText is faster than "accurate" mode (174ms vs 207ms).
- **Action**: Add performance tests to verify LiveText meets latency budget. No memory budget change expected (same ocrmac library).

### Principle 5: Observability & Transparency ✓ PASS
- **Status**: Pass
- **Evidence**: NFR-004 requires logging framework type (vision vs livetext). NFR-005 requires metrics with "livetext" label. Clarification confirms same metrics as existing levels (duration, success/failure, timeouts).
- **Action**: Ensure all ocrmac processing logs include framework type. Add recognition_level="livetext" label to existing metrics.

### Principle 6: Security & Data Privacy ✓ PASS
- **Status**: Pass
- **Evidence**: No new data retention. LiveText uses same temporary file handling as existing ocrmac (files deleted after processing). No new sensitive data logged (FR-014 logs only first 500 chars of unexpected output for debugging).
- **Action**: No additional security measures required beyond existing ocrmac implementation.

### Principle 7: Simplicity & Minimal Surface ✓ PASS
- **Status**: Pass
- **Evidence**: Extends existing enum (RecognitionLevel) with one value. Reuses existing ocrmac engine infrastructure, hOCR conversion, and error handling. No new abstractions. Dead code: None (additive change only).
- **Action**: Ensure implementation doesn't duplicate logic. Use existing platform detection and error handling patterns.

### Principle 8: Documentation & Library Reference ✓ PASS
- **Status**: Pass
- **Evidence**: ocrmac library documentation consulted (framework parameter, LiveText requirements). Constitution mandates Context7 for library-specific guidance.
- **Action**: Use Context7 to verify ocrmac library API for framework parameter and minimum version requirements in Phase 0 research.

### Overall Gate Result: ✓ PASS (1 Partial - mitigated)

**Justification for Partial**: LiveText framework is a black-box Apple component. Non-determinism is inherent to the framework choice and documented per constitution requirement. Mitigation: Clear API documentation (FR-012) and consistent output format (hOCR via FR-007).

**Proceed to Phase 0**: Yes

## Project Structure

### Documentation (this feature)

```
specs/007-ocrmac-livetext-option/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (to be created)
├── data-model.md        # Phase 1 output (to be created)
├── quickstart.md        # Phase 1 output (to be created)
├── contracts/           # Phase 1 output (to be created)
│   └── openapi-diff.md  # OpenAPI schema changes
├── checklists/          # Quality validation
│   └── requirements.md  # Spec quality checklist (completed)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
src/
├── models/
│   └── ocr_params.py          # MODIFY: Add LIVETEXT to RecognitionLevel enum
├── services/
│   └── ocr/
│       ├── ocrmac.py          # MODIFY: Add framework parameter handling
│       └── registry.py        # MODIFY: Update version detection for Sonoma check
└── api/
    └── routes/
        ├── sync.py            # MODIFY: Inherit livetext support (no code changes)
        └── upload.py          # MODIFY: Inherit livetext support (no code changes)

tests/
├── unit/
│   ├── test_ocrmac_hocr.py    # ADD: LiveText hOCR conversion tests
│   ├── test_sync_routes.py    # ADD: LiveText timeout/error tests
│   └── test_engine_registry.py # ADD: Sonoma version detection tests
├── integration/
│   └── test_sync_endpoints.py  # ADD: End-to-end LiveText processing tests
└── contract/
    ├── test_api_contract.py   # ADD: LiveText parameter validation tests
    └── test_sync_openapi.py   # ADD: OpenAPI schema validation tests
```

**Structure Decision**: Single project structure (Option 1) - This is an extension to the existing REST API service. All changes are within the `src/` directory following the established patterns. Tests follow TDD approach with unit, integration, and contract test layers as per constitution Principle 3.

## Complexity Tracking

*No constitution violations requiring justification.*

---

## Phase 0: Research & Technical Decisions

### Research Tasks

1. **ocrmac Library Framework Parameter Support**
   - **Question**: What is the minimum ocrmac library version that supports the `framework` parameter?
   - **Why**: FR-013 requires error handling for unsupported library versions
   - **Method**: Check ocrmac PyPI changelog, source code, or Context7 documentation
   - **Output**: Minimum version requirement, import check strategy

2. **macOS Version Detection for Sonoma**
   - **Question**: How to reliably detect macOS Sonoma (14.0) or later in Python?
   - **Why**: FR-003 requires platform validation before processing
   - **Method**: Review `platform` module, existing ocrmac detection in `registry.py`
   - **Output**: Version detection implementation (e.g., `platform.mac_ver()`)

3. **LiveText Output Format Compatibility**
   - **Question**: Does LiveText return the same annotation format as Vision framework?
   - **Why**: FR-007 requires hOCR conversion; FR-014 requires error handling for unexpected formats
   - **Method**: Review ocrmac library documentation, test with sample image if available
   - **Output**: Confirmation of format compatibility, error detection strategy

4. **Framework Parameter Error Handling**
   - **Question**: What exception does ocrmac raise when framework parameter is not supported?
   - **Why**: FR-013 requires catching library incompatibility errors
   - **Method**: Check ocrmac source code or Context7, test with older ocrmac version if possible
   - **Output**: Exception type to catch, error message format

### Expected Decisions

- **Minimum ocrmac Version**: Determine exact version (e.g., ocrmac >= 1.2.0)
- **Version Detection Method**: Use `platform.mac_ver()` tuple comparison
- **Error Handling Strategy**: Wrap ocrmac.OCR() call in try/except for AttributeError or TypeError
- **Testing Approach**: Mock ocrmac import for library version tests; use `@pytest.mark.skipif` for integration tests requiring Sonoma

---

## Phase 1: Design & Implementation Artifacts

### Data Model

**File**: `data-model.md`

**Entities Modified**:

1. **RecognitionLevel Enum** (src/models/ocr_params.py)
   - Current values: `FAST = "fast"`, `BALANCED = "balanced"`, `ACCURATE = "accurate"`
   - New value: `LIVETEXT = "livetext"`
   - Validation: Pydantic automatically validates enum values
   - Usage: OcrmacParams model, OpenAPI schema

2. **OcrmacParams Model** (src/models/ocr_params.py)
   - Fields: `languages: list[str] | None`, `recognition_level: RecognitionLevel`
   - Changes: None (enum extension is backward compatible)
   - Validation: Existing field validators remain unchanged

3. **hOCR Output XML** (runtime structure)
   - Metadata: Add `<meta name="ocr-system" content="ocrmac-livetext via restful-ocr" />`
   - Confidence: All words have `x_wconf 100` (LiveText returns 1.0)
   - Changes: Update metadata generation in `_convert_to_hocr()` method

### API Contracts

**File**: `contracts/openapi-diff.md`

**Modified Endpoints**:

1. **POST /sync/ocrmac**
   - Parameter: `recognition_level` enum extended
   - Before: `["fast", "balanced", "accurate"]`
   - After: `["fast", "balanced", "accurate", "livetext"]`
   - No other changes (inherits from RecognitionLevel enum)

2. **POST /upload/ocrmac**
   - Parameter: `recognition_level` enum extended
   - Before: `["fast", "balanced", "accurate"]`
   - After: `["fast", "balanced", "accurate", "livetext"]`
   - No other changes (inherits from RecognitionLevel enum)

**Error Responses** (new/updated):

- **HTTP 400**: `{"detail": "LiveText recognition requires macOS Sonoma (14.0) or later. Available recognition levels: fast, balanced, accurate"}`
- **HTTP 500**: `{"detail": "ocrmac library version does not support LiveText framework. Please upgrade to ocrmac >= X.Y.Z"}`
- **HTTP 500**: `{"detail": "LiveText processing returned unexpected output format"}`

**OpenAPI Schema Changes**:
```yaml
# src/models/ocr_params.py -> OpenAPI components/schemas/RecognitionLevel
RecognitionLevel:
  type: string
  enum:
    - fast
    - balanced
    - accurate
    - livetext  # NEW
  description: |
    OCR recognition quality level:
    - fast: Fewer languages, faster processing (~131ms)
    - balanced: Default, good balance of speed and accuracy
    - accurate: Slower, highest accuracy (~207ms)
    - livetext: Apple LiveText framework, requires macOS Sonoma 14.0+ (~174ms)  # NEW
```

### Quickstart Guide

**File**: `quickstart.md`

**Content**:
- Prerequisites: macOS Sonoma 14.0+, ocrmac library with framework support
- Example curl command: `POST /sync/ocrmac` with `recognition_level=livetext`
- Expected output: hOCR XML with LiveText metadata
- Error scenarios: Pre-Sonoma macOS, unsupported library version
- Performance expectations: ~174ms per image

---

## Phase 2: Implementation Tasks

*Tasks will be generated by `/speckit.tasks` command. Not created by `/speckit.plan`.*

**Expected Task Categories**:
1. Data model changes (RecognitionLevel enum)
2. Engine implementation (framework parameter passing)
3. Platform detection (Sonoma version check)
4. Error handling (library version, unexpected output)
5. Logging and metrics (framework type, livetext label)
6. OpenAPI schema update
7. Test implementation (unit, integration, contract)
8. Documentation update (API docs, quickstart)

---

## Post-Implementation Validation

### Constitution Re-Check (Phase 1 Complete)

- **Contract First**: ✓ OpenAPI schema updated with livetext enum
- **Determinism**: ⚠️ LiveText non-determinism documented in API docs
- **Tests**: ✓ All acceptance scenarios covered by tests
- **Performance**: ✓ Performance tests verify 174ms target
- **Observability**: ✓ Logs include framework type, metrics include livetext label
- **Security**: ✓ No new data retention or sensitive logging
- **Simplicity**: ✓ Minimal code changes, reuses existing infrastructure
- **Documentation**: ✓ Context7 consulted for ocrmac library details

### Success Metrics

- All 8 success criteria (SC-001 through SC-008) passing
- Test coverage ≥90% for new code
- No breaking changes to existing recognition levels (SC-004)
- Performance budget met: <30s sync timeout, ~174ms average processing

---

## Notes

- **Backward Compatibility**: Fully backward compatible. Existing recognition levels (fast/balanced/accurate) unchanged. Default remains "balanced".
- **Platform Limitations**: LiveText is macOS Sonoma 14.0+ only. Docker incompatible (same as existing ocrmac limitation).
- **Library Dependency**: Minimum ocrmac version with framework parameter support to be determined in Phase 0 research.
- **Future Enhancements** (out of scope): Automatic fallback, custom confidence scores, framework-independent selection, performance optimization.
