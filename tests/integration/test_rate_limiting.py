"""Integration tests for rate limiting enforcement (FR-015: 100 req/min per IP).

Note: Tests use /upload/tesseract endpoint since generic /upload was removed.
"""

import asyncio
from pathlib import Path

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_rate_limit_enforcement_upload_endpoint(
    async_client: AsyncClient, sample_jpeg: Path
) -> None:
    """Test that rate limiting blocks requests exceeding 100/min on POST /upload."""
    # Read sample file
    file_content = sample_jpeg.read_bytes()

    # Make 100 requests (should all succeed)
    successful_requests = 0
    for _ in range(100):
        response = await async_client.post(
            "/upload/tesseract",
            files={"file": ("test.jpg", file_content, "image/jpeg")},
        )
        if response.status_code in [200, 201]:
            successful_requests += 1

    # Should have 100 successful requests
    assert successful_requests == 100, (
        f"Expected 100 successful requests, got {successful_requests}"
    )

    # 101st request should be rate limited
    response = await async_client.post(
        "/upload/tesseract",
        files={"file": ("test.jpg", file_content, "image/jpeg")},
    )
    assert response.status_code == 429, (
        f"Expected 429 Too Many Requests, got {response.status_code}"
    )
    assert "Retry-After" in response.headers or "retry-after" in response.headers.lower()


@pytest.mark.asyncio
async def test_rate_limit_enforcement_status_endpoint(
    async_client: AsyncClient, sample_jpeg: Path
) -> None:
    """Test that rate limiting blocks requests exceeding 100/min on GET /jobs/{id}/status."""
    # First upload a file to get a job ID
    file_content = sample_jpeg.read_bytes()
    upload_response = await async_client.post(
        "/upload/tesseract",
        files={"file": ("test.jpg", file_content, "image/jpeg")},
    )
    assert upload_response.status_code in [200, 201]
    job_id = upload_response.json()["job_id"]

    # Make 99 more status requests (total 100 including upload)
    successful_requests = 1  # Count the upload
    for _ in range(99):
        response = await async_client.get(f"/jobs/{job_id}/status")
        if response.status_code == 200:
            successful_requests += 1

    # Should have 100 successful requests total
    assert successful_requests == 100, (
        f"Expected 100 successful requests, got {successful_requests}"
    )

    # 101st request should be rate limited
    response = await async_client.get(f"/jobs/{job_id}/status")
    assert response.status_code == 429, (
        f"Expected 429 Too Many Requests, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_rate_limit_reset_after_window(async_client: AsyncClient, sample_jpeg: Path) -> None:
    """Test that rate limit window resets after 60 seconds."""
    # Read sample file
    file_content = sample_jpeg.read_bytes()

    # Make 100 requests to hit the limit
    for _ in range(100):
        await async_client.post(
            "/upload/tesseract",
            files={"file": ("test.jpg", file_content, "image/jpeg")},
        )

    # Verify we're rate limited
    response = await async_client.post(
        "/upload/tesseract",
        files={"file": ("test.jpg", file_content, "image/jpeg")},
    )
    assert response.status_code == 429

    # Wait for rate limit window to reset (60 seconds + buffer)
    # Note: This test is marked as slow
    await asyncio.sleep(61)

    # Should be able to make requests again
    response = await async_client.post(
        "/upload/tesseract",
        files={"file": ("test.jpg", file_content, "image/jpeg")},
    )
    assert response.status_code in [200, 201], (
        f"Expected successful request after window reset, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_rate_limit_per_ip_isolation(async_client: AsyncClient, sample_jpeg: Path) -> None:
    """Test that rate limits are tracked per IP address (via X-Forwarded-For header)."""
    # Read sample file
    file_content = sample_jpeg.read_bytes()

    # Make 100 requests from IP 1.1.1.1
    for _ in range(100):
        await async_client.post(
            "/upload/tesseract",
            files={"file": ("test.jpg", file_content, "image/jpeg")},
            headers={"X-Forwarded-For": "1.1.1.1"},
        )

    # 101st request from 1.1.1.1 should be rate limited
    response = await async_client.post(
        "/upload/tesseract",
        files={"file": ("test.jpg", file_content, "image/jpeg")},
        headers={"X-Forwarded-For": "1.1.1.1"},
    )
    assert response.status_code == 429

    # But request from different IP (2.2.2.2) should succeed
    response = await async_client.post(
        "/upload/tesseract",
        files={"file": ("test.jpg", file_content, "image/jpeg")},
        headers={"X-Forwarded-For": "2.2.2.2"},
    )
    assert response.status_code in [200, 201], (
        "Request from different IP should not be rate limited"
    )


@pytest.mark.asyncio
async def test_rate_limit_error_response_format(
    async_client: AsyncClient, sample_jpeg: Path
) -> None:
    """Test that rate limit error response follows ErrorResponse schema."""
    # Read sample file
    file_content = sample_jpeg.read_bytes()

    # Make 100 requests to hit the limit
    for _ in range(100):
        await async_client.post(
            "/upload/tesseract",
            files={"file": ("test.jpg", file_content, "image/jpeg")},
        )

    # Get rate limited response
    response = await async_client.post(
        "/upload/tesseract",
        files={"file": ("test.jpg", file_content, "image/jpeg")},
    )
    assert response.status_code == 429

    # Verify response format
    data = response.json()
    assert "detail" in data, "Error response should include 'detail' field"
    assert isinstance(data["detail"], str)
    assert "rate limit" in data["detail"].lower() or "too many" in data["detail"].lower()

    # Verify Retry-After header is present
    assert "Retry-After" in response.headers or any(
        h.lower() == "retry-after" for h in response.headers
    ), "Rate limit response should include Retry-After header"


# Mark the slow test
pytest.mark.slow = pytest.mark.skipif(
    "not config.getoption('--run-slow')",
    reason="Slow test - requires 61 second wait",
)
test_rate_limit_reset_after_window = pytest.mark.slow(test_rate_limit_reset_after_window)
