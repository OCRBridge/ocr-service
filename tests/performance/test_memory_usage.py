"""Performance tests for memory usage (<512MB per request budget)."""

import tracemalloc
from pathlib import Path

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_endpoint_memory_usage(async_client: AsyncClient, sample_jpeg: Path) -> None:
    """Test that POST /upload stays within 512MB memory budget."""
    # Read sample file
    file_content = sample_jpeg.read_bytes()

    # Start memory tracking
    tracemalloc.start()
    baseline_current, baseline_peak = tracemalloc.get_traced_memory()

    # Make upload request
    response = await async_client.post(
        "/upload/tesseract",
        files={"file": ("test.jpg", file_content, "image/jpeg")},
    )

    # Get memory usage
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Calculate memory used by this request
    memory_used_mb = (peak - baseline_peak) / 1024 / 1024

    # Verify response succeeded
    assert response.status_code in [200, 201], f"Upload failed with {response.status_code}"

    # Verify memory budget
    assert memory_used_mb < 512, (
        f"Memory usage {memory_used_mb:.2f} MB exceeds 512MB budget. "
        f"Baseline: {baseline_peak / 1024 / 1024:.2f} MB, Peak: {peak / 1024 / 1024:.2f} MB"
    )


@pytest.mark.asyncio
async def test_status_endpoint_memory_usage(async_client: AsyncClient, sample_jpeg: Path) -> None:
    """Test that GET /jobs/{id}/status stays within 512MB memory budget."""
    # First upload a file to get a job ID
    file_content = sample_jpeg.read_bytes()
    upload_response = await async_client.post(
        "/upload/tesseract",
        files={"file": ("test.jpg", file_content, "image/jpeg")},
    )
    assert upload_response.status_code in [200, 201]
    job_id = upload_response.json()["job_id"]

    # Start memory tracking
    tracemalloc.start()
    baseline_current, baseline_peak = tracemalloc.get_traced_memory()

    # Make status request
    response = await async_client.get(f"/jobs/{job_id}/status")

    # Get memory usage
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Calculate memory used by this request
    memory_used_mb = (peak - baseline_peak) / 1024 / 1024

    # Verify response succeeded
    assert response.status_code == 200, f"Status check failed with {response.status_code}"

    # Verify memory budget (status should use much less than upload)
    assert memory_used_mb < 512, (
        f"Memory usage {memory_used_mb:.2f} MB exceeds 512MB budget. "
        f"Baseline: {baseline_peak / 1024 / 1024:.2f} MB, Peak: {peak / 1024 / 1024:.2f} MB"
    )


@pytest.mark.asyncio
async def test_result_endpoint_memory_usage(async_client: AsyncClient, sample_jpeg: Path) -> None:
    """Test that GET /jobs/{id}/result stays within 512MB memory budget."""
    import asyncio

    # First upload a file to get a job ID
    file_content = sample_jpeg.read_bytes()
    upload_response = await async_client.post(
        "/upload/tesseract",
        files={"file": ("test.jpg", file_content, "image/jpeg")},
    )
    assert upload_response.status_code in [200, 201]
    job_id = upload_response.json()["job_id"]

    # Wait for processing to complete (with timeout)
    max_wait = 30  # seconds
    waited = 0
    while waited < max_wait:
        status_response = await async_client.get(f"/jobs/{job_id}/status")
        if status_response.status_code == 200:
            status_data = status_response.json()
            if status_data["status"] in ["completed", "failed"]:
                break
        await asyncio.sleep(1)
        waited += 1

    # Start memory tracking
    tracemalloc.start()
    baseline_current, baseline_peak = tracemalloc.get_traced_memory()

    # Make result request
    response = await async_client.get(f"/jobs/{job_id}/result")

    # Get memory usage
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Calculate memory used by this request
    memory_used_mb = (peak - baseline_peak) / 1024 / 1024

    # Verify response succeeded (or job not ready yet)
    assert response.status_code in [200, 202, 404], (
        f"Result retrieval got unexpected {response.status_code}"
    )

    # Verify memory budget
    assert memory_used_mb < 512, (
        f"Memory usage {memory_used_mb:.2f} MB exceeds 512MB budget. "
        f"Baseline: {baseline_peak / 1024 / 1024:.2f} MB, Peak: {peak / 1024 / 1024:.2f} MB"
    )


@pytest.mark.asyncio
async def test_large_pdf_memory_usage(async_client: AsyncClient, sample_pdf: Path) -> None:
    """Test that processing a multi-page PDF stays within 512MB memory budget."""
    # Read sample PDF file
    file_content = sample_pdf.read_bytes()

    # Start memory tracking
    tracemalloc.start()
    baseline_current, baseline_peak = tracemalloc.get_traced_memory()

    # Make upload request
    response = await async_client.post(
        "/upload/tesseract",
        files={"file": ("test.pdf", file_content, "application/pdf")},
    )

    # Get memory usage
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Calculate memory used by this request
    memory_used_mb = (peak - baseline_peak) / 1024 / 1024

    # Verify response succeeded
    assert response.status_code in [200, 201], f"PDF upload failed with {response.status_code}"

    # Verify memory budget (PDFs may use more memory but must stay under 512MB)
    assert memory_used_mb < 512, (
        f"Memory usage {memory_used_mb:.2f} MB exceeds 512MB budget. "
        f"Baseline: {baseline_peak / 1024 / 1024:.2f} MB, Peak: {peak / 1024 / 1024:.2f} MB"
    )


@pytest.mark.asyncio
async def test_concurrent_requests_memory_isolation(
    async_client: AsyncClient, sample_jpeg: Path
) -> None:
    """Test that concurrent requests don't cause memory to accumulate beyond budget."""
    import asyncio

    file_content = sample_jpeg.read_bytes()

    # Start memory tracking
    tracemalloc.start()
    baseline_current, baseline_peak = tracemalloc.get_traced_memory()

    # Make 10 concurrent upload requests
    async def upload_file():
        return await async_client.post(
            "/upload/tesseract",
            files={"file": ("test.jpg", file_content, "image/jpeg")},
        )

    tasks = [upload_file() for _ in range(10)]
    responses = await asyncio.gather(*tasks)

    # Get memory usage
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Calculate memory used
    memory_used_mb = (peak - baseline_peak) / 1024 / 1024

    # Verify all requests succeeded
    for response in responses:
        assert response.status_code in [200, 201, 429], (
            f"Request failed with {response.status_code}"
        )

    # Verify total memory stays reasonable (allowing for some overhead)
    # Even with 10 concurrent requests, total should be well under 512MB * 10
    assert memory_used_mb < 1024, (
        f"Concurrent memory usage {memory_used_mb:.2f} MB is excessive. "
        f"Baseline: {baseline_peak / 1024 / 1024:.2f} MB, Peak: {peak / 1024 / 1024:.2f} MB"
    )
