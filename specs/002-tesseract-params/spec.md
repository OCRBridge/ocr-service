# Feature Specification: Configurable Tesseract OCR Parameters

**Feature Branch**: `002-tesseract-params`
**Created**: 2025-10-18
**Status**: Draft
**Input**: User description: "Expose tesseract arguments as parameters for the endpoint."

## Clarifications

### Session 2025-10-18

- Q: When a user specifies a valid language code (e.g., `lang=fra`) but the corresponding Tesseract language data file is not installed on the server, how should the system respond? → A: Return clear error immediately during upload validation (HTTP 400) listing available languages
- Q: When a user specifies conflicting parameter combinations (e.g., PSM and OEM values that are incompatible with each other or the Tesseract version), how should the system respond? → A: Reject immediately with HTTP 400 error listing incompatible combinations
- Q: When a user specifies multiple languages (e.g., `lang=eng+fra+deu+spa`), what is the maximum number of languages allowed in a single request? → A: Maximum 5 languages per request
- Q: How should the system track and log parameter usage for debugging and operational monitoring? → A: Log parameter values in structured JSON logs with job ID
- Q: How should the system protect against malicious input or injection attacks through parameter values (e.g., command injection, path traversal attempts)? → A: Strict whitelist validation with regex patterns for allowed characters and formats

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Custom Language Selection (Priority: P1)

A user needs to process documents in languages other than English (e.g., Spanish, French, German, Chinese) and wants to specify which language model Tesseract should use for optimal recognition accuracy.

**Why this priority**: This is the most critical parameter that directly impacts OCR accuracy for non-English documents. Without language selection, users with multilingual documents cannot get accurate results. This delivers immediate value for international use cases.

**Independent Test**: Can be fully tested by uploading a document with French text and specifying `lang=fra`, then verifying the OCR results are accurate. Delivers value by supporting multiple languages.

**Acceptance Scenarios**:

1. **Given** a user has a document in Spanish, **When** they upload it with `lang=spa` parameter, **Then** the system uses the Spanish language model and returns accurate Spanish text recognition
2. **Given** a user has a document with mixed English and French text, **When** they upload it with `lang=eng+fra` parameter, **Then** the system recognizes both languages accurately
3. **Given** a user specifies an invalid language code, **When** they submit the upload request, **Then** the system returns a clear error message listing supported languages
4. **Given** a user omits the language parameter, **When** they upload a document, **Then** the system defaults to English (`eng`) as currently implemented

---

### User Story 2 - Page Segmentation Mode Control (Priority: P2)

A user needs to process documents with specific layouts (single column, multi-column, single word, single character) and wants to specify the appropriate page segmentation mode (PSM) to improve recognition accuracy for their specific document type.

**Why this priority**: PSM significantly affects accuracy for specialized document types (receipts, business cards, forms). While not as universally needed as language selection, it's critical for users with non-standard layouts.

**Independent Test**: Can be tested by uploading a single-word image with `psm=8` (treat as single word) and verifying better accuracy than default mode. Delivers value for specialized document types.

**Acceptance Scenarios**:

1. **Given** a user has a business card with sparse text, **When** they upload it with `psm=6` (assume uniform block of text), **Then** the system correctly segments the text blocks
2. **Given** a user has a document with a single line of text, **When** they upload it with `psm=7` (treat as single line), **Then** recognition accuracy improves compared to default multi-line mode
3. **Given** a user specifies an invalid PSM value, **When** they submit the upload, **Then** the system returns an error with the valid PSM range (0-13)
4. **Given** a user omits the PSM parameter, **When** they upload a document, **Then** the system uses Tesseract's default automatic page segmentation

---

### User Story 3 - OCR Engine Mode Selection (Priority: P3)

A user wants to control which OCR engine mode Tesseract uses (legacy, neural network LSTM, or combined) to balance speed versus accuracy based on their specific requirements.

**Why this priority**: Provides advanced control for users who understand trade-offs between speed and accuracy. Less critical than language and PSM but useful for performance optimization.

**Independent Test**: Can be tested by uploading the same document with `oem=0` (legacy) and `oem=1` (LSTM) and comparing processing times and accuracy. Delivers value through performance tuning.

**Acceptance Scenarios**:

1. **Given** a user needs fast processing for simple documents, **When** they upload with `oem=0` (legacy engine), **Then** processing completes faster with acceptable accuracy for clear text
2. **Given** a user needs maximum accuracy for complex documents, **When** they upload with `oem=1` (LSTM neural network), **Then** recognition accuracy is maximized at the cost of processing time
3. **Given** a user specifies an invalid OEM value, **When** they submit the upload, **Then** the system returns an error with valid OEM options (0-3)
4. **Given** a user omits the OEM parameter, **When** they upload a document, **Then** the system uses the default LSTM engine (OEM 1)

---

### User Story 4 - DPI Configuration (Priority: P3)

A user has scanned images at non-standard resolutions and wants to specify the DPI (dots per inch) value to help Tesseract correctly interpret character sizes and improve recognition accuracy.

**Why this priority**: Important for handling images from various sources with different resolutions, but less frequently needed than language or PSM settings. Tesseract can often auto-detect DPI.

**Independent Test**: Can be tested by uploading a low-resolution scan with `dpi=150` and verifying improved character recognition compared to auto-detection. Delivers value for non-standard scans.

**Acceptance Scenarios**:

1. **Given** a user has a low-resolution scan (150 DPI), **When** they upload with `dpi=150`, **Then** Tesseract correctly interprets character sizes
2. **Given** a user has a high-resolution scan (600 DPI), **When** they upload with `dpi=600`, **Then** recognition accuracy is optimized for the resolution
3. **Given** a user specifies an invalid DPI value (e.g., negative or extremely high), **When** they submit the upload, **Then** the system returns an error with acceptable DPI range (70-2400)
4. **Given** a user omits the DPI parameter, **When** they upload a document, **Then** the system uses the default DPI value (300) or auto-detects from image metadata

---

### Edge Cases

- When a user specifies a valid language code but the language data file is not installed, the system returns HTTP 400 error immediately during upload validation with a message listing available installed languages
- When multiple conflicting parameters are specified (e.g., PSM and OEM combinations incompatible with each other or the Tesseract version), the system rejects the upload immediately with HTTP 400 error listing which combinations are incompatible and why
- When a user specifies more than 5 languages in a single request, the system rejects with HTTP 400 error indicating the maximum limit
- When a user attempts malicious input (command injection, path traversal, special characters), the system rejects with HTTP 400 error using strict whitelist validation with regex patterns before any processing occurs
- How does the system handle parameter values that are technically valid but result in poor OCR performance?
- What happens when a user specifies parameters for one language but uploads a document in a different language?
- How are parameter errors reported - before job creation or during processing?
- What happens when a user changes parameters for the same document and submits multiple jobs?
- How does the system handle deprecated Tesseract parameters or version-specific parameters?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept an optional `lang` parameter specifying Tesseract language code(s) (e.g., "eng", "spa", "fra+eng") with a maximum of 5 languages per request
- **FR-002**: System MUST accept an optional `psm` parameter specifying page segmentation mode (0-13)
- **FR-003**: System MUST accept an optional `oem` parameter specifying OCR engine mode (0-3)
- **FR-004**: System MUST accept an optional `dpi` parameter specifying image resolution (70-2400)
- **FR-005**: System MUST validate all Tesseract parameters before accepting the upload and return clear error messages for invalid values
- **FR-005a**: System MUST use strict whitelist validation with regex patterns to validate parameter formats and reject any values containing characters outside allowed patterns (alphanumeric and '+' for lang codes, integers only for psm/oem/dpi)
- **FR-005b**: System MUST reject requests with more than 5 languages specified with HTTP 400 error indicating the maximum allowed
- **FR-006**: System MUST use parameter defaults that match current behavior when parameters are omitted (lang=eng, default PSM, default OEM, dpi=300)
- **FR-007**: System MUST return descriptive error messages when invalid parameter values are provided (e.g., "Invalid language code 'xyz'. Supported: eng, fra, deu, spa...")
- **FR-008**: System MUST document available parameter values in API documentation (supported languages, PSM modes, OEM modes)
- **FR-009**: System MUST validate language codes against installed Tesseract language data files and reject uploads with HTTP 400 error if language data is not available, listing all supported languages in the error message
- **FR-010**: System MUST include parameter values in job metadata for debugging and reproducibility
- **FR-010a**: System MUST log all Tesseract parameter values (lang, psm, oem, dpi) in structured JSON format with job ID correlation for debugging and operational monitoring (Constitution Principle 5)
- **FR-011**: System MUST preserve deterministic processing - same document with same parameters produces identical results (Constitution Principle 2)
- **FR-012**: System MUST validate that PSM and OEM combinations are compatible with the Tesseract version in use and reject incompatible combinations with HTTP 400 error explaining the conflict
- **FR-013**: System MUST reject parameter combinations that would result in processing failures before starting OCR, returning HTTP 400 with clear explanation of which combinations are invalid

### Key Entities

- **OCR Configuration**: Represents the Tesseract parameters for a job; attributes include language code(s), page segmentation mode (PSM), OCR engine mode (OEM), DPI setting, parameter validation status; logged in structured JSON format for debugging
- **OCR Job** (extended): Existing job entity now includes OCR configuration parameters; enables reproducibility and debugging by recording exact parameters used in both job metadata and structured logs with job ID correlation
- **Parameter Validation Result**: Represents validation outcome; attributes include valid/invalid status, error messages, suggested corrections, list of supported values

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can successfully process documents in at least 10 different languages by specifying the language parameter
- **SC-002**: Recognition accuracy for non-English documents improves by at least 20% when the correct language parameter is specified versus default English
- **SC-003**: System correctly rejects 100% of invalid parameter values with clear error messages before processing starts
- **SC-004**: Processing time remains under 30 seconds for single-page documents regardless of parameter combinations (maintaining existing performance budget)
- **SC-005**: Users can reproduce identical OCR results by resubmitting the same document with the same parameters (100% deterministic)
- **SC-006**: API response time for parameter validation remains under 100ms (validation happens synchronously during upload)
- **SC-007**: Documentation clearly lists all supported parameter values, reducing parameter-related errors by 50%
- **SC-008**: Users with specialized document types (receipts, forms, business cards) report improved accuracy when using appropriate PSM values
- **SC-009**: All OCR jobs include parameter values in structured logs, enabling debugging of 100% of parameter-related issues through log analysis
- **SC-010**: System rejects 100% of malicious input attempts (injection attacks, path traversal, invalid characters) through strict whitelist validation before any processing occurs

## Assumptions *(mandatory)*

- Users understand basic OCR concepts and Tesseract parameters, or can reference documentation
- Tesseract language data files for common languages are pre-installed on the server
- Parameter validation can be performed quickly without significantly impacting upload response time
- Most users will only need language parameter; advanced parameters (PSM, OEM) are for power users
- Default parameter values work well for 80% of use cases
- Users are willing to experiment with parameters to find optimal settings for their specific documents
- Invalid parameter combinations can be detected through validation rules without running actual OCR
- Parameter errors should be reported immediately during upload, not during processing
- Tesseract version and available features are stable across deployments

## Dependencies

- Requires Tesseract language data files for supported languages to be installed
- Requires knowledge of valid PSM and OEM values for the deployed Tesseract version
- May require Tesseract version detection to validate parameter compatibility
- Requires parameter validation logic to prevent incompatible combinations
- Requires documentation updates to list supported parameter values

## Out of Scope

- Auto-detection of optimal parameters based on document content
- Machine learning to recommend best parameters for a given document type
- Custom Tesseract configuration files or advanced parameters beyond lang/psm/oem/dpi
- Dynamic installation of additional language data files based on user requests
- Performance benchmarking tools to compare parameter combinations
- Parameter presets or templates (e.g., "receipt mode", "business card mode")
- Tesseract version upgrades or management
- Parameter impact analysis or recommendations in API responses
- Batch processing with different parameters for different pages
