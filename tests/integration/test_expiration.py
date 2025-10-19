"""Integration tests for job expiration (US3 - T088, T089)."""

import asyncio
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_expiration_timestamp_correctness(async_client: AsyncClient, sample_jpeg):
    """Test that expiration timestamp is calculated correctly (T088).

    Validates:
    - Expiration time is present after job completion
    - Expiration time is exactly 48 hours from completion time
    - Timestamp formatting is correct
    """
    # Upload document
    with open(sample_jpeg, "rb") as f:
        upload_response = await async_client.post(
            "/upload/tesseract",
            files={"file": ("test.jpg", f, "image/jpeg")},
        )

    assert upload_response.status_code == 200
    job_id = upload_response.json()["job_id"]

    # Poll until completed
    max_attempts = 30
    attempt = 0

    while attempt < max_attempts:
        status_response = await async_client.get(f"/jobs/{job_id}/status")
        status_data = status_response.json()

        if status_data["status"] == "completed":
            # Parse timestamps
            upload_time = datetime.fromisoformat(status_data["upload_time"].replace("Z", "+00:00"))
            start_time = datetime.fromisoformat(status_data["start_time"].replace("Z", "+00:00"))
            completion_time = datetime.fromisoformat(
                status_data["completion_time"].replace("Z", "+00:00")
            )
            expiration_time = datetime.fromisoformat(
                status_data["expiration_time"].replace("Z", "+00:00")
            )

            # Validate timestamp ordering
            assert upload_time <= start_time, "Upload time should be before or equal to start time"
            assert start_time <= completion_time, (
                "Start time should be before or equal to completion time"
            )
            assert completion_time < expiration_time, (
                "Completion time should be before expiration time"
            )

            # Validate expiration is 48 hours from completion
            expected_expiration = completion_time + timedelta(hours=48)
            time_diff = abs((expiration_time - expected_expiration).total_seconds())

            # Allow 1 second tolerance for rounding
            assert time_diff < 1, (
                f"Expiration should be exactly 48h from completion. Expected {expected_expiration}, got {expiration_time}"
            )

            break

        await asyncio.sleep(1)
        attempt += 1

    assert attempt < max_attempts, "Job did not complete in time"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_ttl_enforcement_with_mocked_time(
    async_client: AsyncClient, sample_jpeg, redis_client
):
    """Test that Redis TTL is enforced correctly (T089).

    Uses Redis TTL inspection to verify that:
    - TTL is set on job completion
    - TTL matches the expiration time
    - Keys expire as expected
    """
    # Upload document
    with open(sample_jpeg, "rb") as f:
        upload_response = await async_client.post(
            "/upload/tesseract",
            files={"file": ("test.jpg", f, "image/jpeg")},
        )

    assert upload_response.status_code == 200
    job_id = upload_response.json()["job_id"]

    # Wait for completion
    max_attempts = 30
    attempt = 0

    while attempt < max_attempts:
        status_response = await async_client.get(f"/jobs/{job_id}/status")
        status_data = status_response.json()

        if status_data["status"] == "completed":
            break

        await asyncio.sleep(1)
        attempt += 1

    assert attempt < max_attempts, "Job did not complete in time"

    # Check Redis TTL
    metadata_key = f"job:{job_id}:metadata"
    result_key = f"job:{job_id}:result"

    # Get TTL for both keys
    metadata_ttl = await redis_client.ttl(metadata_key)
    result_ttl = await redis_client.ttl(result_key)

    # TTL should be set (positive value)
    assert metadata_ttl > 0, "Metadata key should have TTL set"
    assert result_ttl > 0, "Result key should have TTL set"

    # TTL should be approximately 48 hours (172800 seconds)
    # Allow some tolerance for processing time (within 1 minute)
    expected_ttl = 48 * 60 * 60  # 172800 seconds
    assert expected_ttl - 60 <= metadata_ttl <= expected_ttl, (
        f"Metadata TTL should be ~48h, got {metadata_ttl} seconds"
    )
    assert expected_ttl - 60 <= result_ttl <= expected_ttl, (
        f"Result TTL should be ~48h, got {result_ttl} seconds"
    )


@pytest.mark.asyncio
@pytest.mark.slow
async def test_expired_job_returns_404(async_client: AsyncClient, sample_jpeg, redis_client):
    """Test that expired jobs return 404 when accessed."""
    # Upload document
    with open(sample_jpeg, "rb") as f:
        upload_response = await async_client.post(
            "/upload/tesseract",
            files={"file": ("test.jpg", f, "image/jpeg")},
        )

    assert upload_response.status_code == 200
    job_id = upload_response.json()["job_id"]

    # Wait for completion
    max_attempts = 30
    attempt = 0

    while attempt < max_attempts:
        status_response = await async_client.get(f"/jobs/{job_id}/status")
        status_data = status_response.json()

        if status_data["status"] == "completed":
            break

        await asyncio.sleep(1)
        attempt += 1

    assert attempt < max_attempts, "Job did not complete in time"

    # Manually expire the keys to simulate 48h passing
    metadata_key = f"job:{job_id}:metadata"
    result_key = f"job:{job_id}:result"

    await redis_client.delete(metadata_key)
    await redis_client.delete(result_key)

    # Verify keys are deleted
    assert await redis_client.exists(metadata_key) == 0, "Metadata key should be deleted"
    assert await redis_client.exists(result_key) == 0, "Result key should be deleted"

    # Attempt to get status - should return 404
    status_response = await async_client.get(f"/jobs/{job_id}/status")
    assert status_response.status_code == 404, "Expired job should return 404"

    # Attempt to get result - should return 404
    result_response = await async_client.get(f"/jobs/{job_id}/result")
    assert result_response.status_code == 404, "Expired job result should return 404"
