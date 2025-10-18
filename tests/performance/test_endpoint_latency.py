"""Performance tests for endpoint latency (US3 - T091, T092)."""

import asyncio
import time
from statistics import mean

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.slow
async def test_status_endpoint_p95_latency(async_client: AsyncClient, sample_jpeg):
    """Test status endpoint p95 latency is <800ms (US3 - T091).

    Performance budget from constitution: p95 ≤ 800ms for status endpoint
    """
    # Upload document first
    with open(sample_jpeg, "rb") as f:
        upload_response = await async_client.post(
            "/upload",
            files={"file": ("test.jpg", f, "image/jpeg")},
        )

    assert upload_response.status_code == 200
    job_id = upload_response.json()["job_id"]

    # Wait for job to complete
    max_wait = 30
    attempt = 0
    while attempt < max_wait:
        status_response = await async_client.get(f"/jobs/{job_id}/status")
        if status_response.json()["status"] == "completed":
            break
        await asyncio.sleep(1)
        attempt += 1

    assert attempt < max_wait, "Job did not complete in time"

    # Measure latency for status endpoint (100 requests)
    latencies = []
    num_requests = 100

    for _ in range(num_requests):
        start = time.perf_counter()
        response = await async_client.get(f"/jobs/{job_id}/status")
        end = time.perf_counter()

        assert response.status_code == 200
        latency_ms = (end - start) * 1000
        latencies.append(latency_ms)

    # Sort latencies for percentile calculation
    latencies.sort()

    # Calculate percentiles
    p50 = latencies[int(0.50 * num_requests)]
    p95 = latencies[int(0.95 * num_requests)]
    p99 = latencies[int(0.99 * num_requests)]
    avg = mean(latencies)

    # Log performance metrics
    print("\nStatus Endpoint Latency Metrics:")
    print(f"  Average: {avg:.2f}ms")
    print(f"  Median (p50): {p50:.2f}ms")
    print(f"  p95: {p95:.2f}ms")
    print(f"  p99: {p99:.2f}ms")
    print(f"  Min: {min(latencies):.2f}ms")
    print(f"  Max: {max(latencies):.2f}ms")

    # Assert performance budget
    assert p95 < 800, f"Status endpoint p95 latency {p95:.2f}ms exceeds budget of 800ms"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_result_endpoint_p95_latency(async_client: AsyncClient, sample_jpeg):
    """Test result endpoint p95 latency is <800ms (US3 - T092).

    Performance budget from constitution: p95 ≤ 800ms for result endpoint
    """
    # Upload document first
    with open(sample_jpeg, "rb") as f:
        upload_response = await async_client.post(
            "/upload",
            files={"file": ("test.jpg", f, "image/jpeg")},
        )

    assert upload_response.status_code == 200
    job_id = upload_response.json()["job_id"]

    # Wait for job to complete
    max_wait = 30
    attempt = 0
    while attempt < max_wait:
        status_response = await async_client.get(f"/jobs/{job_id}/status")
        if status_response.json()["status"] == "completed":
            break
        await asyncio.sleep(1)
        attempt += 1

    assert attempt < max_wait, "Job did not complete in time"

    # Measure latency for result endpoint (100 requests)
    latencies = []
    num_requests = 100

    for _ in range(num_requests):
        start = time.perf_counter()
        response = await async_client.get(f"/jobs/{job_id}/result")
        end = time.perf_counter()

        assert response.status_code == 200
        latency_ms = (end - start) * 1000
        latencies.append(latency_ms)

    # Sort latencies for percentile calculation
    latencies.sort()

    # Calculate percentiles
    p50 = latencies[int(0.50 * num_requests)]
    p95 = latencies[int(0.95 * num_requests)]
    p99 = latencies[int(0.99 * num_requests)]
    avg = mean(latencies)

    # Log performance metrics
    print("\nResult Endpoint Latency Metrics:")
    print(f"  Average: {avg:.2f}ms")
    print(f"  Median (p50): {p50:.2f}ms")
    print(f"  p95: {p95:.2f}ms")
    print(f"  p99: {p99:.2f}ms")
    print(f"  Min: {min(latencies):.2f}ms")
    print(f"  Max: {max(latencies):.2f}ms")

    # Assert performance budget
    assert p95 < 800, f"Result endpoint p95 latency {p95:.2f}ms exceeds budget of 800ms"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_concurrent_status_requests(async_client: AsyncClient, sample_jpeg):
    """Test status endpoint handles concurrent requests efficiently."""
    # Upload document first
    with open(sample_jpeg, "rb") as f:
        upload_response = await async_client.post(
            "/upload",
            files={"file": ("test.jpg", f, "image/jpeg")},
        )

    assert upload_response.status_code == 200
    job_id = upload_response.json()["job_id"]

    # Wait for job to complete
    max_wait = 30
    attempt = 0
    while attempt < max_wait:
        status_response = await async_client.get(f"/jobs/{job_id}/status")
        if status_response.json()["status"] == "completed":
            break
        await asyncio.sleep(1)
        attempt += 1

    assert attempt < max_wait, "Job did not complete in time"

    # Make 50 concurrent requests
    async def check_status():
        start = time.perf_counter()
        response = await async_client.get(f"/jobs/{job_id}/status")
        end = time.perf_counter()
        return (end - start) * 1000, response.status_code

    # Execute concurrent requests
    tasks = [check_status() for _ in range(50)]
    results = await asyncio.gather(*tasks)

    # Verify all requests succeeded
    latencies = [r[0] for r in results]
    status_codes = [r[1] for r in results]

    assert all(code == 200 for code in status_codes), "Some requests failed"

    # Check p95 latency for concurrent requests
    latencies.sort()
    p95 = latencies[int(0.95 * len(latencies))]

    print("\nConcurrent Status Requests (n=50):")
    print(f"  p95 latency: {p95:.2f}ms")
    print(f"  Max latency: {max(latencies):.2f}ms")

    assert p95 < 800, f"Concurrent p95 latency {p95:.2f}ms exceeds budget"
