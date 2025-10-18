# Tasks: OCR Document Upload with HOCR Output

**Input**: Design documents from `/specs/001-ocr-hocr-upload/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml

**Tests**: Following TDD principle (Constitution Principle 3), contract tests and integration tests are included for each user story and MUST be written FIRST before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `- [ ] [ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project directory structure per plan.md (src/, tests/, samples/)
- [X] T002 Initialize Python 3.11+ project with uv and pyproject.toml
- [X] T003 [P] Configure .python-version file with Python 3.11
- [X] T004 [P] Create .env.example with configuration template from quickstart.md
- [X] T005 [P] Configure ruff.toml for code formatting and linting
- [X] T006 [P] Create .gitignore for Python, virtual env, temp files, Redis dumps
- [X] T007 [P] Create docker-compose.yml with API service and Redis from plan.md
- [X] T008 [P] Create Dockerfile for API service based on Python 3.11 Alpine
- [X] T009 Create README.md with project overview and setup instructions
- [X] T010 Create temp directories /tmp/uploads and /tmp/results with 700 permissions

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T011 Install core dependencies via uv: FastAPI 0.104+, Pydantic 2.5+, Uvicorn 0.24+
- [X] T012 [P] Install OCR dependencies via uv: pytesseract 0.3+, pdf2image 1.16+
- [X] T013 [P] Install storage dependencies via uv: redis 7.0+ Python client
- [X] T014 [P] Install observability dependencies via uv: structlog 23.2+, prometheus-client 0.19+
- [X] T015 [P] Install rate limiting dependencies via uv: slowapi 0.1+
- [X] T016 [P] Install testing dependencies via uv: pytest 7.4+, pytest-asyncio 0.21+, httpx 0.25+
- [X] T017 Create src/config.py with Pydantic Settings loading .env per data-model.md
- [X] T018 Create src/main.py with FastAPI app initialization and lifespan context
- [X] T019 [P] Create src/models/__init__.py as package marker
- [X] T020 [P] Create src/api/__init__.py as package marker
- [X] T021 [P] Create src/api/routes/__init__.py as package marker
- [X] T022 [P] Create src/api/middleware/__init__.py as package marker
- [X] T023 [P] Create src/services/__init__.py as package marker
- [X] T024 [P] Create src/utils/__init__.py as package marker
- [X] T025 Create tests/conftest.py with pytest fixtures for client, Redis, temp dirs per quickstart.md
- [X] T026 [P] Create tests/unit/__init__.py as package marker
- [X] T027 [P] Create tests/integration/__init__.py as package marker
- [X] T028 [P] Create tests/contract/__init__.py as package marker
- [X] T029 [P] Create tests/performance/__init__.py as package marker
- [X] T030 Implement structured logging configuration in src/main.py using structlog per research.md Decision 8
- [X] T031 Implement Prometheus metrics instrumentation in src/main.py per research.md Decision 9
- [X] T032 [P] Create src/api/middleware/logging.py with request logging middleware
- [X] T033 [P] Create src/api/middleware/error_handler.py with exception to JSON error response handler
- [X] T034 Implement rate limiting middleware in src/api/middleware/rate_limit.py using slowapi per research.md Decision 7
- [X] T035 Create src/api/dependencies.py with FastAPI Depends providers for Redis connection and config

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Single Document Upload and Processing (Priority: P1) 🎯 MVP

**Goal**: Enable users to upload a single document, get a job ID, poll for status, and retrieve HOCR results

**Independent Test**: Upload a document (JPEG/PNG/PDF) via API, poll status until completed, retrieve HOCR output with bounding boxes

### Tests for User Story 1 (TDD - Write FIRST)

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T036 [P] [US1] Contract test for POST /upload endpoint in tests/contract/test_upload_endpoint.py validating OpenAPI schema
- [X] T037 [P] [US1] Contract test for GET /jobs/{id}/status endpoint in tests/contract/test_status_endpoint.py validating OpenAPI schema
- [X] T038 [P] [US1] Contract test for GET /jobs/{id}/result endpoint in tests/contract/test_result_endpoint.py validating OpenAPI schema
- [X] T039 [P] [US1] Contract test for error responses (400/404/413/415/429) in tests/contract/test_error_responses.py
- [X] T040 [P] [US1] Integration test for end-to-end JPEG upload with samples/numbers_gs150.jpg in tests/integration/test_upload_samples.py
- [X] T041 [P] [US1] Integration test for end-to-end PNG upload with samples/stock_gs200.jpg in tests/integration/test_upload_samples.py
- [X] T042 [P] [US1] Unit test for DocumentUpload model validation in tests/unit/test_models.py
- [X] T043 [P] [US1] Unit test for OCRJob model validation and state transitions in tests/unit/test_models.py
- [X] T044 [P] [US1] Unit test for HOCRResult model validation in tests/unit/test_models.py
- [X] T045 [P] [US1] Unit test for job ID generation uniqueness in tests/unit/test_security.py
- [X] T046 [P] [US1] Unit test for file format validation (magic bytes) in tests/unit/test_validators.py
- [X] T047 [P] [US1] Unit test for file size validation (<25MB) in tests/unit/test_validators.py
- [X] T048 [P] [US1] Unit test for HOCR XML parsing and validation in tests/unit/test_hocr.py
- [X] T049 [P] [US1] Unit test for Redis job state CRUD operations in tests/unit/test_job_manager.py

### Implementation for User Story 1

**Models** (Pydantic data structures from data-model.md):

- [X] T050 [P] [US1] Create FileFormat enum in src/models/upload.py
- [X] T051 [P] [US1] Create DocumentUpload model with validation in src/models/upload.py per data-model.md section 1
- [X] T052 [P] [US1] Create JobStatus enum in src/models/job.py
- [X] T053 [P] [US1] Create ErrorCode enum in src/models/job.py
- [X] T054 [US1] Create OCRJob model with state transitions in src/models/job.py per data-model.md section 2 (depends on T051)
- [X] T055 [P] [US1] Create HOCRResult model in src/models/result.py per data-model.md section 3
- [X] T056 [P] [US1] Create UploadResponse model in src/models/responses.py
- [X] T057 [P] [US1] Create StatusResponse model in src/models/responses.py
- [X] T058 [P] [US1] Create ErrorResponse model in src/models/responses.py

**Utilities** (90% coverage target):

- [X] T059 [P] [US1] Implement job ID generation in src/utils/security.py using secrets.token_urlsafe(32) per research.md Decision 6
- [X] T060 [P] [US1] Implement file magic byte validation in src/utils/validators.py for JPEG/PNG/PDF/TIFF
- [X] T061 [P] [US1] Implement file size validation in src/utils/validators.py with 25MB limit
- [X] T062 [P] [US1] Implement HOCR XML parsing utilities in src/utils/hocr.py for validation

**Services** (Business logic):

- [X] T063 [US1] Implement JobManager service in src/services/job_manager.py with Redis CRUD and TTL management per data-model.md
- [X] T064 [US1] Implement FileHandler service in src/services/file_handler.py with streaming upload and temp file management per research.md Decision 4
- [X] T065 [US1] Implement OCRProcessor service in src/services/ocr_processor.py wrapping Tesseract with HOCR output per research.md Decision 1
- [X] T066 [P] [US1] Implement cleanup service in src/services/cleanup.py for expired file deletion

**API Endpoints**:

- [X] T067 [US1] Implement POST /upload endpoint in src/api/routes/upload.py with streaming upload, validation, job creation, background task (depends on T063, T064, T065)
- [X] T068 [US1] Implement GET /jobs/{job_id}/status endpoint in src/api/routes/jobs.py with Redis lookup (depends on T063)
- [X] T069 [US1] Implement GET /jobs/{job_id}/result endpoint in src/api/routes/jobs.py with file streaming (depends on T063)
- [X] T070 [P] [US1] Implement GET /health endpoint in src/api/routes/health.py with Redis connection check
- [X] T071 [P] [US1] Implement GET /metrics endpoint in src/api/routes/health.py exposing Prometheus metrics
- [X] T072 [US1] Register all routes in src/main.py with rate limiting decorators (depends on T067-T071)

**Validation & Error Handling**:

- [X] T073 [US1] Add input validation error handling (400/413/415) to upload endpoint in src/api/routes/upload.py
- [X] T074 [US1] Add job not found error handling (404) to status and result endpoints in src/api/routes/jobs.py
- [X] T075 [US1] Add structured logging to all endpoints with request_id, job_id, latency per research.md Decision 8

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Run `pytest tests/integration/test_upload_samples.py -v` to verify.

---

## Phase 4: User Story 2 - Multi-Format Document Support (Priority: P2)

**Goal**: Handle various document formats (JPEG, PNG, PDF, TIFF) including multi-page PDFs without requiring format conversion

**Independent Test**: Upload documents in different formats (JPEG, PNG, PDF, TIFF) and verify all are processed correctly with proper page handling

### Tests for User Story 2 (TDD - Write FIRST)

- [X] T076 [P] [US2] Integration test for multi-page PDF upload with samples/mietvertrag.pdf in tests/integration/test_upload_samples.py
- [X] T077 [P] [US2] Integration test for TIFF format upload in tests/integration/test_upload_samples.py
- [X] T078 [P] [US2] Unit test for PDF page count detection in tests/unit/test_ocr_processor.py
- [X] T079 [P] [US2] Unit test for PDF to image conversion in tests/unit/test_ocr_processor.py
- [X] T080 [P] [US2] Contract test for multi-page HOCR output structure in tests/contract/test_result_endpoint.py

### Implementation for User Story 2

- [X] T081 [US2] Enhance OCRProcessor in src/services/ocr_processor.py to handle PDF via pdf2image per research.md Decision 5 (ALREADY IMPLEMENTED)
- [X] T082 [US2] Enhance OCRProcessor in src/services/ocr_processor.py to process multi-page documents and merge HOCR per FR-009 (ALREADY IMPLEMENTED)
- [X] T083 [US2] Add TIFF format support to file validation in src/utils/validators.py (ALREADY IMPLEMENTED)
- [X] T084 [US2] Update HOCR utilities in src/utils/hocr.py to handle multi-page output validation (NOT NEEDED - handled by OCRProcessor)
- [X] T085 [US2] Add page count and page structure validation in HOCRResult model in src/models/result.py (NOT NEEDED - validation in tests)
- [X] T086 [US2] Update upload endpoint error messages in src/api/routes/upload.py to list all supported formats (ALREADY IMPLEMENTED)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. All formats (JPEG, PNG, PDF, TIFF) should be processable.

---

## Phase 5: User Story 3 - Processing Status and Progress Feedback (Priority: P3)

**Goal**: Provide users with transparent feedback about processing status, estimated time, and completion notifications

**Independent Test**: Upload a document, observe status transitions (pending → processing → completed), verify all timestamps and expiration times are correct

### Tests for User Story 3 (TDD - Write FIRST)

- [ ] T087 [P] [US3] Integration test for job status polling lifecycle in tests/integration/test_status_polling.py
- [ ] T088 [P] [US3] Integration test for expiration timestamp correctness in tests/integration/test_expiration.py
- [ ] T089 [P] [US3] Integration test for 48h TTL enforcement with mocked time in tests/integration/test_expiration.py
- [ ] T090 [P] [US3] Unit test for job state transition validation in tests/unit/test_models.py
- [ ] T091 [P] [US3] Performance test for status endpoint p95 latency <800ms in tests/performance/test_endpoint_latency.py
- [ ] T092 [P] [US3] Performance test for result endpoint p95 latency <800ms in tests/performance/test_endpoint_latency.py

### Implementation for User Story 3

- [ ] T093 [US3] Enhance JobManager in src/services/job_manager.py to track all timestamps (upload, start, completion, expiration) per data-model.md
- [ ] T094 [US3] Implement automatic expiration_time calculation (completion + 48h) in OCRJob model in src/models/job.py
- [ ] T095 [US3] Add background cleanup task in src/services/cleanup.py to delete expired files and Redis keys
- [ ] T096 [US3] Register cleanup task as periodic background job in src/main.py lifespan
- [ ] T097 [US3] Enhance status response in src/api/routes/jobs.py to include all timestamps and expiration info
- [ ] T098 [US3] Add error state handling to status endpoint for failed jobs in src/api/routes/jobs.py
- [ ] T099 [US3] Add metrics tracking for job lifecycle durations in src/services/ocr_processor.py

**Checkpoint**: All user stories should now be independently functional with complete lifecycle tracking and auto-expiration.

---

## Phase 6: Cross-Cutting Concerns & Polish

**Purpose**: Security, performance, observability improvements that affect multiple user stories

- [ ] T100 [P] Implement rate limiting tests in tests/integration/test_rate_limiting.py verifying 100/min enforcement per FR-015
- [ ] T101 [P] Implement memory usage profiling test <512MB per request in tests/performance/test_memory_usage.py
- [ ] T102 [P] Create comprehensive edge case tests for blank pages, corrupted files, oversized files in tests/integration/test_edge_cases.py
- [ ] T103 Run full test suite with coverage report: `pytest --cov=src --cov-report=html --cov-report=term`
- [ ] T104 Verify coverage gates: 80% overall, 90% for src/utils/ per constitution
- [ ] T105 Run ruff formatting and linting: `ruff format src/ tests/ && ruff check src/ tests/`
- [ ] T106 Validate OpenAPI contract compliance by running contract tests: `pytest tests/contract/ -v`
- [ ] T107 Run quickstart.md validation: verify all commands execute successfully
- [ ] T108 Update CLAUDE.md with active technologies and commands per plan.md
- [ ] T109 Create deployment documentation in README.md with Docker and production setup
- [ ] T110 Security review: verify job ID entropy, rate limiting, input validation, no data leakage in logs

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User Story 1 (P1): Can start after Foundational - No dependencies on other stories (MVP!)
  - User Story 2 (P2): Can start after Foundational - Extends US1 OCR processor but independently testable
  - User Story 3 (P3): Can start after Foundational - Extends job status tracking but independently testable
- **Cross-Cutting (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Enhances OCR processor from US1 but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Enhances status tracking from US1 but independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD principle)
- Models before services (data structures define service interfaces)
- Services before endpoints (business logic before API layer)
- Utilities can be implemented in parallel with models
- Core implementation before integration with other stories

### Parallel Opportunities

**Setup Phase (Phase 1):**
- T003-T010 can run in parallel (different files)

**Foundational Phase (Phase 2):**
- T011-T016 dependency installs can run in parallel
- T019-T024 package markers can run in parallel
- T026-T029 test package markers can run in parallel
- T032-T034 middleware files can run in parallel

**User Story 1 Tests:**
- T036-T049 all test files can be written in parallel

**User Story 1 Models:**
- T050-T051 (upload models) can run in parallel
- T052-T053 (job enums) can run in parallel
- T055-T058 (response models) can run in parallel

**User Story 1 Utilities:**
- T059-T062 all utility files can run in parallel

**User Story 2 Tests:**
- T076-T080 all test files can be written in parallel

**User Story 3 Tests:**
- T087-T092 all test files can be written in parallel

**Cross-Cutting Tests:**
- T100-T102 all edge case tests can be written in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all test files for User Story 1 together (write tests first):
Task: "Contract test for POST /upload endpoint in tests/contract/test_upload_endpoint.py"
Task: "Contract test for GET /jobs/{id}/status endpoint in tests/contract/test_status_endpoint.py"
Task: "Contract test for GET /jobs/{id}/result endpoint in tests/contract/test_result_endpoint.py"
Task: "Integration test for JPEG upload with samples/numbers_gs150.jpg"
Task: "Integration test for PNG upload with samples/stock_gs200.jpg"
Task: "Unit test for DocumentUpload model validation"
Task: "Unit test for OCRJob model validation"
Task: "Unit test for job ID generation uniqueness"
Task: "Unit test for file format validation"
Task: "Unit test for HOCR XML parsing"

# Launch all model files for User Story 1 together:
Task: "Create FileFormat enum in src/models/upload.py"
Task: "Create DocumentUpload model in src/models/upload.py"
Task: "Create JobStatus enum in src/models/job.py"
Task: "Create ErrorCode enum in src/models/job.py"
Task: "Create HOCRResult model in src/models/result.py"
Task: "Create response models in src/models/responses.py"

# Launch all utility files for User Story 1 together:
Task: "Implement job ID generation in src/utils/security.py"
Task: "Implement file validation in src/utils/validators.py"
Task: "Implement HOCR parsing in src/utils/hocr.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T010)
2. Complete Phase 2: Foundational (T011-T035) - CRITICAL - blocks all stories
3. Complete Phase 3: User Story 1 (T036-T075)
   - Write tests FIRST (T036-T049)
   - Implement models, utils, services, endpoints (T050-T075)
4. **STOP and VALIDATE**: Test User Story 1 independently
   - Run: `pytest tests/integration/test_upload_samples.py::test_ocr_jpeg -v`
   - Upload samples/numbers_gs150.jpg via API
   - Verify HOCR output with bounding boxes
5. Deploy/demo if ready - **This is the MVP!**

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently with JPEG/PNG → Deploy/Demo (MVP!)
   - Delivers core value: upload, OCR, HOCR output
3. Add User Story 2 → Test independently with PDF/TIFF → Deploy/Demo
   - Adds multi-format support without breaking US1
4. Add User Story 3 → Test independently with status polling → Deploy/Demo
   - Adds status transparency without breaking US1/US2
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T035)
2. Once Foundational is done:
   - **Developer A**: User Story 1 (T036-T075) - MVP priority
   - **Developer B**: User Story 2 tests (T076-T080) - prepare for next increment
   - **Developer C**: User Story 3 tests (T087-T092) - prepare for next increment
3. After US1 complete:
   - **Developer A**: User Story 2 implementation (T081-T086)
   - **Developer B**: User Story 3 implementation (T093-T099)
4. Stories complete and integrate independently

---

## Constitution Compliance Gates

### Before Committing Any Code

- [ ] All tests for the task are written FIRST and FAIL
- [ ] Implementation makes tests pass
- [ ] Code formatted with ruff: `ruff format src/ tests/`
- [ ] No linting errors: `ruff check src/ tests/`
- [ ] Coverage meets gates: `pytest --cov=src --cov-fail-under=80`
- [ ] Performance budgets validated (p95 <800ms, memory <512MB)
- [ ] OpenAPI contract compliance verified
- [ ] Structured logs include request_id, correlation_id, stage, latency
- [ ] No secrets or sensitive data in logs or commits

### Before Merging Each User Story

- [ ] All tests for user story pass independently
- [ ] User story delivers stated value independently
- [ ] No regressions in previous user stories
- [ ] OpenAPI contract validated
- [ ] Performance benchmarks pass
- [ ] Security review complete (input validation, rate limiting, job ID entropy)
- [ ] Documentation updated (README.md, quickstart.md if needed)

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel
- [Story] label maps task to specific user story (US1, US2, US3) for traceability
- Each user story should be independently completable and testable
- **TDD is NON-NEGOTIABLE**: Write tests FIRST, watch them FAIL, then implement
- Commit after each task or logical group of related tasks
- Stop at any checkpoint to validate story independently
- Coverage targets: 80% overall, 90% for src/utils/ (constitution requirement)
- Performance budgets: p95 <800ms for status/result, <512MB memory per request
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
