"""Contract tests for GET /jobs/{id}/status endpoint validating OpenAPI schema."""

from fastapi.testclient import TestClient


def test_status_with_valid_job_returns_200(client: TestClient, sample_jpeg):
    """Test getting status for valid job returns 200."""
    # First upload a document
    with open(sample_jpeg, "rb") as f:
        upload_response = client.post("/upload/tesseract", files={"file": f})
    job_id = upload_response.json()["job_id"]

    # Get status
    response = client.get(f"/jobs/{job_id}/status")

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert "status" in data
    assert data["job_id"] == job_id


def test_status_with_invalid_job_returns_404(client: TestClient):
    """Test getting status for non-existent job returns 404."""
    fake_job_id = "nonexistent_job_id_that_does_not_exist_12345"
    response = client.get(f"/jobs/{fake_job_id}/status")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


def test_status_response_schema_matches_openapi(client: TestClient, sample_jpeg):
    """Test status response matches OpenAPI schema."""
    # Upload document
    with open(sample_jpeg, "rb") as f:
        upload_response = client.post("/upload/tesseract", files={"file": f})
    job_id = upload_response.json()["job_id"]

    # Get status
    response = client.get(f"/jobs/{job_id}/status")

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert isinstance(data["job_id"], str)
    assert isinstance(data["status"], str)
    assert data["status"] in ["pending", "processing", "completed", "failed"]
    assert "upload_time" in data
    # Optional fields
    if "error_message" in data:
        assert isinstance(data["error_message"], (str, type(None)))
    if "error_code" in data:
        assert isinstance(data["error_code"], (str, type(None)))
