# Contributing to RESTful OCR API

Thank you for your interest in contributing to RESTful OCR API! This document provides guidelines and instructions for contributing features and bug fixes to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Environment Setup](#development-environment-setup)
  - [Mise Tasks Reference](#mise-tasks-reference)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Submitting Changes](#submitting-changes)
  - [CI/CD Build Strategy](#cicd-build-strategy)
- [Bug Reports](#bug-reports)
- [Feature Requests](#feature-requests)

## Getting Started

Before you begin contributing, please:

1. Read the [README.md](README.md) to understand the project
2. Check existing [issues](../../issues) and [pull requests](../../pulls) to avoid duplicates
3. Join our community discussions (if applicable)

## Development Environment Setup

### Prerequisites

- Python 3.10+
- Tesseract OCR 5.3+
- Poppler utils (for PDF processing)
- libmagic (for file type detection)
- mise (task runner and tool manager)
- Git

### Installation

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/ocr-service.git
cd ocr-service

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/ocr-service.git

# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng poppler-utils libmagic1

# Install pinned tools and project dependencies
mise install

# Install all dev dependencies and OCR engines
mise run install:all

# Optional: install specific engine sets
# mise run install:tesseract
# mise run install:easyocr
# mise run install:ocrmac

# Create required directories
mkdir -p /tmp/uploads /tmp/results
chmod 700 /tmp/uploads /tmp/results

# Copy environment configuration
cp .env.example .env
```

### Running the Development Server

**Option 1: Local Development** (fastest iteration)
```bash
# Development mode with auto-reload
mise run dev
```

**Option 2: Docker Development** (matches production environment)
```bash
# Lite flavor (fastest Docker builds, Tesseract only)
docker compose -f docker-compose.base.yml -f docker-compose.lite.yml up -d

# Full flavor (includes EasyOCR, slower builds)
docker compose -f docker-compose.base.yml -f docker-compose.yml up -d

# View logs for full flavor
docker compose -f docker-compose.base.yml -f docker-compose.yml logs -f api

# Rebuild full flavor after code changes
docker compose -f docker-compose.base.yml -f docker-compose.yml down
docker compose -f docker-compose.base.yml -f docker-compose.yml build
docker compose -f docker-compose.base.yml -f docker-compose.yml up -d
```

**Building Docker Images Locally**:
```bash
# Build lite image (fast, ~2-3 min)
docker build --target lite -t ocr-service:lite .

# Build full image (slow, ~10-15 min due to PyTorch)
docker build --target full -t ocr-service:full -t ocr-service:latest .

# Build both flavors
docker build --target lite -t ocr-service:lite .
docker build --target full -t ocr-service:full -t ocr-service:latest .
```

### Mise Tasks Reference

The project includes a comprehensive set of mise tasks for common development tasks. Run `mise tasks ls` to see all available commands.

## Project Structure

Understanding the project structure will help you navigate the codebase:

```
ocr-service/
├── src/                    # Application source code
│   ├── main.py            # FastAPI app entry point
│   ├── config.py          # Pydantic settings
│   ├── models/            # Data models (Pydantic, domain objects)
│   ├── api/               # API routes and middleware
│   │   ├── routes/        # Endpoint definitions
│   │   └── middleware/    # Custom middleware
│   ├── services/          # Business logic and OCR processing
│   └── utils/             # Shared utilities and helpers
├── tests/                 # Test suite
│   ├── unit/              # Unit tests (90% coverage target)
│   ├── integration/       # Integration tests (80% coverage)
│   ├── contract/          # OpenAPI contract tests
│   └── performance/       # Performance benchmarks
├── samples/               # Test fixtures and sample documents
├── pyproject.toml         # Project metadata and dependencies
├── Dockerfile             # Multi-stage build (lite & full targets)
├── docker-compose.base.yml    # Shared Docker config (common API)
├── docker-compose.yml         # Full flavor (Tesseract + EasyOCR)
└── docker-compose.lite.yml    # Lite flavor (Tesseract only)
```

### Key Directories

- **src/models/**: Define data models, request/response schemas, and domain objects
- **src/api/routes/**: Implement API endpoints
- **src/services/**: Implement business logic, OCR processing, and external integrations
- **tests/unit/**: Write unit tests with mocks/stubs for isolated testing
- **tests/integration/**: Write integration tests that use real services (Tesseract)

## Development Workflow

This project follows **Test-Driven Development (TDD)** principles. All contributions should adhere to this workflow:

### TDD Cycle

1. **Write a failing test first**
   - Write a test that describes the desired behavior
   - Run the test to verify it fails (Red)

2. **Implement minimal code to make the test pass**
   - Write just enough code to make the test pass
   - Run the test to verify it passes (Green)

3. **Refactor while keeping tests green**
   - Improve code quality, remove duplication
   - Ensure all tests still pass

4. **Repeat**
   - Continue with the next feature or bug fix

### Detailed TDD Workflow

### Branch Naming Convention

Use descriptive branch names that indicate the type of change:

- `feature/add-pdf-support` - For new features
- `bugfix/fix-rate-limit-bypass` - For bug fixes
- `refactor/improve-error-handling` - For refactoring
- `docs/update-api-examples` - For documentation updates

### Commit Message Guidelines

Write clear, descriptive commit messages:

```
<type>: <short summary>

<optional detailed description>

<optional footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `docs`: Documentation changes
- `chore`: Maintenance tasks

Example:
```
feat: add support for TIFF multi-page documents

Implemented TIFF processing using PIL to extract and process
multiple pages from TIFF files. Each page is converted to JPEG
before OCR processing.

Closes #123
```

## Testing

Testing is a critical part of our development process. All contributions must include appropriate tests. We follow a comprehensive testing strategy with **296 tests** covering unit, integration, and E2E scenarios.

> **Quick Command Reference**: For a quick reference of all development commands (testing, formatting, type checking, Docker, etc.), see [AGENTS.md](AGENTS.md).

### Test Suite Overview

Our test suite consists of three types of tests:

1. **Unit Tests** (`tests/unit/`) - Fast, isolated tests with mocks
   - 127 tests covering validators, config, security, HOCR, registry
   - ~87% pass rate, targeting 90%+ coverage
   - Uses mock OCR engines for speed

2. **Integration Tests** (`tests/integration/`) - Real I/O, FastAPI client
   - 111 tests covering API endpoints, health checks, file handling
   - ~87% pass rate, targeting 80%+ coverage
   - Uses TestClient for API testing

3. **E2E Tests** (`tests/e2e/`) - Real OCR engines
   - 40 tests with actual Tesseract and EasyOCR
   - 100% pass rate for Tesseract E2E
   - Marked with `@pytest.mark.easyocr` for CI flexibility

### Running Tests

```bash
# Quick test (excludes EasyOCR and macOS-only)
uv run pytest -m "not easyocr and not ocrmac" -v

# Run specific test suites
mise run test:unit
mise run test:integration
mise run test:contract

# Run slow tests (EasyOCR)
mise run test:easyocr

# Run macOS-specific tests
mise run test:macos

# Run all tests
mise run test:all

# Run with coverage report (excludes slow)
mise run test:coverage

# Run full coverage report (includes slow)
mise run test:coverage:full

# Run specific test file
uv run pytest tests/unit/test_validators.py -v

# Run tests matching a pattern
uv run pytest -k "test_upload" -v
```

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures (20+ fixtures)
├── mocks/                   # Mock OCR engines for unit tests
│   ├── mock_engines.py      # MockTesseractEngine, MockEasyOCREngine
│   └── mock_entry_points.py # Entry point mocking
├── unit/                    # Fast isolated tests with mocks
│   ├── test_validators.py   # File format/size validation (45 tests)
│   ├── test_config.py       # Settings validation (17 tests)
│   ├── test_hocr.py         # HOCR parsing/conversion (29 tests)
│   ├── test_security.py     # Job ID generation (7 tests)
│   ├── test_platform.py     # OS detection (11 tests)
│   ├── test_metrics.py      # Prometheus metrics (31 tests)
│   └── services/
│       ├── ocr/test_registry_v2.py  # Engine registry (29 tests)
│       └── test_cleanup.py          # File cleanup (18 tests)
├── integration/             # API and I/O integration tests
│   ├── services/
│   │   └── test_file_handler.py # Async file operations
│   └── api/
│       ├── test_health.py   # Health endpoint (11 tests)
│       └── v2/
│           ├── test_discovery.py     # Engine discovery
│           └── test_dynamic_process.py # OCR processing
└── e2e/                     # Real OCR engine tests
    ├── test_ocr_tesseract.py # Tesseract E2E (25 tests)
    └── test_ocr_easyocr.py   # EasyOCR E2E (15 tests, slow)
```

### Coverage Requirements

- **Overall**: Targeting 80-90% code coverage
- **Unit tests**: 90%+ for critical paths
- **Integration tests**: 80%+ for API endpoints
- **Current coverage**: 89%+
- New code should maintain or improve existing coverage

### Writing Tests

#### Unit Tests with Mock Engines

Unit tests should be fast, isolated, and use mock OCR engines:

```python
# tests/unit/test_validators.py
import pytest
from src.utils.validators import validate_file_format

def test_validate_jpeg_format():
    """Test JPEG format validation with magic bytes."""
    # Valid JPEG magic bytes
    jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF"

    # Should not raise exception
    validate_file_format(jpeg_bytes, "image.jpg")
```

#### Integration Tests with TestClient

Integration tests use FastAPI's TestClient and mock engines:

```python
# tests/integration/api/test_ocr_endpoints.py
def test_process_document_success_tesseract(client, sample_jpeg_bytes):
    """Test successful document processing with tesseract."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    data = {"engine": "tesseract"}

    response = client.post("/v2/ocr/process", files=files, data=data)

    assert response.status_code == 200
    result = response.json()
    assert result["engine"] == "tesseract"
    assert result["hocr"].startswith("<?xml")
```

#### E2E Tests with Real Engines

E2E tests use actual OCR engines and PIL-generated test images:

```python
# tests/e2e/test_ocr_tesseract.py
import pytest

# Skip if Tesseract not installed
pytestmark = pytest.mark.skipif(
    not TESSERACT_AVAILABLE, reason="Tesseract engine not installed"
)

def test_tesseract_detects_text(tesseract_engine, test_image_simple_text):
    """Test that Tesseract actually detects text from image."""
    result = tesseract_engine.process(test_image_simple_text)

    # Should contain the word "TESTING"
    result_lower = result.lower()
    assert "test" in result_lower or "testing" in result_lower
```

### Test Fixtures

We provide comprehensive fixtures in `tests/conftest.py`:

**Mock Fixtures:**
- `mock_engine_registry` - Registry with mock Tesseract/EasyOCR
- `mock_tesseract_engine` - Individual mock engine instance
- `app` - FastAPI app with mock engine registry injected
- `client` - TestClient with mocked engines

**File Fixtures:**
- `sample_jpeg_bytes` - Valid JPEG magic bytes
- `sample_png_bytes` - Valid PNG magic bytes
- `sample_pdf_bytes` - Valid PDF magic bytes
- `test_image_with_text` - PIL-generated image with multi-line text
- `test_image_simple_text` - PIL-generated image with "TESTING"
- `test_image_multiline` - PIL-generated image with 3 lines

**HOCR Fixtures:**
- `sample_hocr` - Valid HOCR XML with proper DOCTYPE
- `sample_hocr_multipage` - Multi-page HOCR document
- `sample_easyocr_output` - Raw EasyOCR detection output

### Test Markers

Use pytest markers to categorize tests:

```python
# Mark EasyOCR tests (deep learning)
@pytest.mark.easyocr
def test_easyocr_processing():
    ...

# Mark Tesseract tests
@pytest.mark.tesseract
def test_tesseract_processing():
    ...

# Mark Ocrmac tests
@pytest.mark.ocrmac
def test_ocrmac_processing():
    ...

# Skip if dependency not available
@pytest.mark.skipif(not TESSERACT_AVAILABLE, reason="Tesseract not installed")
def test_tesseract_processing():
    ...
```

### Test Organization Best Practices

- **One assertion concept per test** - Test one thing at a time
- **Descriptive names** - `test_validate_jpeg_with_valid_magic_bytes()`
- **Arrange-Act-Assert** - Clear structure in every test
- **Use fixtures** - Avoid code duplication
- **Fast by default** - Unit tests should run in milliseconds
- **Mock external dependencies** - Keep tests isolated
- **Test error paths** - Don't just test happy paths

### CI/CD Testing

Our GitHub Actions workflow runs tests automatically:

- **Fast Tests Job**: Unit + Integration tests (~5 min)
  - Runs on every push and PR
  - Includes linting, formatting, type checking
  - Uploads coverage to Codecov

- **E2E Tests Job**: Tesseract E2E tests (~2 min)
  - Validates real OCR functionality
  - Runs on every push and PR

- **Slow Tests Job**: EasyOCR E2E tests (~30 min)
  - Runs only on main branch or manual trigger
  - Deep learning model initialization is slow

- **Coverage Report Job**: Generates HTML coverage report
  - Uploads as GitHub artifact
  - 30-day retention

## Code Quality

We maintain high code quality standards using automated tools.

### Code Formatting

We use [Ruff](https://github.com/astral-sh/ruff) for code formatting and linting:

```bash
# Format code
mise run lint:format

# Auto-fix linting issues
mise run lint:lint:fix
```

### Code Style Guidelines

- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Write docstrings for public functions and classes
- Keep functions small and focused (single responsibility)
- Avoid deep nesting (max 3-4 levels)
- Use meaningful variable and function names

### Example Code Style

```python
from typing import Optional
from pydantic import BaseModel

class JobStatus(BaseModel):
    """Represents the status of an OCR job.

    Attributes:
        job_id: Unique identifier for the job
        status: Current status (pending, processing, completed, failed)
        upload_time: ISO timestamp of upload
        error_message: Error details if status is failed
    """
    job_id: str
    status: str
    upload_time: str
    error_message: Optional[str] = None

    def is_complete(self) -> bool:
        """Check if the job has finished processing.

        Returns:
            True if status is completed or failed, False otherwise
        """
        return self.status in ("completed", "failed")
```

### Type Checking

This project uses [ty](https://docs.astral.sh/ty) for static type checking. All code should include type hints:

```bash
# Run type checker
mise run lint:typecheck

# Check specific directory
uv run ty check src/
```

**Note**: Type checking is automatically run via `mise run release:pre-commit`. See [AGENTS.md](AGENTS.md) for task configuration and usage.

## Submitting Changes

### Pull Request Process

1. **Update your fork**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes following TDD**
   - Write tests first
   - Implement the feature
   - Ensure all tests pass
   - Run code formatters

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Open a Pull Request**
   - Go to the original repository
   - Click "New Pull Request"
   - Select your branch
   - Fill out the PR template

### CI/CD Build Strategy

Understanding our CI/CD workflow helps you know what to expect when submitting PRs:

**Automatic Builds on Your PR**:
- ✅ **Lite flavor**: Builds automatically on every PR (~2-3 min)
  - Validates core functionality with Tesseract OCR
  - Fast feedback for most code changes
- ⏭️ **Full flavor**: Skipped on PRs to save CI resources
  - Large PyTorch/EasyOCR dependencies (~10-15 min build)
  - Not needed for most PRs

**When Full Flavor Builds Run**:
- 🏷️ **Release tags** (`v*.*.*`) - Automatic on version releases
- 🔀 **Main branch** pushes - Automatic after PR merge
- 🖱️ **Manual dispatch** - Maintainers can trigger via GitHub Actions UI

**Why This Strategy?**
- Faster PR feedback (3 min vs 15 min)
- Reduced CI costs and resource usage
- Most code changes don't require GPU dependencies
- Full validation happens before releases

**For Maintainers**: To manually build the full flavor for a specific PR:
1. Go to Actions → Docker Image CI → Run workflow
2. Select the PR branch
3. Check "Build full flavor"
4. Run workflow

**What This Means for Contributors**:
- Your PR will show a passing check if lite builds successfully
- If your changes specifically affect EasyOCR functionality, mention it in the PR
- Maintainers may trigger a full build if needed
- All flavors are validated before merging to main

### Pull Request Checklist

Before submitting a PR, ensure:

- [ ] All tests pass (`mise run test:all`)
- [ ] Code is formatted (`mise run lint:format`)
- [ ] Linting passes (`mise run lint:lint`)
- [ ] Coverage is maintained or improved
- [ ] Documentation is updated (if needed)
- [ ] Commit messages follow guidelines
- [ ] PR description clearly explains the changes
- [ ] Related issues are referenced

### PR Review Process

1. **Automated checks will run**:
   - Lite Docker image build (~2-3 min)
   - Tests, linting, and coverage checks
2. **Maintainers will review your code**
3. **Address any feedback or requested changes**
4. **Once approved, your PR will be merged**
   - Full flavor build will run automatically on main branch
   - All flavors validated before release tags

## Bug Reports

When reporting bugs, please include:

### Bug Report Template

```markdown
**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Send request to '...'
2. With payload '....'
3. See error

**Expected behavior**
What you expected to happen.

**Actual behavior**
What actually happened.

**Environment:**
- OS: [e.g., Ubuntu 22.04]
- Python version: [e.g., 3.10.12]
- Tesseract version: [e.g., 5.3.0]

**Logs**
```
Paste relevant log output here
```

**Additional context**
Any other context about the problem.
```

## Feature Requests

When requesting features, please include:

### Feature Request Template

```markdown
**Is your feature request related to a problem?**
A clear description of the problem. Ex. I'm frustrated when [...]

**Describe the solution you'd like**
A clear description of what you want to happen.

**Describe alternatives you've considered**
Alternative solutions or features you've considered.

**Additional context**
Any other context, mockups, or examples.

**Acceptance Criteria**
What would make this feature complete?
- [ ] Criterion 1
- [ ] Criterion 2
```

## Platform Limitations

### macOS-specific Dependencies

The `ocrmac` package provides access to Apple's Vision and LiveText OCR frameworks but has important limitations:

- **Docker Incompatibility**: ocrmac requires macOS-native frameworks that are unavailable in Docker containers (even on Mac hosts)
- **Local Development**: Works only when running the application natively on macOS
- **Alternative Engines**: Tesseract and EasyOCR work in all environments including Docker

For detailed platform requirements and limitations, see the [Platform Limitations section in AGENTS.md](AGENTS.md#platform-limitations).

## Questions?

If you have questions about contributing:

1. Search closed issues for similar questions
2. Open a new issue with the "question" label
3. Join community discussions (if available)

## Code of Conduct

Please be respectful and constructive in all interactions. We're all here to build great software together.

Thank you for contributing to RESTful OCR API!
