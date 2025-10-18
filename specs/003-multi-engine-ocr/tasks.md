# Tasks: Multi-Engine OCR Support

**Feature**: 003-multi-engine-ocr
**Branch**: `003-multi-engine-ocr`
**Input**: Design documents from `/specs/003-multi-engine-ocr/`

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- All file paths are relative to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for multi-engine support

- [ ] T001 Create new directory structure for engine abstraction layer at src/services/ocr/
- [ ] T002 [P] Add ocrmac package to pyproject.toml dependencies with platform markers for macOS-only installation
- [ ] T003 [P] Update .gitignore for any new temporary files or engine-specific outputs

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create EngineType enum in src/models/job.py with values TESSERACT and OCRMAC
- [ ] T005 [P] Create base OCR engine interface in src/services/ocr/base.py with abstract process() method
- [ ] T006 [P] Create OcrmacParams model with languages and recognition_level fields in src/models/ocr_params.py
- [ ] T007 [P] Create RecognitionLevel enum (fast/balanced/accurate) in src/models/ocr_params.py
- [ ] T008 [P] Create EngineCapabilities dataclass in src/services/ocr/registry.py with available, version, supported_languages, platform_requirement fields
- [ ] T009 Create EngineRegistry singleton class in src/services/ocr/registry.py with startup engine detection and capability caching
- [ ] T010 [P] Create platform detection utility in src/utils/platform.py using platform.system()
- [ ] T011 Implement EngineRegistry._detect_tesseract() method to query Tesseract version and supported languages
- [ ] T012 Implement EngineRegistry._detect_ocrmac() method to query ocrmac availability, version, and supported languages on macOS
- [ ] T013 Implement EngineRegistry.is_available() method to check engine availability from cache
- [ ] T014 [P] Implement EngineRegistry.validate_platform() method to check platform compatibility for ocrmac
- [ ] T015 [P] Implement EngineRegistry.validate_languages() method to validate language codes against engine capabilities
- [ ] T016 Extend OCRJob model in src/models/job.py to add engine field (default: TESSERACT) and rename tesseract_params to engine_params (Union[TesseractParams, OcrmacParams])
- [ ] T017 Initialize EngineRegistry singleton in src/main.py application lifespan startup event
- [ ] T018 [P] Add unit tests for platform detection in tests/unit/test_platform.py
- [ ] T019 [P] Add unit tests for EngineRegistry initialization and capability detection in tests/unit/test_engine_registry.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Engine Selection for macOS Users (Priority: P1) 🎯 MVP

**Goal**: Enable users to choose between Tesseract and ocrmac engines with platform-specific validation

**Independent Test**: Upload a document with engine parameter on macOS, verify correct engine is used and returns OCR results

### Tests for User Story 1

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T020 [P] [US1] Add contract test for POST /upload/tesseract endpoint in tests/contract/test_api_contract.py
- [ ] T021 [P] [US1] Add contract test for POST /upload/ocrmac endpoint in tests/contract/test_api_contract.py
- [ ] T022 [P] [US1] Add contract test for invalid engine name returns HTTP 400 in tests/contract/test_api_contract.py
- [ ] T023 [P] [US1] Add contract test for ocrmac on non-macOS returns HTTP 400 in tests/contract/test_api_contract.py
- [ ] T024 [P] [US1] Add integration test for default engine behavior (backward compatibility) in tests/integration/test_engine_selection.py

### Implementation for User Story 1

- [ ] T025 [P] [US1] Refactor existing Tesseract processing logic into TesseractEngine class in src/services/ocr/tesseract.py implementing base.py interface
- [ ] T026 [P] [US1] Create OcrmacEngine class in src/services/ocr/ocrmac.py implementing base.py interface with process() method
- [ ] T027 [US1] Create POST /upload/tesseract endpoint in src/api/routes/upload.py accepting TesseractParams
- [ ] T028 [US1] Create POST /upload/ocrmac endpoint in src/api/routes/upload.py accepting OcrmacParams
- [ ] T029 [US1] Add engine availability validation to /upload/tesseract endpoint using EngineRegistry.is_available()
- [ ] T030 [US1] Add engine availability and platform validation to /upload/ocrmac endpoint using EngineRegistry.validate_platform()
- [ ] T031 [US1] Update existing /upload endpoint to default to Tesseract for backward compatibility
- [ ] T032 [US1] Add HTTP 400 error responses for invalid engine selection with list of available engines
- [ ] T033 [US1] Add HTTP 400 error responses for platform-incompatible engine requests (ocrmac on Linux/Windows)
- [ ] T034 [US1] Update OCR job manager in src/services/job_manager.py to store engine type and engine_params in job metadata
- [ ] T035 [US1] Add structured logging with engine field for all OCR operations
- [ ] T036 [US1] Run contract tests to verify US1 acceptance scenarios pass

**Checkpoint**: At this point, User Story 1 should be fully functional - users can select engines on appropriate platforms

---

## Phase 4: User Story 2 - Tesseract with Custom Parameters (Priority: P1)

**Goal**: Ensure Tesseract users retain full parameter control when explicitly selecting Tesseract engine

**Independent Test**: Upload document with engine=tesseract and custom lang, psm parameters, verify they are applied correctly

### Tests for User Story 2

- [ ] T037 [P] [US2] Add contract test for /upload/tesseract with lang=spa&psm=6 in tests/contract/test_api_contract.py
- [ ] T038 [P] [US2] Add contract test for /upload/tesseract without lang defaults to eng in tests/contract/test_api_contract.py
- [ ] T039 [P] [US2] Add contract test for /upload/tesseract with invalid parameters returns HTTP 400 in tests/contract/test_api_contract.py
- [ ] T040 [P] [US2] Add contract test for backward compatibility: /upload with Tesseract params (no engine) in tests/contract/test_api_contract.py

### Implementation for User Story 2

- [ ] T041 [P] [US2] Add Tesseract parameter validation to /upload/tesseract endpoint using existing TesseractParams Pydantic model
- [ ] T042 [US2] Ensure TesseractEngine.process() method accepts and applies all TesseractParams (lang, psm, oem, dpi)
- [ ] T043 [US2] Add HTTP 400 error responses for Tesseract-specific parameter validation failures
- [ ] T044 [US2] Ensure existing /upload endpoint passes TesseractParams to Tesseract engine for backward compatibility
- [ ] T045 [US2] Add unit tests for TesseractParams validation in tests/unit/test_validators.py
- [ ] T046 [US2] Run contract tests to verify US2 acceptance scenarios pass

**Checkpoint**: Tesseract users can configure all parameters with explicit engine selection and via backward-compatible /upload endpoint

---

## Phase 5: User Story 3 - ocrmac with Language Selection (Priority: P2)

**Goal**: Enable ocrmac users to specify languages for multilingual document recognition

**Independent Test**: Upload document with engine=ocrmac&languages=de, verify German text recognition

### Tests for User Story 3

- [ ] T047 [P] [US3] Add contract test for /upload/ocrmac with languages=de in tests/contract/test_api_contract.py
- [ ] T048 [P] [US3] Add contract test for /upload/ocrmac with multiple languages (en,fr) in tests/contract/test_api_contract.py
- [ ] T049 [P] [US3] Add contract test for /upload/ocrmac without languages uses auto-detection in tests/contract/test_api_contract.py
- [ ] T050 [P] [US3] Add contract test for /upload/ocrmac with unsupported language returns HTTP 400 in tests/contract/test_api_contract.py
- [ ] T051 [P] [US3] Add contract test for /upload/ocrmac with more than 5 languages returns HTTP 400 in tests/contract/test_api_contract.py

### Implementation for User Story 3

- [ ] T052 [P] [US3] Add IETF BCP 47 language code validation to OcrmacParams model using field_validator
- [ ] T053 [P] [US3] Add maximum 5 languages validation to OcrmacParams model
- [ ] T054 [US3] Implement language parameter handling in OcrmacEngine.process() method to pass languages to ocrmac
- [ ] T055 [US3] Add runtime language validation to /upload/ocrmac endpoint using EngineRegistry.validate_languages()
- [ ] T056 [US3] Add HTTP 400 error responses for invalid or unsupported language codes with list of valid codes
- [ ] T057 [US3] Add HTTP 400 error responses for exceeding maximum 5 languages limit
- [ ] T058 [US3] Add unit tests for OcrmacParams language validation in tests/unit/test_validators.py
- [ ] T059 [US3] Run contract tests to verify US3 acceptance scenarios pass

**Checkpoint**: ocrmac users can specify single or multiple languages with proper validation

---

## Phase 6: User Story 4 - ocrmac with Recognition Level Control (Priority: P2)

**Goal**: Enable ocrmac users to control recognition speed vs accuracy trade-off

**Independent Test**: Upload same document with recognition_level=fast and accurate, compare processing times

### Tests for User Story 4

- [ ] T060 [P] [US4] Add contract test for /upload/ocrmac with recognition_level=fast in tests/contract/test_api_contract.py
- [ ] T061 [P] [US4] Add contract test for /upload/ocrmac with recognition_level=accurate in tests/contract/test_api_contract.py
- [ ] T062 [P] [US4] Add contract test for /upload/ocrmac with invalid recognition_level returns HTTP 400 in tests/contract/test_api_contract.py
- [ ] T063 [P] [US4] Add contract test for /upload/ocrmac without recognition_level defaults to balanced in tests/contract/test_api_contract.py

### Implementation for User Story 4

- [ ] T064 [P] [US4] Implement recognition_level parameter handling in OcrmacEngine.process() to pass to ocrmac API
- [ ] T065 [US4] Add RecognitionLevel enum validation to /upload/ocrmac endpoint
- [ ] T066 [US4] Add HTTP 400 error responses for invalid recognition_level with list of valid options (fast/balanced/accurate)
- [ ] T067 [US4] Ensure recognition_level defaults to "balanced" when not specified in OcrmacParams model
- [ ] T068 [US4] Add unit tests for recognition_level validation in tests/unit/test_validators.py
- [ ] T069 [US4] Run contract tests to verify US4 acceptance scenarios pass

**Checkpoint**: ocrmac users can optimize processing speed vs accuracy based on their use case

---

## Phase 7: User Story 5 - Parameter Isolation Between Engines (Priority: P3)

**Goal**: Validate engine-specific parameters and provide clear errors for incompatible parameter combinations

**Independent Test**: Upload with engine=ocrmac&psm=6 (Tesseract-only param), verify HTTP 400 error with clear message

### Tests for User Story 5

- [ ] T070 [P] [US5] Add contract test for /upload/ocrmac with Tesseract-only parameters (psm, oem, dpi) returns HTTP 400 in tests/contract/test_api_contract.py
- [ ] T071 [P] [US5] Add contract test for /upload/tesseract with ocrmac-only parameters (recognition_level) returns HTTP 400 in tests/contract/test_api_contract.py
- [ ] T072 [P] [US5] Add integration test for parameter isolation in tests/integration/test_parameter_validation.py

### Implementation for User Story 5

- [ ] T073 [P] [US5] Add validation to /upload/ocrmac endpoint to reject Tesseract-only parameters (psm, oem, dpi)
- [ ] T074 [P] [US5] Add validation to /upload/tesseract endpoint to reject ocrmac-only parameters (recognition_level)
- [ ] T075 [US5] Add HTTP 400 error responses listing which parameters are valid for each engine
- [ ] T076 [US5] Update OpenAPI documentation to clearly indicate which parameters apply to which engine
- [ ] T077 [US5] Add unit tests for parameter isolation validation in tests/unit/test_validators.py
- [ ] T078 [US5] Run contract tests to verify US5 acceptance scenarios pass

**Checkpoint**: All user stories should now be independently functional with clear parameter validation

---

## Phase 8: HOCR Conversion & Output Standardization

**Purpose**: Ensure both engines produce consistent HOCR output format (ocrmac requires custom conversion)

- [ ] T079 Create HOCR converter module in src/services/ocr/hocr_converter.py using xml.etree.ElementTree
- [ ] T080 Implement convert_ocrmac_to_hocr() function to transform ocrmac native output to HOCR format
- [ ] T081 Integrate HOCR converter into OcrmacEngine.process() to standardize output
- [ ] T082 Add unit tests for HOCR converter in tests/unit/test_hocr_converter.py
- [ ] T083 Add integration test to verify HOCR format consistency between engines in tests/integration/test_hocr_output.py
- [ ] T084 Validate determinism: same input produces same HOCR output for ocrmac

---

## Phase 9: Error Handling & Timeouts

**Purpose**: Implement robust error handling for engine failures and timeouts

- [ ] T085 [P] Add 60-second timeout per page for Tesseract processing in TesseractEngine.process()
- [ ] T086 [P] Add 60-second timeout per page for ocrmac processing in OcrmacEngine.process()
- [ ] T087 Add timeout error handling with clear error messages indicating which page and engine exceeded limit
- [ ] T088 Add engine unavailability check during job processing (between upload and processing)
- [ ] T089 Add HTTP 500 error responses when engine fails during processing with clear error message indicating which engine failed
- [ ] T090 Add HTTP 500 error responses when ocrmac is specified but not installed/executable on macOS with installation instructions
- [ ] T091 [P] Add unit tests for timeout handling in tests/unit/test_ocrmac_processor.py
- [ ] T092 [P] Add integration test for engine failure scenarios in tests/integration/test_error_handling.py

---

## Phase 10: Observability & Monitoring

**Purpose**: Extend observability infrastructure for multi-engine monitoring

- [ ] T093 [P] Add engine field to all OCR-related structured log entries in src/services/ocr_processor.py
- [ ] T094 [P] Extend Prometheus metrics with engine label for jobs_completed_total counter
- [ ] T095 [P] Extend Prometheus metrics with engine label for jobs_failed_total counter
- [ ] T096 Add engine availability status to /health endpoint in src/api/routes/health.py
- [ ] T097 Add structured logging for engine detection at startup with version and capabilities
- [ ] T098 Add structured logging for engine selection and parameters in job creation

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements affecting multiple user stories

- [ ] T099 [P] Update OpenAPI specification with /upload/tesseract and /upload/ocrmac endpoints
- [ ] T100 [P] Update API documentation with engine-specific parameter descriptions
- [ ] T101 [P] Add examples to API documentation showing engine selection usage
- [ ] T102 Code cleanup: refactor duplicated validation logic across endpoints
- [ ] T103 Performance optimization: benchmark ocrmac vs Tesseract on 50-document test corpus
- [ ] T104 Validate SC-005 (ocrmac 20% faster than Tesseract for simple documents)
- [ ] T105 Validate SC-006 (ocrmac accuracy within 5% of Tesseract)
- [ ] T106 Run all contract tests to verify 100% of acceptance scenarios pass
- [ ] T107 Validate test coverage meets 80% overall, 90% for utilities
- [ ] T108 Run quickstart.md scenarios to validate end-to-end functionality
- [ ] T109 Update CLAUDE.md with multi-engine technologies and structure

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (US1 → US2 → US3 → US4 → US5)
- **HOCR Conversion (Phase 8)**: Depends on US1 (ocrmac engine implementation)
- **Error Handling (Phase 9)**: Depends on US1 (engine implementations exist)
- **Observability (Phase 10)**: Depends on US1 (engine field exists in job model)
- **Polish (Phase 11)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Independent from US1 (but both P1 priority)
- **User Story 3 (P2)**: Depends on US1 (ocrmac engine must exist) - Extends ocrmac with language support
- **User Story 4 (P2)**: Depends on US1 (ocrmac engine must exist) - Extends ocrmac with recognition level
- **User Story 5 (P3)**: Depends on US1, US2, US3, US4 (all endpoints must exist for parameter validation)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- US1 and US2 can be worked on in parallel (both P1, independent implementations)
- Once US1 is complete, US3 and US4 can run in parallel (both extend ocrmac)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Observability tasks (Phase 10) marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all contract tests for User Story 1 together:
Task: "Add contract test for POST /upload/tesseract endpoint"
Task: "Add contract test for POST /upload/ocrmac endpoint"
Task: "Add contract test for invalid engine name returns HTTP 400"
Task: "Add contract test for ocrmac on non-macOS returns HTTP 400"
Task: "Add integration test for default engine behavior"

# Launch engine implementations in parallel:
Task: "Refactor existing Tesseract processing logic into TesseractEngine class"
Task: "Create OcrmacEngine class implementing base.py interface"
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2 Only - Both P1)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Engine Selection)
4. Complete Phase 4: User Story 2 (Tesseract Parameters)
5. Complete Phase 8: HOCR Conversion (required for ocrmac output)
6. Complete Phase 9: Error Handling (robust production readiness)
7. **STOP and VALIDATE**: Test both engines independently
8. Deploy/demo if ready

**MVP Scope**: Basic engine selection (Tesseract + ocrmac) with full Tesseract parameter support and backward compatibility

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 + 2 + HOCR + Error Handling → Test independently → Deploy/Demo (MVP!)
3. Add User Story 3 (ocrmac languages) → Test independently → Deploy/Demo
4. Add User Story 4 (ocrmac recognition level) → Test independently → Deploy/Demo
5. Add User Story 5 (parameter isolation) → Test independently → Deploy/Demo
6. Add Observability + Polish → Final production release

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Engine Selection)
   - Developer B: User Story 2 (Tesseract Parameters)
   - Developer C: Phase 8 (HOCR Conversion - can start when US1 T026 done)
3. After US1 complete:
   - Developer A: User Story 3 (ocrmac Languages)
   - Developer B: User Story 4 (ocrmac Recognition Level)
4. Final: User Story 5 (Parameter Isolation - requires all previous stories)

---

## Summary

**Total Tasks**: 109 tasks
**Tasks per User Story**:
- Setup: 3 tasks
- Foundational: 16 tasks
- User Story 1 (Engine Selection): 17 tasks
- User Story 2 (Tesseract Parameters): 10 tasks
- User Story 3 (ocrmac Languages): 13 tasks
- User Story 4 (ocrmac Recognition Level): 10 tasks
- User Story 5 (Parameter Isolation): 9 tasks
- HOCR Conversion: 6 tasks
- Error Handling: 8 tasks
- Observability: 6 tasks
- Polish: 11 tasks

**Parallel Opportunities**: 39 tasks marked [P] can run in parallel within their phase
**Independent Test Criteria**: Each user story has clear acceptance scenarios and can be tested independently
**MVP Scope**: User Stories 1 & 2 (Engine Selection + Tesseract Parameters) + HOCR Conversion + Error Handling = 37 core tasks for production-ready multi-engine support

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Platform-specific testing: US1, US3, US4 require macOS for ocrmac testing
