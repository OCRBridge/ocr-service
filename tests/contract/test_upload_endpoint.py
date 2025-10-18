"""Contract tests for POST /upload endpoint validating OpenAPI schema."""

import pytest
from fastapi.testclient import TestClient


def test_upload_jpeg_returns_202_with_job_id(client: TestClient, sample_jpeg):
    """Test uploading JPEG returns 202 with valid job_id."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload", files={"file": f})

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert "status" in data
    assert "message" in data
    assert len(data["job_id"]) == 43  # URL-safe token length
    assert data["status"] == "pending"


def test_upload_png_returns_202_with_job_id(client: TestClient, sample_png):
    """Test uploading PNG returns 202 with valid job_id."""
    with open(sample_png, "rb") as f:
        response = client.post("/upload", files={"file": f})

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"


def test_upload_without_file_returns_400(client: TestClient):
    """Test uploading without file returns 400 validation error."""
    response = client.post("/upload")

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


def test_upload_response_schema_matches_openapi(client: TestClient, sample_jpeg):
    """Test upload response matches OpenAPI schema."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload", files={"file": f})

    assert response.status_code == 202
    data = response.json()

    # Validate response structure
    assert isinstance(data["job_id"], str)
    assert isinstance(data["status"], str)
    assert isinstance(data["message"], str)
    assert data["status"] in ["pending", "processing", "completed", "failed"]
