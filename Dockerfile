# Multi-stage build for production deployment
FROM python:3.11-alpine AS base

# Install system dependencies for Tesseract and PDF processing
RUN apk add --no-cache \
    tesseract-ocr \
    tesseract-ocr-data-eng \
    poppler-utils \
    build-base \
    libffi-dev \
    openssl-dev

# Set working directory
WORKDIR /app

# Install uv for faster dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install Python dependencies
RUN uv pip install --system -e .

# Copy application source
COPY src ./src
COPY samples ./samples

# Create temporary directories with correct permissions
RUN mkdir -p /tmp/uploads /tmp/results && \
    chmod 700 /tmp/uploads /tmp/results

# Non-root user for security
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser && \
    chown -R appuser:appuser /app /tmp/uploads /tmp/results

USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
