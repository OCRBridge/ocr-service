# restful-ocr Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-18

## Active Technologies
- Python 3.11+ (001-ocr-hocr-upload)
- FastAPI 0.104+ (Web framework)
- Pydantic 2.5+ (Data validation)
- Uvicorn 0.24+ (ASGI server)
- Tesseract 5.3+ (OCR engine via pytesseract)
- Redis 7.0+ (Job state storage)
- pytest 7.4+ (Testing framework)
- Python 3.11+ + FastAPI 0.104+, Pydantic 2.5+, pytesseract 0.3+, Tesseract 5.3+ (002-tesseract-params)
- Redis 7.0+ (job state), filesystem (temporary uploaded files) (002-tesseract-params)
- Redis 7.0+ (job state), filesystem (temporary uploaded files, results) (003-multi-engine-ocr)
- Python 3.11+ + FastAPI 0.104+, Pydantic 2.5+, EasyOCR (new), PyTorch (new - EasyOCR dependency), pytesseract 0.3+, Redis 7.0+ (004-easyocr-engine)
- Redis 7.0+ (job state), filesystem (temporary uploaded files, results), configurable persistent volume (EasyOCR models, 5GB default) (004-easyocr-engine)
- Python 3.11 + FastAPI 0.104+, Pydantic 2.5+, pytest 7.4+ (005-remove-generic-upload)

## Project Structure
```
src/                    # Application source code
├── main.py            # FastAPI app entry point
├── config.py          # Pydantic settings
├── models/            # Data models
├── api/               # API routes and middleware
├── services/          # Business logic
└── utils/             # Shared utilities
tests/                 # Test suite (TDD)
├── unit/              # Unit tests
├── integration/       # Integration tests
├── contract/          # OpenAPI contract tests
└── performance/       # Performance tests
samples/               # Test fixtures
specs/                 # Design documentation
```

## Commands

### Development
```bash
# Install dependencies
uv sync --group dev

# Run development server
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
uv run pytest                                    # All tests
uv run pytest tests/unit/                        # Unit tests only
uv run pytest tests/integration/                 # Integration tests only
uv run pytest tests/contract/                    # Contract tests only

# Run tests with coverage
uv run pytest --cov=src --cov-report=html --cov-report=term

# Code formatting and linting
uv run ruff format src/ tests/                   # Format code
uv run ruff check src/ tests/                    # Check for linting errors
uv run ruff check src/ tests/ --fix             # Auto-fix linting errors
```

### Docker
```bash
# Start services (API + Redis)
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f api
```

### Redis
```bash
# Check Redis connection
redis-cli ping

# Monitor Redis operations
redis-cli monitor

# Flush test data
redis-cli flushdb
```

## Code Style
Python 3.11+: Follow PEP 8 conventions, enforced via ruff

### Key Conventions
- Use type hints for all function parameters and return values
- Pydantic models for all data validation
- Async/await for I/O operations
- Structured logging with structlog (JSON format)
- 80% overall test coverage, 90% for utilities

## Recent Changes
- 005-remove-generic-upload: Added Python 3.11 + FastAPI 0.104+, Pydantic 2.5+, pytest 7.4+
- 004-easyocr-engine: Added Python 3.11+ + FastAPI 0.104+, Pydantic 2.5+, EasyOCR (new), PyTorch (new - EasyOCR dependency), pytesseract 0.3+, Redis 7.0+
- 004-easyocr-engine: Added Python 3.11+ + FastAPI 0.104+, Pydantic 2.5+, EasyOCR (new), PyTorch (new - EasyOCR dependency), pytesseract 0.3+, Redis 7.0+

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
