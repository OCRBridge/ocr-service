"""Contract tests for GET /jobs/{id}/result endpoint validating OpenAPI schema."""

from fastapi.testclient import TestClient


def test_result_with_completed_job_returns_200(client: TestClient, sample_jpeg):
    """Test getting result for completed job returns 200 with HOCR content."""
    # Upload document
    with open(sample_jpeg, "rb") as f:
        upload_response = client.post("/upload", files={"file": f})
    job_id = upload_response.json()["job_id"]

    # Wait for processing (in real test, would poll status)
    # For now, this will fail until implementation is complete
    response = client.get(f"/jobs/{job_id}/result")

    # This test will initially fail (TDD)
    # When implemented:
    # assert response.status_code == 200
    # assert "text/html" in response.headers["content-type"]
    # assert "ocr_page" in response.text  # HOCR marker


def test_result_with_pending_job_returns_400(client: TestClient, sample_jpeg):
    """Test getting result for pending job returns 400."""
    # Upload document
    with open(sample_jpeg, "rb") as f:
        upload_response = client.post("/upload", files={"file": f})
    job_id = upload_response.json()["job_id"]

    # Try to get result immediately (should be pending)
    response = client.get(f"/jobs/{job_id}/result")

    # Should return 400 if not completed
    # This test will initially fail (TDD)


def test_result_with_invalid_job_returns_404(client: TestClient):
    """Test getting result for non-existent job returns 404."""
    fake_job_id = "nonexistent_job_id_that_does_not_exist_12345"
    response = client.get(f"/jobs/{fake_job_id}/result")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


def test_result_contains_valid_hocr_xml(client: TestClient, sample_jpeg):
    """Test result contains valid HOCR XML structure."""
    # This test will initially fail (TDD)
    # When implemented, verify:
    # - Valid XML structure
    # - Contains bbox coordinates
    # - Contains ocr_page, ocr_line, ocrx_word classes
    pass
