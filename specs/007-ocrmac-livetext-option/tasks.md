# Tasks: Add LiveText Recognition Level to ocrmac Engine

**Input**: Design documents from `/specs/007-ocrmac-livetext-option/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Tests**: NOT requested in specification - Test tasks excluded per template guidelines

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- Single project structure: `src/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

_No setup tasks required - feature extends existing codebase_

**Checkpoint**: Existing infrastructure ready - no new setup needed

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T001 Add LIVETEXT enum value to RecognitionLevel in src/models/ocr_params.py
- [X] T002 Update RecognitionLevel enum description with platform requirements and performance notes in src/models/ocr_params.py
- [X] T003 Update OcrmacParams.recognition_level field description with LiveText info in src/models/ocr_params.py
- [X] T004 Add macOS version detection helper function in src/services/ocr/ocrmac.py
- [X] T005 Modify _convert_to_hocr method signature to accept recognition_level_str parameter in src/services/ocr/ocrmac.py
- [X] T006 Update _convert_to_hocr metadata generation for livetext framework in src/services/ocr/ocrmac.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel ✓ COMPLETE

---

## Phase 3: User Story 1 - Basic LiveText OCR Processing (Priority: P1) 🎯 MVP

**Goal**: Enable users on macOS Sonoma+ to process documents using LiveText framework by specifying `recognition_level=livetext`, delivering enhanced OCR accuracy comparable to existing recognition levels.

**Independent Test**: Send POST request to `/sync/ocrmac` or `/upload/ocrmac` with `recognition_level=livetext` and validate that OCR output uses LiveText framework (check hOCR metadata for "ocrmac-livetext").

### Implementation for User Story 1

- [X] T007 [US1] Add framework parameter determination logic in _process_image method in src/services/ocr/ocrmac.py
- [X] T008 [US1] Modify ocrmac.OCR() instantiation to pass framework parameter when livetext in src/services/ocr/ocrmac.py
- [X] T009 [US1] Add try/except handling for TypeError/AttributeError from framework parameter in src/services/ocr/ocrmac.py
- [X] T010 [US1] Update _process_image to pass recognition_level_str to _convert_to_hocr in src/services/ocr/ocrmac.py
- [X] T011 [US1] Add framework parameter logic in _process_pdf method in src/services/ocr/ocrmac.py
- [X] T012 [US1] Update _process_pdf to pass recognition_level_str to _convert_to_hocr in src/services/ocr/ocrmac.py
- [X] T013 [US1] Add annotation format validation before hOCR conversion in src/services/ocr/ocrmac.py
- [X] T014 [US1] Add logging for framework type (vision vs livetext) in src/services/ocr/ocrmac.py
- [X] T015 [US1] Add error logging with output sample for unexpected formats in src/services/ocr/ocrmac.py
- [X] T016 [US1] Update metrics collection to include recognition_level="livetext" label in src/services/ocr/ocrmac.py
- [X] T017 [US1] Verify /sync/ocrmac endpoint inherits livetext support automatically (no code changes needed in src/api/routes/sync.py)
- [X] T018 [US1] Verify /upload/ocrmac endpoint inherits livetext support automatically (no code changes needed in src/api/routes/upload.py)

**Checkpoint**: At this point, User Story 1 should be fully functional - users can process documents with recognition_level=livetext on Sonoma+ ✓ COMPLETE

---

## Phase 4: User Story 2 - Platform Compatibility Validation (Priority: P2)

**Goal**: Provide clear error messages to users on incompatible systems (pre-Sonoma macOS or non-macOS) when attempting to use LiveText, ensuring good user experience and preventing cryptic errors.

**Independent Test**: Mock macOS version detection to simulate pre-Sonoma system and verify HTTP 400 error with clear message about platform requirements.

### Implementation for User Story 2

- [X] T019 [US2] Implement _check_sonoma_requirement helper method in src/services/ocr/ocrmac.py
- [X] T020 [US2] Add platform validation call before LiveText processing in _process_image in src/services/ocr/ocrmac.py
- [X] T021 [US2] Add platform validation call before LiveText processing in _process_pdf in src/services/ocr/ocrmac.py
- [X] T022 [US2] Raise HTTPException(400) with platform incompatibility message in src/services/ocr/ocrmac.py
- [X] T023 [US2] Include available recognition levels in error message in src/services/ocr/ocrmac.py
- [X] T024 [US2] Add logging for platform validation failures in src/services/ocr/ocrmac.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - Sonoma+ users get LiveText, pre-Sonoma users get clear errors ✓ COMPLETE

---

## Phase 5: User Story 3 - Backward Compatibility and Consistency (Priority: P3)

**Goal**: Ensure existing recognition levels (fast, balanced, accurate) continue working unchanged when LiveText is added, maintaining stability for existing integrations.

**Independent Test**: Run existing test suites for fast/balanced/accurate recognition levels and verify all tests pass without modification.

### Implementation for User Story 3

- [X] T025 [P] [US3] Add unit test for RecognitionLevel enum includes LIVETEXT in tests/unit/test_models.py
- [X] T026 [P] [US3] Add unit test for Pydantic validation accepts "livetext" in tests/unit/test_models.py
- [X] T027 [P] [US3] Add unit test for Pydantic validation rejects "livetextt" typo in tests/unit/test_models.py
- [X] T028 [P] [US3] Add unit test for default recognition_level remains BALANCED in tests/unit/test_models.py
- [X] T029 [P] [US3] Add unit test for macOS version detection with Sonoma 14.0+ in tests/unit/test_ocrmac_engine.py
- [X] T030 [P] [US3] Add unit test for macOS version detection with pre-Sonoma versions in tests/unit/test_ocrmac_engine.py
- [X] T031 [P] [US3] Add unit test for framework parameter TypeError handling in tests/unit/test_ocrmac_engine.py
- [X] T032 [P] [US3] Add unit test for annotation format validation in tests/unit/test_ocrmac_hocr.py
- [X] T033 [P] [US3] Add unit test for hOCR metadata with livetext framework in tests/unit/test_ocrmac_hocr.py
- [X] T034 [P] [US3] Add unit test for hOCR confidence values always 100 for livetext in tests/unit/test_ocrmac_hocr.py
- [X] T035 [US3] Add integration test for end-to-end LiveText processing in tests/integration/test_sync_endpoints.py
- [X] T036 [US3] Add pytest.mark.skipif decorator for Sonoma requirement in tests/integration/test_sync_endpoints.py
- [X] T037 [P] [US3] Add contract test for livetext parameter validation in tests/contract/test_api_contract.py
- [X] T038 [P] [US3] Add contract test for HTTP 400 platform incompatibility error in tests/contract/test_api_contract.py
- [X] T039 [P] [US3] Add contract test for HTTP 500 library incompatibility error in tests/contract/test_api_contract.py
- [X] T040 [P] [US3] Add contract test for OpenAPI schema includes livetext in tests/contract/test_sync_openapi.py
- [X] T041 [P] [US3] Add contract test verifying fast recognition_level still works in tests/contract/test_api_contract.py
- [X] T042 [P] [US3] Add contract test verifying balanced recognition_level still works in tests/contract/test_api_contract.py
- [X] T043 [P] [US3] Add contract test verifying accurate recognition_level still works in tests/contract/test_api_contract.py
- [X] T044 [US3] Run full test suite and verify all existing tests pass unchanged

**Checkpoint**: All user stories should now be independently functional with comprehensive test coverage

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T045 [P] Update CLAUDE.md with ocrmac library version requirement in CLAUDE.md
- [X] T046 [P] Update CLAUDE.md with LiveText platform limitations in CLAUDE.md
- [X] T047 Verify OpenAPI schema auto-generation includes livetext enum value at /openapi.json
- [X] T048 Run quickstart.md validation with actual curl commands from quickstart.md
- [X] T049 Verify performance metrics meet budget (~174ms per image) per NFR-001
- [X] T050 Verify logging includes framework type for all ocrmac requests per NFR-004
- [X] T051 Verify metrics include recognition_level="livetext" label per NFR-005
- [X] T052 [P] Run ruff format and ruff check on modified files
- [X] T053 [P] Run pyright type checking on modified files (validated via pre-commit)
- [X] T054 Run pre-commit hooks on all modified files
- [X] T055 Verify all 8 success criteria (SC-001 through SC-008) passing

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No tasks - existing infrastructure used
- **Foundational (Phase 2)**: No dependencies - BLOCKS all user stories (T001-T006)
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - US1 (T007-T018): Can start after Phase 2 - No dependencies on other stories
  - US2 (T019-T024): Can start after Phase 2 - No dependencies on other stories
  - US3 (T025-T044): Can start after Phase 2 - Tests validate US1 and US2 work correctly
- **Polish (Phase 6)**: Depends on all user stories being complete (T045-T055)

### User Story Dependencies

- **User Story 1 (P1) - Basic LiveText**: Can start after Foundational (T001-T006) - Core functionality
- **User Story 2 (P2) - Platform Validation**: Can start after Foundational (T001-T006) - Independent error handling
- **User Story 3 (P3) - Backward Compatibility**: Can start after Foundational (T001-T006) - Validates US1 & US2

### Within Each User Story

**User Story 1**:
- T007-T009 (framework parameter logic) before T010, T012 (passing to hOCR conversion)
- T007-T016 (core implementation) before T017-T018 (endpoint verification)

**User Story 2**:
- T019 (_check_sonoma_requirement) before T020-T021 (validation calls)
- T020-T021 before T022-T024 (error handling and logging)

**User Story 3**:
- T025-T034 (unit tests) can run in parallel
- T037-T043 (contract tests) can run in parallel
- T035-T036 (integration tests) after unit tests pass
- T044 (full suite) after all other tests complete

### Parallel Opportunities

- **Foundational Phase**: T001-T003 (enum changes) can run together; T004 separate; T005-T006 after T005
- **User Story 1**: T007-T009, T011, T013-T016 can be written in parallel (different concerns in same file)
- **User Story 2**: T019-T024 sequential (same helper method)
- **User Story 3 Unit Tests**: T025-T034 all parallel (different test files/functions)
- **User Story 3 Contract Tests**: T037-T043 all parallel (different test files/functions)
- **Polish**: T045-T046, T052-T054 can run in parallel

---

## Parallel Example: User Story 1

```bash
# After Foundational Phase (T001-T006) completes:

# Launch core framework logic tasks together:
Task: "Add framework parameter determination logic in _process_image"
Task: "Add framework parameter logic in _process_pdf"
Task: "Add annotation format validation before hOCR conversion"
Task: "Add logging for framework type"
Task: "Update metrics collection to include livetext label"

# Then proceed with integration:
Task: "Modify ocrmac.OCR() instantiation to pass framework parameter"
Task: "Update _process_image to pass recognition_level_str to _convert_to_hocr"
Task: "Update _process_pdf to pass recognition_level_str to _convert_to_hocr"
```

---

## Parallel Example: User Story 3 Tests

```bash
# All unit tests can launch together:
Task: "Add unit test for RecognitionLevel enum includes LIVETEXT"
Task: "Add unit test for Pydantic validation accepts livetext"
Task: "Add unit test for macOS version detection with Sonoma"
Task: "Add unit test for framework parameter TypeError handling"
Task: "Add unit test for hOCR metadata with livetext framework"

# All contract tests can launch together:
Task: "Add contract test for livetext parameter validation"
Task: "Add contract test for HTTP 400 platform incompatibility"
Task: "Add contract test for OpenAPI schema includes livetext"
Task: "Add contract test verifying fast still works"
Task: "Add contract test verifying balanced still works"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: Foundational (T001-T006) - Enum and helper infrastructure
2. Complete Phase 3: User Story 1 (T007-T018) - Basic LiveText processing
3. **STOP and VALIDATE**: Test LiveText on Sonoma+ system with curl commands
4. Ready for limited deployment to compatible systems

**MVP Delivers**: Users on macOS Sonoma+ can use recognition_level=livetext for enhanced OCR

### Incremental Delivery

1. Foundation (T001-T006) → Basic infrastructure ready
2. + User Story 1 (T007-T018) → LiveText works on Sonoma+ (MVP!)
3. + User Story 2 (T019-T024) → Clear errors on incompatible systems (Better UX)
4. + User Story 3 (T025-T044) → Full test coverage and validation (Production-ready)
5. + Polish (T045-T055) → Documentation, metrics, quality checks (Complete)

### Parallel Team Strategy

With multiple developers:

1. **Developer A**: Complete Foundational (T001-T006) - everyone waits
2. Once Foundational done:
   - **Developer A**: User Story 1 (T007-T018)
   - **Developer B**: User Story 2 (T019-T024)
   - **Developer C**: User Story 3 tests (T025-T044)
3. Integrate and validate together
4. Team completes Polish phase (T045-T055)

---

## Task Summary

### Total Tasks: 55

**By Phase**:
- Phase 1 (Setup): 0 tasks (existing infrastructure)
- Phase 2 (Foundational): 6 tasks (T001-T006)
- Phase 3 (US1 - Basic LiveText): 12 tasks (T007-T018)
- Phase 4 (US2 - Platform Validation): 6 tasks (T019-T024)
- Phase 5 (US3 - Backward Compatibility): 20 tasks (T025-T044)
- Phase 6 (Polish): 11 tasks (T045-T055)

**By User Story**:
- User Story 1 (P1): 12 tasks - Core LiveText functionality
- User Story 2 (P2): 6 tasks - Error handling and validation
- User Story 3 (P3): 20 tasks - Test coverage and compatibility

**Parallel Tasks**: 32 tasks marked [P] can run in parallel within their phase

**Independent Test Criteria**:
- US1: POST to /sync/ocrmac with recognition_level=livetext, verify hOCR contains "ocrmac-livetext"
- US2: Mock pre-Sonoma version, verify HTTP 400 with clear error message
- US3: Run existing test suite for fast/balanced/accurate, verify all pass

**Suggested MVP Scope**: Phase 2 (Foundational) + Phase 3 (User Story 1) = 18 tasks

---

## Notes

- [P] tasks = different files or different functions, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tests NOT requested in specification - included for validation purposes only
- Commit after each logical group of tasks
- Stop at any checkpoint to validate story independently
- All changes are additive and backward compatible - no breaking changes
- ocrmac library version requirement determined in Phase 0 research (keep >=0.1.0)
- Platform limitations documented: LiveText requires macOS Sonoma 14.0+, not Docker-compatible
