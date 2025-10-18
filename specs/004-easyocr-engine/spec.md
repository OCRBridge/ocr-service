# Feature Specification: EasyOCR Engine Support

**Feature Branch**: `004-easyocr-engine`
**Created**: 2025-10-19
**Status**: Draft
**Input**: User description: "Add easyocr as the third OCR engine"

## Clarifications

### Session 2025-10-19

- Q: Where should EasyOCR model files be stored and what size limits should apply? → A: Store in configurable persistent volume with 5GB default size limit
- Q: How should the system handle concurrent GPU-enabled EasyOCR jobs to prevent GPU memory exhaustion? → A: Limit concurrent GPU-enabled EasyOCR jobs to 2, queue additional requests
- Q: How should the system detect and prevent corrupted EasyOCR model files from causing failures? → A: Validate model files using checksums at startup and before first use of each language
- Q: What should happen if EasyOCR capability detection fails at startup? → A: Start service but mark EasyOCR as unavailable, log warning
- Q: What operational metrics should be captured for monitoring EasyOCR performance and resource usage? → A: Track per-job processing time, GPU/CPU mode, language count, queue wait time, model load time

## User Scenarios & Testing *(mandatory)*

### User Story 1 - EasyOCR Selection for Multi-Language Documents (Priority: P1)

A user wants to use EasyOCR for processing documents containing multiple languages (especially Asian languages like Chinese, Japanese, Korean, Thai) where EasyOCR excels compared to Tesseract and ocrmac, taking advantage of its deep learning-based recognition capabilities.

**Why this priority**: This is the core value proposition - EasyOCR provides superior support for 80+ languages (especially non-Latin scripts) with state-of-the-art deep learning models. This enables users to process multilingual documents that may not work well with Tesseract or ocrmac.

**Independent Test**: Can be fully tested by uploading a document with Chinese text using `engine=easyocr&languages=ch_sim,en` parameter, then verifying the OCR results use EasyOCR and return accurate text. Delivers immediate value by supporting a third engine option with unique capabilities.

**Acceptance Scenarios**:

1. **Given** a user wants to use EasyOCR, **When** they upload a document with `engine=easyocr` parameter, **Then** the system uses EasyOCR for processing and returns accurate OCR results
2. **Given** a user does not specify an engine parameter, **When** they upload a document, **Then** the system defaults to Tesseract (preserving backward compatibility)
3. **Given** a user specifies `engine=easyocr`, **When** they submit the upload request, **Then** the system validates EasyOCR availability and returns HTTP 400 if not installed
4. **Given** a user uploads a document with mixed Chinese and English text using `engine=easyocr&languages=ch_sim,en`, **When** processing completes, **Then** both languages are accurately recognized

---

### User Story 2 - EasyOCR Language Selection (Priority: P1)

A user chooses EasyOCR as their OCR engine and wants to specify which language(s) the engine should recognize from the 80+ supported languages for optimal accuracy.

**Why this priority**: Language selection is critical for EasyOCR's accuracy and performance. Unlike Tesseract's 3-letter codes or ocrmac's 2-letter codes, EasyOCR uses its own language naming convention. Users must be able to specify languages correctly.

**Independent Test**: Can be tested by uploading a Japanese document with `engine=easyocr&languages=ja` and verifying accurate Japanese text recognition. Delivers value by supporting EasyOCR's extensive language support.

**Acceptance Scenarios**:

1. **Given** a user selects EasyOCR engine, **When** they upload with `engine=easyocr&languages=ja`, **Then** the system processes using EasyOCR with Japanese language recognition
2. **Given** a user selects EasyOCR with multiple languages, **When** they upload with `languages=en,ko`, **Then** the system recognizes both English and Korean text
3. **Given** a user selects EasyOCR but omits language parameter, **When** they upload, **Then** the system defaults to English (en)
4. **Given** a user selects EasyOCR with unsupported language codes, **When** they submit the upload, **Then** the system returns HTTP 400 error listing valid language codes for EasyOCR
5. **Given** a user selects EasyOCR with more than 5 languages, **When** they submit the upload, **Then** the system returns HTTP 400 error indicating the maximum of 5 languages allowed

---

### User Story 3 - GPU Acceleration Control (Priority: P2)

A user wants to control whether EasyOCR uses GPU acceleration for processing, allowing them to balance performance (GPU) versus resource availability (CPU-only).

**Why this priority**: EasyOCR can leverage GPU acceleration for significantly faster processing, but not all deployment environments have GPU support. Users need to explicitly control this based on their infrastructure.

**Independent Test**: Can be tested by uploading the same document twice with `engine=easyocr&gpu=true` and `gpu=false`, comparing processing times. Delivers value through performance optimization options.

**Acceptance Scenarios**:

1. **Given** a user has GPU available and wants faster processing, **When** they upload with `engine=easyocr&gpu=true`, **Then** EasyOCR uses GPU acceleration for faster processing
2. **Given** a user has no GPU or wants to preserve GPU resources, **When** they upload with `engine=easyocr&gpu=false`, **Then** EasyOCR uses CPU-only processing
3. **Given** a user selects EasyOCR without specifying GPU parameter, **When** they upload, **Then** the system defaults to `gpu=false` (conservative default for wider compatibility)
4. **Given** a user requests GPU but GPU is not available in the environment, **When** processing starts, **Then** EasyOCR automatically falls back to CPU with a warning logged

---

### User Story 4 - Text Detection and Recognition Thresholds (Priority: P3)

A user wants to control EasyOCR's detection and recognition confidence thresholds to fine-tune the balance between recall (finding all text) and precision (only high-confidence text).

**Why this priority**: Advanced users may want to adjust thresholds for specific document types. Less critical than core functionality but provides useful fine-tuning capability similar to Tesseract's advanced parameters.

**Independent Test**: Can be tested by uploading a low-quality document with different threshold values and comparing the amount of text detected. Delivers value through advanced parameter control.

**Acceptance Scenarios**:

1. **Given** a user wants to detect all possible text (high recall), **When** they upload with `engine=easyocr&text_threshold=0.5`, **Then** the system detects more text regions with lower confidence
2. **Given** a user wants only high-confidence text (high precision), **When** they upload with `engine=easyocr&text_threshold=0.9`, **Then** the system detects fewer but more accurate text regions
3. **Given** a user specifies invalid threshold values (outside 0.0-1.0 range), **When** they submit the upload, **Then** the system returns HTTP 400 error indicating valid range
4. **Given** a user selects EasyOCR without specifying thresholds, **When** they upload, **Then** the system uses EasyOCR's default thresholds (0.7 for both text and link threshold)

---

### User Story 5 - Parameter Isolation for EasyOCR (Priority: P3)

A user wants to understand which parameters apply to EasyOCR and receive clear errors when they specify parameters incompatible with the EasyOCR engine.

**Why this priority**: Prevents user confusion and invalid parameter combinations across three engines. Maintains API clarity and consistency with existing engine parameter validation.

**Independent Test**: Can be tested by uploading with `engine=easyocr&psm=6` (Tesseract-only parameter) and verifying the system returns HTTP 400 error explaining PSM is not valid for EasyOCR. Delivers value through clear API contract.

**Acceptance Scenarios**:

1. **Given** a user selects EasyOCR engine, **When** they specify Tesseract-only parameters (psm, oem, dpi, lang), **Then** the system returns HTTP 400 error indicating these parameters are not valid for EasyOCR
2. **Given** a user selects EasyOCR engine, **When** they specify ocrmac-only parameters (recognition_level), **Then** the system returns HTTP 400 error indicating this parameter is not valid for EasyOCR
3. **Given** a user selects Tesseract or ocrmac, **When** they specify EasyOCR-only parameters (gpu, text_threshold, link_threshold), **Then** the system returns HTTP 400 error indicating these parameters are not valid for the selected engine
4. **Given** a user requests API documentation, **When** they view parameter descriptions, **Then** each parameter clearly indicates it applies to EasyOCR engine

---

### Edge Cases

- When a user specifies `engine=easyocr` but EasyOCR is not installed in the environment or failed startup detection, the system returns HTTP 400 error immediately indicating EasyOCR is not available
- When EasyOCR detection fails at startup (not installed, model corruption, etc.), the service starts successfully with EasyOCR marked unavailable and a warning logged, allowing Tesseract and ocrmac engines to continue functioning
- When a user specifies conflicting parameters for the selected engine (e.g., Tesseract PSM with EasyOCR engine), the system rejects with HTTP 400 listing incompatible parameters
- When EasyOCR processing exceeds 60 seconds per page, the job fails with a timeout error indicating which page exceeded the limit
- When EasyOCR GPU processing is requested but no GPU is available, EasyOCR automatically falls back to CPU mode with a warning logged (graceful degradation)
- When a user switches engines between multiple uploads of the same document, each job must be independently processable with its specified engine
- When an engine fails during processing (crash, timeout), the error message must clearly indicate EasyOCR engine failed
- When an engine that was available at upload time becomes unavailable during processing, the job fails immediately with a clear error message
- When a user specifies language codes in Tesseract format (3-letter like "eng") with EasyOCR, the system returns HTTP 400 explaining EasyOCR uses different language codes
- When EasyOCR model files are not downloaded, missing, or fail checksum validation at startup or first use, the system returns HTTP 500 error with instructions to re-download models
- When processing documents with extremely complex layouts or very small text, EasyOCR may produce different results than Tesseract or ocrmac (expected behavior due to different detection algorithms)
- When more than 2 GPU-enabled EasyOCR jobs are requested concurrently, additional jobs are queued and processed in FIFO order as GPU slots become available
- When a queued GPU job waits longer than the overall job timeout, it fails with a timeout error before GPU processing begins

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept `engine=easyocr` as a valid engine parameter value
- **FR-002**: System MUST maintain backward compatibility - existing requests without engine parameter continue to default to Tesseract
- **FR-003**: System MUST validate EasyOCR engine availability during upload validation and return HTTP 400 if not available
- **FR-004**: System MUST accept EasyOCR-specific parameters: `languages` (array of language codes), `gpu` (boolean), `text_threshold` (float 0.0-1.0), `link_threshold` (float 0.0-1.0)
- **FR-005**: System MUST validate EasyOCR language codes against supported languages (80+ languages using EasyOCR naming convention) and return HTTP 400 if unsupported
- **FR-006**: System MUST reject requests with more than 5 languages for EasyOCR with HTTP 400 error indicating the maximum allowed
- **FR-007**: System MUST default to `languages=en` when EasyOCR is selected but no languages parameter is provided
- **FR-008**: System MUST default to `gpu=false` when EasyOCR is selected but no gpu parameter is provided
- **FR-009**: System MUST validate threshold parameters (text_threshold, link_threshold) are within 0.0-1.0 range and return HTTP 400 if invalid
- **FR-010**: System MUST default text_threshold and link_threshold to 0.7 when not specified
- **FR-011**: System MUST reject requests that specify parameters incompatible with EasyOCR engine, returning HTTP 400 with clear explanation
- **FR-012**: System MUST reject requests that specify EasyOCR-only parameters with non-EasyOCR engines, returning HTTP 400 error
- **FR-013**: System MUST include engine type (easyocr) and all EasyOCR-specific parameters in job metadata for debugging and reproducibility
- **FR-014**: System MUST log EasyOCR selection and all parameters in structured JSON format with job ID correlation, including operational metrics: per-job processing time, GPU/CPU mode used, language count, queue wait time (if queued), and model load time
- **FR-015**: System MUST preserve deterministic processing - same document with same EasyOCR parameters produces consistent results (within model variance)
- **FR-016**: System MUST document EasyOCR engine and its parameters in API documentation
- **FR-017**: System MUST enforce a 60-second timeout per page for EasyOCR processing and fail jobs that exceed this limit
- **FR-018**: System MUST fail jobs immediately with clear error messages when EasyOCR becomes unavailable between upload and processing
- **FR-019**: System MUST detect EasyOCR capability (installation, model availability) at startup and cache the results for request validation; if detection fails, the service MUST start but mark EasyOCR as unavailable and log a warning
- **FR-020**: System MUST produce hOCR output format from EasyOCR results for consistency with other engines
- **FR-021**: System MUST handle GPU availability gracefully - if GPU requested but not available, fall back to CPU with warning logged
- **FR-022**: System MUST isolate EasyOCR-specific processing logic following the same pattern as Tesseract and ocrmac engines
- **FR-023**: System MUST store EasyOCR model files in a configurable persistent volume with a default size limit of 5GB to prevent unbounded disk usage
- **FR-024**: System MUST limit concurrent GPU-enabled EasyOCR jobs to a maximum of 2 simultaneous executions to prevent GPU memory exhaustion
- **FR-025**: System MUST queue additional GPU-enabled EasyOCR job requests when the concurrency limit is reached, processing them in FIFO order as slots become available
- **FR-026**: System MUST validate EasyOCR model file integrity using checksums at startup and before first use of each language, returning HTTP 500 with re-download instructions if validation fails

### Key Entities

- **OCR Engine** (extended): Now includes "easyocr" as a third engine type; attributes include engine type, platform requirements, supported parameters, availability status, GPU support
- **EasyOCR Configuration**: Represents EasyOCR-specific parameters; attributes include language codes array (EasyOCR naming: en, ch_sim, ch_tra, ja, ko, etc.), gpu flag (boolean), text_threshold (float 0.0-1.0), link_threshold (float 0.0-1.0)
- **Engine Configuration** (extended): Existing entity now supports EasyOCR configuration alongside Tesseract and ocrmac configurations
- **OCR Job** (extended): Existing job entity now includes support for EasyOCR engine type and configuration

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can successfully process documents using EasyOCR engine with appropriate parameters (languages, gpu, thresholds)
- **SC-002**: System correctly rejects 100% of engine-parameter mismatches (e.g., Tesseract/ocrmac params with EasyOCR engine, EasyOCR params with other engines) with clear error messages
- **SC-003**: System correctly handles GPU availability - gracefully falls back to CPU when GPU requested but not available
- **SC-004**: Processing completes within 30 seconds for 95% of single-page documents (performance target), with hard timeout of 60 seconds per page
- **SC-005**: Recognition accuracy for EasyOCR on multilingual documents (especially Asian languages) is comparable to or better than Tesseract (within 5% difference on benchmark datasets)
- **SC-006**: All existing API clients continue to work without modification (100% backward compatibility - defaults to Tesseract)
- **SC-007**: API response time for engine validation remains under 100ms (validation happens synchronously during upload)
- **SC-008**: Documentation clearly lists EasyOCR and its specific parameters, maintaining consistency with existing engine documentation
- **SC-009**: All OCR jobs using EasyOCR include engine type and parameters in structured logs, enabling debugging of 100% of engine-related issues
- **SC-010**: GPU-accelerated EasyOCR processing is at least 50% faster than CPU-only processing for complex documents (when GPU available)
- **SC-011**: Operational metrics (processing time, GPU/CPU mode, language count, queue wait time, model load time) are captured for 100% of EasyOCR jobs to enable performance monitoring and capacity planning

## Assumptions *(mandatory)*

- EasyOCR library can be installed via pip and is compatible with the Python version used by the project
- EasyOCR model files can be stored in a configurable persistent volume with 5GB default capacity, sufficient for typical language combinations (average model size ~100-200MB per language)
- EasyOCR provides checksums or a reliable mechanism to validate model file integrity
- Users understand that EasyOCR uses deep learning models which may have different characteristics than Tesseract/ocrmac
- Most users will continue using Tesseract (default); EasyOCR is for users needing superior multilingual support
- EasyOCR produces text and bounding box information that can be converted to hOCR format for consistency
- GPU support is optional - system must work in CPU-only environments
- GPU memory is limited; concurrent GPU-enabled EasyOCR jobs are capped at 2 to prevent out-of-memory errors while maintaining reasonable throughput
- Service availability is prioritized over individual engine availability - service starts even if EasyOCR detection fails, allowing other engines to function
- Different engines may produce slightly different results for the same document due to different algorithms
- EasyOCR language naming convention is different from Tesseract (3-letter) and ocrmac (2-letter) - users can reference documentation
- Engine-specific parameters are validated independently - no cross-engine parameter validation needed
- EasyOCR model downloads happen during installation/initialization, not during request processing
- Adding EasyOCR follows the same parameter isolation pattern as established with Tesseract and ocrmac

## Dependencies

- Requires EasyOCR Python library to be installed (pip install easyocr)
- Requires PyTorch dependency (EasyOCR's underlying framework)
- Requires EasyOCR model files to be downloaded for each language used
- Requires configurable persistent volume for EasyOCR model storage (default 5GB capacity)
- Requires abstraction layer to support third engine (extending existing multi-engine architecture)
- Requires updates to OpenAPI specification to document EasyOCR parameters
- Requires updates to validation logic to handle EasyOCR-specific parameter sets
- Requires testing infrastructure for EasyOCR engine alongside Tesseract and ocrmac
- May require GPU drivers and CUDA toolkit for GPU acceleration (optional)
- Requires conversion logic from EasyOCR output format to hOCR format

## Out of Scope

- Automatic engine selection based on document language detection
- Automatic GPU vs CPU selection based on availability (user must explicitly choose via gpu parameter)
- Converting parameters between engines (e.g., mapping Tesseract OEM to EasyOCR equivalents)
- Cloud-based OCR engines (Google Vision, Azure OCR, AWS Textract)
- Engine fallback mechanisms (trying alternate engine if primary fails)
- Engine capability discovery API endpoints
- Real-time engine health monitoring or availability status endpoints
- Mixed-engine processing (using different engines for different pages)
- Custom EasyOCR model training or fine-tuning
- Automatic EasyOCR model download during request processing (models must be pre-installed)
- Paragraph detection or reading order optimization (use EasyOCR's default behavior)
- Support for EasyOCR's experimental features or unstable APIs
