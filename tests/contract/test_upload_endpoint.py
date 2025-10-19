"""Contract tests for POST /upload endpoint validating OpenAPI schema."""

from fastapi.testclient import TestClient


def test_generic_upload_endpoint_returns_404(client: TestClient, sample_jpeg):
    """Test that the generic /upload endpoint returns 404 after removal."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload", files={"file": f})

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
