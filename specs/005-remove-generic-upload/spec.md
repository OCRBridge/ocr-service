# Feature Specification: Remove Generic Upload Endpoint

**Feature Branch**: `005-remove-generic-upload`
**Created**: 2025-10-19
**Status**: Draft
**Input**: User description: "Remove generic upload endpoint"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - API Client Migrates to Engine-Specific Endpoints (Priority: P1)

API clients that previously used the generic upload endpoint now exclusively use engine-specific endpoints (`/upload/tesseract`, `/upload/ocrmac`, `/upload/easyocr`) to perform OCR tasks.

**Why this priority**: This is the core functionality change. The generic endpoint is removed, and clients must use engine-specific endpoints. Since no production clients currently exist, this is the only story needed.

**Independent Test**: Can be fully tested by attempting to access the generic endpoint (expecting 404) and verifying all engine-specific endpoints continue to work properly.

**Acceptance Scenarios**:

1. **Given** the API is running, **When** a client sends a POST request to `/upload`, **Then** the system returns a 404 Not Found response
2. **Given** the API is running, **When** a client sends a POST request to `/upload/tesseract` with valid parameters, **Then** the system processes the request successfully
3. **Given** the API is running, **When** a client sends a POST request to `/upload/ocrmac` with valid parameters, **Then** the system processes the request successfully (on macOS)
4. **Given** the API is running, **When** a client sends a POST request to `/upload/easyocr` with valid parameters, **Then** the system processes the request successfully

---

### Edge Cases

- What happens when a client attempts to use the removed `/upload` endpoint with valid request parameters?
- How does the system handle API documentation requests for the removed endpoint?
- What happens when old API clients with hardcoded `/upload` paths attempt to connect?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST return a 404 Not Found response when clients attempt to access the `/upload` endpoint
- **FR-002**: System MUST continue to support all engine-specific upload endpoints (`/upload/tesseract`, `/upload/ocrmac`, `/upload/easyocr`) without any functional changes
- **FR-003**: API documentation MUST be updated to remove references to the generic `/upload` endpoint
- **FR-004**: API documentation MUST clearly indicate that clients should use engine-specific endpoints
- **FR-005**: System MUST maintain all existing functionality for engine-specific endpoints (parameter validation, error handling, response formatting)

### Key Entities

- **Upload Endpoint**: The generic `/upload` route that accepts OCR requests without specifying an engine
- **Engine-Specific Endpoints**: Routes like `/upload/tesseract`, `/upload/ocrmac`, `/upload/easyocr` that specify which OCR engine to use

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Generic `/upload` endpoint returns 404 Not Found for all HTTP methods
- **SC-002**: All engine-specific endpoints (`/upload/tesseract`, `/upload/ocrmac`, `/upload/easyocr`) continue to function with 100% of existing test cases passing
- **SC-003**: API documentation contains zero references to the generic `/upload` endpoint
- **SC-004**: API documentation clearly directs users to engine-specific endpoints with examples for each engine

## Assumptions *(mandatory)*

- No production API clients are currently using the generic `/upload` endpoint
- All necessary functionality previously provided by `/upload` is fully covered by engine-specific endpoints
- Engine-specific endpoints have been tested and are stable
- This is a non-breaking change since no clients depend on the generic endpoint

## Out of Scope

- Adding new OCR engines or modifying engine-specific endpoint behavior
- Implementing endpoint deprecation warnings (not needed since no clients exist)
- Creating redirect logic from `/upload` to a default engine
- Modifying authentication or authorization mechanisms
- Changing the response format of engine-specific endpoints

## Dependencies

- Engine-specific endpoints (`/upload/tesseract`, `/upload/ocrmac`, `/upload/easyocr`) must be fully functional
- API documentation system must support updates to reflect endpoint removal
- Test suite must cover all engine-specific endpoints to ensure no regression

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Unknown clients using generic endpoint | High | Verify through logs that no recent requests to `/upload` exist; monitor for 404 errors after removal |
| Tests still referencing generic endpoint | Medium | Review and update all test suites to use engine-specific endpoints |
| Documentation links to removed endpoint | Low | Search all documentation for `/upload` references and update them |
