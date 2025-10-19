---
description: "Task list for removing generic upload endpoint"
---

# Tasks: Remove Generic Upload Endpoint

**Input**: Design documents from `/specs/005-remove-generic-upload/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are included following TDD approach as specified in the project constitution.

**Organization**: Tasks are organized by user story to enable independent implementation and testing.

## Format: `- [ ] [ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1)
- Include exact file paths in descriptions

## Path Conventions
- Single project structure: `src/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and verification

- [X] T001 Verify all existing tests pass with uv run pytest
- [X] T002 [P] Verify Redis is running via docker compose up -d redis
- [X] T003 [P] Confirm code coverage baseline meets thresholds (≥80% overall, ≥90% utilities)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational changes needed - existing infrastructure is sufficient

**⚠️ CRITICAL**: This feature has no foundational prerequisites beyond Phase 1

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - API Client Migrates to Engine-Specific Endpoints (Priority: P1) 🎯 MVP

**Goal**: Remove the generic `/upload` endpoint and ensure all clients use engine-specific endpoints (`/upload/tesseract`, `/upload/ocrmac`, `/upload/easyocr`)

**Independent Test**:
1. Accessing `POST /upload` returns 404 Not Found
2. All engine-specific endpoints continue to work properly with existing functionality
3. OpenAPI documentation no longer shows `/upload` endpoint

### Tests for User Story 1 (TDD Approach) ⚠️

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T004 [P] [US1] Add contract test for removed generic endpoint returning 404 in tests/contract/test_upload_contract.py
- [X] T005 [P] [US1] Add unit test for generic endpoint 404 response in tests/unit/api/routes/test_upload.py
- [X] T006 [P] [US1] Verify existing contract tests for engine-specific endpoints in tests/contract/test_upload_contract.py
- [X] T007 [US1] Run all tests to confirm generic endpoint tests fail (expect 200 but get current behavior)

### Implementation for User Story 1

- [X] T008 [US1] Remove upload_document function and @router.post("/upload") decorator from src/api/routes/upload.py
- [X] T009 [US1] Verify FastAPI router still includes engine-specific endpoints (upload_document_tesseract, upload_document_ocrmac, upload_document_easyocr) in src/api/routes/upload.py
- [X] T010 [US1] Run unit tests to verify generic endpoint returns 404 with uv run pytest tests/unit/api/routes/test_upload.py::test_generic_upload_endpoint_returns_404
- [X] T011 [US1] Run contract tests to verify OpenAPI schema excludes /upload endpoint with uv run pytest tests/contract/

### Verification for User Story 1

- [X] T012 [P] [US1] Remove obsolete tests that specifically tested the generic upload_document function in tests/unit/api/routes/test_upload.py
- [X] T013 [P] [US1] Update integration tests to use engine-specific endpoints if they reference /upload in tests/integration/
- [X] T014 [US1] Run full test suite to ensure all tests pass with uv run pytest
- [X] T015 [US1] Verify code coverage still meets thresholds (≥80% overall) with uv run pytest --cov=src --cov-report=term
- [X] T016 [US1] Start development server and manually verify POST /upload returns 404 with uvicorn src.main:app --reload
- [X] T017 [US1] Manually verify POST /upload/tesseract works correctly with sample file
- [X] T018 [US1] Manually verify POST /upload/easyocr works correctly with sample file
- [X] T019 [US1] Check OpenAPI documentation at http://localhost:8000/docs to confirm /upload is not listed

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Documentation updates and final validation

- [X] T020 [P] Update README.md to remove any references to POST /upload endpoint
- [X] T021 [P] Update CLAUDE.md if it contains endpoint examples
- [X] T022 [P] Search for any remaining references to generic upload in documentation with grep -r "POST /upload" docs/ README.md
- [X] T023 Run quickstart.md validation to ensure all examples work correctly
- [X] T024 [P] Run linting and formatting checks with uv run ruff format src/ tests/ and uv run ruff check src/ tests/
- [X] T025 Final verification: Run complete test suite with coverage with uv run pytest --cov=src --cov-report=html --cov-report=term

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: No tasks - existing infrastructure sufficient
- **User Story 1 (Phase 3)**: Depends on Setup completion - This is the only user story
- **Polish (Phase 4)**: Depends on User Story 1 completion

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Setup (Phase 1) - No dependencies on other stories (only story in this feature)

### Within User Story 1

1. Tests MUST be written FIRST and FAIL before implementation (T004-T007)
2. Implementation removes the endpoint (T008-T009)
3. Verification ensures endpoint returns 404 and tests pass (T010-T011)
4. Cleanup removes obsolete tests and updates related tests (T012-T019)

### Parallel Opportunities

- **Phase 1 (Setup)**: T002 and T003 can run in parallel
- **User Story 1 Tests**: T004, T005, and T006 can be written in parallel (different test files)
- **User Story 1 Verification**: T012 and T013 can run in parallel (different test directories)
- **Phase 4 (Polish)**: T020, T021, T022, and T024 can run in parallel (different files)

---

## Parallel Example: User Story 1

```bash
# Launch all test creation tasks together (Phase 3, Tests section):
Task T004: "Add contract test for removed generic endpoint returning 404 in tests/contract/test_upload_contract.py"
Task T005: "Add unit test for generic endpoint 404 response in tests/unit/api/routes/test_upload.py"
Task T006: "Verify existing contract tests for engine-specific endpoints in tests/contract/test_upload_contract.py"

# Launch verification tasks together (Phase 3, Verification section):
Task T012: "Remove obsolete tests that specifically tested the generic upload_document function in tests/unit/api/routes/test_upload.py"
Task T013: "Update integration tests to use engine-specific endpoints if they reference /upload in tests/integration/"

# Launch all documentation updates together (Phase 4):
Task T020: "Update README.md to remove any references to POST /upload endpoint"
Task T021: "Update CLAUDE.md if it contains endpoint examples"
Task T022: "Search for any remaining references to generic upload in documentation"
Task T024: "Run linting and formatting checks"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verify environment)
2. Complete Phase 3: User Story 1 (the core feature)
   - Write tests first (TDD)
   - Remove endpoint
   - Verify tests pass
   - Clean up obsolete tests
3. **STOP and VALIDATE**: Test User Story 1 independently
4. Complete Phase 4: Polish (documentation and final validation)
5. Ready to deploy

### Sequential Execution (Recommended)

Since this is a single user story feature:

1. Phase 1 (Setup) → Verify environment is ready
2. Phase 3 (User Story 1) → Implement the feature following TDD
3. Phase 4 (Polish) → Update documentation and final checks
4. Each phase validates before proceeding

### Single Developer Strategy

1. Complete Setup tasks (T001-T003)
2. Write tests first (T004-T007) following TDD
3. Implement endpoint removal (T008-T009)
4. Verify tests pass (T010-T011)
5. Clean up and verify (T012-T019)
6. Polish and document (T020-T025)

---

## Notes

- [P] tasks = different files, no dependencies
- [US1] label = User Story 1 (API Client Migrates to Engine-Specific Endpoints)
- This feature has only one user story, making it simple and focused
- TDD approach: Tests must fail before implementation (critical for T004-T007)
- Verify tests fail before implementing
- Each checkpoint validates the story independently
- Zero new files created - this is a removal-only change
- No data model changes - routing layer only
- No breaking changes to engine-specific endpoints

---

## Summary

**Total Tasks**: 25 tasks
- **Phase 1 (Setup)**: 3 tasks
- **Phase 2 (Foundational)**: 0 tasks (no prerequisites)
- **Phase 3 (User Story 1)**: 16 tasks
  - Tests: 4 tasks
  - Implementation: 2 tasks
  - Verification: 10 tasks
- **Phase 4 (Polish)**: 6 tasks

**Parallel Opportunities**: 9 tasks can run in parallel at various stages

**MVP Scope**: Complete all 25 tasks (single user story feature)

**Estimated Time**: ~50 minutes (per quickstart.md)
- Test writing: 15 minutes (T004-T007)
- Implementation: 10 minutes (T008-T011)
- Verification: 15 minutes (T012-T019)
- Documentation: 10 minutes (T020-T025)
