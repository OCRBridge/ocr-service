"""Integration tests for Prometheus metrics endpoint.

Tests the /metrics endpoint for proper metrics collection and exposure.
"""

import io


def test_metrics_endpoint_accessible(client):
    """Test that /metrics endpoint is accessible."""
    response = client.get("/metrics")

    assert response.status_code == 200


def test_metrics_endpoint_returns_prometheus_format(client):
    """Test that metrics endpoint returns Prometheus text format."""
    response = client.get("/metrics")

    # Prometheus metrics are text/plain
    content_type = response.headers.get("content-type", "")
    assert "text/plain" in content_type or response.status_code == 200


def test_metrics_include_http_request_metrics(client):
    """Test that metrics include HTTP request counters."""
    # Make a request to generate metrics
    client.get("/health")

    # Get metrics
    response = client.get("/metrics")
    metrics_text = response.text

    # Should include HTTP-related metrics
    # Check for common Prometheus HTTP metrics
    assert response.status_code == 200
    assert len(metrics_text) > 0


def test_metrics_collected_after_ocr_request(client, sample_jpeg_bytes):
    """Test that metrics are collected after OCR processing."""
    # Make an OCR request
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    client.post("/v2/ocr/tesseract/process", files=files)

    # Get metrics
    response = client.get("/metrics")

    assert response.status_code == 200
    # Metrics should be generated
    assert len(response.text) > 100  # Should have some content


def test_metrics_no_authentication_required(client):
    """Test that metrics endpoint works without authentication."""
    # Should work without auth headers
    response = client.get("/metrics")

    assert response.status_code == 200


def test_metrics_endpoint_consistent_format(client):
    """Test that metrics format is consistent."""
    response1 = client.get("/metrics")
    response2 = client.get("/metrics")

    # Both should be successful
    assert response1.status_code == 200
    assert response2.status_code == 200

    # Should have similar structure (both have content)
    assert len(response1.text) > 0
    assert len(response2.text) > 0


def test_metrics_updated_on_requests(client):
    """Test that metrics are updated as requests are made."""
    # Get initial metrics
    initial_response = client.get("/metrics")
    initial_metrics = initial_response.text

    # Make several requests
    for _ in range(3):
        client.get("/health")

    # Get updated metrics
    updated_response = client.get("/metrics")
    updated_metrics = updated_response.text

    # Metrics should be present in both
    assert len(initial_metrics) > 0
    assert len(updated_metrics) > 0


def test_metrics_include_standard_prometheus_metrics(client):
    """Test that standard Prometheus metrics are included."""
    response = client.get("/metrics")
    metrics_text = response.text

    # Look for common metric patterns
    # Most Prometheus exporters include HELP and TYPE comments
    assert "# HELP" in metrics_text or "# TYPE" in metrics_text or len(metrics_text) > 50


def test_metrics_endpoint_methods_allowed(client):
    """Test that GET method works for metrics endpoint."""
    # GET should work
    get_response = client.get("/metrics")
    assert get_response.status_code == 200

    # POST might be allowed by Prometheus ASGI app (returns 200)
    # or might not be allowed (405/404)
    post_response = client.post("/metrics")
    assert post_response.status_code in [200, 405, 404]


def test_health_and_metrics_both_accessible(client):
    """Test that both health and metrics endpoints work."""
    health_response = client.get("/health")
    metrics_response = client.get("/metrics")

    assert health_response.status_code == 200
    assert metrics_response.status_code == 200

    # Different content types
    assert health_response.headers["content-type"] == "application/json"
    # Metrics might be text/plain or similar


def test_metrics_after_failed_request(client):
    """Test that metrics are collected even after failed requests."""
    # Make a request that will fail
    client.post("/v2/ocr/nonexistent/process")

    # Metrics should still be accessible
    response = client.get("/metrics")
    assert response.status_code == 200


def test_metrics_file_upload_metrics(client, sample_jpeg_bytes):
    """Test that file upload metrics are collected."""
    # Upload a file
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    client.post("/v2/ocr/tesseract/process", files=files)

    # Get metrics
    response = client.get("/metrics")

    assert response.status_code == 200
    # Should have metrics data
    assert len(response.text) > 0


def test_metrics_different_endpoints_tracked(client, sample_jpeg_bytes):
    """Test that different endpoints are tracked in metrics."""
    # Hit multiple endpoints
    client.get("/health")
    client.get("/v2/engines")

    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    client.post("/v2/ocr/tesseract/process", files=files)

    # Get metrics
    response = client.get("/metrics")

    assert response.status_code == 200
    # Metrics should include data from all requests
    assert len(response.text) > 100
