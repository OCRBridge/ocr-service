<!--
Sync Impact Report
Version change: (none prior) → 1.0.0
Modified principles: N/A (initial adoption)
Added sections: Core Principles; Security & Performance Requirements; Development Workflow & Quality Gates; Governance
Removed sections: None
Templates requiring updates:
	.specify/templates/plan-template.md ✅ updated
	.specify/templates/tasks-template.md ✅ updated
	.specify/templates/spec-template.md ✅ no change needed (already aligned)
	.specify/templates/agent-file-template.md ⚠ pending (will auto-populate later when plans exist)
	.specify/templates/checklist-template.md ⚠ optional enhancements (add categories for Security, Observability later)
Follow-up TODOs: None
-->

# RESTful OCR Constitution

## Core Principles

### 1. API Contract First
All externally callable OCR functionality (upload, process, health, metrics) MUST be defined via a stable
HTTP+JSON contract (OpenAPI spec or explicit path + method + schema) before implementation starts.
Breaking changes REQUIRE a versioned path or explicit negotiation header. No ad‑hoc implicit
behaviour is introduced without updating the contract. Contracts live beside code and are versioned
atomically with their implementation.

Rationale: Prevents drift between client expectations and server behaviour and enables automated
testing, documentation generation, and early review of scope.

### 2. Deterministic & Reproducible Processing
Given the same image bytes and configuration parameters, the OCR pipeline MUST produce identical
text output (aside from timestamp / trace identifiers). Any non‑determinism (e.g., heuristic model
randomness) MUST be seeded and documented. Intermediate artifacts (preprocessed image, layout
segmentation results) SHOULD be optionally emitted for debugging when a debug flag is set.

Rationale: Determinism enables reliable regression detection and confident optimization.

### 3. Test‑First & Coverage Discipline (NON‑NEGOTIABLE)
For each new endpoint, pipeline stage or bug fix: write failing unit/contract tests BEFORE code.
Minimum coverage gates: 90% lines for pure utilities, 80% overall project, 100% for critical parsing
and coordinate math functions. Integration tests MUST cover: end‑to‑end image → text, error paths
(unsupported format, corrupt image), and performance budget checks. A PR without required tests is
blocked.

Rationale: Ensures correctness, prevents silent accuracy regressions and enforces maintainable change.

### 4. Performance & Resource Efficiency
Baseline performance budgets MUST be defined for each release: p95 end‑to‑end latency <= 800ms for
standard 1MP grayscale image on reference hardware; memory peak < 512MB per request; throughput
scales linearly across CPU cores (document test harness). Any change exceeding +10% latency or
memory requires explicit justification and possibly a feature flag. Profiling data MUST accompany
optimizations altering algorithmic complexity.

Rationale: Keeps service cost‑efficient and responsive as feature set grows.

### 5. Observability & Transparency
Structured logs (JSON) MUST include: request id, correlation id, stage, latency, and outcome. Metrics
MUST expose: request_count (labels: status), latency_histogram, ocr_char_accuracy (if ground truth
available in tests), and error_type counters. Tracing MUST annotate each pipeline stage. Severity
levels: debug (development only), info (state changes), warning (recoverable anomalies), error
(user‑visible failure). No silent exception swallowing.

Rationale: Enables rapid diagnosis and SLO tracking.

### 6. Security & Data Privacy
Only necessary data is retained. Uploaded images MUST NOT persist beyond processing unless an
explicit retention flag AND legal basis are present. All temporary files are removed after request.
Sensitive logs (raw image bytes, full extracted text) are NEVER logged. Dependency vulnerabilities
with CVSS >= 7 MUST be remediated or mitigated before release. TLS is mandatory in production.

Rationale: Protects user data and reduces breach risk.

### 7. Simplicity & Minimal Surface
Prefer the simplest working algorithm or library that meets accuracy and performance targets before
introducing complex heuristics or ML model changes. Remove dead code within the same PR that obsoletes
it. Avoid premature abstraction: create shared modules only after 3 concrete usages.

Rationale: Reduces cognitive load, accelerates onboarding, and limits defect vectors.

## Security & Performance Requirements
1. Input Validation: Reject unsupported formats early with 415 or 400 and descriptive JSON error.
2. Rate Limiting: MUST be configurable (default soft limit) to prevent abuse.
3. Resource Isolation: Large image processing MUST stream or chunk to avoid memory spikes.
4. Accuracy Benchmarks: Each model change MUST report char accuracy vs baseline test corpus; regression
> 0.5 percentage points requires sign‑off.
5. Dependency Hygiene: Weekly automated scan; critical alerts create blocking tasks.

## Development Workflow & Quality Gates
Pipeline:
1. Design / Contract: Define or update OpenAPI + performance & accuracy budgets.
2. Tests First: Add/modify failing contract + unit + integration tests.
3. Implementation: Code passes style, type checks (if types added later) and tests locally.
4. Observability Hooks: Ensure new stages emit logs, metrics, traces before merge.
5. Review: Reviewer MUST verify principles checklist (contract, determinism, tests, performance,
observability, security) in PR description.
6. CI Gates (must all pass): lint, unit tests, integration tests, performance smoke (budget), security
scan, coverage thresholds.
7. Release: Tag semantic version; update changelog with any breaking changes & migrations.

Violations: Any temporary deviation (e.g., relaxed performance budget) MUST be labelled with a
tracking issue and removal date.

## Governance
Authority: This constitution supersedes informal practices. Conflicts are resolved in favor of the
most recent ratified version.

Amendments: Propose via PR modifying this file. Include: (a) rationale, (b) impact assessment, (c)
version bump justification (SEMVER governance). Require at least one maintainer approval + passing
CI. MAJOR: removal or incompatible redefinition of a principle or governance rule. MINOR: new
principle, new required gate, or material expansion. PATCH: clarifications without changing
enforceable meaning.

Compliance Review: Each PR template MUST include a checklist referencing Core Principles 1–7. CI may
automate checks (coverage, performance, lint). Quarterly review audits metrics vs declared budgets.

Versioning Policy: Semantic Versioning (MAJOR.MINOR.PATCH) applied to governance. All version bumps
recorded in Sync Impact Report comment.

Enforcement: Merges blocked if mandatory gates fail or checklist is incomplete. Emergency fixes may
temporarily waive performance gate with maintainer approval and MUST create a follow‑up task.

**Version**: 1.0.0 | **Ratified**: 2025-10-18 | **Last Amended**: 2025-10-18
