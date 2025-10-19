# Research: Remove Generic Upload Endpoint

**Feature**: Remove Generic Upload Endpoint
**Branch**: `005-remove-generic-upload`
**Date**: 2025-10-19

## Overview

This document captures the research and decisions made for removing the generic `/upload` endpoint from the RESTful OCR API.

## Technical Context Analysis

### Current State

The API currently exposes the following upload endpoints:

1. **Generic endpoint**: `POST /upload` (upload_document function)
2. **Engine-specific endpoints**:
   - `POST /upload/tesseract` (upload_document_tesseract)
   - `POST /upload/ocrmac` (upload_document_ocrmac) - macOS only
   - `POST /upload/easyocr` (upload_document_easyocr)

### Architecture Review

**Current routing structure** (from `src/api/routes/upload.py`):
- All endpoints are defined in a single FastAPI router
- Generic endpoint likely uses a default engine or requires engine parameter
- Engine-specific endpoints explicitly target their respective OCR engines

**Dependencies identified**:
- FastAPI routing (`APIRouter`)
- Pydantic models for request validation
- OCR service layer (unchanged by this feature)
- Redis job state management (unchanged by this feature)

## Research Questions & Decisions

### Question 1: Impact on Existing Tests

**Research**: Need to identify all tests that reference the generic `/upload` endpoint

**Decision**:
- Remove all tests for the generic endpoint
- Add a new test to verify 404 response when accessing `/upload`
- Ensure all existing tests for engine-specific endpoints continue to pass

**Rationale**: Tests should reflect the new API contract where only engine-specific endpoints are valid.

**Alternatives considered**:
- Keep tests but mark as "should fail" - Rejected because it creates confusion and dead code

### Question 2: Documentation Updates

**Research**: Determine what documentation references the generic endpoint

**Decision**:
- Update API documentation (likely OpenAPI/Swagger schema)
- Update README.md if it contains endpoint examples
- Update quickstart.md to only show engine-specific endpoints

**Rationale**: Documentation must accurately reflect the available API surface.

**Alternatives considered**:
- Add deprecation notice - Rejected because no clients exist and immediate removal is cleaner

### Question 3: FastAPI Route Removal Best Practices

**Research**: How to cleanly remove a FastAPI route without affecting other routes

**Decision**:
- Simply delete the function definition and its `@router.post("/upload")` decorator
- Verify no other code references this function
- Ensure router registration in main.py is unchanged

**Rationale**: FastAPI routes are declarative; removing the decorated function is sufficient.

**Alternatives considered**:
- Return 410 Gone instead of 404 - Rejected because spec requires 404 and there's no need to distinguish "removed" vs "never existed"

### Question 4: Deployment Strategy

**Research**: Can this be deployed without downtime?

**Decision**:
- Standard deployment process (rolling update with Docker)
- No special migration needed since no clients exist
- Monitor for 404s in the first 24 hours post-deployment

**Rationale**: Spec confirms no production clients, so risk is minimal.

**Alternatives considered**:
- Phased rollout with feature flag - Rejected as over-engineered for a simple removal with no clients

### Question 5: Testing Strategy

**Research**: What testing approach ensures we don't break engine-specific endpoints?

**Decision**:
- Test-first approach (TDD):
  1. Write test for 404 on `/upload`
  2. Verify all engine-specific endpoint tests still pass
  3. Run contract tests to verify OpenAPI schema is updated
  4. Run integration tests end-to-end

**Rationale**: Aligns with Constitution Principle 3 (Test-First & Coverage Discipline).

**Alternatives considered**:
- Manual testing only - Rejected because constitution requires automated tests

## Technology Decisions

### No New Technologies Required

This feature requires no new dependencies or libraries. The implementation uses:

- **FastAPI**: Existing routing framework
- **pytest**: Existing testing framework
- **httpx**: Existing HTTP client for API testing

All technologies are already in use and well-understood by the team.

## Best Practices Applied

### FastAPI Route Management

**Practice**: Keep route definitions clean and explicit
- Remove the entire function definition for `/upload`
- No need for placeholder or stub functions
- FastAPI will naturally return 404 for undefined routes

**Source**: FastAPI best practices for API versioning and deprecation

### Testing Deleted Functionality

**Practice**: Add explicit tests for expected failures
- Test that deleted endpoint returns 404
- Verify error response format is consistent with other 404s

**Source**: RESTful API testing best practices

### Breaking Change Management

**Practice**: Document breaking changes clearly
- Update CHANGELOG.md with breaking change notice
- Update API version if following semantic versioning for API

**Source**: Semantic versioning and API evolution best practices

## Summary

This is a straightforward refactoring task with minimal complexity:

1. **No new technologies** required
2. **No architectural changes** needed
3. **Low risk** due to absence of production clients
4. **Clear success criteria** from specification
5. **Well-defined testing approach** following constitution principles

The main work involves:
- Removing code (upload_document function)
- Updating tests (remove generic endpoint tests, add 404 test)
- Updating documentation (OpenAPI schema, README, quickstart)

All decisions align with the project constitution, particularly:
- **Principle 3**: Test-first approach
- **Principle 7**: Simplicity by removing dead code
- **Principle 1**: API contract clarity
