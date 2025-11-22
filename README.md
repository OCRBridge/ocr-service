# RESTful OCR API

A high-performance RESTful API service for document OCR processing with HOCR (HTML-based OCR) output format.

## Features

- **Multi-format Support**: Process JPEG, PNG, PDF, and TIFF documents
- **HOCR Output**: Industry-standard HTML-based OCR with bounding boxes and text hierarchy
- **Async Processing**: Job-based async processing with status polling
- **Rate Limiting**: 100 requests/minute per IP address
- **Auto-expiration**: Results auto-delete after 48 hours
- **No Authentication**: Public API for easy integration
- **High Performance**: <30s processing time for typical documents

## OCR Engine Flavors

This service supports multiple OCR engines with different capabilities and resource requirements. Choose the right flavor for your deployment:

| Flavor | Engines | Docker Build Target | Installation | Best For |
|--------|---------|---------------------|--------------|----------|
| **Lite** | Tesseract only | `--target lite` | `pip install .` | CPU-only, resource-constrained, edge devices |
| **Full** | Tesseract + EasyOCR | `--target full` | `pip install .[easyocr]` | GPU-enabled servers, high-accuracy OCR |
| **macOS Native** | All (Tesseract + EasyOCR + ocrmac) | N/A (no Docker) | `pip install .[full]` | Local macOS development, native Vision framework |

### Engine Comparison

| Engine | Accuracy | Speed | GPU Support | Languages | Size Impact |
|--------|----------|-------|-------------|-----------|-------------|
| **Tesseract** | Good | Fast | No | 100+ | ~500MB (base) |
| **EasyOCR** | Excellent | Medium | Yes | 80+ | +2GB (PyTorch) |
| **ocrmac** | Excellent | Very Fast | Yes (Apple Neural Engine) | 30+ | +10MB (macOS only) |

## Quick Start

### Option 1: Docker (Lite - Tesseract Only)

**Best for**: Production deployments, CPU-only environments, smallest image size

```bash
# Build lite image using multi-stage build target
docker build --target lite -t ocr-service:lite .

# Run lite image
docker run -d -p 8000:8000 --name ocr-service \
  -e REDIS_URL=redis://redis:6379/0 \
  ocr-service:lite

# Or use docker-compose (uses docker-compose.base.yml + docker-compose.lite.yml)
docker compose -f docker-compose.base.yml -f docker-compose.lite.yml up -d
```

**Image size**: ~500MB

### Option 2: Docker (Full - Tesseract + EasyOCR)

**Best for**: GPU-enabled servers, high-accuracy requirements

```bash
# Build full image using multi-stage build target
docker build --target full -t ocr-service:full .

# Run full image
docker run -d -p 8000:8000 --name ocr-service \
  -e REDIS_URL=redis://redis:6379/0 \
  --gpus all \  # Optional: Enable GPU support
  ocr-service:full

# Or use docker-compose (merges base + full compose files)
docker compose -f docker-compose.base.yml -f docker-compose.yml up -d

# With GPU support (uncomment GPU section in docker-compose.yml first)
docker compose -f docker-compose.base.yml -f docker-compose.yml up -d
```

**Image size**: ~2.5GB

**Note**: Both flavors are built from a single `Dockerfile` using multi-stage builds. The base layers are shared between targets, improving build efficiency.

### Option 3: Local Development

**Best for**: Development and testing

> **For Contributors**: See [CONTRIBUTING.md](CONTRIBUTING.md) for the complete development setup guide, including Makefile commands, testing instructions, and workflow details.

**macOS (with native Vision framework support)**:
```bash
# Install with all engines (including ocrmac)
pip install -e .[full]

# Or install specific flavors:
pip install -e .[easyocr]  # Tesseract + EasyOCR only
pip install -e .[ocrmac]   # Tesseract + ocrmac only

# Start Redis
brew install redis
brew services start redis

# Run the service
uvicorn src.main:app --reload
```

### Option 4: Local Development (Linux/Windows)

**Best for**: Non-macOS development environments

```bash
# Install base (Tesseract only)
pip install -e .

# Or install with EasyOCR
pip install -e .[easyocr]

# Install system dependencies
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr redis-server poppler-utils

# Fedora/RHEL:
sudo dnf install tesseract redis poppler-utils

# Run the service
uvicorn src.main:app --reload
```

### Verify Installation

The API will be available at `http://localhost:8000`. Check available engines:

```bash
# Health check
curl http://localhost:8000/health

# Check logs for detected engines
# You should see: "ocr_engines_detected" with available_engines list
```

### Selecting an OCR Engine

You can specify the engine when uploading documents:

```bash
# Use Tesseract (default)
curl -X POST http://localhost:8000/upload \
  -F "file=@document.pdf" \
  -F "engine=tesseract"

# Use EasyOCR (if installed)
curl -X POST http://localhost:8000/upload \
  -F "file=@document.pdf" \
  -F "engine=easyocr"

# Use ocrmac (macOS only, not in Docker)
curl -X POST http://localhost:8000/upload \
  -F "file=@document.pdf" \
  -F "engine=ocrmac"
```

Or set a default engine via environment variable:
```bash
DEFAULT_OCR_ENGINE=easyocr
```

## API Usage

### 1. Upload Document

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@samples/numbers_gs150.jpg"
```

Response:
```json
{
  "job_id": "Kj4TY2vN8xQz9wR5pL7mH3fC1sD6aB8nE0gU4tV2iX1",
  "status": "pending",
  "message": "Upload successful, processing started"
}
```

### 2. Check Status

```bash
curl -X GET "http://localhost:8000/jobs/{job_id}/status"
```

Response:
```json
{
  "job_id": "Kj4TY...",
  "status": "completed",
  "upload_time": "2025-10-18T10:00:00Z",
  "start_time": "2025-10-18T10:00:05Z",
  "completion_time": "2025-10-18T10:00:12Z",
  "expiration_time": "2025-10-20T10:00:12Z",
  "error_message": null,
  "error_code": null
}
```

### 3. Download HOCR Result

```bash
curl -X GET "http://localhost:8000/jobs/{job_id}/result" -o result.hocr
```

### 4. Health Check

```bash
curl -X GET http://localhost:8000/health
```

### 5. Metrics (Prometheus)

```bash
curl -X GET http://localhost:8000/metrics
```

## Configuration

All configuration is via environment variables (see `.env.example`):

- `REDIS_URL`: Redis connection string
- `UPLOAD_DIR`: Temporary upload directory
- `RESULTS_DIR`: HOCR results directory
- `MAX_UPLOAD_SIZE_MB`: Maximum file size (default: 25MB)
- `RATE_LIMIT_REQUESTS`: Requests per minute per IP (default: 100)
- `JOB_EXPIRATION_HOURS`: Auto-delete results after (default: 48)
- `TESSERACT_LANG`: OCR language (default: eng)

## Performance

- **OCR Processing**: <30 seconds for single-page documents <5MB
- **Status Endpoint**: <800ms p95 latency
- **Result Endpoint**: <800ms p95 latency
- **Throughput**: 100 requests/min per IP
- **Concurrency**: 10+ simultaneous users
- **Memory**: <512MB per request

## Architecture

- **Web Framework**: FastAPI with async/await
- **OCR Engines**:
  - Tesseract 5.3+ (base, always available)
  - EasyOCR 1.7+ (optional, deep learning)
  - ocrmac (optional, macOS only)
- **Job Store**: Redis with 48h TTL
- **PDF Processing**: pdf2image (poppler wrapper)
- **Rate Limiting**: slowapi with Redis backend
- **Logging**: structlog (JSON format)
- **Metrics**: Prometheus client

### Docker Architecture

The project uses **multi-stage Dockerfile** with build targets for different flavors:

```
Dockerfile (multi-stage)
├── base (stage 1): Common setup (Python, uv, pyproject.toml)
├── lite (stage 2): Tesseract-only build target
└── full (stage 3): Tesseract + EasyOCR build target
```

**Benefits**:
- Single Dockerfile for all flavors
- Shared base layers reduce build time
- Efficient layer caching
- DRY principle (no duplication)

The Docker Compose configuration uses **file merging** with the `-f` flag:

```
docker-compose.base.yml  (shared: Redis + common API config)
├── docker-compose.yml  (merged via -f flag for full flavor)
└── docker-compose.lite.yml  (merged via -f flag for lite flavor)
```

**Usage**:
```bash
# Full flavor
docker compose -f docker-compose.base.yml -f docker-compose.yml up -d

# Lite flavor
docker compose -f docker-compose.base.yml -f docker-compose.lite.yml up -d
```

**Benefits**:
- No duplication of Redis or common API config
- Easy to maintain and update
- Clear separation of concerns
- Standard Docker Compose merge behavior

## Platform Notes

### macOS OCR Engine

This API includes support for macOS's native Vision and LiveText OCR frameworks when running natively on macOS. However, these features are **not available in Docker containers** due to macOS framework limitations.

- When running in Docker (recommended): Tesseract and EasyOCR engines are available
- When running natively on macOS: All engines including ocrmac (Vision/LiveText) are available

See [CONTRIBUTING.md](CONTRIBUTING.md) for more details on platform-specific limitations.

## Deployment

### Production Deployment with Docker

#### Prerequisites
- Docker Engine 20.10+
- Docker Compose v2+
- At least 2GB RAM available
- Persistent storage for results

#### Docker Compose Production Setup

1. **Clone and configure**:
```bash
git clone <repository-url>
cd restful-ocr
git checkout 001-ocr-hocr-upload

# Copy and edit production environment
cp .env.example .env
# Edit .env with production values (Redis URL, directories, etc.)
```

2. **Build and start services**:
```bash
# Build the Docker image
docker compose build

# Start services in detached mode
docker compose up -d

# View logs
docker compose logs -f api

# Check health
curl http://localhost:8000/health
```

3. **Production configuration** (edit `docker compose.yml`):
- Increase worker count: `command: uvicorn src.main:app --host 0.0.0.0 --workers 4`
- Add volume mounts for persistent results storage
- Configure Redis persistence
- Set resource limits (memory, CPU)

#### Kubernetes Deployment

For Kubernetes deployments, see example manifests in `k8s/` (to be added):
- Deployment with horizontal pod autoscaling
- Service (LoadBalancer or Ingress)
- ConfigMap for environment variables
- PersistentVolumeClaim for results storage
- Redis StatefulSet

#### Environment Variables for Production

Required environment variables:
```bash
# Redis Configuration
REDIS_URL=redis://redis:6379/0

# Storage Configuration
UPLOAD_DIR=/tmp/uploads
RESULTS_DIR=/tmp/results

# API Configuration
MAX_UPLOAD_SIZE_MB=25
RATE_LIMIT_REQUESTS=100
JOB_EXPIRATION_HOURS=48

# OCR Configuration
TESSERACT_LANG=eng
TESSERACT_DPI=300

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

#### Health Monitoring

- **Liveness probe**: `GET /health` (returns 200 if Redis is reachable)
- **Readiness probe**: `GET /health` (checks Redis connectivity)
- **Metrics**: `GET /metrics` (Prometheus format)

#### Scaling Considerations

- **Horizontal scaling**: Add more Uvicorn workers or pods
- **Redis**: Use Redis Cluster for high availability
- **Storage**: Mount shared NFS/S3 for results directory across pods
- **Rate limiting**: Shared Redis ensures consistent rate limits across instances

#### Security Hardening

- Run containers as non-root user
- Use read-only root filesystem where possible
- Enable TLS/HTTPS via reverse proxy (nginx, traefik)
- Configure network policies to isolate Redis
- Implement request timeout limits
- Monitor for suspicious file uploads

#### Backup and Recovery

- **Results**: Backup `/tmp/results` directory daily (though files auto-expire in 48h)
- **Redis**: Use Redis RDB/AOF persistence and backup snapshots
- **Logs**: Forward to centralized logging (ELK, Loki, etc.)

#### Resource Requirements

Minimum per instance:
- **CPU**: 1 core (2+ recommended)
- **Memory**: 2GB RAM (4GB+ recommended)
- **Storage**: 10GB for temp files + results
- **Redis**: 512MB RAM minimum

## Contributing

Interested in contributing? Check out our [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Setting up your development environment
- Using Makefile commands for development tasks
- Running tests and code quality checks
- Following our Test-Driven Development workflow
- Understanding the CI/CD build strategy
- Submitting bug fixes and features

## License

[Add your license here]
