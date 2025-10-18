"""Prometheus metrics for job lifecycle tracking (US3 - T099)."""

from prometheus_client import Counter, Gauge, Histogram

# Job lifecycle counters
jobs_created_total = Counter(
    "ocr_jobs_created_total",
    "Total number of OCR jobs created",
)

jobs_completed_total = Counter(
    "ocr_jobs_completed_total",
    "Total number of OCR jobs completed successfully",
    ["engine"],
)

jobs_failed_total = Counter(
    "ocr_jobs_failed_total",
    "Total number of OCR jobs that failed",
    ["error_code", "engine"],
)

# Job duration histograms (in seconds)
job_processing_duration_seconds = Histogram(
    "ocr_job_processing_duration_seconds",
    "Time taken to process an OCR job (from start to completion)",
    buckets=[1, 5, 10, 15, 20, 30, 45, 60, 90, 120, 180],
)

job_total_duration_seconds = Histogram(
    "ocr_job_total_duration_seconds",
    "Total time from upload to completion",
    buckets=[1, 5, 10, 15, 20, 30, 45, 60, 90, 120, 180],
)

job_queue_duration_seconds = Histogram(
    "ocr_job_queue_duration_seconds",
    "Time job spent in queue before processing started",
    buckets=[0.1, 0.5, 1, 2, 5, 10, 20, 30],
)

# Active jobs gauge
active_jobs = Gauge(
    "ocr_active_jobs",
    "Number of jobs currently being processed",
)

# File size histogram (in bytes)
document_size_bytes = Histogram(
    "ocr_document_size_bytes",
    "Size of uploaded documents",
    buckets=[1024, 10240, 102400, 1048576, 5242880, 10485760, 26214400],  # 1KB to 25MB
)

# Page count histogram
document_pages = Histogram(
    "ocr_document_pages",
    "Number of pages in processed documents",
    buckets=[1, 2, 5, 10, 20, 50, 100],
)
