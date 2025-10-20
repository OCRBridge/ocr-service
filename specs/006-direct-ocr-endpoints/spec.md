# Feature Specification: Direct OCR Processing Endpoints

**Feature Branch**: `006-direct-ocr-endpoints`
**Created**: 2025-10-19
**Status**: Draft
**Input**: User description: "Add endpoints for direct processing without having to check for the status in the queue. A client should be able to directly provide a document via REST API call and receive the HOCR output as result."

## Clarifications

### Session 2025-10-19

- Q: When a multi-page document times out during synchronous processing, what should the system return? → A: Clear timeout error with no partial results (for data integrity - prevents clients from processing incomplete data without realizing pages are missing)
- Q: How should the hOCR content be returned in the HTTP response body? → A: JSON object with hOCR as escaped string field (maintains API consistency with error responses)
- Q: What metrics should the system track for synchronous endpoint observability beyond basic logging? → A: Request count, latency percentiles, timeout rate, engine-specific success rate

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Synchronous Tesseract Processing (Priority: P1)

A developer integrating OCR into their application wants to submit a single-page document and receive the OCR results immediately in the same HTTP response, without the complexity of job status polling. They need a simple request-response flow for quick, interactive document processing.

**Why this priority**: This is the core value proposition - eliminating the async job queue complexity for simple use cases. Tesseract is cross-platform and the most common engine, making it the highest-priority synchronous endpoint. This delivers immediate value for the majority of users who process single-page documents.

**Independent Test**: Can be fully tested by posting a single-page PDF to the synchronous Tesseract endpoint and receiving hOCR in the response body within seconds. Delivers immediate value by simplifying the integration for simple use cases.

**Acceptance Scenarios**:

1. **Given** a user has a single-page document, **When** they POST to the synchronous Tesseract endpoint with the document, **Then** they receive hOCR output directly in the HTTP response body within 5 seconds
2. **Given** a user specifies Tesseract parameters (lang, psm, oem, dpi), **When** they POST to the synchronous endpoint, **Then** the system processes with those parameters and returns hOCR immediately
3. **Given** a user uploads a document that processes quickly, **When** they use the synchronous endpoint, **Then** they avoid the overhead of job creation, status polling, and result retrieval
4. **Given** a user's document contains no recognizable text, **When** they POST to the synchronous endpoint, **Then** they receive an empty or minimal hOCR structure immediately rather than an error

---

### User Story 2 - Synchronous EasyOCR Processing (Priority: P1)

A developer working with multilingual documents wants to use EasyOCR's GPU-accelerated processing and receive results immediately, particularly for languages that Tesseract handles poorly. They want the same simple request-response flow with EasyOCR's superior multilingual capabilities.

**Why this priority**: EasyOCR is the second most popular engine (after Tesseract) and provides critical capabilities for non-Latin scripts and multilingual documents. Making it available synchronously has equal value to Tesseract for users who need these capabilities.

**Independent Test**: Can be fully tested by posting a document with Chinese or Arabic text to the synchronous EasyOCR endpoint and receiving hOCR with accurate multilingual recognition in the response. Delivers value through immediate access to advanced multilingual OCR.

**Acceptance Scenarios**:

1. **Given** a user has a document with non-Latin text, **When** they POST to the synchronous EasyOCR endpoint with appropriate language parameters, **Then** they receive accurate hOCR output directly in the response
2. **Given** a user specifies multiple languages for EasyOCR, **When** they POST to the synchronous endpoint, **Then** the system recognizes text in all specified languages and returns hOCR immediately
3. **Given** a user needs GPU-accelerated processing, **When** they use the synchronous EasyOCR endpoint, **Then** processing completes faster than Tesseract for complex multilingual documents
4. **Given** a user omits language parameters, **When** they POST to the synchronous EasyOCR endpoint, **Then** the system uses default language settings and returns results immediately

---

### User Story 3 - Synchronous ocrmac Processing (Priority: P2)

A macOS developer wants to leverage Apple's Vision framework for fast, accurate OCR and receive results immediately without job polling. They value the platform-optimized performance of ocrmac and want the simplicity of synchronous processing.

**Why this priority**: While ocrmac is platform-specific (macOS only), users who have access to it benefit from superior performance and accuracy. This is P2 rather than P1 because it's limited to a single platform, but it's important for macOS users.

**Independent Test**: Can be fully tested by posting a document to the synchronous ocrmac endpoint on macOS and receiving hOCR with high confidence scores in under 2 seconds. Delivers value through platform-optimized synchronous processing.

**Acceptance Scenarios**:

1. **Given** a macOS user has a document, **When** they POST to the synchronous ocrmac endpoint, **Then** they receive hOCR output leveraging Apple's Vision framework in the response
2. **Given** a macOS user specifies recognition level and languages, **When** they POST to the synchronous ocrmac endpoint, **Then** the system processes with those parameters and returns hOCR immediately
3. **Given** a non-macOS user attempts to use the synchronous ocrmac endpoint, **When** they POST a document, **Then** they receive an HTTP 400 error immediately indicating ocrmac is only available on macOS
4. **Given** a macOS system where ocrmac is unavailable, **When** a user POSTs to the synchronous ocrmac endpoint, **Then** they receive an HTTP 400 error indicating the engine is unavailable

---

### User Story 4 - Timeout and Error Handling (Priority: P2)

A developer using synchronous endpoints wants to receive clear, immediate feedback when documents take too long to process or encounter errors, enabling them to handle these cases gracefully in their application (e.g., fall back to async processing or notify users).

**Why this priority**: Proper error handling and timeout management are essential for production reliability. Without clear timeouts and error responses, developers can't build robust integrations. This is P2 because it supports the P1 stories rather than providing independent value.

**Independent Test**: Can be fully tested by posting a large or complex document that exceeds processing limits and verifying the system returns HTTP 408 timeout or appropriate error within the timeout period. Delivers value through predictable error handling.

**Acceptance Scenarios**:

1. **Given** a user submits a document that takes longer than the timeout limit to process, **When** the timeout is exceeded, **Then** the system returns HTTP 408 error with a clear message indicating timeout and suggesting async endpoints
2. **Given** a user submits a corrupted or invalid document, **When** the synchronous endpoint attempts processing, **Then** the system returns HTTP 400 error with details about the validation failure immediately
3. **Given** a user submits a document that causes an OCR engine error, **When** the error occurs, **Then** the system returns HTTP 500 error with error details rather than hanging or timing out silently
4. **Given** a user's document is too large for synchronous processing, **When** they POST to a synchronous endpoint, **Then** they receive HTTP 413 error indicating file size limit and suggesting async endpoints

---

### User Story 5 - Backward Compatibility (Priority: P3)

Existing users of the async job-based endpoints want to continue using them without any changes to their integrations. New synchronous endpoints must not affect existing functionality, performance, or behavior of async endpoints.

**Why this priority**: Preserving backward compatibility prevents breaking existing integrations. This is P3 because it's a constraint on implementation rather than delivering new user value - it ensures we don't break existing value.

**Independent Test**: Can be fully tested by running existing async endpoint tests and verifying 100% pass rate with no performance degradation. Delivers value by protecting existing users.

**Acceptance Scenarios**:

1. **Given** an existing user of async upload endpoints, **When** they continue using `/upload/tesseract`, `/upload/easyocr`, or `/upload/ocrmac`, **Then** all functionality works exactly as before with no changes required
2. **Given** the system has synchronous endpoints deployed, **When** users submit jobs to async endpoints, **Then** processing performance and queue behavior remain unchanged
3. **Given** existing API clients, **When** synchronous endpoints are added, **Then** no API contract changes occur for async endpoints (same request/response formats)
4. **Given** a user reads API documentation, **When** they review endpoint options, **Then** they can clearly understand when to use synchronous vs. async endpoints based on their use case

---

### Edge Cases

- When a user submits a multi-page document to a synchronous endpoint, the system processes all pages but may timeout if total processing exceeds the limit - returns HTTP 408 timeout error with no partial results to preserve data integrity
- When a user submits a document at exactly the file size limit, the system accepts it and processes normally without edge case failures
- When synchronous processing takes 99% of the timeout limit, the system completes successfully and returns results rather than preemptively timing out
- When multiple users submit documents to synchronous endpoints concurrently, the system handles all requests without one timing out due to another's processing time
- When a synchronous endpoint request is cancelled by the client mid-processing, the system cleans up resources and doesn't continue processing unnecessarily
- When an OCR engine becomes unavailable during synchronous processing, the system returns HTTP 503 error immediately rather than timing out
- When a user submits identical documents to both sync and async endpoints, both return identical hOCR output (deterministic processing)
- When a user provides invalid engine parameters to a synchronous endpoint, the system validates and rejects immediately (same validation as async endpoints)
- When system load is high, synchronous endpoints may take longer but should not exceed timeout limits or affect async endpoint queue processing
- When a document contains unusual formatting or embedded content, synchronous processing handles it the same way async processing does

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide synchronous OCR endpoints for each supported engine (Tesseract, EasyOCR, ocrmac)
- **FR-002**: Synchronous endpoints MUST accept the same parameters as their async counterparts (all engine-specific parameters)
- **FR-003**: Synchronous endpoints MUST return hOCR content in a JSON response body upon successful processing, with the hOCR XML as an escaped string field
- **FR-003a**: Success response JSON MUST include at minimum: hOCR content field (string), processing duration field, and HTTP 200 status with Content-Type application/json
- **FR-004**: Synchronous endpoints MUST enforce a request timeout of 30 seconds by default
- **FR-005**: System MUST return HTTP 408 (Request Timeout) error when processing exceeds the timeout limit, with a message suggesting async endpoints for long-running documents
- **FR-006**: Synchronous endpoints MUST enforce a file size limit of 5MB to prevent timeout issues
- **FR-007**: System MUST return HTTP 413 (Payload Too Large) error when file size exceeds the limit, with a message suggesting async endpoints for large documents
- **FR-008**: Synchronous endpoints MUST validate engine availability before processing and return HTTP 400 error if engine is unavailable
- **FR-009**: Synchronous endpoints MUST validate all engine-specific parameters using the same validation logic as async endpoints
- **FR-010**: System MUST return HTTP 400 errors for invalid parameters with the same error format and detail as async endpoints
- **FR-011**: Synchronous endpoints MUST handle document format validation identically to async endpoints (same supported formats: JPEG, PNG, PDF, TIFF)
- **FR-012**: System MUST return HTTP 415 (Unsupported Media Type) error for invalid document formats, matching async endpoint behavior
- **FR-013**: Synchronous processing MUST produce identical hOCR output to async processing for the same document and parameters (deterministic processing)
- **FR-014**: System MUST log all synchronous processing requests with correlation IDs for debugging and monitoring
- **FR-014a**: System MUST track metrics for synchronous endpoints including: request count (per engine), latency percentiles (p50, p95, p99), timeout rate, and engine-specific success rate
- **FR-015**: Synchronous endpoints MUST NOT create jobs in the job queue or persist processing state
- **FR-016**: System MUST clean up temporary uploaded files immediately after synchronous processing completes or fails
- **FR-017**: Synchronous endpoints MUST return appropriate HTTP status codes: 200 for success, 400 for validation errors, 408 for timeouts, 413 for size limits, 415 for format errors, 500 for processing errors, 503 for engine unavailable
- **FR-018**: System MUST document synchronous endpoints in API documentation with clear guidance on when to use sync vs. async
- **FR-019**: Synchronous endpoints MUST maintain the same rate limiting behavior as async endpoints
- **FR-020**: System MUST preserve all existing async endpoint functionality without modification or performance degradation
- **FR-021**: Synchronous endpoints MUST include the same CORS headers and middleware as async endpoints for consistent API behavior
- **FR-022**: System MUST return error responses in the same JSON format as async endpoints for consistency
- **FR-023**: System MUST NOT return partial results when timeouts occur - if processing exceeds timeout limit, return HTTP 408 error with no hOCR content to preserve data integrity

### Key Entities

- **Synchronous OCR Request**: Represents a direct processing request; attributes include uploaded document, engine type, engine-specific parameters, timeout limit, file size
- **Synchronous OCR Response**: Represents the immediate JSON response; attributes include hOCR content as escaped XML string, processing duration, HTTP status code, error details (if failed)
- **Processing Timeout**: Represents timeout configuration; attributes include timeout duration (default 30s), timeout error message, suggested alternative (async endpoint reference)
- **File Size Limit**: Represents size constraints; attributes include maximum file size (5MB), size validation status, exceeded size error message

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 95% of single-page documents process successfully via synchronous endpoints in under 5 seconds
- **SC-002**: Users complete document processing in 1 HTTP request instead of 3+ requests (upload → status check → result retrieval)
- **SC-003**: Synchronous endpoints handle at least 100 concurrent requests without timeouts or performance degradation
- **SC-004**: Timeout errors occur for less than 2% of requests (indicating appropriate file size limits)
- **SC-005**: Synchronous and async endpoints produce byte-identical hOCR output for 100% of identical documents and parameters
- **SC-006**: API documentation clearly distinguishes sync vs. async use cases, reducing support questions about endpoint selection by 60%
- **SC-007**: Existing async endpoint performance remains unchanged (within 5% of current metrics) after synchronous endpoints are deployed
- **SC-008**: 100% of parameter validation errors return identical error messages between sync and async endpoints
- **SC-009**: Zero temporary file leaks occur - all uploaded files are cleaned up within 1 second of request completion or failure
- **SC-010**: Synchronous endpoint error rates (excluding timeouts) match async endpoint error rates (within 1% difference)
- **SC-011**: Metrics tracking captures 100% of synchronous requests with latency percentiles (p50, p95, p99), timeout rate, and per-engine success rate for operational visibility

## Assumptions *(mandatory)*

- Most users need synchronous processing for single-page or simple documents; multi-page documents are better suited for async
- Users can determine whether their use case fits synchronous constraints (file size, processing time) from API documentation
- 30-second timeout is sufficient for 95% of single-page documents across all engines
- 5MB file size limit is appropriate for synchronous processing and aligns with timeout constraints
- Users accept that synchronous endpoints may have lower throughput under high load compared to async queue-based processing
- Network stability is sufficient for maintaining HTTP connections during 30-second processing windows
- Synchronous processing doesn't require the same durability guarantees as async (no job recovery on server restart)
- Users understand the trade-off: synchronous endpoints are simpler but less suitable for large/complex documents
- OCR engines process documents quickly enough that synchronous processing is viable for typical use cases
- Existing async endpoints remain the recommended approach for batch processing, multi-page documents, and long-running jobs

## Dependencies

- Requires all three OCR engines (Tesseract, EasyOCR, ocrmac) to support synchronous processing without modification
- Requires the same file upload and validation infrastructure as async endpoints
- Requires the same temporary file storage and cleanup mechanisms as async endpoints
- Requires timeout enforcement mechanism at the HTTP request level
- Requires file size validation before processing begins
- Requires updates to API documentation to explain sync vs. async endpoint selection
- Requires the same rate limiting and middleware infrastructure as async endpoints
- Requires monitoring and logging infrastructure to track synchronous endpoint performance and timeouts
- Requires metrics collection infrastructure to capture request count, latency percentiles (p50, p95, p99), timeout rate, and per-engine success rate

## Out of Scope

- Automatic fallback from synchronous to async when documents exceed timeout
- Streaming or partial results during synchronous processing
- Configurable per-request timeout values (uses fixed 30-second timeout)
- Synchronous batch processing of multiple documents in a single request
- Job IDs or result persistence for synchronous requests (purely ephemeral)
- Progress indicators or status updates during synchronous processing
- Retry mechanisms for failed synchronous requests (users can retry at application level)
- Automatic engine selection for synchronous endpoints (users must specify engine as with async)
- Converting existing async jobs to synchronous processing or vice versa
- WebSocket or Server-Sent Events alternatives to synchronous HTTP
- Caching of synchronous processing results for identical documents
- Priority queuing or fast-lane processing for synchronous requests
