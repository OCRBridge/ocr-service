# Docker Image Flavors

The OCR service provides three Docker image flavors, each optimized for different use cases:

## 1. Tesseract-only (Lightweight)

**Image**: Built from `Dockerfile.tesseract`

**Includes**:
- Tesseract OCR engine
- Core API dependencies
- PDF processing support

**Excludes**:
- EasyOCR
- PyTorch and deep learning dependencies
- Heavy ML libraries

**Use case**: Lightweight deployment when you only need traditional Tesseract OCR

**Build**:
```bash
# Using environment variable
DOCKERFILE=Dockerfile.tesseract docker-compose up --build

# Or using override file
docker-compose -f docker-compose.yml -f docker-compose.tesseract.yml up --build

# Or build directly
docker build -f Dockerfile.tesseract -t ocr-service:tesseract .
```

**Image size**: ~500MB (estimated)

## 2. EasyOCR-only (Deep Learning)

**Image**: Built from `Dockerfile.easyocr`

**Includes**:
- EasyOCR engine
- PyTorch
- OpenCV
- Core API dependencies
- PDF processing support

**Excludes**:
- Tesseract OCR

**Use case**: When you prefer deep learning-based OCR with multi-language support

**Build**:
```bash
# Using environment variable
DOCKERFILE=Dockerfile.easyocr docker-compose up --build

# Or using override file
docker-compose -f docker-compose.yml -f docker-compose.easyocr.yml up --build

# Or build directly
docker build -f Dockerfile.easyocr -t ocr-service:easyocr .
```

**Image size**: ~2.5GB (estimated, includes PyTorch)

**Note**: EasyOCR supports GPU acceleration if you have NVIDIA Docker runtime configured.

## 3. Combined (All Engines)

**Image**: Built from `Dockerfile` or `Dockerfile.combined`

**Includes**:
- Tesseract OCR engine
- EasyOCR engine
- PyTorch
- OpenCV
- All dependencies

**Use case**: Maximum flexibility with all OCR engines available

**Build**:
```bash
# Default - just use docker-compose
docker-compose up --build

# Or explicitly
DOCKERFILE=Dockerfile.combined docker-compose up --build

# Or using override file
docker-compose -f docker-compose.yml -f docker-compose.combined.yml up --build

# Or build directly
docker build -f Dockerfile.combined -t ocr-service:combined .
```

**Image size**: ~2.6GB (estimated)

## Choosing the Right Flavor

| Flavor | Size | OCR Engines | Best For |
|--------|------|-------------|----------|
| **Tesseract** | ~500MB | Tesseract | Lightweight deployments, traditional OCR |
| **EasyOCR** | ~2.5GB | EasyOCR | Deep learning OCR, multi-language support |
| **Combined** | ~2.6GB | Both | Maximum flexibility, production use |

## Production Images

Pre-built images are available on GitHub Container Registry:

```bash
# Combined (default)
docker pull ghcr.io/ocrbridge/ocr-service:latest

# Tesseract-only
docker pull ghcr.io/ocrbridge/ocr-service:tesseract

# EasyOCR-only
docker pull ghcr.io/ocrbridge/ocr-service:easyocr
```

## GPU Support

To enable GPU acceleration for EasyOCR:

1. Install [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
2. Update docker-compose.yml:

```yaml
services:
  api:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

3. EasyOCR will automatically detect and use the GPU

## Environment Variables

All flavors support the same environment variables:

- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6379/0`)
- `API_HOST`: API host binding (default: `0.0.0.0`)
- `API_PORT`: API port (default: `8000`)
- `API_WORKERS`: Number of Uvicorn workers (default: `4`)
- `LOG_LEVEL`: Logging level (default: `INFO`)
- `LOG_FORMAT`: Log format - `json` or `text` (default: `json`)
- `MAX_UPLOAD_SIZE_MB`: Maximum upload size in MB (default: `25`)
- `RATE_LIMIT_REQUESTS`: Rate limit per minute (default: `100`)
- `JOB_EXPIRATION_HOURS`: Job result retention (default: `24`)

## Build Arguments

You can customize the builds with build arguments:

```bash
docker build \
  --build-arg PYTHON_VERSION=3.14 \
  -f Dockerfile.tesseract \
  -t ocr-service:tesseract \
  .
```

## Multi-Architecture Support

Images are built for:
- `linux/amd64` (x86_64)
- `linux/arm64` (ARM 64-bit)

Use the appropriate architecture for your deployment platform.

## Development vs Production

**Development** (docker-compose.yml):
- Builds locally
- Mounts source code for live reloading
- Uses local build cache

**Production** (docker-compose.prod.yml):
- Uses pre-built images from GHCR
- No source code mounting
- Automatic restart policies
- Optimized for deployment

## Troubleshooting

### Image too large
- Use the `tesseract` flavor for minimal size
- Use multi-stage builds (already implemented)
- Use `.dockerignore` to exclude unnecessary files (already configured)

### Missing OCR engine
- Check which flavor you're using
- Verify the engine is available at `/api/engines`
- Check container logs: `docker-compose logs api`

### Slow builds
- Use build cache: `docker-compose build --parallel`
- Use pre-built images for production
- Consider BuildKit: `DOCKER_BUILDKIT=1 docker-compose build`

### GPU not detected (EasyOCR)
- Install NVIDIA Container Toolkit
- Add GPU configuration to docker-compose.yml
- Verify with: `docker run --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi`
