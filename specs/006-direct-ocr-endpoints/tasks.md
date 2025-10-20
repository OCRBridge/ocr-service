# Tasks: Direct OCR Processing Endpoints

**Input**: Design documents from `/specs/006-direct-ocr-endpoints/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: This feature follows TDD (Test-First) discipline per Constitution Principle 3. Tests are written BEFORE implementation for each user story.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `- [ ] [ID] [P?] [Story?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root (per plan.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Configuration and shared models for synchronous OCR endpoints

- [X] T001 Add sync timeout configuration to src/config.py (sync_timeout_seconds=30, sync_max_file_size_mb=5)
- [X] T002 [P] Add SyncOCRResponse model to src/models/responses.py
- [X] T003 [P] Add file size validation constants and validate_sync_file_size function to src/utils/validators.py
- [X] T004 [P] Add Prometheus metrics for sync endpoints to src/utils/metrics.py (sync_ocr_requests_total, sync_ocr_duration_seconds, sync_ocr_timeouts_total, sync_ocr_file_size_bytes)

**Checkpoint**: ✅ COMPLETE - Shared models and configuration ready - user story implementation can now begin

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Create src/api/routes/sync.py file with FastAPI router initialization and basic imports
- [X] T006 Register sync router in src/main.py (app.include_router with prefix="/sync")

**Checkpoint**: ✅ COMPLETE - Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Synchronous Tesseract Processing (Priority: P1) 🎯 MVP

**Goal**: Enable developers to POST a single-page document to /sync/tesseract and receive hOCR output immediately in the response body, eliminating job queue polling complexity.

**Independent Test**: POST a single-page PDF to /sync/tesseract endpoint and receive hOCR in response body within 5 seconds, completing document processing in 1 HTTP request instead of 3+ (upload → status → result).

### Tests for User Story 1 (TDD - Write FIRST, ensure FAIL before implementation)

- [X] T007 [P] [US1] Write contract test for /sync/tesseract OpenAPI compliance in tests/contract/test_sync_openapi.py
- [X] T008 [P] [US1] Write integration test for end-to-end Tesseract sync processing in tests/integration/test_sync_endpoints.py (test_sync_tesseract_success)
- [X] T009 [P] [US1] Write unit test for Tesseract timeout handling in tests/unit/test_sync_routes.py (test_tesseract_timeout_408)
- [X] T010 [P] [US1] Write unit test for Tesseract file size validation in tests/unit/test_sync_validation.py (test_file_size_exceeds_limit_413)

### Implementation for User Story 1

- [X] T011 [US1] Implement /sync/tesseract endpoint in src/api/routes/sync.py (POST handler with file upload, TesseractParams, asyncio.wait_for timeout, SyncOCRResponse)
- [X] T012 [US1] Add file cleanup context manager (temporary_upload) to src/api/routes/sync.py for guaranteed cleanup
- [X] T013 [US1] Integrate file size validation dependency (Depends(validate_sync_file_size)) for /sync/tesseract endpoint
- [X] T014 [US1] Add timeout error handling (asyncio.TimeoutError → HTTP 408) for /sync/tesseract endpoint
- [X] T015 [US1] Add metrics instrumentation (sync_ocr_requests_total, sync_ocr_duration_seconds) for /sync/tesseract endpoint
- [X] T016 [US1] Add structured logging with correlation IDs for /sync/tesseract requests

**Checkpoint**: ✅ COMPLETE - User Story 1 complete - /sync/tesseract endpoint fully functional and independently testable. Delivers immediate value for Tesseract users. Successfully tested with sample file (processing time: 0.18s).

---

## Phase 4: User Story 2 - Synchronous EasyOCR Processing (Priority: P1)

**Goal**: Enable developers to POST multilingual documents to /sync/easyocr and receive hOCR output immediately, leveraging GPU-accelerated processing for languages that Tesseract handles poorly.

**Independent Test**: POST a document with Chinese or Arabic text to /sync/easyocr endpoint and receive hOCR with accurate multilingual recognition in the response. Delivers value through immediate access to advanced multilingual OCR.

### Tests for User Story 2 (TDD - Write FIRST, ensure FAIL before implementation)

- [X] T017 [P] [US2] Write contract test for /sync/easyocr OpenAPI compliance in tests/contract/test_sync_openapi.py
- [X] T018 [P] [US2] Write integration test for end-to-end EasyOCR sync processing in tests/integration/test_sync_endpoints.py (test_sync_easyocr_success)
- [X] T019 [P] [US2] Write integration test for EasyOCR multilingual processing in tests/integration/test_sync_endpoints.py (test_sync_easyocr_multilingual)
- [X] T020 [P] [US2] Write unit test for EasyOCR timeout handling in tests/unit/test_sync_routes.py (test_easyocr_timeout_408)

### Implementation for User Story 2

- [X] T021 [P] [US2] Implement /sync/easyocr endpoint in src/api/routes/sync.py (POST handler with file upload, EasyOCRParams, asyncio.wait_for timeout, SyncOCRResponse)
- [X] T022 [US2] Reuse file cleanup context manager (temporary_upload) for /sync/easyocr endpoint
- [X] T023 [US2] Integrate file size validation dependency for /sync/easyocr endpoint
- [X] T024 [US2] Add timeout error handling for /sync/easyocr endpoint
- [X] T025 [US2] Add metrics instrumentation for /sync/easyocr endpoint
- [X] T026 [US2] Add structured logging with correlation IDs for /sync/easyocr requests

**Checkpoint**: ✅ COMPLETE - User Story 2 complete - /sync/easyocr endpoint fully functional. Combined with US1, delivers sync OCR for the two most popular engines (Tesseract + EasyOCR).

---

## Phase 5: User Story 3 - Synchronous ocrmac Processing (Priority: P2)

**Goal**: Enable macOS developers to POST documents to /sync/ocrmac and receive hOCR output immediately using Apple's Vision framework, delivering platform-optimized synchronous processing.

**Independent Test**: POST a document to /sync/ocrmac endpoint on macOS and receive hOCR with high confidence scores in under 2 seconds. On non-macOS platforms, receive HTTP 400 error indicating platform requirement.

### Tests for User Story 3 (TDD - Write FIRST, ensure FAIL before implementation)

- [X] T027 [P] [US3] Write contract test for /sync/ocrmac OpenAPI compliance in tests/contract/test_sync_openapi.py
- [X] T028 [P] [US3] Write integration test for end-to-end ocrmac sync processing in tests/integration/test_sync_endpoints.py (test_sync_ocrmac_success, skip if not macOS)
- [X] T029 [P] [US3] Write unit test for ocrmac platform validation in tests/unit/test_sync_routes.py (test_ocrmac_unavailable_non_macos_400)
- [X] T030 [P] [US3] Write unit test for ocrmac timeout handling in tests/unit/test_sync_routes.py (test_ocrmac_timeout_408)

### Implementation for User Story 3

- [X] T031 [P] [US3] Implement /sync/ocrmac endpoint in src/api/routes/sync.py (POST handler with file upload, OcrmacParams, engine availability check, asyncio.wait_for timeout, SyncOCRResponse)
- [X] T032 [US3] Add engine availability validation (OCREngineRegistry.is_available("ocrmac")) for /sync/ocrmac endpoint
- [X] T033 [US3] Reuse file cleanup context manager for /sync/ocrmac endpoint
- [X] T034 [US3] Integrate file size validation dependency for /sync/ocrmac endpoint
- [X] T035 [US3] Add timeout error handling for /sync/ocrmac endpoint
- [X] T036 [US3] Add metrics instrumentation for /sync/ocrmac endpoint
- [X] T037 [US3] Add structured logging with correlation IDs for /sync/ocrmac requests

**Checkpoint**: ✅ COMPLETE - User Story 3 complete - /sync/ocrmac endpoint fully functional. All three sync engines (Tesseract, EasyOCR, ocrmac) now available.

---

## Phase 6: User Story 4 - Timeout and Error Handling (Priority: P2)

**Goal**: Provide clear, immediate feedback when documents take too long to process or encounter errors, enabling developers to handle these cases gracefully (e.g., fall back to async processing or notify users).

**Independent Test**: POST a large or complex document that exceeds processing limits and verify the system returns HTTP 408 timeout or appropriate error within the timeout period (30 seconds). Delivers value through predictable error handling.

### Tests for User Story 4 (TDD - Write FIRST, ensure FAIL before implementation)

- [ ] T038 [P] [US4] Write integration test for timeout error handling in tests/integration/test_sync_endpoints.py (test_sync_timeout_large_multipage_pdf_408)
- [X] T039 [P] [US4] Write integration test for file size limit error in tests/integration/test_sync_endpoints.py (test_sync_file_too_large_413)
- [X] T040 [P] [US4] Write integration test for invalid file format error in tests/integration/test_sync_endpoints.py (test_sync_unsupported_format_415)
- [ ] T041 [P] [US4] Write unit test for corrupted document handling in tests/unit/test_sync_routes.py (test_corrupted_document_500)
- [ ] T042 [P] [US4] Write unit test for engine error handling in tests/unit/test_sync_routes.py (test_ocr_engine_error_500)

### Implementation for User Story 4

- [X] T043 [P] [US4] Enhance error message for HTTP 408 timeout to suggest async endpoints (update all three sync endpoints)
- [X] T044 [P] [US4] Enhance error message for HTTP 413 file size to suggest async endpoints (already implemented in validate_sync_file_size)
- [X] T045 [P] [US4] Add HTTP 500 error handling for OCR processing errors with detailed error messages (all three sync endpoints)
- [ ] T046 [P] [US4] Add HTTP 503 error handling for engine unavailability during processing (all three sync endpoints)
- [ ] T047 [US4] Verify error response format consistency with async endpoints (same JSON structure per FR-022)
- [ ] T048 [US4] Add metrics tracking for timeout rate (sync_ocr_timeouts_total) verification

**Checkpoint**: User Story 4 complete - comprehensive error handling ensures production reliability. Developers can confidently handle timeouts, size limits, format errors, and engine failures.

---

## Phase 7: User Story 5 - Backward Compatibility (Priority: P3)

**Goal**: Ensure existing users of async job-based endpoints can continue using them without any changes to their integrations. New synchronous endpoints must not affect existing functionality, performance, or behavior of async endpoints.

**Independent Test**: Run existing async endpoint tests and verify 100% pass rate with no performance degradation. Delivers value by protecting existing users from breaking changes.

### Tests for User Story 5 (Validation - Run EXISTING tests)

- [X] T049 [US5] Run existing async endpoint test suite (pytest tests/integration/test_upload.py tests/integration/test_jobs.py)
- [X] T050 [US5] Verify 100% pass rate for existing async endpoint tests (no failures allowed)
- [ ] T051 [US5] Run performance benchmarks for async endpoints and verify no degradation (within 5% of baseline per SC-007)

### Implementation for User Story 5

- [X] T052 [P] [US5] Verify no modifications to src/api/routes/upload.py (async upload endpoints unchanged)
- [X] T053 [P] [US5] Verify no modifications to src/api/routes/jobs.py (job status endpoints unchanged)
- [X] T054 [P] [US5] Verify no modifications to src/services/ocr_processor.py (OCRProcessor logic unchanged)
- [ ] T055 [P] [US5] Verify sync endpoints use same middleware (rate limiting, CORS, error handling) as async endpoints (per FR-019, FR-021)
- [ ] T056 [US5] Verify no changes to Redis job queue behavior (sync endpoints do not create jobs per FR-015)

**Checkpoint**: User Story 5 complete - backward compatibility verified. Existing async endpoint users protected from breaking changes.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, performance testing, and final quality checks

- [ ] T057 [P] Update API documentation with sync vs async endpoint guidance (reference quickstart.md)
- [ ] T058 [P] Add OpenAPI spec registration in src/main.py (include sync endpoint OpenAPI schemas)
- [ ] T059 [P] Create performance test for 100 concurrent requests in tests/performance/test_sync_load.py (verify SC-003)
- [ ] T060 [P] Create performance test for p95 latency <5s in tests/performance/test_sync_latency.py (verify SC-001)
- [ ] T061 Verify metrics endpoint exposes all sync metrics (sync_ocr_requests_total, sync_ocr_duration_seconds, sync_ocr_timeouts_total, sync_ocr_file_size_bytes)
- [ ] T062 Run full test suite with coverage report (pytest --cov=src --cov-report=html --cov-report=term)
- [ ] T063 Verify 90% coverage for new sync endpoint code (target per Constitution Principle 3)
- [ ] T064 Verify 80% overall project coverage maintained (target per Constitution Principle 3)
- [ ] T065 Manual smoke testing: POST single-page doc to each sync endpoint (Tesseract, EasyOCR, ocrmac if macOS)
- [ ] T066 Manual smoke testing: Verify timeout with large multi-page PDF (should return HTTP 408 within 30s)
- [ ] T067 Manual smoke testing: Verify file size limit with 6MB file (should return HTTP 413 immediately)
- [ ] T068 Update CLAUDE.md with sync endpoint implementation details (if not already auto-updated)

**Final Checkpoint**: Feature complete - all user stories implemented, tested, and documented. Ready for deployment.

---

## Dependencies & Execution Order

### Story Completion Order

```
Phase 1 (Setup)
└─> Phase 2 (Foundational)
    └─> Phase 3 (US1 - Tesseract) 🎯 MVP
        ├─> Phase 4 (US2 - EasyOCR) [parallel with US3]
        └─> Phase 5 (US3 - ocrmac) [parallel with US2]
            └─> Phase 6 (US4 - Error Handling)
                └─> Phase 7 (US5 - Backward Compat)
                    └─> Phase 8 (Polish)
```

### Parallel Execution Opportunities

**Phase 1 (Setup)**: Tasks T002, T003, T004 can run in parallel (different files)

**Phase 3 (US1 Tests)**: Tasks T007, T008, T009, T010 can run in parallel (different test files)

**Phase 4 (US2 Tests)**: Tasks T017, T018, T019, T020 can run in parallel (different test files)

**Phase 5 (US3 Tests)**: Tasks T027, T028, T029, T030 can run in parallel (different test files)

**Phase 6 (US4 Tests)**: Tasks T038, T039, T040, T041, T042 can run in parallel (different test files)

**Phase 6 (US4 Implementation)**: Tasks T043, T044, T045, T046 can run in parallel (independent error handling enhancements)

**Phase 7 (US5 Validation)**: Tasks T052, T053, T054, T055 can run in parallel (verification tasks)

**Phase 8 (Polish)**: Tasks T057, T058, T059, T060 can run in parallel (documentation, specs, performance tests)

### Independent Stories (Can be implemented in parallel after Phase 2)

- **US1 (Tesseract)**: Phase 3 - Independent, delivers MVP
- **US2 (EasyOCR)** + **US3 (ocrmac)**: Phases 4 & 5 - Can run in parallel with each other (different endpoints)
- **US4 (Error Handling)**: Phase 6 - Depends on US1, US2, US3 (enhances all endpoints)
- **US5 (Backward Compat)**: Phase 7 - Validation only, can run anytime after US1

---

## Implementation Strategy

### MVP Scope (Minimum Viable Product)

**Deliver User Story 1 ONLY for initial release**:
- Phase 1: Setup (T001-T004)
- Phase 2: Foundational (T005-T006)
- Phase 3: US1 - Tesseract (T007-T016)
- Subset of Phase 8: T062-T064 (coverage verification)

**MVP Deliverables**:
- `/sync/tesseract` endpoint functional
- Single-page documents process in < 5 seconds
- Timeout handling (HTTP 408)
- File size validation (HTTP 413)
- Metrics and logging
- 90% test coverage for sync code

**Estimated MVP Tasks**: 20 tasks (T001-T016 + T062-T064)

### Full Feature Scope

**After MVP validation, incrementally add**:
- Phase 4: US2 - EasyOCR (T017-T026)
- Phase 5: US3 - ocrmac (T027-T037)
- Phase 6: US4 - Error Handling (T038-T048)
- Phase 7: US5 - Backward Compatibility (T049-T056)
- Phase 8: Polish (T057-T068)

**Total Tasks**: 68 tasks

---

## Success Criteria Mapping

| Success Criteria | Verified By |
|------------------|-------------|
| SC-001: 95% of docs process in <5s | T060 (p95 latency test) |
| SC-002: 1 HTTP request instead of 3+ | T008, T018, T028 (integration tests) |
| SC-003: 100 concurrent requests without timeout | T059 (load test) |
| SC-004: Timeout errors <2% of requests | T048 (metrics verification) |
| SC-005: Identical hOCR output sync vs async | T054 (deterministic processing verification) |
| SC-006: API docs distinguish sync vs async | T057 (documentation update) |
| SC-007: Async endpoint performance unchanged | T051 (performance benchmarks) |
| SC-008: Identical error messages sync vs async | T047 (error format consistency) |
| SC-009: Zero file leaks, cleanup <1s | T012, T022, T033 (context manager implementation) |
| SC-010: Error rates match async (±1%) | T045, T046 (error handling) |
| SC-011: 100% metrics capture | T061 (metrics endpoint verification) |

---

## Task Summary

- **Total Tasks**: 68
- **MVP Tasks**: 20 (Phases 1-3 + coverage verification)
- **Parallelizable Tasks**: 37 tasks marked with [P]
- **User Story Distribution**:
  - US1 (Tesseract): 10 implementation tasks (T007-T016)
  - US2 (EasyOCR): 10 implementation tasks (T017-T026)
  - US3 (ocrmac): 11 implementation tasks (T027-T037)
  - US4 (Error Handling): 11 implementation tasks (T038-T048)
  - US5 (Backward Compat): 8 validation tasks (T049-T056)
  - Setup: 4 tasks (T001-T004)
  - Foundational: 2 tasks (T005-T006)
  - Polish: 12 tasks (T057-T068)

---

## Next Steps

1. **Start with MVP** (Phase 1-3): Implement User Story 1 (Tesseract sync endpoint)
2. **Validate MVP**: Run tests, verify coverage, manual smoke testing
3. **Incremental Delivery**: Add US2 (EasyOCR), US3 (ocrmac) in parallel
4. **Complete Feature**: Add US4 (Error Handling), US5 (Backward Compat), Polish
5. **Deploy**: Use `/speckit.implement` to execute tasks or implement manually

---

**Generated**: 2025-10-19
**Feature Branch**: `006-direct-ocr-endpoints`
**Design Docs**: `/specs/006-direct-ocr-endpoints/`
