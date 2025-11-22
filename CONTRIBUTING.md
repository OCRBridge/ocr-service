# Contributing to RESTful OCR API

Thank you for your interest in contributing to RESTful OCR API! This document provides guidelines and instructions for contributing features and bug fixes to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Environment Setup](#development-environment-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Submitting Changes](#submitting-changes)
- [Bug Reports](#bug-reports)
- [Feature Requests](#feature-requests)

## Getting Started

Before you begin contributing, please:

1. Read the [README.md](README.md) to understand the project
2. Check existing [issues](../../issues) and [pull requests](../../pulls) to avoid duplicates
3. Join our community discussions (if applicable)

## Development Environment Setup

### Prerequisites

- Python 3.11+
- Redis 7.0+
- Tesseract OCR 5.3+
- Poppler utils (for PDF processing)
- uv (Python package manager)
- Git

### Installation

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/restful-ocr.git
cd restful-ocr

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/restful-ocr.git

# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng poppler-utils redis-server

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv sync --group dev

# Create required directories
mkdir -p /tmp/uploads /tmp/results
chmod 700 /tmp/uploads /tmp/results

# Copy environment configuration
cp .env.example .env

# Start Redis
sudo systemctl start redis
```

### Running the Development Server

```bash
# Development mode with auto-reload
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

## Project Structure

Understanding the project structure will help you navigate the codebase:

```
restful-ocr/
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
├── docker-compose.yml     # Docker stack configuration
└── Dockerfile             # API container image
```

### Key Directories

- **src/models/**: Define data models, request/response schemas, and domain objects
- **src/api/routes/**: Implement API endpoints
- **src/services/**: Implement business logic, OCR processing, and external integrations
- **tests/unit/**: Write unit tests with mocks/stubs for isolated testing
- **tests/integration/**: Write integration tests that use real services (Redis, Tesseract)

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

This project follows the **[Conventional Commits](https://www.conventionalcommits.org/)** specification for commit messages. This enables automatic version bumping and changelog generation through semantic-release.

#### Commit Message Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

#### Commit Types

- **`feat`**: A new feature (triggers a MINOR version bump)
- **`fix`**: A bug fix (triggers a PATCH version bump)
- **`docs`**: Documentation only changes
- **`style`**: Changes that don't affect code meaning (formatting, missing semicolons, etc.)
- **`refactor`**: Code change that neither fixes a bug nor adds a feature
- **`perf`**: Performance improvements (triggers a PATCH version bump)
- **`test`**: Adding or updating tests
- **`build`**: Changes to build system or dependencies
- **`ci`**: Changes to CI configuration files
- **`chore`**: Other changes that don't modify src or test files

#### Breaking Changes

To trigger a MAJOR version bump, add `BREAKING CHANGE:` in the commit body or append `!` after the type/scope:

```
feat!: remove deprecated OCR engine support

BREAKING CHANGE: The legacy OCR engine has been removed.
Use Tesseract or EasyOCR instead.
```

#### Examples

```bash
# Feature commit (MINOR version bump: 1.1.0 -> 1.2.0)
feat: add support for TIFF multi-page documents

Implemented TIFF processing using PIL to extract and process
multiple pages from TIFF files. Each page is converted to JPEG
before OCR processing.

Closes #123

# Bug fix commit (PATCH version bump: 1.1.0 -> 1.1.1)
fix: resolve rate limiting bypass vulnerability

Fixed race condition in rate limiter that allowed requests
to bypass rate limits under high concurrency.

Fixes #456

# Breaking change (MAJOR version bump: 1.1.0 -> 2.0.0)
feat!: redesign API response format

BREAKING CHANGE: API responses now use a standardized envelope format.
All clients must be updated to parse the new response structure.
```

#### Using Commitizen

To ensure your commits follow the conventional format, use the provided commitizen tool:

```bash
# Interactive commit helper
make commit

# Or directly with commitizen
uv run cz commit
```

This will guide you through creating a properly formatted commit message.

#### Commit Validation

Pre-commit hooks automatically validate commit messages. If your commit message doesn't follow the conventional format, the commit will be rejected with a helpful error message.

## Testing

Testing is a critical part of our development process. All contributions must include appropriate tests.

> **Quick Command Reference**: For a quick reference of all development commands (testing, formatting, type checking, Docker, etc.), see [AGENTS.md](AGENTS.md).

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=src --cov-report=html --cov-report=term

# Run specific test module
uv run pytest tests/unit/test_models.py -v

# Run integration tests
uv run pytest tests/integration/ -v

# Run tests matching a pattern
uv run pytest -k "test_upload" -v
```

### Coverage Requirements

- **Unit tests**: Aim for 90%+ coverage
- **Integration tests**: Aim for 80%+ coverage
- New code should maintain or improve existing coverage

### Writing Tests

#### Unit Tests

Unit tests should be fast, isolated, and test a single unit of functionality:

```python
# tests/unit/test_job_service.py
import pytest
from unittest.mock import Mock, patch
from src.services.job_service import JobService

@patch('src.services.job_service.redis_client')
def test_create_job_generates_unique_id(mock_redis):
    """Test that job creation generates a unique job ID."""
    service = JobService()
    job_id = service.create_job("test.jpg")

    assert len(job_id) == 48
    assert job_id.isalnum()
    mock_redis.set.assert_called_once()
```

#### Integration Tests

Integration tests verify that components work together correctly:

```python
# tests/integration/test_ocr_processing.py
import pytest
from src.services.ocr_service import OCRService

def test_ocr_processes_sample_image():
    """Test OCR processing with a real sample image."""
    service = OCRService()
    result = service.process_image("samples/numbers_gs150.jpg")

    assert result.text is not None
    assert len(result.text) > 0
    assert "hocr" in result.format
```

### Test Organization

- Group related tests in classes
- Use descriptive test names that explain what is being tested
- Follow the Arrange-Act-Assert pattern
- Use fixtures for common setup

## Code Quality

We maintain high code quality standards using automated tools.

### Code Formatting

We use [Ruff](https://github.com/astral-sh/ruff) for code formatting and linting:

```bash
# Format code
uv run ruff format src/ tests/

# Check linting
uv run ruff check src/ tests/

# Auto-fix linting issues
uv run ruff check --fix src/ tests/
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

This project uses [Pyright](https://github.com/microsoft/pyright) for static type checking. All code should include type hints:

```bash
# Run type checker
uv run pyright

# Check specific directory
uv run pyright src/

# Watch mode for continuous checking
uv run pyright --watch
```

**Note**: Type checking is automatically run via pre-commit hooks. See [AGENTS.md](AGENTS.md) for pre-commit hook configuration and commands.

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

### Pull Request Checklist

Before submitting a PR, ensure:

- [ ] All tests pass (`uv run pytest`)
- [ ] Code is formatted (`uv run ruff format`)
- [ ] Linting passes (`uv run ruff check`)
- [ ] Coverage is maintained or improved
- [ ] Documentation is updated (if needed)
- [ ] Commit messages follow guidelines
- [ ] PR description clearly explains the changes
- [ ] Related issues are referenced

### PR Review Process

1. Automated checks will run (tests, linting, coverage)
2. Maintainers will review your code
3. Address any feedback or requested changes
4. Once approved, your PR will be merged

## Semantic Versioning and Releases

This project uses **[Semantic Versioning](https://semver.org/)** (SemVer) and automated release management through **[Python Semantic Release](https://python-semantic-release.readthedocs.io/)**.

### Version Format

Versions follow the format: `MAJOR.MINOR.PATCH` (e.g., `1.2.3`)

- **MAJOR**: Incremented for breaking changes (incompatible API changes)
- **MINOR**: Incremented for new features (backward-compatible)
- **PATCH**: Incremented for bug fixes (backward-compatible)

### Automatic Releases

When commits are merged to the `main` branch:

1. **Semantic Release analyzes commits** to determine the next version
2. **Version is bumped** in `pyproject.toml`
3. **CHANGELOG.md is updated** with new changes
4. **Git tag is created** (e.g., `v1.2.0`)
5. **GitHub Release is published** with release notes

### Triggering Version Bumps

Your commit messages directly control version bumps:

| Commit Type | Version Bump | Example |
|-------------|--------------|---------|
| `feat:` | MINOR (1.1.0 → 1.2.0) | `feat: add TIFF support` |
| `fix:` | PATCH (1.1.0 → 1.1.1) | `fix: resolve memory leak` |
| `perf:` | PATCH (1.1.0 → 1.1.1) | `perf: optimize image processing` |
| `feat!:` or `BREAKING CHANGE:` | MAJOR (1.1.0 → 2.0.0) | `feat!: remove deprecated API` |
| `docs:`, `chore:`, etc. | No bump | `docs: update README` |

### Testing Releases Locally

Before merging, you can test what version would be released:

```bash
# Preview the next version without making changes
make release-dry-run

# View current version
make version

# Generate changelog preview
make changelog
```

### Release Workflow (Maintainers)

Releases are fully automated via GitHub Actions. When a PR is merged to `main`:

1. The `release.yml` workflow triggers automatically
2. Semantic Release analyzes commits since the last release
3. If releasable commits exist, a new version is published
4. GitHub Release is created with auto-generated release notes

No manual intervention is required for releases.

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
- Python version: [e.g., 3.11.5]
- Redis version: [e.g., 7.0.12]
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
