# Implementation Plan: EasyOCR Engine Support

**Branch**: `004-easyocr-engine` | **Date**: 2025-10-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-easyocr-engine/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add EasyOCR as a third OCR engine option alongside Tesseract and ocrmac, enabling superior multilingual support (80+ languages, especially Asian scripts) via deep learning-based recognition. Users can select `engine=easyocr` with EasyOCR-specific parameters (languages, gpu, text_threshold, link_threshold) while maintaining backward compatibility with existing Tesseract default behavior.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI 0.104+, Pydantic 2.5+, EasyOCR (new), PyTorch (new - EasyOCR dependency), pytesseract 0.3+, Redis 7.0+
**Storage**: Redis 7.0+ (job state), filesystem (temporary uploaded files, results), configurable persistent volume (EasyOCR models, 5GB default)
**Testing**: pytest 7.4+ (unit, integration, contract, performance tests)
**Target Platform**: Linux server (primary), macOS (development), Docker containers
**Project Type**: Single web application (FastAPI REST API)
**Performance Goals**: p95 latency <= 30s for single-page documents, 60s hard timeout per page, GPU-accelerated processing 50% faster than CPU
**Constraints**: GPU memory management (max 2 concurrent GPU jobs), model storage limit (5GB default), parameter validation synchronous (<100ms), deterministic output
**Scale/Scope**: Multi-engine OCR service (3 engines: Tesseract, ocrmac, EasyOCR), 80+ language support via EasyOCR, concurrent job processing with queue management

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence / Notes |
|-----------|--------|------------------|
| **1. API Contract First** | ✅ PASS | Will define OpenAPI spec for EasyOCR parameters before implementation. Extends existing `/upload` endpoint with new engine option. No breaking changes - backward compatible. |
| **2. Deterministic & Reproducible** | ⚠️ CONDITIONAL | EasyOCR uses deep learning models which may have minor variance. Will document expected variance and validate consistency within acceptable bounds. Determinism seeded where possible. |
| **3. Test-First & Coverage** | ✅ PASS | Will write failing tests before implementation. Target: 90% for utilities, 80% overall. Contract tests for all parameter combinations. Integration tests for end-to-end EasyOCR flow. |
| **4. Performance & Resource** | ✅ PASS | Performance budgets defined: 30s p95, 60s timeout. GPU memory managed via concurrency limit (2 jobs). Model storage capped at 5GB. Will measure baseline and track regression. |
| **5. Observability** | ✅ PASS | Structured JSON logs for all EasyOCR operations. Metrics for processing time, GPU/CPU mode, queue wait time, model load time. Request correlation via job IDs. |
| **6. Security & Privacy** | ✅ PASS | No change to existing data retention policy. Model files validated via checksums. Dependency scan required for EasyOCR + PyTorch. No sensitive data in logs. |
| **7. Simplicity & Minimal Surface** | ✅ PASS | Following existing multi-engine pattern (Tesseract, ocrmac). No premature abstraction - reusing proven architecture. Clean parameter isolation per engine. |
| **8. Documentation & Library Reference** | ✅ PASS | Will use Context7 for EasyOCR and PyTorch integration guidance. Consult official docs for API usage patterns, configuration, and best practices. |

**Overall Assessment**: PASS with one conditional (Principle 2 - acceptable for ML models)

**Justification for Conditional**:
- EasyOCR uses neural networks which inherently have minor numerical variance
- This is expected behavior for deep learning models, not a defect
- Will document variance characteristics and establish acceptable bounds
- Determinism enforced where possible (seeding, consistent preprocessing)

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
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
├── main.py                      # FastAPI app entry point - will register EasyOCR routes
├── config.py                    # Pydantic settings - add EasyOCR config
├── models/
│   ├── request.py              # Request models - add EasyOCR parameters
│   ├── response.py             # Response models (existing)
│   └── engine.py               # Engine models - add EasyOCR engine type
├── api/
│   └── routes/
│       └── upload.py           # Upload endpoint - extend for EasyOCR
├── services/
│   ├── engines/
│   │   ├── tesseract.py        # Existing Tesseract engine
│   │   ├── ocrmac.py           # Existing ocrmac engine
│   │   └── easyocr.py          # NEW: EasyOCR engine implementation
│   ├── validators.py           # Parameter validation - add EasyOCR validators
│   ├── platform.py             # Platform detection (existing)
│   └── engine_registry.py      # Engine registration - register EasyOCR
└── utils/
    ├── hocr.py                 # hOCR conversion - extend for EasyOCR output
    └── gpu.py                  # NEW: GPU detection and management

tests/
├── contract/
│   └── test_api_contract.py    # API contract tests - add EasyOCR scenarios
├── integration/
│   └── test_easyocr.py         # NEW: End-to-end EasyOCR integration tests
└── unit/
    ├── test_validators.py      # Validation tests - add EasyOCR parameter tests
    └── test_easyocr_engine.py  # NEW: EasyOCR engine unit tests
```

**Structure Decision**: Single web application (FastAPI REST API). Following existing multi-engine architecture established with Tesseract and ocrmac. New EasyOCR engine implementation in `src/services/engines/easyocr.py`, extending validation in `src/services/validators.py`, and adding GPU utilities in `src/utils/gpu.py`. Tests follow existing pattern with contract, integration, and unit test layers.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

No violations requiring justification. The conditional pass on Principle 2 (Deterministic & Reproducible) is acceptable given the inherent nature of deep learning models and is documented with variance expectations.

---

## Post-Design Constitution Re-evaluation

*Re-check after Phase 1 design completion*

**Date**: 2025-10-19

| Principle | Status | Post-Design Evidence |
|-----------|--------|---------------------|
| **1. API Contract First** | ✅ CONFIRMED | OpenAPI spec completed in `contracts/openapi-easyocr-extension.yaml`. Extends `/upload` endpoint with backward-compatible EasyOCR parameters. Contract defines all request/response schemas before implementation. |
| **2. Deterministic & Reproducible** | ✅ CONFIRMED | Documented expected variance from neural network models in research.md. Same image + same config produces consistent results within model variance bounds (~1-2% confidence variation). Job metadata includes all parameters for reproducibility. |
| **3. Test-First & Coverage** | ✅ CONFIRMED | Test strategy defined in quickstart.md: unit tests for validators, contract tests for API parameter validation, integration tests for end-to-end flow. Following TDD: write failing tests before implementation. |
| **4. Performance & Resource** | ✅ CONFIRMED | Performance budgets enforced: 60s timeout per page, GPU concurrency limit (2 jobs), 5GB model storage limit. Metrics tracking (processing time, GPU/CPU mode, queue wait, model load time) defined in data-model.md. |
| **5. Observability** | ✅ CONFIRMED | Structured logging defined for all EasyOCR operations. Job metadata includes gpu_used, model_load_time_ms, processing_time_ms, queue_wait_time_ms for debugging. Request correlation via job_id. |
| **6. Security & Privacy** | ✅ CONFIRMED | No new data retention beyond existing policy. Model file checksum validation at startup. EasyOCR + PyTorch dependencies require security scan. No sensitive data in logs (no image bytes, no full text). |
| **7. Simplicity & Minimal Surface** | ✅ CONFIRMED | Reuses existing multi-engine pattern from Tesseract/ocrmac. No new abstractions - extends EngineConfiguration, UploadRequest models. Clean parameter isolation via Pydantic validation. |
| **8. Documentation & Library Reference** | ✅ CONFIRMED | Used Context7 for EasyOCR and PyTorch research (see research.md). Implementation patterns derived from official documentation. API usage documented in quickstart.md. |

**Overall Assessment**: FULL PASS (all principles satisfied)

**Changes from Initial Check**:
- Principle 2 upgraded from CONDITIONAL to CONFIRMED after documenting acceptable variance bounds
- All design artifacts (research.md, data-model.md, contracts/, quickstart.md) demonstrate adherence to constitution
- No new violations introduced during design phase

