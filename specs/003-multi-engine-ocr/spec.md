# Feature Specification: Multi-Engine OCR Support

**Feature Branch**: `003-multi-engine-ocr`
**Created**: 2025-10-18
**Status**: Draft
**Input**: User description: "Add ocrmac as another option for an OCR engine. The user can choose which engine should perform OCR. Each engine has its own parameters."

## Clarifications

### Session 2025-10-18

- Q: What language code format should ocrmac use (ISO 639-1 2-letter vs ISO 639-3 3-letter like Tesseract)? → A: ISO 639-1 2-letter codes (en, fr, de) - more common, matches examples in spec
- Q: What is the maximum number of languages allowed for ocrmac in a single request? → A: Same as Tesseract (5 languages maximum) - consistent limits across engines
- Q: What happens when an engine becomes unavailable between upload validation and actual processing? → A: Fail the job immediately with clear error message indicating which engine is unavailable
- Q: What are the OCR processing timeout limits and what happens when they are exceeded? → A: 60 seconds per page with job failure on timeout - allows headroom beyond performance target
- Q: How are engine capabilities discovered and validated at runtime versus configuration time? → A: Runtime detection with startup cache - detect at startup, cache, validate against cache

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Engine Selection for macOS Users (Priority: P1)

A macOS user wants to use the native ocrmac engine for faster, more accurate OCR processing of their documents instead of the default Tesseract engine, taking advantage of Apple's Vision framework optimizations.

**Why this priority**: This is the core value proposition - enabling users to choose between engines based on their platform, performance needs, and accuracy requirements. Without engine selection, users cannot leverage platform-specific optimizations.

**Independent Test**: Can be fully tested by uploading a document with `engine=ocrmac` parameter on a macOS system, then verifying the OCR results use ocrmac and return accurate text. Delivers immediate value by supporting platform-specific engines.

**Acceptance Scenarios**:

1. **Given** a user on macOS with ocrmac installed, **When** they upload a document with `engine=ocrmac` parameter, **Then** the system uses ocrmac for processing and returns accurate OCR results
2. **Given** a user does not specify an engine parameter, **When** they upload a document, **Then** the system defaults to Tesseract (preserving backward compatibility)
3. **Given** a user specifies an invalid engine name, **When** they submit the upload request, **Then** the system returns HTTP 400 error listing available engines
4. **Given** a user on a non-macOS platform requests ocrmac, **When** they submit the upload, **Then** the system returns HTTP 400 error indicating ocrmac is only available on macOS

---

### User Story 2 - Tesseract with Custom Parameters (Priority: P1)

A user chooses Tesseract as their OCR engine and wants to configure Tesseract-specific parameters (language, PSM, OEM, DPI) to optimize recognition for their specific document type.

**Why this priority**: Existing Tesseract users (from feature 002-tesseract-params) must retain full parameter control when explicitly selecting Tesseract engine. This ensures backward compatibility and preserves advanced configuration capabilities.

**Independent Test**: Can be tested by uploading a French document with `engine=tesseract`, `lang=fra`, `psm=6` and verifying French text recognition with correct page segmentation. Delivers value through continued support for advanced Tesseract features.

**Acceptance Scenarios**:

1. **Given** a user selects Tesseract engine, **When** they upload with `engine=tesseract&lang=spa&psm=6`, **Then** the system processes using Tesseract with Spanish language and specified PSM mode
2. **Given** a user selects Tesseract but omits language parameter, **When** they upload, **Then** the system defaults to English (lang=eng) as currently implemented
3. **Given** a user selects Tesseract with invalid parameters, **When** they submit the upload, **Then** the system returns HTTP 400 error with Tesseract-specific parameter validation messages
4. **Given** a user omits engine parameter but provides Tesseract parameters (lang, psm, oem, dpi), **When** they upload, **Then** the system uses Tesseract by default and applies the specified parameters (backward compatibility)

---

### User Story 3 - ocrmac with Language Selection (Priority: P2)

A user chooses ocrmac as their OCR engine and wants to specify which language(s) the engine should recognize for optimal accuracy with multilingual documents.

**Why this priority**: Language selection is critical for accuracy with non-English documents. While ocrmac has different capabilities than Tesseract, language specification is still a key parameter for many users.

**Independent Test**: Can be tested by uploading a German document with `engine=ocrmac&languages=de` and verifying accurate German text recognition. Delivers value by supporting multilingual ocrmac processing.

**Acceptance Scenarios**:

1. **Given** a user selects ocrmac engine, **When** they upload with `engine=ocrmac&languages=de`, **Then** the system processes using ocrmac with German language recognition
2. **Given** a user selects ocrmac with multiple languages, **When** they upload with `languages=en,fr`, **Then** the system recognizes both English and French text
3. **Given** a user selects ocrmac but omits language parameter, **When** they upload, **Then** the system uses automatic language detection (ocrmac default behavior)
4. **Given** a user selects ocrmac with unsupported language codes, **When** they submit the upload, **Then** the system returns HTTP 400 error listing valid language codes for ocrmac
5. **Given** a user selects ocrmac with more than 5 languages, **When** they submit the upload, **Then** the system returns HTTP 400 error indicating the maximum of 5 languages allowed

---

### User Story 4 - ocrmac with Recognition Level Control (Priority: P2)

A user chooses ocrmac and wants to specify the recognition level (fast vs. accurate) to balance processing speed against accuracy based on their use case.

**Why this priority**: Provides ocrmac-specific optimization control similar to Tesseract's OEM parameter. Important for users who need fast processing for simple documents or maximum accuracy for complex ones.

**Independent Test**: Can be tested by uploading the same document twice with `engine=ocrmac&recognition_level=fast` and `recognition_level=accurate`, comparing processing times and accuracy. Delivers value through performance tuning.

**Acceptance Scenarios**:

1. **Given** a user selects ocrmac for simple documents, **When** they upload with `engine=ocrmac&recognition_level=fast`, **Then** processing completes quickly with acceptable accuracy
2. **Given** a user selects ocrmac for complex documents, **When** they upload with `engine=ocrmac&recognition_level=accurate`, **Then** recognition accuracy is maximized at the cost of processing time
3. **Given** a user selects ocrmac with invalid recognition level, **When** they submit the upload, **Then** the system returns HTTP 400 error listing valid options (fast, balanced, accurate)
4. **Given** a user selects ocrmac without specifying recognition level, **When** they upload, **Then** the system uses "balanced" as the default

---

### User Story 5 - Parameter Isolation Between Engines (Priority: P3)

A user wants to understand which parameters apply to each engine and receive clear errors when they specify parameters incompatible with their selected engine.

**Why this priority**: Prevents user confusion and invalid parameter combinations. Less critical than core functionality but important for good user experience and API clarity.

**Independent Test**: Can be tested by uploading with `engine=ocrmac&psm=6` (Tesseract-only parameter) and verifying the system returns HTTP 400 error explaining PSM is not valid for ocrmac. Delivers value through clear API contract.

**Acceptance Scenarios**:

1. **Given** a user selects ocrmac engine, **When** they specify Tesseract-only parameters (psm, oem, dpi), **Then** the system returns HTTP 400 error indicating these parameters are not valid for ocrmac
2. **Given** a user selects Tesseract engine, **When** they specify ocrmac-only parameters (recognition_level), **Then** the system returns HTTP 400 error indicating these parameters are not valid for Tesseract
3. **Given** a user requests API documentation, **When** they view parameter descriptions, **Then** each parameter clearly indicates which engine(s) it applies to
4. **Given** a user specifies no engine, **When** they provide engine-specific parameters, **Then** the system infers the correct engine or defaults to Tesseract with clear behavior documentation

---

### Edge Cases

- When a user specifies `engine=ocrmac` on a non-macOS system (Linux, Windows), the system returns HTTP 400 error immediately indicating ocrmac is only available on macOS platforms
- When ocrmac is specified but the ocrmac binary is not installed or executable on the macOS system, the system returns HTTP 500 error with installation instructions
- When a user specifies conflicting parameters for the selected engine (e.g., Tesseract PSM with ocrmac engine), the system rejects with HTTP 400 listing incompatible parameters
- When a user omits the engine parameter but provides parameters that belong to multiple different engines, the system returns HTTP 400 error requesting explicit engine selection
- When a user switches engines between multiple uploads of the same document, each job must be independently processable with its specified engine
- When an engine fails during processing (crash, timeout), the error message must clearly indicate which engine failed
- When OCR processing exceeds 60 seconds per page for either engine, the job fails with a timeout error indicating which page and engine exceeded the limit
- When an engine that was available at upload time becomes unavailable during processing (e.g., ocrmac uninstalled, service restart), the job fails immediately with a clear error message indicating which engine is unavailable
- Engine capabilities (available languages, supported features) are detected at system startup by querying each engine and cached in memory for request validation; cache refreshes on service restart
- How does the system handle engine version differences across deployments (e.g., different Tesseract versions, different ocrmac capabilities)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept an optional `engine` parameter specifying which OCR engine to use (valid values: "tesseract", "ocrmac")
- **FR-002**: System MUST default to Tesseract engine when the `engine` parameter is omitted (backward compatibility)
- **FR-003**: System MUST validate the `engine` parameter value and return HTTP 400 error for invalid engine names, listing available engines
- **FR-004**: System MUST validate engine availability on the current platform (e.g., reject ocrmac requests on non-macOS systems with HTTP 400)
- **FR-005**: System MUST accept Tesseract-specific parameters (lang, psm, oem, dpi) when engine is Tesseract or default
- **FR-006**: System MUST accept ocrmac-specific parameters (languages, recognition_level) when engine is ocrmac, with a maximum of 5 languages per request
- **FR-007**: System MUST reject requests that specify parameters incompatible with the selected engine, returning HTTP 400 with clear explanation of which parameters are valid for the selected engine
- **FR-008**: System MUST support language specification for both engines using engine-appropriate parameter names (lang for Tesseract, languages for ocrmac)
- **FR-009**: System MUST validate language codes against engine-specific supported languages and return HTTP 400 if unsupported (Tesseract uses ISO 639-3 3-letter codes like "eng", "fra"; ocrmac uses ISO 639-1 2-letter codes like "en", "fr")
- **FR-009a**: System MUST reject requests with more than 5 languages for either engine with HTTP 400 error indicating the maximum allowed
- **FR-010**: System MUST include engine type and all engine-specific parameters in job metadata for debugging and reproducibility
- **FR-011**: System MUST log engine selection and all parameters in structured JSON format with job ID correlation
- **FR-012**: System MUST preserve deterministic processing - same document with same engine and parameters produces identical results
- **FR-013**: System MUST document available engines and their parameters in API documentation
- **FR-014**: System MUST support ocrmac recognition levels (fast, balanced, accurate) with "balanced" as default when ocrmac is selected
- **FR-015**: System MUST maintain backward compatibility - existing requests without engine parameter continue to work with Tesseract
- **FR-016**: System MUST validate engine availability during upload validation (synchronously) to fail fast
- **FR-016a**: System MUST detect engine capabilities (available languages, supported features) at startup by querying each engine and cache the results in memory for request validation
- **FR-017**: System MUST return descriptive error messages indicating which engine was requested and why it's unavailable
- **FR-017a**: System MUST fail jobs immediately with clear error messages when the selected engine becomes unavailable between upload and processing (no automatic fallback to alternative engines)
- **FR-017b**: System MUST enforce a 60-second timeout per page for OCR processing and fail jobs that exceed this limit with a clear timeout error message
- **FR-018**: System MUST isolate engine-specific processing logic to enable future engine additions without affecting existing engines

### Key Entities

- **OCR Engine**: Represents an available OCR processing engine; attributes include engine type (tesseract, ocrmac), platform requirements, supported parameters, availability status
- **Engine Configuration**: Represents engine-specific parameters for a job; attributes include engine type, parameter name-value pairs, validation status
- **Tesseract Configuration** (existing): Represents Tesseract-specific parameters; attributes include language code(s), PSM, OEM, DPI
- **ocrmac Configuration**: Represents ocrmac-specific parameters; attributes include language codes array (ISO 639-1 2-letter format: en, fr, de, etc.), recognition level (fast/balanced/accurate)
- **OCR Job** (extended): Existing job entity now includes engine type and engine-specific configuration; enables reproducibility across different engines

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users on macOS can successfully process documents using ocrmac engine with appropriate parameters
- **SC-002**: Users can successfully process documents using Tesseract engine with all existing parameters (backward compatibility: 100% of existing functionality preserved)
- **SC-003**: System correctly rejects 100% of engine-parameter mismatches (e.g., Tesseract params with ocrmac engine) with clear error messages
- **SC-004**: System correctly rejects 100% of platform-incompatible engine requests (e.g., ocrmac on Linux) with clear error messages
- **SC-004a**: Processing completes within 30 seconds for 95% of single-page documents (performance target), with hard timeout of 60 seconds per page
- **SC-005**: Processing time for ocrmac engine is at least 20% faster than Tesseract for simple documents (leveraging platform optimizations)
- **SC-006**: Recognition accuracy for ocrmac on macOS is comparable to or better than Tesseract (within 5% difference on benchmark datasets)
- **SC-007**: All existing API clients continue to work without modification (100% backward compatibility)
- **SC-008**: API response time for engine validation remains under 100ms (validation happens synchronously during upload)
- **SC-009**: Documentation clearly lists all engines and their specific parameters, reducing engine-related errors by 50%
- **SC-010**: All OCR jobs include engine type and parameters in structured logs, enabling debugging of 100% of engine-related issues

## Assumptions *(mandatory)*

- ocrmac is only available on macOS systems running macOS 10.15+ with Vision framework support
- Users understand the trade-offs between different OCR engines or can reference documentation
- Engine capabilities (availability, supported languages) can be detected reliably at startup through engine queries without significant performance impact
- Most users will continue using Tesseract (default); ocrmac is for macOS users seeking optimization
- Engine-specific parameters are validated independently - no cross-engine parameter validation needed
- Each engine produces output in the same format (HOCR) for consistent downstream processing
- Engine failures are distinct from parameter validation failures and are handled separately
- Users accept that different engines may produce slightly different results for the same document
- Platform detection (OS type) is reliable for determining ocrmac availability
- Adding new engines in the future should follow the same parameter isolation pattern

## Dependencies

- Requires ocrmac binary to be installed on macOS deployment environments
- Requires detection of operating system platform to validate ocrmac availability
- Requires abstraction layer to isolate engine-specific processing logic
- Requires updates to OpenAPI specification to document engine parameter
- Requires updates to validation logic to handle engine-specific parameter sets
- Requires testing infrastructure for both Tesseract and ocrmac engines
- May require conditional deployment configurations for platforms that don't support ocrmac

## Out of Scope

- Automatic engine selection based on document characteristics or platform
- Engine performance benchmarking or comparison tools
- Converting parameters between engines (e.g., mapping Tesseract PSM to ocrmac equivalents)
- Supporting more than two engines in this initial implementation
- Cloud-based OCR engines (Google Vision, Azure OCR, AWS Textract)
- Engine fallback mechanisms (trying alternate engine if primary fails)
- Engine capability discovery API endpoints
- Real-time engine health monitoring or availability status endpoints
- Mixed-engine processing (using different engines for different pages)
- Engine-specific output format differences (all engines must produce HOCR)
