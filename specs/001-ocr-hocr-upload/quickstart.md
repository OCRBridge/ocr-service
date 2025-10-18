# Quickstart Guide: OCR Document Upload API

**Feature**: OCR Document Upload with HOCR Output
**Version**: 1.0.0
**Last Updated**: 2025-10-18

## Overview

This guide will help you get the OCR RESTful API up and running locally, perform TDD development, and understand the development workflow.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python**: 3.11 or higher
- **uv**: Latest version (install via `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Redis**: 7.0 or higher (install via package manager or Docker)
- **Tesseract OCR**: 5.3 or higher with English language pack
- **Poppler Utils**: For PDF to image conversion
- **Git**: For version control

### System Dependencies (Ubuntu/Debian)

```bash
# Tesseract OCR
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng

# Poppler utils for PDF processing
sudo apt-get install -y poppler-utils

# Redis (option 1: native)
sudo apt-get install -y redis-server
sudo systemctl start redis
sudo systemctl enable redis

# Redis (option 2: Docker)
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

### System Dependencies (macOS)

```bash
# Homebrew
brew install tesseract tesseract-lang
brew install poppler
brew install redis
brew services start redis
```

## Project Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd restful-ocr
git checkout 001-ocr-hocr-upload
```

### 2. Install Dependencies with uv

```bash
# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install project dependencies
uv pip install -e ".[dev]"
```

### 3. Verify Prerequisites

```bash
# Check Tesseract version
tesseract --version
# Expected: tesseract 5.3.x

# Check Redis connection
redis-cli ping
# Expected: PONG

# Check Python version
python --version
# Expected: Python 3.11.x or higher

# Check poppler (pdfinfo)
pdfinfo -v
# Expected: pdfinfo version 23.x or higher
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# .env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# File Storage
UPLOAD_DIR=/tmp/uploads
RESULTS_DIR=/tmp/results
MAX_UPLOAD_SIZE_MB=25

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60

# Job Configuration
JOB_EXPIRATION_HOURS=48

# OCR Configuration
TESSERACT_LANG=eng
TESSERACT_PSM=3  # Auto page segmentation
TESSERACT_OEM=1  # LSTM only

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Development
DEBUG=false
RELOAD=false  # Set to true for auto-reload during development
```

### Create Required Directories

```bash
mkdir -p /tmp/uploads /tmp/results
chmod 700 /tmp/uploads /tmp/results
```

## Development Workflow (TDD)

### Step 1: Run Existing Tests (Should Fail)

Following the **Test-First** principle from the constitution, tests are written before implementation:

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=src --cov-report=html --cov-report=term

# Run specific test module
uv run pytest tests/unit/test_models.py -v

# Run tests with sample fixtures
uv run pytest tests/integration/test_upload_samples.py -v
```

**Expected Initial State**: Most tests will fail because implementation doesn't exist yet.

### Step 2: Implement to Make Tests Pass

The TDD cycle for each feature:

1. **Write failing test** (already done in test files)
2. **Implement minimal code** to make the test pass
3. **Refactor** while keeping tests green
4. **Repeat** for next test

Example workflow for implementing the upload endpoint:

```bash
# 1. Run upload test (fails)
uv run pytest tests/contract/test_upload_endpoint.py::test_upload_jpeg -v

# 2. Implement src/api/routes/upload.py to make it pass

# 3. Verify test passes
uv run pytest tests/contract/test_upload_endpoint.py::test_upload_jpeg -v

# 4. Run full suite to ensure no regressions
uv run pytest
```

### Step 3: Format Code with Ruff

```bash
# Format all Python files
uv run ruff format src/ tests/

# Check for linting issues
uv run ruff check src/ tests/

# Auto-fix linting issues
uv run ruff check --fix src/ tests/
```

### Step 4: Verify Constitution Compliance

Before committing, ensure all gates pass:

```bash
# Coverage check (minimum 80% overall, 90% for utilities)
uv run pytest --cov=src --cov-report=term --cov-fail-under=80

# Type checking (via Pydantic validation in tests)
uv run pytest tests/unit/test_models.py

# Performance smoke test
uv run pytest tests/performance/ -v

# Contract validation
uv run pytest tests/contract/ -v
```

## Running the API

### Local Development Server

```bash
# Standard run (manual restart on code changes)
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000

# Development mode (auto-reload on code changes)
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# With specific number of workers (production-like)
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker Compose (Full Stack)

```bash
# Start all services (API + Redis)
docker compose up -d

# View logs
docker compose logs -f api

# Stop services
docker compose down
```

## API Usage Examples

### 1. Upload a Document

```bash
# Upload JPEG
curl -X POST http://localhost:8000/upload \
  -F "file=@samples/numbers_gs150.jpg" \
  -H "Content-Type: multipart/form-data"

# Response:
# {
#   "job_id": "Kj4TY2vN8xQz9wR5pL7mH3fC1sD6aB8nE0gU4tV2iX1",
#   "status": "pending",
#   "message": "Upload successful, processing started"
# }
```

### 2. Check Job Status

```bash
JOB_ID="Kj4TY2vN8xQz9wR5pL7mH3fC1sD6aB8nE0gU4tV2iX1"

curl -X GET "http://localhost:8000/jobs/${JOB_ID}/status"

# Response (completed):
# {
#   "job_id": "Kj4TY...",
#   "status": "completed",
#   "upload_time": "2025-10-18T10:00:00Z",
#   "start_time": "2025-10-18T10:00:05Z",
#   "completion_time": "2025-10-18T10:00:12Z",
#   "expiration_time": "2025-10-20T10:00:12Z",
#   "error_message": null,
#   "error_code": null
# }
```

### 3. Download HOCR Result

```bash
curl -X GET "http://localhost:8000/jobs/${JOB_ID}/result" \
  -o result.hocr

# View HOCR in browser (preserves bounding boxes)
open result.hocr  # macOS
xdg-open result.hocr  # Linux
```

### 4. Health Check

```bash
curl -X GET http://localhost:8000/health

# Response:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "uptime_seconds": 3600
# }
```

### 5. Prometheus Metrics

```bash
curl -X GET http://localhost:8000/metrics

# Response (text/plain):
# http_requests_total{method="POST",path="/upload",status="202"} 1234
# http_request_duration_seconds_bucket{...} ...
```

## Testing with Sample Documents

The `samples/` directory contains test fixtures for TDD:

### Using Sample Files in Tests

```python
# tests/integration/test_samples.py
import pytest
from pathlib import Path

SAMPLES_DIR = Path(__file__).parent.parent.parent / "samples"

@pytest.mark.parametrize("sample_file", [
    "numbers_gs150.jpg",
    "stock_gs200.jpg",
    "mietvertrag.pdf"
])
def test_ocr_samples(client, sample_file):
    """Test OCR processing with real sample documents"""
    sample_path = SAMPLES_DIR / sample_file

    # Upload
    with open(sample_path, 'rb') as f:
        response = client.post("/upload", files={"file": f})
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # Poll status (with timeout)
    max_wait = 30
    for _ in range(max_wait):
        status_response = client.get(f"/jobs/{job_id}/status")
        status = status_response.json()["status"]
        if status in ["completed", "failed"]:
            break
        time.sleep(1)

    # Verify success
    assert status == "completed"

    # Download result
    result_response = client.get(f"/jobs/{job_id}/result")
    assert result_response.status_code == 200
    hocr_content = result_response.text

    # Validate HOCR structure
    assert '<?xml version="1.0"' in hocr_content
    assert 'ocr_page' in hocr_content
    assert 'bbox' in hocr_content  # Bounding boxes present
```

### Manual Testing with Samples

```bash
# Test with low DPI grayscale JPEG
curl -X POST http://localhost:8000/upload \
  -F "file=@samples/numbers_gs150.jpg"

# Test with medium DPI grayscale JPEG
curl -X POST http://localhost:8000/upload \
  -F "file=@samples/stock_gs200.jpg"

# Test with multi-page PDF
curl -X POST http://localhost:8000/upload \
  -F "file=@samples/mietvertrag.pdf"
```

## Performance Testing

### Latency Benchmarks

```bash
# Install Apache Bench (if not present)
sudo apt-get install apache2-utils

# Test status endpoint latency (should be <800ms p95)
ab -n 1000 -c 10 http://localhost:8000/jobs/test-job-id/status

# Analyze results
# Look for: "Percentage of requests served within a certain time"
# 95% should be under 800ms
```

### Memory Profiling

```bash
# Install memory_profiler
uv pip install memory-profiler

# Profile OCR processing
python -m memory_profiler src/services/ocr_processor.py

# Expected: Peak memory <512MB per request (constitution requirement)
```

## Observability

### Structured Logs

Logs are output in JSON format for machine parsing:

```bash
# View logs
tail -f logs/app.log | jq .

# Filter by log level
tail -f logs/app.log | jq 'select(.level == "error")'

# Filter by request_id
tail -f logs/app.log | jq 'select(.request_id == "req_abc123")'
```

### Prometheus Metrics

Metrics are exposed at `/metrics` in Prometheus format:

```bash
# View all metrics
curl http://localhost:8000/metrics

# View in Prometheus (if running)
# Add scrape target to prometheus.yml:
# - targets: ['localhost:8000']

# View in Grafana (if running)
# Import dashboard from grafana/dashboards/api-metrics.json
```

## Troubleshooting

### Issue: Tesseract not found

```bash
# Verify Tesseract installation
which tesseract
tesseract --list-langs

# If not found, install:
# Ubuntu: sudo apt-get install tesseract-ocr tesseract-ocr-eng
# macOS: brew install tesseract tesseract-lang
```

### Issue: Redis connection failed

```bash
# Check Redis is running
redis-cli ping

# If not running:
# Ubuntu: sudo systemctl start redis
# macOS: brew services start redis
# Docker: docker run -d -p 6379:6379 redis:7-alpine

# Check Redis URL in .env matches your setup
```

### Issue: PDF processing fails

```bash
# Verify poppler-utils installed
pdfinfo -v

# If not found, install:
# Ubuntu: sudo apt-get install poppler-utils
# macOS: brew install poppler
```

### Issue: Rate limit errors in tests

```bash
# Flush Redis between test runs
redis-cli FLUSHALL

# Or run tests with isolated Redis database
REDIS_URL=redis://localhost:6379/1 pytest
```

### Issue: Tests fail due to missing fixtures

```bash
# Ensure samples directory exists
ls -la samples/

# Should contain:
# - numbers_gs150.jpg
# - stock_gs200.jpg
# - mietvertrag.pdf

# If missing, they should be committed to the repository
```

## Code Organization

```
restful-ocr/
├── src/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Pydantic settings (from .env)
│   ├── models/                 # Pydantic data models
│   │   ├── job.py              # OCRJob, JobStatus, ErrorCode
│   │   ├── upload.py           # DocumentUpload, FileFormat
│   │   ├── result.py           # HOCRResult
│   │   └── responses.py        # API response models
│   ├── api/
│   │   ├── routes/
│   │   │   ├── upload.py       # POST /upload
│   │   │   ├── jobs.py         # GET /jobs/{id}/status, /result
│   │   │   └── health.py       # GET /health, /metrics
│   │   └── middleware/
│   │       ├── rate_limit.py   # Rate limiting logic
│   │       └── logging.py      # Request logging
│   ├── services/
│   │   ├── ocr_processor.py    # Tesseract wrapper
│   │   ├── job_manager.py      # Redis job state management
│   │   ├── file_handler.py     # Upload/temp file handling
│   │   └── cleanup.py          # Expired file cleanup
│   └── utils/
│       ├── validators.py       # File format validation
│       ├── hocr.py              # HOCR parsing utilities
│       └── security.py         # Job ID generation
├── tests/
│   ├── unit/                   # 90% coverage target
│   │   ├── test_models.py
│   │   ├── test_validators.py
│   │   └── test_job_manager.py
│   ├── integration/            # 80% coverage target
│   │   ├── test_upload_samples.py
│   │   └── test_expiration.py
│   ├── contract/               # OpenAPI compliance
│   │   ├── test_upload_endpoint.py
│   │   ├── test_status_endpoint.py
│   │   └── test_result_endpoint.py
│   ├── performance/            # Latency/memory budgets
│   │   ├── test_endpoint_latency.py
│   │   └── test_memory_usage.py
│   └── conftest.py             # Pytest fixtures
├── samples/                    # TDD fixtures
│   ├── numbers_gs150.jpg
│   ├── stock_gs200.jpg
│   └── mietvertrag.pdf
├── specs/001-ocr-hocr-upload/  # Design docs
│   ├── spec.md
│   ├── plan.md
│   ├── research.md
│   ├── data-model.md
│   ├── quickstart.md (this file)
│   └── contracts/
│       └── openapi.yaml
├── pyproject.toml              # Project metadata, dependencies
├── uv.lock                     # Locked dependencies
├── .env                        # Environment configuration
├── .python-version             # Python 3.11
├── docker compose.yml          # Full stack setup
├── Dockerfile                  # API container
└── README.md                   # Project overview
```

## Next Steps

1. **Read the Specification**: Review `specs/001-ocr-hocr-upload/spec.md` for requirements
2. **Read the Plan**: Review `specs/001-ocr-hocr-upload/plan.md` for architecture
3. **Read the Data Model**: Review `specs/001-ocr-hocr-upload/data-model.md` for entities
4. **Review OpenAPI Contract**: Open `specs/001-ocr-hocr-upload/contracts/openapi.yaml` in Swagger Editor
5. **Run Tests**: `pytest` to see current implementation status
6. **Start TDD**: Pick a failing test and implement the feature to make it pass
7. **Check Constitution**: Ensure each PR meets all 7 core principles

## Resources

- **FastAPI Documentation**: https://fastapi.tiangolo.com
- **Pydantic Documentation**: https://docs.pydantic.dev
- **Tesseract OCR**: https://github.com/tesseract-ocr/tesseract
- **HOCR Specification**: https://github.com/kba/hocr-spec
- **uv Package Manager**: https://github.com/astral-sh/uv
- **Ruff Formatter**: https://docs.astral.sh/ruff/
- **Project Constitution**: `.specify/memory/constitution.md`

## Support

For questions or issues:
1. Check this quickstart guide
2. Review the specification and plan documents
3. Check existing tests for examples
4. Review constitution compliance checklist
5. Open an issue with reproduction steps
