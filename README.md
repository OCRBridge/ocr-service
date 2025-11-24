# RESTful OCR API

A high-performance RESTful API service for document OCR processing with modular engine architecture using datenzar OCR Bridge packages.

## Features

- **Modular Engine Architecture**: Plugin-based OCR engines via PyPI packages
- **Multi-format Support**: Process JPEG, PNG, PDF, and TIFF documents
- **HOCR Output**: Industry-standard HTML-based OCR with bounding boxes and text hierarchy
- **Multiple OCR Engines**: Tesseract, EasyOCR, and ocrmac (macOS only)
- **Dynamic Engine Discovery**: Automatically detects installed engine packages
- **Engine-agnostic API**: Unified endpoint works with any installed engine
- **No Authentication**: Public API for easy integration

## Architecture

This service uses a **modular plugin architecture** powered by the [datenzar OCR Bridge packages](https://pypi.org/user/datenzar/):

- **Core Framework**: FastAPI with async/await
- **Base Package**: `ocrbridge-core` - Base classes and utilities
- **Engine Packages** (optional, installed separately):
  - `ocrbridge-tesseract` - Tesseract OCR (100+ languages)
  - `ocrbridge-easyocr` - EasyOCR deep learning (80+ languages, GPU support)
  - `ocrbridge-ocrmac` - Apple Vision framework (macOS only)
- **Engine Discovery**: Python entry points for automatic detection
- **Job Store**: Redis for rate limiting
- **Logging**: structlog (JSON format)
- **Metrics**: Prometheus client

### How It Works

1. OCR engine packages register themselves via Python entry points (`ocrbridge.engines`)
2. On startup, the service discovers all installed engines dynamically
3. API endpoints work with any engine - no code changes needed
4. Add new engines by installing packages, no service modification required

## Installation

### Prerequisites

- Python 3.11+
- Redis server

### Base Installation

Install the core service (no engines):

```bash
# Clone the repository
git clone <repository-url>
cd ocr-service

# Install base dependencies
pip install -e .
```

### Install OCR Engines

Choose which engines to install:

```bash
# Option 1: Install Tesseract engine
pip install -e .[tesseract]
# System requirement: tesseract binary must be installed
# Ubuntu/Debian: sudo apt-get install tesseract-ocr
# macOS: brew install tesseract

# Option 2: Install EasyOCR engine (includes PyTorch, ~2GB)
pip install -e .[easyocr]

# Option 3: Install ocrmac engine (macOS only)
pip install -e .[ocrmac]

# Option 4: Install all engines
pip install -e .[full]
```

### Engine Comparison

| Engine | Package | Accuracy | Speed | GPU Support | Languages | Size Impact |
|--------|---------|----------|-------|-------------|-----------|-------------|
| **Tesseract** | `ocrbridge-tesseract` | Good | Fast | No | 100+ | ~500MB |
| **EasyOCR** | `ocrbridge-easyocr` | Excellent | Medium | Yes | 80+ | +2GB (PyTorch) |
| **ocrmac** | `ocrbridge-ocrmac` | Excellent | Very Fast | Yes (Apple Neural Engine) | 30+ | +10MB (macOS only) |

## Quick Start

### 1. Start Redis

```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Or use Docker
docker run -d -p 6379:6379 redis:alpine
```

### 2. Install an OCR Engine

```bash
# Install Tesseract engine (lightest option)
pip install -e .[tesseract]

# Make sure tesseract binary is installed
# macOS: brew install tesseract
# Ubuntu: sudo apt-get install tesseract-ocr
```

### 3. Run the Service

```bash
uvicorn src.main:app --reload
```

The API will be available at `http://localhost:8000`.

### 4. Verify Installation

```bash
# Health check
curl http://localhost:8000/health

# List available engines
curl http://localhost:8000/v2/ocr/engines

# Check engine parameter schema
curl http://localhost:8000/v2/ocr/engines/tesseract/schema
```

## API Usage

### Process a Document

The unified `/v2/ocr/process` endpoint works with any installed engine:

```bash
# Process with Tesseract
curl -X POST http://localhost:8000/v2/ocr/process \
  -F "file=@document.pdf" \
  -F "engine=tesseract"

# Process with custom parameters (JSON string)
curl -X POST http://localhost:8000/v2/ocr/process \
  -F "file=@document.pdf" \
  -F "engine=tesseract" \
  -F 'params={"lang": "eng+fra", "psm": 3, "dpi": 300}'

# Process with EasyOCR (if installed)
curl -X POST http://localhost:8000/v2/ocr/process \
  -F "file=@document.pdf" \
  -F "engine=easyocr" \
  -F 'params={"languages": ["en", "ch_sim"], "text_threshold": 0.7}'

# Process with ocrmac (macOS only, if installed)
curl -X POST http://localhost:8000/v2/ocr/process \
  -F "file=@document.pdf" \
  -F "engine=ocrmac" \
  -F 'params={"languages": ["en-US"], "recognition_level": "accurate"}'
```

**Response**:
```json
{
  "hocr": "<?xml version='1.0' encoding='UTF-8'?>...",
  "processing_duration_seconds": 2.456,
  "engine": "tesseract",
  "pages": 1
}
```

### List Available Engines

```bash
curl http://localhost:8000/v2/ocr/engines
```

**Response**:
```json
{
  "engines": ["tesseract", "easyocr"],
  "count": 2,
  "details": [
    {
      "name": "tesseract",
      "class": "TesseractEngine",
      "supported_formats": [".jpg", ".jpeg", ".png", ".tiff", ".tif", ".pdf"],
      "has_param_model": true
    }
  ]
}
```

### Get Engine Parameter Schema

```bash
curl http://localhost:8000/v2/ocr/engines/tesseract/schema
```

**Response**:
```json
{
  "engine": "tesseract",
  "schema": {
    "properties": {
      "lang": {
        "type": "string",
        "description": "Language code(s): 'eng', 'fra', 'eng+fra' (max 5)",
        "pattern": "^[a-z_]{3,7}(\\+[a-z_]{3,7})*$"
      },
      "psm": {
        "type": "integer",
        "minimum": 0,
        "maximum": 13,
        "description": "Page segmentation mode (0-13)"
      },
      "oem": {
        "type": "integer",
        "minimum": 0,
        "maximum": 3,
        "description": "OCR Engine mode: 0=Legacy, 1=LSTM, 2=Both, 3=Default"
      },
      "dpi": {
        "type": "integer",
        "minimum": 70,
        "maximum": 2400,
        "description": "Image DPI (70-2400, typical: 300)"
      }
    }
  }
}
```

### Other Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Prometheus metrics
curl http://localhost:8000/metrics
```

## Configuration

Configuration via environment variables:

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# API Configuration
MAX_UPLOAD_SIZE_MB=5
RATE_LIMIT_REQUESTS=100

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## Engine-Specific Parameters

### Tesseract Parameters

From `ocrbridge-tesseract`:

- `lang` (string): Language codes, e.g., "eng", "eng+fra" (max 5 languages)
- `psm` (integer 0-13): Page segmentation mode
- `oem` (integer 0-3): OCR engine mode (0=Legacy, 1=LSTM, 2=Both, 3=Default)
- `dpi` (integer 70-2400): DPI for PDF conversion (default: 300)

### EasyOCR Parameters

From `ocrbridge-easyocr`:

- `languages` (list of strings): Language codes, e.g., ["en", "ch_sim"] (max 5)
- `text_threshold` (float 0.0-1.0): Confidence threshold for text detection (default: 0.7)
- `link_threshold` (float 0.0-1.0): Threshold for linking text regions (default: 0.7)

### ocrmac Parameters

From `ocrbridge-ocrmac` (macOS only):

- `languages` (list of strings): IETF BCP 47 codes, e.g., ["en-US", "fr-FR"] (max 5)
- `recognition_level` (string): "fast", "balanced" (default), "accurate", or "livetext"

## Adding Custom Engines

To create a custom OCR engine:

1. Create a Python package that depends on `ocrbridge-core>=1.0.0`
2. Implement `OCREngine` base class from `ocrbridge.core`
3. Register via entry point in `pyproject.toml`:

```toml
[project.entry-points."ocrbridge.engines"]
my_engine = "my_package:MyEngine"
```

4. Install your package - the service will automatically discover it!

No code changes to the service required.

## Development

### Install Development Dependencies

```bash
# Install with uv (recommended)
pip install uv
uv sync --group dev

# Or with pip
pip install -e .[tesseract] -r requirements-dev.txt
```

### Run Linting and Type Checking

```bash
# Using uv
uv run ruff check src/
uv run pyright src/

# Using make
make lint
make typecheck
```

### Project Structure

```
ocr-service/
├── src/
│   ├── api/
│   │   └── routes/
│   │       └── v2/
│   │           └── ocr.py          # V2 unified OCR endpoints
│   ├── services/
│   │   └── ocr/
│   │       └── registry_v2.py      # Entry point discovery registry
│   ├── models/
│   │   └── responses.py            # API response models
│   └── main.py                      # FastAPI application
├── pyproject.toml                   # Dependencies and entry points
└── README.md
```

## Deployment

### Docker Deployment

```bash
# Build image
docker build -t ocr-service:latest .

# Run with Redis
docker run -d -p 8000:8000 \
  -e REDIS_URL=redis://redis:6379/0 \
  ocr-service:latest
```

### Production Considerations

- **Horizontal Scaling**: Service is stateless (except Redis for rate limiting)
- **Engine Installation**: Install only needed engines to minimize image size
- **GPU Support**: Use GPU-enabled base image for EasyOCR
- **Health Monitoring**: Use `/health` endpoint for liveness/readiness probes
- **Metrics**: Scrape `/metrics` with Prometheus

## Troubleshooting

### No Engines Detected

```bash
# Check if engine packages are installed
pip list | grep ocrbridge

# Check logs for engine discovery
# Look for: "ocr_engines_discovered"
```

### Engine Import Errors

```bash
# For Tesseract: Ensure tesseract binary is installed
which tesseract

# For ocrmac: Only works on macOS, not in Docker
uname -s  # Should return "Darwin"
```

### Rate Limiting

Default: 100 requests/minute per IP. Configure with `RATE_LIMIT_REQUESTS`.

## License

[Add your license here]

## Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [datenzar OCR Bridge](https://pypi.org/user/datenzar/) - Modular OCR engines
- [Redis](https://redis.io/) - Rate limiting backend
- [structlog](https://www.structlog.org/) - Structured logging
