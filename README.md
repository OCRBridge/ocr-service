# RESTful OCR API

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checker: Pyright](https://img.shields.io/badge/type%20checker-pyright-blue.svg)](https://github.com/microsoft/pyright)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://hub.docker.com/)
[![Tests](https://github.com/OCRBridge/ocr-service/actions/workflows/tests.yml/badge.svg)](https://github.com/OCRBridge/ocr-service/actions/workflows/tests.yml)
[![Ruff](https://github.com/OCRBridge/ocr-service/actions/workflows/ruff.yml/badge.svg)](https://github.com/OCRBridge/ocr-service/actions/workflows/ruff.yml)

A high-performance RESTful API service for document OCR processing with HOCR (HTML-based OCR) output format.

## Features

- **Multi-format Support**: Process JPEG, PNG, PDF, and TIFF documents
- **HOCR Output**: Industry-standard HTML-based OCR with bounding boxes and text hierarchy
- **Async Processing**: Job-based async processing with status polling
- **Rate Limiting**: 100 requests/minute per IP address
- **Auto-expiration**: Results auto-delete after 48 hours
- **No Authentication**: Public API for easy integration
- **High Performance**: <30s processing time for typical documents

## Architecture

```mermaid
graph TB
    subgraph Client
        A[User/Application]
    end

    subgraph "OCR Service"
        B[FastAPI API]
        C[Rate Limiter]
        D[Job Manager]
        E[OCR Processor]
        F[File Handler]
    end

    subgraph "OCR Engines"
        G[Tesseract]
        H[EasyOCR]
        I[ocrmac<br/>macOS only]
    end

    subgraph Storage
        J[(Redis)]
        K[File System<br/>Uploads/Results]
    end

    subgraph Monitoring
        L[Prometheus<br/>Metrics]
        M[Structured<br/>Logs]
    end

    A -->|Upload File| B
    B --> C
    C --> D
    D --> F
    F --> K
    D --> E
    E -.->|Select Engine| G
    E -.->|Select Engine| H
    E -.->|Select Engine| I
    E -->|Store HOCR| K
    D -->|Job Status| J
    B --> L
    B --> M

    style G fill:#90EE90
    style H fill:#87CEEB
    style I fill:#FFB6C1
    style J fill:#FFE4B5
    style K fill:#FFE4B5
```

### Request Flow

1. **Upload**: Client sends document via HTTP POST
2. **Validation**: File type, size, and format validation
3. **Rate Limiting**: Check IP-based rate limits (100 req/min)
4. **Job Creation**: Generate unique job ID, store in Redis
5. **Processing**: Convert to image(s), run OCR engine, generate HOCR
6. **Storage**: Save HOCR result to filesystem with 48h TTL
7. **Polling**: Client checks status via job ID
8. **Download**: Client retrieves HOCR result when complete

## Quick Start

### Running with Docker Compose (Recommended)

```bash
# Start all services (API + Redis)
docker compose up -d

# View logs
docker compose logs -f api

# Stop services
docker compose down
```

The API will be available at `http://localhost:8000`. Check the health endpoint to verify:
```bash
curl http://localhost:8000/health
```

### Development Setup

For local development without Docker, or to contribute to the project, see the [Contributing Guide](CONTRIBUTING.md) for detailed setup instructions including:
- Installing dependencies (Python, Redis, Tesseract, etc.)
- Setting up your development environment
- Running tests and code quality tools

## API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs - Interactive API explorer with "Try it out" functionality
- **ReDoc**: http://localhost:8000/redoc - Alternative documentation with a cleaner layout
- **OpenAPI Schema**: http://localhost:8000/openapi.json - Machine-readable API specification

The interactive documentation allows you to test all endpoints directly from your browser without using curl or Postman.

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
- **OCR Engine**: Tesseract 5.3+ via pytesseract
- **Job Store**: Redis with 48h TTL
- **PDF Processing**: pdf2image (poppler wrapper)
- **Rate Limiting**: slowapi with Redis backend
- **Logging**: structlog (JSON format)
- **Metrics**: Prometheus client

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
- Running tests and code quality checks
- Following our Test-Driven Development workflow
- Submitting bug fixes and features

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
