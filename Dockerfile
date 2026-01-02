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
# Stage 1: Base image with uv pre-installed and common setup
# ============================================================================
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS base

# Set working directory
WORKDIR /app

# Set environment variables for uv and Python
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

# Copy dependency files early to leverage Docker caching
COPY pyproject.toml uv.lock* ./

# ============================================================================
# Stage 2: Lite Builder - Tesseract only (build dependencies)
# ============================================================================
FROM base AS lite_builder

# Install Python dependencies for the 'tesseract' optional group
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev --extra tesseract

# Copy application source (after dependencies for optimal caching)
COPY src ./src

# ============================================================================
# Stage 3: Lite Runtime - Tesseract only (minimal runtime)
# ============================================================================
FROM python:3.11-slim-bookworm AS lite

# Install minimal system dependencies (Tesseract and PDF processing only)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create temporary directories with correct permissions
RUN mkdir -p /tmp/uploads /tmp/results && \
    chmod 700 /tmp/uploads /tmp/results

# Non-root user for security
RUN groupadd -g 1000 appuser && \
    useradd -r -u 1000 -g appuser appuser && \
    chown -R appuser:appuser /app /tmp/uploads /tmp/results

# Copy the virtual environment from the builder stage
COPY --from=lite_builder --chown=appuser:appuser /app/.venv /app/.venv
# Copy application source
COPY --from=lite_builder --chown=appuser:appuser /app/src /app/src

# Add the virtual environment to the PATH
ENV PATH="/app/.venv/bin:$PATH"

USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# ============================================================================
# Stage 4: Full Builder - Tesseract + EasyOCR (build dependencies)
# ============================================================================
FROM base AS full_builder

# Install Python dependencies for the 'full' optional group
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev --extra tesseract --extra easyocr

# Copy application source (after dependencies for optimal caching)
COPY src ./src

# ============================================================================
# Stage 5: Full Runtime - Tesseract + EasyOCR (minimal runtime)
# ============================================================================
FROM python:3.11-slim-bookworm AS full

# Install system dependencies for Tesseract, PDF processing, and ML libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libmagic1 \
    build-essential \
    libffi-dev \
    libssl-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

WORKDIR /app

# Create temporary directories with correct permissions
RUN mkdir -p /tmp/uploads /tmp/results && \
    chmod 700 /tmp/uploads /tmp/results

# Non-root user for security
RUN groupadd -g 1000 appuser && \
    useradd -r -u 1000 -g appuser appuser && \
    chown -R appuser:appuser /app /tmp/uploads /tmp/results

# Copy the virtual environment from the builder stage
COPY --from=full_builder --chown=appuser:appuser /app/.venv /app/.venv
# Copy application source
COPY --from=full_builder --chown=appuser:appuser /app/src /app/src

# Add the virtual environment to the PATH
ENV PATH="/app/.venv/bin:$PATH"

USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
