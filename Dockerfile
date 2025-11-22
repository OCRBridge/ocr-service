# Multi-stage Dockerfile for OCR service with multiple build targets
#
# Build targets:
#   - lite: Lightweight Tesseract-only image (~500MB)
#     Usage: docker build --target lite -t ocr-service:lite .
#
#   - full: Full-featured image with EasyOCR support (~2.5GB)
#     Usage: docker build --target full -t ocr-service:full .
#     Default: docker build -t ocr-service:latest .
#
# Note: ocrmac is not included as it's incompatible with Docker (requires native macOS)

# ============================================================================
# Stage 1: Base image with common setup
# ============================================================================
FROM python:3.11-slim AS base

# Set working directory
WORKDIR /app

# Install uv for faster dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# ============================================================================
# Stage 2: Lite target - Tesseract only (minimal dependencies)
# ============================================================================
FROM base AS lite

# Install minimal system dependencies (Tesseract and PDF processing only)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (base only - no optional extras)
RUN uv pip install --system -e .

# Copy application source
COPY src ./src

# Create temporary directories with correct permissions
RUN mkdir -p /tmp/uploads /tmp/results && \
    chmod 700 /tmp/uploads /tmp/results

# Non-root user for security
RUN groupadd -g 1000 appuser && \
    useradd -r -u 1000 -g appuser appuser && \
    chown -R appuser:appuser /app /tmp/uploads /tmp/results

USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# ============================================================================
# Stage 3: Full target - Tesseract + EasyOCR (with ML libraries)
# ============================================================================
FROM base AS full

# Install system dependencies for Tesseract, PDF processing, and ML libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    build-essential \
    libffi-dev \
    libssl-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies with EasyOCR support
# Includes EasyOCR and PyTorch for deep learning OCR
RUN uv pip install --system -e .[easyocr]

# Copy application source
COPY src ./src

# Create temporary directories with correct permissions
RUN mkdir -p /tmp/uploads /tmp/results && \
    chmod 700 /tmp/uploads /tmp/results

# Non-root user for security
RUN groupadd -g 1000 appuser && \
    useradd -r -u 1000 -g appuser appuser && \
    chown -R appuser:appuser /app /tmp/uploads /tmp/results

USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
