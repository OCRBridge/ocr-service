"""Integration tests for health check endpoint.

Tests the /health endpoint returns correct status and version information.
"""


def test_health_check_returns_200(client):
    """Test that health check endpoint returns 200 OK."""
    response = client.get("/health")

    assert response.status_code == 200


def test_health_check_returns_json(client):
    """Test that health check returns JSON response."""
    response = client.get("/health")

    assert response.headers["content-type"] == "application/json"
    # Should be able to parse as JSON
    json_data = response.json()
    assert isinstance(json_data, dict)


def test_health_check_has_status_field(client):
    """Test that health check includes status field."""
    response = client.get("/health")
    data = response.json()

    assert "status" in data
    assert data["status"] == "healthy"


def test_health_check_has_version_field(client):
    """Test that health check includes version field."""
    response = client.get("/health")
    data = response.json()

    assert "version" in data
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0


def test_health_check_version_format(client):
    """Test that version follows semantic versioning format."""
    response = client.get("/health")
    data = response.json()

    version = data["version"]
    # Should be in format like "2.0.0" or "1.2.3"
    parts = version.split(".")
    assert len(parts) >= 2  # At least major.minor


def test_health_check_consistent_response(client):
    """Test that health check returns consistent responses."""
    response1 = client.get("/health")
    response2 = client.get("/health")

    assert response1.json() == response2.json()


def test_health_check_no_authentication_required(client):
    """Test that health check works without authentication."""
    # Should work without any auth headers
    response = client.get("/health")

    assert response.status_code == 200


def test_health_check_response_structure(client):
    """Test complete health check response structure."""
    response = client.get("/health")
    data = response.json()

    # Should have exactly these fields
    assert set(data.keys()) == {"status", "version"}

    # Status should be string
    assert isinstance(data["status"], str)
    # Version should be string
    assert isinstance(data["version"], str)


def test_health_check_fast_response(client):
    """Test that health check responds quickly."""
    import time

    start = time.time()
    response = client.get("/health")
    duration = time.time() - start

    assert response.status_code == 200
    # Should respond in less than 100ms
    assert duration < 0.1


def test_health_check_methods_allowed(client):
    """Test that only GET method is allowed for health check."""
    # GET should work
    get_response = client.get("/health")
    assert get_response.status_code == 200

    # POST should not be allowed
    post_response = client.post("/health")
    assert post_response.status_code in [405, 404]  # Method Not Allowed or Not Found

    # PUT should not be allowed
    put_response = client.put("/health")
    assert put_response.status_code in [405, 404]

    # DELETE should not be allowed
    delete_response = client.delete("/health")
    assert delete_response.status_code in [405, 404]
