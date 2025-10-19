# Implementation Plan: Remove Generic Upload Endpoint

**Branch**: `005-remove-generic-upload` | **Date**: 2025-10-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-remove-generic-upload/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Remove the generic `/upload` endpoint from the API, requiring all clients to use engine-specific endpoints (`/upload/tesseract`, `/upload/ocrmac`, `/upload/easyocr`). This cleanup task removes redundant routing logic and simplifies the API surface by eliminating an endpoint that is no longer needed since engine-specific endpoints provide full functionality coverage.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI 0.104+, Pydantic 2.5+, pytest 7.4+
**Storage**: Redis 7.0+ (job state), filesystem (temporary uploaded files)
**Testing**: pytest with pytest-asyncio, pytest-cov, httpx for API testing
**Target Platform**: Linux server (containerized with Docker)
**Project Type**: Single web API service
**Performance Goals**: No change - maintain existing performance for engine-specific endpoints
**Constraints**: Must not affect engine-specific endpoints; zero downtime deployment
**Scale/Scope**: 5 API endpoints affected (1 removed, 4 preserved), minimal code changes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle 1: API Contract First
- ✅ **Status**: PASS
- **Justification**: This is a breaking change (endpoint removal), but spec confirms no production clients exist. Engine-specific endpoints remain stable with no contract changes.

### Principle 2: Deterministic & Reproducible Processing
- ✅ **Status**: PASS - NOT APPLICABLE
- **Justification**: No OCR processing logic changes; only routing is affected.

### Principle 3: Test-First & Coverage Discipline
- ✅ **Status**: PASS
- **Justification**: Will write tests first to verify:
  1. Generic endpoint returns 404
  2. All engine-specific endpoints continue working
  3. Coverage gates (80% overall, 90% utilities) maintained

### Principle 4: Performance & Resource Efficiency
- ✅ **Status**: PASS
- **Justification**: No performance impact - removing code improves efficiency slightly. No algorithmic changes.

### Principle 5: Observability & Transparency
- ✅ **Status**: PASS
- **Justification**: Existing logging and metrics for engine-specific endpoints remain unchanged.

### Principle 6: Security & Data Privacy
- ✅ **Status**: PASS - NOT APPLICABLE
- **Justification**: No security or privacy impact; endpoint removal does not affect data handling.

### Principle 7: Simplicity & Minimal Surface
- ✅ **Status**: PASS
- **Justification**: This change directly supports this principle by removing dead/redundant code and reducing API surface area.

### Principle 8: Documentation & Library Reference
- ✅ **Status**: PASS - NOT APPLICABLE
- **Justification**: No new libraries or APIs being integrated; using existing FastAPI routing.

**Overall Constitution Gate**: ✅ PASS - All applicable principles satisfied

## Project Structure

### Documentation (this feature)

```
specs/005-remove-generic-upload/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
src/
├── main.py              # FastAPI app entry point
├── config.py            # Pydantic settings
├── models/              # Data models
├── api/                 # API routes and middleware
│   ├── routes/
│   │   ├── upload.py    # MODIFIED: Remove upload_document function
│   │   ├── health.py    # No changes
│   │   └── jobs.py      # No changes
│   ├── middleware/      # No changes
│   └── dependencies.py  # No changes
├── services/            # Business logic - No changes
└── utils/               # Shared utilities - No changes

tests/
├── unit/                # Unit tests
│   └── api/
│       └── routes/
│           └── test_upload.py  # MODIFIED: Remove generic endpoint tests, add 404 test
├── integration/         # Integration tests - MODIFIED: Update to use engine-specific endpoints
├── contract/            # OpenAPI contract tests - MODIFIED: Remove generic endpoint contract
└── performance/         # Performance tests - No changes needed
```

**Structure Decision**: Single project structure is used. This feature only affects the `src/api/routes/upload.py` file and related tests. No new directories or files are created; this is a removal-only change.

## Complexity Tracking

*No violations - this section is empty as all constitution principles pass.*
