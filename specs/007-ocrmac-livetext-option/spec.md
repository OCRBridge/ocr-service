# Feature Specification: Add LiveText Recognition Level to ocrmac Engine

**Feature Branch**: `007-ocrmac-livetext-option`
**Created**: 2025-10-20
**Status**: Draft
**Input**: User description: "Add lifetext option to ocrmac engine."

## Clarifications

### Session 2025-10-20

- Q: What happens when a user specifies `recognition_level=livetext` on a system where the ocrmac library version doesn't support the framework parameter? → A: Return HTTP 500 (Internal Server Error) with message indicating ocrmac library version incompatibility
- Q: What logging and metrics should be collected for livetext recognition level? → A: Log framework type (vision vs livetext) and collect same metrics as existing levels (duration, success/failure, timeouts) with "livetext" label
- Q: How does the system handle when LiveText processing returns unexpected output format? → A: Log error with output sample (first 500 chars) and return HTTP 500 with message about unexpected format

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic LiveText OCR Processing (Priority: P1)

As an API user, I want to process documents using Apple's LiveText framework (available in macOS Sonoma+) by specifying `recognition_level=livetext`, so that I can benefit from the enhanced OCR accuracy and performance that LiveText provides.

**Why this priority**: This is the core functionality - enabling LiveText as a recognition level option. Without this, the feature provides no value. It's the minimum viable product that delivers immediate value to users on compatible systems.

**Independent Test**: Can be fully tested by sending a POST request to `/sync/ocrmac` or `/upload/ocrmac` with `recognition_level=livetext` parameter and validating that the OCR output uses Apple's LiveText framework.

**Acceptance Scenarios**:

1. **Given** a user on macOS Sonoma+ with a JPEG image, **When** they POST to `/sync/ocrmac` with `recognition_level=livetext`, **Then** the system returns HTTP 200 with hOCR output processed using LiveText framework
2. **Given** a user on macOS Sonoma+ with a PNG image, **When** they POST to `/upload/ocrmac` with `recognition_level=livetext`, **Then** the system accepts the request (HTTP 202) and processes it asynchronously using LiveText
3. **Given** a user with a PDF document, **When** they request processing with `recognition_level=livetext`, **Then** each page is converted to images and processed with LiveText framework
4. **Given** a user specifies `recognition_level=livetext` with language parameters, **When** the request is processed, **Then** the language preferences are honored by the LiveText framework

---

### User Story 2 - Platform Compatibility Validation (Priority: P2)

As an API user on an older macOS version (pre-Sonoma), I want to receive a clear error message when I try to use `recognition_level=livetext`, so that I understand why the option isn't available and can choose an alternative recognition level.

**Why this priority**: Essential for good user experience and preventing confusion. Users on incompatible systems need clear feedback rather than cryptic errors. This is P2 because P1 delivers value to compatible systems, but this ensures the feature doesn't break existing functionality.

**Independent Test**: Can be tested by mocking the macOS version detection to simulate pre-Sonoma systems and verifying appropriate error responses.

**Acceptance Scenarios**:

1. **Given** a user on macOS version prior to Sonoma, **When** they request `recognition_level=livetext`, **Then** the system returns HTTP 400 with error message "LiveText recognition requires macOS Sonoma (14.0) or later"
2. **Given** a user on non-macOS platform (Linux/Windows), **When** they request `recognition_level=livetext`, **Then** the system returns HTTP 400 indicating ocrmac is only available on macOS
3. **Given** the system detects an incompatible macOS version, **When** the error is returned, **Then** the error message suggests alternative recognition levels (fast, balanced, accurate)

---

### User Story 3 - Backward Compatibility and Consistency (Priority: P3)

As an existing API user, I want the existing recognition levels (fast, balanced, accurate) to continue working unchanged when LiveText is added, so that my existing integrations are not disrupted.

**Why this priority**: Important for maintaining stability and preventing regressions, but P3 because if implemented correctly, this should happen automatically without special effort. It's more of a validation priority than a functional development priority.

**Independent Test**: Can be tested by running existing test suites for fast/balanced/accurate recognition levels and verifying all tests continue to pass.

**Acceptance Scenarios**:

1. **Given** a user requests `recognition_level=fast`, **When** the request is processed, **Then** the system uses the Vision framework with fast recognition (unchanged from current behavior)
2. **Given** a user requests `recognition_level=balanced`, **When** the request is processed, **Then** the system uses the Vision framework with balanced recognition (unchanged from current behavior)
3. **Given** a user requests `recognition_level=accurate`, **When** the request is processed, **Then** the system uses the Vision framework with accurate recognition (unchanged from current behavior)
4. **Given** a user requests processing without specifying recognition_level, **When** the request is processed, **Then** the system defaults to balanced recognition level (unchanged from current behavior)

---

### Edge Cases

- **Unsupported ocrmac library version**: When `recognition_level=livetext` is requested but the ocrmac library version doesn't support the framework parameter, the system returns HTTP 500 with error message indicating library version incompatibility and required version
- **Unexpected LiveText output format**: When LiveText processing returns output in an unexpected format, the system logs error with output sample (first 500 characters) and returns HTTP 500 with message indicating unexpected format
- **Invalid recognition level value**: When a user specifies an invalid recognition level value (e.g., "livetextt" with typo), the system returns HTTP 400 with validation error listing valid options (fast, balanced, accurate, livetext)
- **Large image processing**: When processing images exceeding 5MB with LiveText, behavior follows existing file size validation (rejected before processing begins)
- **Processing timeout**: When LiveText processing exceeds 30 second limit for sync endpoint, system returns HTTP 408 (Request Timeout) consistent with existing timeout handling for other recognition levels

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST extend the RecognitionLevel enum to include "livetext" as a valid option
- **FR-002**: System MUST pass `framework="livetext"` to the ocrmac library when recognition_level is set to "livetext"
- **FR-003**: System MUST detect the macOS version and return HTTP 400 error when livetext is requested on macOS versions prior to Sonoma (14.0)
- **FR-004**: System MUST maintain backward compatibility with existing recognition levels (fast, balanced, accurate)
- **FR-005**: System MUST support livetext recognition level on both `/sync/ocrmac` and `/upload/ocrmac` endpoints
- **FR-006**: System MUST accept language parameters with livetext recognition level and pass them to the LiveText framework
- **FR-007**: System MUST convert LiveText output to hOCR format, maintaining consistency with other recognition levels
- **FR-008**: System MUST handle the fact that LiveText always returns confidence=1 in the hOCR output
- **FR-009**: System MUST include appropriate metadata in hOCR output indicating LiveText framework was used
- **FR-010**: System MUST validate that livetext is only used with the ocrmac engine (not with tesseract or easyocr)
- **FR-011**: System MUST update OpenAPI schema to include "livetext" as a valid enum value for recognition_level
- **FR-012**: API documentation MUST clearly indicate that livetext requires macOS Sonoma or later
- **FR-013**: System MUST return HTTP 500 with descriptive error message when livetext is requested but the ocrmac library version doesn't support the framework parameter
- **FR-014**: System MUST log error with output sample (first 500 characters) and return HTTP 500 when LiveText processing returns unexpected output format

### Non-Functional Requirements

- **NFR-001**: LiveText processing performance should be comparable to existing recognition levels (approximately 174ms per image)
- **NFR-002**: Error messages for platform incompatibility must be clear and actionable
- **NFR-003**: The implementation must not introduce breaking changes to existing API contracts
- **NFR-004**: System MUST log framework type (vision vs livetext) for all ocrmac processing requests
- **NFR-005**: System MUST collect metrics for livetext using the same metric names as other recognition levels (processing duration, success/failure counts, timeout counts) with engine label set to "ocrmac" and recognition_level label set to "livetext"

### Key Entities *(include if feature involves data)*

- **RecognitionLevel Enum**: Enumeration of OCR recognition quality levels, extended to include: fast, balanced, accurate, and livetext
- **OcrmacParams**: Parameter model for ocrmac engine requests, containing languages (list of IETF BCP 47 codes) and recognition_level (enum value)
- **hOCR Output**: Structured XML format containing OCR results with word-level bounding boxes and confidence scores (always 1.0 for livetext)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users on macOS Sonoma+ can successfully process documents with `recognition_level=livetext` and receive hOCR output
- **SC-002**: LiveText processing completes within 30 seconds for images under 5MB (sync endpoint timeout)
- **SC-003**: Users on incompatible macOS versions receive clear HTTP 400 error messages explaining the requirement
- **SC-004**: All existing tests for fast/balanced/accurate recognition levels continue to pass without modification
- **SC-005**: OpenAPI specification correctly documents livetext as a valid recognition_level option with platform requirements
- **SC-006**: LiveText processing produces valid hOCR XML that passes existing schema validation
- **SC-007**: Language preferences specified with livetext are honored by the underlying LiveText framework
- **SC-008**: Both sync and async endpoints support livetext with consistent behavior and response formats

## Assumptions & Constraints

### Assumptions

1. Users have ocrmac library version that supports the `framework` parameter (version with LiveText support)
2. macOS Sonoma detection can be reliably performed using platform and version checks
3. LiveText framework is available and functional when macOS Sonoma or later is detected
4. LiveText output format is compatible with the existing hOCR conversion logic
5. The performance characteristics from the ocrmac library documentation (174ms average) are representative of real-world usage

### Constraints

- **Platform Limitation**: LiveText is only available on macOS Sonoma (14.0) or later
- **Confidence Values**: LiveText always returns confidence=1, unlike other recognition levels which return quantized confidence scores from Vision framework
- **Library Dependency**: Requires compatible version of ocrmac Python library with framework parameter support
- **Docker Limitation**: LiveText will not work in Docker containers (same as existing ocrmac limitation - requires native macOS environment)

### Out of Scope

- Automatic fallback from livetext to other recognition levels on incompatible systems
- Custom confidence score calculation for LiveText output
- Support for framework selection independent of recognition level
- Performance optimization specifically for LiveText (beyond what ocrmac library provides)
- Comparison/benchmarking tools between recognition levels

## Dependencies

- **External**: ocrmac Python library (version with `framework="livetext"` support)
- **Platform**: macOS Sonoma (14.0) or later with Apple's LiveText framework
- **Internal**: Existing ocrmac engine implementation and hOCR conversion logic

## Open Questions

None - all clarifications have been resolved through user feedback.
