"""Unit tests for Prometheus metrics.

Tests for metric definitions, types, and basic functionality.
"""

from prometheus_client import Counter, Gauge, Histogram

from src.utils import metrics


def test_jobs_created_total_metric():
    """Test that jobs_created_total counter is defined."""
    assert hasattr(metrics, "jobs_created_total")
    assert isinstance(metrics.jobs_created_total, Counter)
    # Prometheus automatically appends _total to counter names
    assert metrics.metric_name(metrics.jobs_created_total) == "ocr_jobs_created"


def test_jobs_completed_total_metric():
    """Test that jobs_completed_total counter is defined with engine label."""
    assert hasattr(metrics, "jobs_completed_total")
    assert isinstance(metrics.jobs_completed_total, Counter)
    # Prometheus automatically appends _total to counter names, so _name doesn't include it
    assert metrics.metric_name(metrics.jobs_completed_total) == "ocr_jobs_completed"
    # Should have 'engine' label
    assert "engine" in metrics.metric_labels(metrics.jobs_completed_total)


def test_jobs_failed_total_metric():
    """Test that jobs_failed_total counter is defined with labels."""
    assert hasattr(metrics, "jobs_failed_total")
    assert isinstance(metrics.jobs_failed_total, Counter)
    # Prometheus automatically appends _total to counter names, so _name doesn't include it
    assert metrics.metric_name(metrics.jobs_failed_total) == "ocr_jobs_failed"
    # Should have 'error_code' and 'engine' labels
    labels = metrics.metric_labels(metrics.jobs_failed_total)
    assert "error_code" in labels
    assert "engine" in labels


def test_job_processing_duration_seconds_metric():
    """Test that processing duration histogram is defined."""
    assert hasattr(metrics, "job_processing_duration_seconds")
    assert isinstance(metrics.job_processing_duration_seconds, Histogram)
    assert (
        metrics.metric_name(metrics.job_processing_duration_seconds)
        == "ocr_job_processing_duration_seconds"
    )


def test_job_total_duration_seconds_metric():
    """Test that total duration histogram is defined."""
    assert hasattr(metrics, "job_total_duration_seconds")
    assert isinstance(metrics.job_total_duration_seconds, Histogram)
    assert (
        metrics.metric_name(metrics.job_total_duration_seconds) == "ocr_job_total_duration_seconds"
    )


def test_job_queue_duration_seconds_metric():
    """Test that queue duration histogram is defined."""
    assert hasattr(metrics, "job_queue_duration_seconds")
    assert isinstance(metrics.job_queue_duration_seconds, Histogram)
    assert (
        metrics.metric_name(metrics.job_queue_duration_seconds) == "ocr_job_queue_duration_seconds"
    )


def test_active_jobs_metric():
    """Test that active jobs gauge is defined."""
    assert hasattr(metrics, "active_jobs")
    assert isinstance(metrics.active_jobs, Gauge)
    assert metrics.metric_name(metrics.active_jobs) == "ocr_active_jobs"


def test_document_size_bytes_metric():
    """Test that document size histogram is defined."""
    assert hasattr(metrics, "document_size_bytes")
    assert isinstance(metrics.document_size_bytes, Histogram)
    assert metrics.metric_name(metrics.document_size_bytes) == "ocr_document_size_bytes"


def test_document_pages_metric():
    """Test that document pages histogram is defined."""
    assert hasattr(metrics, "document_pages")
    assert isinstance(metrics.document_pages, Histogram)
    assert metrics.metric_name(metrics.document_pages) == "ocr_document_pages"


def test_sync_ocr_requests_total_metric():
    """Test that sync requests counter is defined with labels."""
    assert hasattr(metrics, "sync_ocr_requests_total")
    assert isinstance(metrics.sync_ocr_requests_total, Counter)
    labels = metrics.metric_labels(metrics.sync_ocr_requests_total)
    assert "engine" in labels
    assert "status" in labels


def test_sync_ocr_duration_seconds_metric():
    """Test that sync duration histogram is defined with engine label."""
    assert hasattr(metrics, "sync_ocr_duration_seconds")
    assert isinstance(metrics.sync_ocr_duration_seconds, Histogram)
    assert "engine" in metrics.metric_labels(metrics.sync_ocr_duration_seconds)


def test_sync_ocr_timeouts_total_metric():
    """Test that sync timeouts counter is defined."""
    assert hasattr(metrics, "sync_ocr_timeouts_total")
    assert isinstance(metrics.sync_ocr_timeouts_total, Counter)
    assert "engine" in metrics.metric_labels(metrics.sync_ocr_timeouts_total)


def test_sync_ocr_file_size_bytes_metric():
    """Test that sync file size histogram is defined."""
    assert hasattr(metrics, "sync_ocr_file_size_bytes")
    assert isinstance(metrics.sync_ocr_file_size_bytes, Histogram)
    assert "engine" in metrics.metric_labels(metrics.sync_ocr_file_size_bytes)


def test_histogram_buckets_processing_duration():
    """Test that processing duration has appropriate buckets."""
    buckets = metrics.metric_buckets(metrics.job_processing_duration_seconds)
    # Should include buckets from 1 to 180 seconds (as floats)
    assert 1.0 in buckets
    assert 30.0 in buckets
    assert 180.0 in buckets


def test_histogram_buckets_queue_duration():
    """Test that queue duration has appropriate buckets for fast queues."""
    buckets = metrics.metric_buckets(metrics.job_queue_duration_seconds)
    # Should include sub-second buckets for fast queue times
    assert 0.1 in buckets
    assert 0.5 in buckets
    assert 1.0 in buckets


def test_histogram_buckets_document_size():
    """Test that document size has appropriate buckets."""
    buckets = metrics.metric_buckets(metrics.document_size_bytes)
    # Should include 1KB, 1MB, 5MB buckets (as floats)
    assert 1024.0 in buckets  # 1KB
    assert 1048576.0 in buckets  # 1MB
    assert 5242880.0 in buckets  # 5MB


def test_histogram_buckets_sync_duration():
    """Test that sync duration buckets align with 30s timeout."""
    buckets = metrics.metric_buckets(metrics.sync_ocr_duration_seconds)
    # Should include 0.5s to 30s range
    assert 0.5 in buckets
    assert 30.0 in buckets


def test_counter_increment():
    """Test that counters can be incremented."""
    # Get initial value
    initial = metrics.metric_value(metrics.jobs_created_total)

    # Increment
    metrics.jobs_created_total.inc()

    # Check incremented
    assert metrics.metric_value(metrics.jobs_created_total) == initial + 1


def test_counter_with_labels():
    """Test that labeled counters can be used."""
    # Should be able to increment with labels
    metrics.jobs_completed_total.labels(engine="tesseract").inc()
    metrics.jobs_failed_total.labels(error_code="timeout", engine="easyocr").inc()
    # Should not raise any errors


def test_gauge_operations():
    """Test that gauge supports inc/dec operations."""
    # Get initial value
    initial = metrics.metric_value(metrics.active_jobs)

    # Increment
    metrics.active_jobs.inc()
    assert metrics.metric_value(metrics.active_jobs) == initial + 1

    # Decrement
    metrics.active_jobs.dec()
    assert metrics.metric_value(metrics.active_jobs) == initial


def test_histogram_observe():
    """Test that histograms can observe values."""
    # Should be able to observe values
    metrics.job_processing_duration_seconds.observe(15.5)
    metrics.document_size_bytes.observe(1048576)  # 1MB
    # Should not raise any errors


def test_histogram_with_labels_observe():
    """Test that labeled histograms can observe values."""
    # Sync metrics with labels
    metrics.sync_ocr_duration_seconds.labels(engine="tesseract").observe(2.5)
    metrics.sync_ocr_file_size_bytes.labels(engine="easyocr").observe(524288)
    # Should not raise any errors


def test_all_metrics_exported():
    """Test that all expected metrics are exported from module."""
    expected_metrics = [
        "jobs_created_total",
        "jobs_completed_total",
        "jobs_failed_total",
        "job_processing_duration_seconds",
        "job_total_duration_seconds",
        "job_queue_duration_seconds",
        "active_jobs",
        "document_size_bytes",
        "document_pages",
        "sync_ocr_requests_total",
        "sync_ocr_duration_seconds",
        "sync_ocr_timeouts_total",
        "sync_ocr_file_size_bytes",
    ]

    for metric_name in expected_metrics:
        assert hasattr(metrics, metric_name), f"Missing metric: {metric_name}"


def test_metric_naming_convention():
    """Test that metrics follow Prometheus naming conventions."""
    # All metric names should be lowercase with underscores
    metric_names = [
        metrics.metric_name(metrics.jobs_created_total),
        metrics.metric_name(metrics.jobs_completed_total),
        metrics.metric_name(metrics.active_jobs),
        metrics.metric_name(metrics.document_size_bytes),
    ]

    for name in metric_names:
        assert name.islower() or "_" in name
        assert " " not in name
        # Should start with application prefix
        assert name.startswith("ocr_") or name.startswith("sync_ocr_")


def test_metrics_have_help_text():
    """Test that metrics have documentation strings."""
    assert metrics.metric_help(metrics.jobs_created_total)
    assert metrics.metric_help(metrics.jobs_completed_total)
    assert metrics.metric_help(metrics.active_jobs)
    assert len(metrics.metric_help(metrics.jobs_created_total)) > 0
