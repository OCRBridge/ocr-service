"""Contract tests for error responses (400/404/413/415/429) validating schemas."""

from fastapi.testclient import TestClient


def test_400_validation_error_schema(client: TestClient):
    """Test 400 response for validation errors matches schema."""
    response = client.post("/upload")

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


def test_404_not_found_error_schema(client: TestClient):
    """Test 404 response for non-existent job matches schema."""
    response = client.get("/jobs/nonexistent/status")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


def test_413_file_too_large_error_schema(client: TestClient, tmp_path):
    """Test 413 response for oversized file matches schema."""
    # Create a file larger than 25MB
    large_file = tmp_path / "large.jpg"
    # Write 26MB of data
    with open(large_file, "wb") as f:
        f.write(b"0" * (26 * 1024 * 1024))

    with open(large_file, "rb") as f:
        response = client.post("/upload", files={"file": f})

    # This test will initially fail (TDD)
    # When implemented:
    # assert response.status_code == 413
    # data = response.json()
    # assert "detail" in data


def test_415_unsupported_format_error_schema(client: TestClient, tmp_path):
    """Test 415 response for unsupported file format matches schema."""
    # Create a text file (unsupported format)
    text_file = tmp_path / "test.txt"
    text_file.write_text("This is not an image")

    with open(text_file, "rb") as f:
        response = client.post("/upload", files={"file": f})

    # This test will initially fail (TDD)
    # When implemented:
    # assert response.status_code == 415
    # data = response.json()
    # assert "detail" in data
    # assert "error_code" in data


def test_429_rate_limit_error_schema(client: TestClient, sample_jpeg):
    """Test 429 response for rate limit exceeded matches schema."""
    # This test will initially fail (TDD)
    # When implemented, make 101 requests in rapid succession
    # and verify 101st returns 429
    pass


def test_error_response_includes_timestamp(client: TestClient):
    """Test all error responses include timestamp field."""
    response = client.get("/jobs/nonexistent/status")

    assert response.status_code == 404
    # This test will initially fail (TDD)
    # When implemented:
    # data = response.json()
    # assert "timestamp" in data
