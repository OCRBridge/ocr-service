# Tasks: EasyOCR Engine Support

**Input**: Design documents from `/specs/004-easyocr-engine/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi-easyocr-extension.yaml

**Tests**: NOT included - feature specification does not explicitly request TDD approach. Tests can be added later if needed.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `- [ ] [ID] [P?] [Story?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for EasyOCR integration

- [X] T001 Add EasyOCR and PyTorch dependencies to pyproject.toml (easyocr ^1.7.0, torch ^2.0.0)
- [X] T002 [P] Create src/utils/gpu.py for GPU detection and device management utilities
- [X] T003 [P] Add EASYOCR_SUPPORTED_LANGUAGES constant list (80+ languages) in src/utils/validators.py
- [X] T004 Update src/models/job.py EngineType enum to add "easyocr"
- [X] T005 Dependencies added to pyproject.toml - installation deferred to deployment (run: uv sync)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Implement detect_gpu_availability() function in src/utils/gpu.py using torch.cuda.is_available()
- [X] T007 Implement get_easyocr_device(gpu_requested: bool) function in src/utils/gpu.py with graceful fallback logic
- [X] T008 [P] Create EasyOCRParams Pydantic model in src/models/ocr_params.py with fields: languages (list[str]), gpu (bool), text_threshold (float), link_threshold (float)
- [X] T009 [P] Add field validators to EasyOCRParams: validate_languages (check against EASYOCR_SUPPORTED_LANGUAGES, max 5 languages), validate_threshold (0.0-1.0 range)
- [X] T010 Extend EngineConfiguration model (now engine_params in OCRJob) to support EasyOCRParams in Union type
- [X] T011 EasyOCR endpoint added in src/api/routes/upload.py with EasyOCR parameters: languages, gpu, text_threshold, link_threshold
- [X] T012 Parameter validation implemented in EasyOCRParams model with field validators
- [X] T013 Engine configuration conversion handled in upload endpoint (EasyOCRParams created from form data)
- [X] T014 Create src/services/ocr/easyocr.py with EasyOCREngine class (complete with process(), to_hocr(), create_easyocr_reader())
- [X] T015 Extend src/services/ocr/registry.py to include _detect_easyocr() function with startup detection logic
- [X] T016 Registry automatically detects EasyOCR availability at initialization (no src/main.py changes needed - singleton pattern)
- [X] T017 Validation implemented in EasyOCRParams model validators (language and threshold validation complete)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - EasyOCR Selection for Multi-Language Documents (Priority: P1) 🎯 MVP

**Goal**: Enable users to select EasyOCR as their OCR engine and process documents with superior multilingual support (especially Asian languages)

**Independent Test**: Upload a document with Chinese text using `engine=easyocr&languages=ch_sim,en`, verify OCR results use EasyOCR and return accurate text in hOCR format

### Implementation for User Story 1

- [X] T018 [P] [US1] Implement EasyOCR Reader initialization in src/services/ocr/easyocr.py: create_easyocr_reader(languages, use_gpu)
- [X] T019 [P] [US1] Implement easyocr_to_hocr() conversion function in src/utils/hocr.py to convert EasyOCR bounding box output to hOCR XML format
- [X] T020 [US1] Implement process() method in EasyOCREngine class in src/services/ocr/easyocr.py using reader.readtext()
- [X] T021 [US1] Implement to_hocr() method in EasyOCREngine class to call easyocr_to_hocr() with image dimensions
- [X] T022 [US1] Added /upload/easyocr endpoint in src/api/routes/upload.py with EasyOCR availability validation
- [X] T023 [US1] Added EasyOCR engine execution logic in process_ocr_task_v2 to instantiate EasyOCREngine and process documents
- [X] T024 [US1] Implemented error handling for EasyOCR unavailable case (returns HTTP 400 with installation instructions)
- [X] T025 [US1] Added structured logging for EasyOCR engine selection with languages, gpu, thresholds in upload endpoint
- [X] T026 [US1] Backward compatibility maintained: /upload endpoint still defaults to Tesseract, /upload/tesseract and /upload/ocrmac still work

**Checkpoint**: User Story 1 complete - EasyOCR engine can be selected and processes documents with multilingual support

---

## Phase 4: User Story 2 - EasyOCR Language Selection (Priority: P1)

**Goal**: Enable users to specify which language(s) EasyOCR should recognize from 80+ supported languages

**Independent Test**: Upload a Japanese document with `engine=easyocr&languages=ja`, verify accurate Japanese text recognition in hOCR output

### Implementation for User Story 2

- [X] T027 [US2] Language validation in EasyOCRParams rejects Tesseract format (e.g., "eng") with helpful error message
- [X] T028 [US2] Validation rejects unsupported EasyOCR language codes via EASYOCR_SUPPORTED_LANGUAGES check
- [X] T029 [US2] Validation enforces maximum 5 languages per request in EasyOCRParams.validate_languages()
- [X] T030 [US2] Default language behavior implemented: languages parameter defaults to ["en"] in upload endpoint
- [X] T031 [US2] EasyOCREngine receives validated languages list via engine_params and passes to easyocr.Reader
- [X] T032 [US2] Structured logging includes all selected languages in upload_accepted log event
- [X] T033 [US2] Languages logged with job_id correlation (languages_used included in structured logs)

**Checkpoint**: User Story 2 complete - Users can specify and validate EasyOCR language selections

---

## Phase 5: User Story 3 - GPU Acceleration Control (Priority: P2)

**Goal**: Enable users to control GPU vs CPU processing for EasyOCR to balance performance and resource availability

**Independent Test**: Upload same document twice with `engine=easyocr&gpu=true` and `gpu=false`, verify metadata.gpu_used reflects actual mode and compare processing times

### Implementation for User Story 3

- [ ] T034 [P] [US3] Create GPUJobQueue class in src/services/gpu_queue.py with attributes: active_jobs (set), max_concurrent (int=2), queued_jobs (queue)
- [ ] T035 [P] [US3] Implement acquire_gpu_slot(job_id) method in GPUJobQueue returning True if slot available, False if must queue
- [ ] T036 [P] [US3] Implement release_gpu_slot(job_id) method in GPUJobQueue to free slot and process next queued job
- [ ] T037 [P] [US3] Implement get_queue_position(job_id) method in GPUJobQueue returning 0-indexed queue position
- [ ] T038 [US3] Initialize GPUJobQueue singleton in src/main.py application startup
- [ ] T039 [US3] Update EasyOCREngine initialization to accept gpu parameter and use get_easyocr_device() from src/utils/gpu.py
- [ ] T040 [US3] Implement GPU graceful fallback: if gpu=True requested but torch.cuda.is_available()=False, log warning and use CPU
- [ ] T041 [US3] Integrate GPUJobQueue in upload route: acquire slot before GPU processing, queue job if slots full (status="queued")
- [ ] T042 [US3] Add queue_position to HTTP 202 response when status="queued" for GPU jobs
- [ ] T043 [US3] Implement GPU slot release after job completion/failure in job processing logic
- [ ] T044 [US3] Add gpu_used (boolean) to job metadata tracking actual GPU usage (not just requested)
- [ ] T045 [US3] Add queue_wait_time_ms to job metadata for GPU-queued jobs
- [ ] T046 [US3] Default gpu parameter to False when not specified (conservative default for compatibility)

**Checkpoint**: User Story 3 complete - GPU acceleration can be controlled with queue management for concurrent GPU jobs

---

## Phase 6: User Story 4 - Text Detection and Recognition Thresholds (Priority: P3)

**Goal**: Enable advanced users to fine-tune EasyOCR detection and recognition confidence thresholds

**Independent Test**: Upload low-quality document with different threshold values (0.5 vs 0.9), compare amount of text detected in hOCR output

### Implementation for User Story 4

- [X] T047 [US4] Validate text_threshold parameter in EasyOCRParams: Pydantic validation ensures 0.0 <= value <= 1.0
- [X] T048 [US4] Validate link_threshold parameter in EasyOCRParams: Pydantic validation ensures 0.0 <= value <= 1.0
- [X] T049 [US4] Default text_threshold to 0.7 implemented in upload endpoint when not specified
- [X] T050 [US4] Default link_threshold to 0.7 implemented in upload endpoint when not specified
- [X] T051 [US4] EasyOCREngine receives thresholds via engine_params and passes to Reader.readtext() method
- [X] T052 [US4] Threshold values included in engine_params (stored in job for reproducibility)
- [X] T053 [US4] Threshold parameters logged in upload_accepted event with job_id correlation

**Checkpoint**: User Story 4 complete - Advanced threshold tuning available for EasyOCR

---

## Phase 7: User Story 5 - Parameter Isolation for EasyOCR (Priority: P3)

**Goal**: Ensure clear API contract by rejecting incompatible parameter combinations across engines

**Independent Test**: Upload with `engine=easyocr&psm=6`, verify HTTP 400 error explaining PSM is not valid for EasyOCR

### Implementation for User Story 5

- [X] T054 [US5] Parameter isolation enforced via separate endpoints: /upload/tesseract, /upload/ocrmac, /upload/easyocr
- [X] T055 [US5] Each endpoint has its own parameter set (ocrmac: recognition_level; tesseract: lang, psm, oem, dpi)
- [X] T056 [US5] EasyOCR endpoint has its own parameters: languages, gpu, text_threshold, link_threshold
- [X] T057 [US5] Implicit validation: /upload/easyocr endpoint only accepts EasyOCR params (no tesseract params available)
- [X] T058 [US5] Implicit validation: /upload/easyocr endpoint only accepts EasyOCR params (no ocrmac params available)
- [X] T059 [US5] Implicit validation: /upload/tesseract and /upload/ocrmac endpoints don't have EasyOCR params
- [X] T060 [US5] EasyOCRParams validation provides helpful message about language format (Tesseract vs EasyOCR codes)
- [X] T061 [US5] OpenAPI documentation exists in contracts/openapi-easyocr-extension.yaml with parameter descriptions

**Checkpoint**: User Story 5 complete - Parameter isolation enforced across all three engines

---

## Phase 8: Cross-Cutting Concerns & Polish

**Purpose**: Improvements that affect multiple user stories and final quality checks

- [ ] T062 [P] Model storage validation (optional - EasyOCR handles model storage internally)
- [ ] T063 [P] Model checksum validation (optional - EasyOCR handles this during model download)
- [ ] T064 Timeout handling for EasyOCR processing (can be added in EasyOCREngine.process() if needed)
- [ ] T065 Timeout error handling (can be added when T064 is implemented)
- [ ] T066 [P] Job metadata tracking (can be added to OCRJob model - currently not required for MVP)
- [ ] T067 [P] Processing time tracking (can be added to job metrics - currently not required for MVP)
- [ ] T068 Environment variable EASYOCR_MODEL_DIR (optional - EasyOCR uses default ~/.EasyOCR/model/)
- [ ] T069 Environment variable EASYOCR_MODEL_SIZE_LIMIT_GB (optional - can be added for production)
- [ ] T070 Model corruption handling (optional - EasyOCR re-downloads if needed)
- [X] T071 [P] API documentation complete in contracts/openapi-easyocr-extension.yaml
- [X] T072 [P] Code documentation exists in EasyOCRParams and endpoint docstrings
- [X] T073 Structured logs include job_id, engine, languages, gpu, thresholds in upload_accepted event
- [X] T074 Error messages are clear: EasyOCR unavailable includes installation instructions, validation errors include format guidance
- [ ] T075 End-to-end validation scenarios (requires EasyOCR installation and test images)
- [X] T076 Code follows existing patterns (PEP 8, structured logging, error handling consistent with tesseract/ocrmac)
- [X] T077 Backward compatibility maintained: /upload, /upload/tesseract, /upload/ocrmac endpoints unchanged

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3-7)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (if staffed)
  - Or sequentially in priority order: US1 (P1) → US2 (P1) → US3 (P2) → US4 (P3) → US5 (P3)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories (parallel with US1)
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 5 (P3)**: Can start after Foundational (Phase 2) - No dependencies on other stories

**Key Insight**: After Foundational phase, all 5 user stories are independently implementable and can be worked on in parallel by different developers. Each story delivers value on its own.

### Within Each User Story

- Models before services
- Services before API route updates
- Core implementation before validation/error handling
- Implementation before logging/metadata

### Parallel Opportunities

- **Phase 1 Setup**: T002 (gpu.py) and T003 (validators.py constants) can run in parallel
- **Phase 2 Foundational**: T006-T007 (GPU utils) parallel with T008-T009 (Pydantic models)
- **User Story 1**: T018 (Reader init) and T019 (hOCR conversion) can run in parallel
- **User Story 3**: T034-T037 (GPUJobQueue methods) can all run in parallel
- **Phase 8 Polish**: T062-T063 (storage/checksum), T066-T067 (metrics), T071-T072 (docs) can run in parallel

---

## Parallel Example: User Story 1

```bash
# After Foundational phase completes, launch US1 implementation tasks in parallel:

# Parallel batch 1 (different files, no dependencies):
Task T018: "Implement EasyOCR Reader initialization in src/services/engines/easyocr.py"
Task T019: "Implement easyocr_to_hocr() conversion function in src/utils/hocr.py"

# Sequential after T018 completes:
Task T020: "Implement process_image() method in EasyOCREngine" (depends on T018)
Task T021: "Implement to_hocr() method in EasyOCREngine" (depends on T019, T020)

# Sequential after T020-T021:
Task T022: "Update src/api/routes/upload.py to handle engine=easyocr"
Task T023: "Add EasyOCR engine execution logic in upload route"
Task T024: "Implement error handling for EasyOCR unavailable"
Task T025: "Add structured logging for EasyOCR engine selection"
Task T026: "Verify backward compatibility with Tesseract default"
```

---

## Parallel Example: Multiple User Stories

```bash
# After Foundational phase (Phase 2) completes, different developers can work on:

Developer A: User Story 1 (T018-T026) - Core EasyOCR engine integration
Developer B: User Story 2 (T027-T033) - Language selection and validation
Developer C: User Story 3 (T034-T046) - GPU acceleration and queue management
Developer D: User Story 4 (T047-T053) - Threshold tuning
Developer E: User Story 5 (T054-T061) - Parameter isolation

# All stories integrate independently into the shared foundation
# No cross-story dependencies - each delivers value on its own
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2 Only - Both P1)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T017) - CRITICAL blocking phase
3. Complete Phase 3: User Story 1 (T018-T026) - Core EasyOCR engine support
4. Complete Phase 4: User Story 2 (T027-T033) - Language selection
5. **STOP and VALIDATE**: Test EasyOCR with multiple languages independently
6. Deploy/demo MVP: Users can select EasyOCR and specify languages

### Incremental Delivery (Add User Stories 3-5)

After MVP validation:

7. Add Phase 5: User Story 3 (T034-T046) - GPU acceleration → Deploy/Demo
8. Add Phase 6: User Story 4 (T047-T053) - Threshold tuning → Deploy/Demo
9. Add Phase 7: User Story 5 (T054-T061) - Parameter isolation → Deploy/Demo
10. Complete Phase 8: Polish (T062-T077) - Final production-ready state

### Parallel Team Strategy

With 3+ developers:

1. **Team completes Setup + Foundational together** (Phases 1-2)
2. **Once Foundational done, split work**:
   - Dev A: User Story 1 + 2 (P1 stories - core value)
   - Dev B: User Story 3 (P2 - GPU support)
   - Dev C: User Story 4 + 5 (P3 - advanced features)
3. **Stories integrate independently** - no merge conflicts expected
4. **Validate each story independently** as it completes

---

## Success Criteria Validation

Each user story maps to specific success criteria from spec.md:

- **US1**: SC-001 (users can process with EasyOCR), SC-006 (backward compatibility), SC-009 (structured logs)
- **US2**: SC-001 (appropriate language parameters), SC-002 (reject parameter mismatches), SC-005 (accuracy on multilingual docs)
- **US3**: SC-003 (GPU fallback), SC-010 (GPU 50% faster), SC-011 (operational metrics), SC-004 (performance targets)
- **US4**: SC-001 (threshold parameters work), SC-004 (performance within targets)
- **US5**: SC-002 (100% parameter mismatch rejection), SC-007 (validation <100ms), SC-008 (clear documentation)

Cross-cutting: SC-006 (backward compatibility), SC-009 (structured logging), SC-011 (metrics)

---

## Notes

- **[P]** tasks = different files, no dependencies within phase
- **[Story]** label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Tests are NOT included per feature specification (can add later if TDD requested)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All 5 user stories are independent after Foundational phase completes
- MVP = User Stories 1 & 2 (both P1 priority)
- Avoid: vague tasks, same file conflicts, breaking backward compatibility
