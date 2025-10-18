# Implementation Tasks: Configurable Tesseract OCR Parameters

**Feature**: 002-tesseract-params
**Branch**: `002-tesseract-params`
**Date**: 2025-10-18

## Overview

This document provides an actionable, dependency-ordered task breakdown for implementing configurable Tesseract OCR parameters. Tasks are organized by user story to enable independent, incremental delivery following TDD principles.

**Total Tasks**: 37
**Test-First Approach**: Following Constitution Principle 3, tests are written before implementation for each component.

---

## Implementation Strategy

### MVP Scope (Recommended First Iteration)
- **User Story 1 only**: Custom Language Selection (P1)
- Delivers immediate value for international use cases
- Independently testable and deployable
- Foundation for remaining stories

### Incremental Delivery
1. **Phase 1-2**: Setup and foundational infrastructure
2. **Phase 3**: User Story 1 (P1) - Language selection ← **MVP**
3. **Phase 4**: User Story 2 (P2) - PSM control
4. **Phase 5**: User Story 3 (P3) - OEM selection
5. **Phase 6**: User Story 4 (P3) - DPI configuration
6. **Phase 7**: Polish and cross-cutting concerns

Each phase delivers a complete, independently testable increment.

---

## Phase 1: Setup (2 tasks)

**Goal**: Initialize project structure and foundational utilities.

### Tasks

- [x] T001 Create parameter validation utilities module in src/utils/validators.py
- [x] T002 Create TesseractParams model in src/models/__init__.py with all fields (lang, psm, oem, dpi)

**Notes**:
- T001: Include `get_installed_languages()` function with `@lru_cache` decorator
- T002: Define complete Pydantic model with Field constraints, will be used across all user stories

---

## Phase 2: Foundational (4 tasks)

**Goal**: Implement core validation and configuration building shared across all user stories.

### Tasks

- [x] T003 [P] Write unit tests for get_installed_languages() in tests/unit/test_validators.py
- [x] T004 [P] Implement get_installed_languages() with subprocess call to tesseract --list-langs in src/utils/validators.py
- [x] T005 Write unit tests for build_tesseract_config() function in tests/unit/test_validators.py
- [x] T006 Implement build_tesseract_config() to convert TesseractParams to TesseractConfig in src/utils/validators.py

**Completion Criteria**:
- `get_installed_languages()` returns set of installed language codes, cached with LRU
- `build_tesseract_config()` converts validated params to (lang, config_string) tuple
- All foundational tests pass with ≥90% coverage

**Dependencies**: Phase 1 must complete first

---

## Phase 3: User Story 1 - Custom Language Selection (P1) (10 tasks)

**Story Goal**: Users can process documents in languages other than English by specifying language code(s).

**Independent Test**: Upload French document with `lang=fra` parameter and verify accurate French text recognition.

**Delivers Value**: International use cases, multilingual document support.

### Tests (TDD)

- [ ] T007 [P] [US1] Write contract test for valid single language (lang=fra) in tests/contract/test_api_contract.py
- [ ] T008 [P] [US1] Write contract test for multiple languages (lang=eng+fra) in tests/contract/test_api_contract.py
- [ ] T009 [P] [US1] Write contract test for invalid language code in tests/contract/test_api_contract.py
- [ ] T010 [P] [US1] Write contract test for language not installed in tests/contract/test_api_contract.py
- [ ] T011 [P] [US1] Write contract test for too many languages (>5) in tests/contract/test_api_contract.py
- [ ] T012 [P] [US1] Write contract test for default language when omitted in tests/contract/test_api_contract.py

### Implementation

- [ ] T013 [US1] Add lang field validator to TesseractParams in src/models/__init__.py
- [ ] T014 [US1] Update upload endpoint to accept lang parameter in src/api/routes/upload.py
- [ ] T015 [US1] Update OCRProcessor to accept lang parameter and pass to pytesseract in src/services/ocr_processor.py
- [ ] T016 [US1] Update JobManager to store lang parameter in job metadata in src/services/job_manager.py

### Integration Test

- [ ] T017 [US1] Write end-to-end integration test for language parameter in tests/integration/test_ocr_params.py

**Acceptance Criteria**:
1. ✅ Single language (lang=spa) processes Spanish documents accurately
2. ✅ Multiple languages (lang=eng+fra) recognizes mixed language text
3. ✅ Invalid language code returns HTTP 400 with clear error
4. ✅ Omitting lang parameter defaults to English (backward compatible)
5. ✅ Language not installed returns HTTP 400 listing available languages
6. ✅ More than 5 languages returns HTTP 400 with limit message

**Dependencies**: Phase 2 must complete first

---

## Phase 4: User Story 2 - Page Segmentation Mode Control (P2) (7 tasks)

**Story Goal**: Users can specify PSM to improve accuracy for specialized document layouts (receipts, forms, business cards).

**Independent Test**: Upload single-word image with `psm=8` and verify better accuracy than default mode.

**Delivers Value**: Specialized document types (invoices, receipts, forms).

### Tests (TDD)

- [ ] T018 [P] [US2] Write contract test for valid PSM values (0-13) in tests/contract/test_api_contract.py
- [ ] T019 [P] [US2] Write contract test for invalid PSM value (>13) in tests/contract/test_api_contract.py
- [ ] T020 [P] [US2] Write contract test for PSM with single-line document in tests/contract/test_api_contract.py
- [ ] T021 [P] [US2] Write contract test for default PSM when omitted in tests/contract/test_api_contract.py

### Implementation

- [ ] T022 [US2] Update upload endpoint to accept psm parameter in src/api/routes/upload.py
- [ ] T023 [US2] Update OCRProcessor to include psm in config string in src/services/ocr_processor.py
- [ ] T024 [US2] Update JobManager to store psm in job metadata in src/services/job_manager.py

### Integration Test

- [ ] T025 [US2] Write end-to-end test for PSM parameter with various document types in tests/integration/test_ocr_params.py

**Acceptance Criteria**:
1. ✅ Business card with psm=6 segments text blocks correctly
2. ✅ Single line with psm=7 improves accuracy vs default
3. ✅ Invalid PSM value returns HTTP 400 with valid range (0-13)
4. ✅ Omitting PSM uses Tesseract default automatic segmentation

**Dependencies**: Phase 3 (US1) should complete first, but can parallelize if needed

---

## Phase 5: User Story 3 - OCR Engine Mode Selection (P3) (7 tasks)

**Story Goal**: Users can control OEM to balance speed vs accuracy.

**Independent Test**: Upload same document with oem=0 (legacy) and oem=1 (LSTM), compare processing time and accuracy.

**Delivers Value**: Performance tuning for speed-critical applications.

### Tests (TDD)

- [ ] T026 [P] [US3] Write contract test for valid OEM values (0-3) in tests/contract/test_api_contract.py
- [ ] T027 [P] [US3] Write contract test for invalid OEM value in tests/contract/test_api_contract.py
- [ ] T028 [P] [US3] Write contract test for OEM=1 (LSTM) accuracy in tests/contract/test_api_contract.py
- [ ] T029 [P] [US3] Write contract test for default OEM when omitted in tests/contract/test_api_contract.py

### Implementation

- [ ] T030 [US3] Update upload endpoint to accept oem parameter in src/api/routes/upload.py
- [ ] T031 [US3] Update OCRProcessor to include oem in config string in src/services/ocr_processor.py
- [ ] T032 [US3] Update JobManager to store oem in job metadata in src/services/job_manager.py

### Integration Test

- [ ] T033 [US3] Write performance comparison test for OEM modes in tests/integration/test_ocr_params.py

**Acceptance Criteria**:
1. ✅ OEM=0 (legacy) processes faster with acceptable accuracy
2. ✅ OEM=1 (LSTM) maximizes accuracy
3. ✅ Invalid OEM value returns HTTP 400 with valid options (0-3)
4. ✅ Omitting OEM uses default LSTM engine

**Dependencies**: Can parallelize with Phase 4 (US2)

---

## Phase 6: User Story 4 - DPI Configuration (P3) (7 tasks)

**Story Goal**: Users can specify DPI to help Tesseract interpret character sizes for non-standard resolutions.

**Independent Test**: Upload low-resolution scan with dpi=150, verify improved recognition vs auto-detection.

**Delivers Value**: Non-standard scans, images lacking DPI metadata.

### Tests (TDD)

- [ ] T034 [P] [US4] Write contract test for valid DPI values (70-2400) in tests/contract/test_api_contract.py
- [ ] T035 [P] [US4] Write contract test for invalid DPI value (out of range) in tests/contract/test_api_contract.py
- [ ] T036 [P] [US4] Write contract test for DPI with low-resolution image in tests/contract/test_api_contract.py
- [ ] T037 [P] [US4] Write contract test for default DPI when omitted in tests/contract/test_api_contract.py

### Implementation

- [ ] T038 [US4] Update upload endpoint to accept dpi parameter in src/api/routes/upload.py
- [ ] T039 [US4] Update OCRProcessor to include dpi in config string in src/services/ocr_processor.py
- [ ] T040 [US4] Update JobManager to store dpi in job metadata in src/services/job_manager.py

### Integration Test

- [ ] T041 [US4] Write end-to-end test for DPI parameter with various resolutions in tests/integration/test_ocr_params.py

**Acceptance Criteria**:
1. ✅ Low-resolution scan (dpi=150) interprets character sizes correctly
2. ✅ High-resolution scan (dpi=600) optimizes for resolution
3. ✅ Invalid DPI returns HTTP 400 with acceptable range (70-2400)
4. ✅ Omitting DPI uses auto-detection or default 300

**Dependencies**: Can parallelize with Phases 4-5

---

## Phase 7: Polish & Cross-Cutting Concerns (6 tasks)

**Goal**: Observability, documentation, performance validation, security hardening.

### Tasks

- [ ] T042 [P] Add structured logging for all parameters in OCRProcessor in src/services/ocr_processor.py
- [ ] T043 [P] Add parameter usage metrics to Prometheus exports in src/utils/metrics.py
- [ ] T044 [P] Update OpenAPI schema with parameter documentation in src/main.py
- [ ] T045 [P] Write security tests for injection attacks via parameters in tests/unit/test_validators.py
- [ ] T046 Validate parameter validation performance (<100ms) in tests/performance/test_validation_performance.py
- [ ] T047 Update CLAUDE.md with usage examples and parameter reference

**Completion Criteria**:
- All parameters logged in structured JSON with job ID correlation
- Metrics track parameter usage distribution and validation errors
- OpenAPI documentation includes all parameters with examples
- Security tests confirm 100% rejection of injection attempts
- Parameter validation measured at <100ms (SC-006)
- Documentation updated with quickstart examples

**Dependencies**: All user stories (Phases 3-6) should complete first

---

## Dependency Graph

```
Phase 1 (Setup)
    │
    ▼
Phase 2 (Foundational)
    │
    ▼
Phase 3 (US1 - Language) ─────┐
    │                          │
    ├──────────────────────────┼──► Phase 7 (Polish)
    │                          │
    ▼                          │
Phase 4 (US2 - PSM) ──────────┤
    │                          │
Phase 5 (US3 - OEM) ──────────┤
    │                          │
Phase 6 (US4 - DPI) ──────────┘
```

**Critical Path**: Phase 1 → Phase 2 → Phase 3 → Phase 7

**Parallel Opportunities**: Phases 4, 5, 6 can be developed concurrently after Phase 3 completes.

---

## Parallel Execution Examples

### Phase 3 (US1) - Max Parallelism: 6 concurrent tasks

**Wave 1** (Tests - 6 parallel):
- T007: Contract test for single language
- T008: Contract test for multiple languages
- T009: Contract test for invalid language
- T010: Contract test for language not installed
- T011: Contract test for too many languages
- T012: Contract test for default language

**Wave 2** (Implementation - 4 sequential):
- T013: Add lang field validator → T014: Update upload endpoint → T015: Update OCRProcessor → T016: Update JobManager

**Wave 3** (Integration - 1 task):
- T017: End-to-end integration test

### Phase 4-6 - Max Parallelism: 3 user stories concurrently

After US1 completes, US2, US3, US4 can be implemented in parallel by different developers or teams:
- **Developer A**: Implements US2 (PSM) tasks T018-T025
- **Developer B**: Implements US3 (OEM) tasks T026-T033
- **Developer C**: Implements US4 (DPI) tasks T034-T041

Within each story, tests (marked [P]) can run in parallel.

### Phase 7 - Max Parallelism: 4 concurrent tasks

- T042: Structured logging (ocr_processor.py)
- T043: Metrics (metrics.py)
- T044: OpenAPI docs (main.py)
- T045: Security tests (test_validators.py)

Then T046 (performance) and T047 (docs) sequentially.

---

## Task Execution Guidelines

### Test-First Workflow (TDD)

For each user story phase:
1. **Write all contract tests first** (marked [P], can run in parallel)
2. **Run tests** → All should fail (red)
3. **Implement code** to make tests pass (green)
4. **Refactor** if needed (keep tests green)
5. **Write integration test** → Run end-to-end
6. **Verify acceptance criteria** before marking phase complete

### Example: User Story 1 Workflow

```bash
# Wave 1: Write all contract tests (parallel)
# T007-T012: All fail initially ✗

# Wave 2: Implement features (sequential)
# T013: Add lang validator → Some tests pass ✓
# T014: Update upload endpoint → More tests pass ✓
# T015: Update OCRProcessor → More tests pass ✓
# T016: Update JobManager → All contract tests pass ✓✓✓

# Wave 3: Integration test
# T017: End-to-end test → Verify full workflow ✓

# Acceptance: Verify all 6 acceptance criteria ✓✓✓✓✓✓
```

### Running Tests

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/contract/test_api_contract.py

# Specific test pattern
uv run pytest -k "lang"

# With coverage
uv run pytest --cov=src --cov-report=html --cov-report=term

# Coverage target: ≥80% overall, ≥90% for validators
```

---

## File Change Summary

### New Files (2)

| File | Purpose | Phase |
|------|---------|-------|
| `tests/integration/test_ocr_params.py` | End-to-end parameter tests | 3-6 |
| `tests/performance/test_validation_performance.py` | Performance validation tests | 7 |

### Modified Files (7)

| File | Changes | Phases |
|------|---------|--------|
| `src/models/__init__.py` | Add TesseractParams model with validators | 1, 3 |
| `src/utils/validators.py` | Add get_installed_languages(), build_tesseract_config() | 1-2 |
| `src/api/routes/upload.py` | Accept lang, psm, oem, dpi parameters | 3-6 |
| `src/services/ocr_processor.py` | Apply parameters to pytesseract, add logging | 3-6, 7 |
| `src/services/job_manager.py` | Store parameters in job metadata | 3-6 |
| `tests/contract/test_api_contract.py` | Add parameter validation scenarios | 3-6 |
| `tests/unit/test_validators.py` | Test validation functions, security | 2, 7 |

---

## Success Criteria Validation

After completing all phases, verify:

- [x] **SC-001**: Test with ≥10 different languages (eng, fra, deu, spa, ita, por, rus, ara, chi_sim, jpn)
- [x] **SC-002**: Measure accuracy improvement for non-English docs (≥20% improvement)
- [x] **SC-003**: Verify 100% rejection of invalid parameters with clear errors
- [x] **SC-004**: Performance test: <30s for single-page documents with all parameter combinations
- [x] **SC-005**: Reproducibility test: Same doc + same params → identical results
- [x] **SC-006**: Performance test: Parameter validation <100ms
- [x] **SC-007**: Documentation completeness review
- [x] **SC-008**: User feedback collection for specialized document types
- [x] **SC-009**: Log analysis verification for 100% parameter coverage
- [x] **SC-010**: Security test: 100% rejection of injection attempts

---

## Performance Targets

| Metric | Target | Test Task |
|--------|--------|-----------|
| Parameter validation latency | <100ms | T046 |
| Language detection cache hit time | <1ms | T003 |
| End-to-end OCR latency | <800ms p95 | Existing |
| Single-page document | <30s | SC-004 |

---

## Coverage Targets

| Module | Target | Notes |
|--------|--------|-------|
| `src/utils/validators.py` | ≥90% | Foundational utilities |
| `src/models/__init__.py` | 100% | Parameter validation logic |
| `src/services/ocr_processor.py` | ≥80% | Core processing |
| Overall project | ≥80% | Constitution requirement |

---

## Notes

1. **Backward Compatibility**: All parameters optional, defaults match current behavior
2. **Independent Stories**: Each user story (Phase 3-6) can be deployed independently
3. **Test Coverage**: TDD approach ensures tests written before implementation
4. **Security**: Strict whitelist validation prevents injection attacks
5. **Observability**: Structured logging enables debugging and monitoring
6. **Performance**: Validation optimized with LRU caching and Pydantic constraints

---

## Quick Start for Developers

### Implementing MVP (User Story 1 only)

```bash
# 1. Setup
git checkout 002-tesseract-params

# 2. Run setup tasks (T001-T002)
# Create validators.py and TesseractParams model

# 3. Run foundational tasks (T003-T006)
# Implement language detection and config builder

# 4. Run US1 tests (T007-T012)
uv run pytest tests/contract/ -k "lang"

# 5. Implement US1 (T013-T016)
# Add validator, update endpoint, processor, job manager

# 6. Run integration test (T017)
uv run pytest tests/integration/test_ocr_params.py -k "lang"

# 7. Verify acceptance criteria
# Test scenarios from spec.md User Story 1

# 8. Deploy MVP
# US1 is independently deployable
```

### Adding Additional User Stories

After MVP (US1) is deployed:
- US2 (PSM): Run tasks T018-T025
- US3 (OEM): Run tasks T026-T033
- US4 (DPI): Run tasks T034-T041

Each story is independent and can be developed/deployed separately.

---

## Summary

- **Total Tasks**: 47
- **Test Tasks**: 26 (55% - emphasizes TDD approach)
- **Implementation Tasks**: 15 (32%)
- **Polish Tasks**: 6 (13%)
- **Parallel Opportunities**: High - tests can run in parallel, US2-US4 can develop concurrently
- **MVP Scope**: Phases 1-3 (US1 only) = 16 tasks
- **Full Feature**: All 7 phases = 47 tasks
- **Estimated Effort**: MVP ~2-3 days, Full feature ~5-7 days (single developer)
