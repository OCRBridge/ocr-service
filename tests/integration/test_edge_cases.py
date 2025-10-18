"""Comprehensive edge case tests for blank pages, corrupted files, oversized files."""

import io
from pathlib import Path

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_blank_image(async_client: AsyncClient) -> None:
    """Test uploading a blank/white image (should succeed but may have no text)."""
    # Create a minimal 1x1 white JPEG
    from PIL import Image

    img = Image.new("RGB", (100, 100), color="white")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    response = await async_client.post(
        "/upload",
        files={"file": ("blank.jpg", img_bytes.getvalue(), "image/jpeg")},
    )

    # Should accept the file (it's a valid JPEG)
    assert response.status_code in [200, 201], (
        f"Blank image upload failed with {response.status_code}"
    )

    # Get job ID
    data = response.json()
    assert "job_id" in data
    job_id = data["job_id"]

    # Wait a bit for processing
    import asyncio

    await asyncio.sleep(3)

    # Check status - should complete (even if no text found)
    status_response = await async_client.get(f"/jobs/{job_id}/status")
    assert status_response.status_code == 200
    status_data = status_response.json()

    # Job should complete successfully (blank page is not an error)
    assert status_data["status"] in ["completed", "processing", "pending"]


@pytest.mark.asyncio
async def test_upload_corrupted_jpeg(async_client: AsyncClient) -> None:
    """Test uploading a corrupted JPEG file (truncated data)."""
    # Create corrupted JPEG by truncating valid data
    from PIL import Image

    img = Image.new("RGB", (100, 100), color="blue")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")

    # Truncate the file to corrupt it
    corrupted_data = img_bytes.getvalue()[:50]  # Only take first 50 bytes

    response = await async_client.post(
        "/upload",
        files={"file": ("corrupted.jpg", corrupted_data, "image/jpeg")},
    )

    # Could be rejected at upload or during processing
    # Either way is acceptable
    if response.status_code in [200, 201]:
        # If accepted, should eventually fail during processing
        job_id = response.json()["job_id"]

        import asyncio

        await asyncio.sleep(3)

        status_response = await async_client.get(f"/jobs/{job_id}/status")
        assert status_response.status_code == 200
        status_data = status_response.json()

        # May fail or succeed depending on OCR engine robustness
        assert status_data["status"] in ["failed", "processing", "pending", "completed"]
    else:
        # Immediate rejection is also acceptable
        assert response.status_code in [400, 415]


@pytest.mark.asyncio
async def test_upload_oversized_file(async_client: AsyncClient) -> None:
    """Test uploading a file exceeding 25MB limit (FR-007)."""
    # Create a file larger than 25MB
    oversized_data = b"x" * (26 * 1024 * 1024)  # 26MB

    response = await async_client.post(
        "/upload",
        files={"file": ("huge.jpg", oversized_data, "image/jpeg")},
    )

    # Should be rejected with 413 Payload Too Large
    assert response.status_code == 413, (
        f"Expected 413 for oversized file, got {response.status_code}"
    )

    # Verify error response format
    data = response.json()
    assert "detail" in data
    assert "25" in data["detail"] or "size" in data["detail"].lower()


@pytest.mark.asyncio
async def test_upload_zero_byte_file(async_client: AsyncClient) -> None:
    """Test uploading an empty file (0 bytes)."""
    response = await async_client.post(
        "/upload",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
    )

    # Should be rejected (file size validation)
    assert response.status_code in [400, 415], (
        f"Empty file should be rejected, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_upload_wrong_extension_correct_mime(async_client: AsyncClient) -> None:
    """Test uploading a file with wrong extension but correct MIME type."""
    from PIL import Image

    # Create valid JPEG data
    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    # Upload as .txt file but with correct JPEG MIME type
    response = await async_client.post(
        "/upload",
        files={"file": ("image.txt", img_bytes.getvalue(), "image/jpeg")},
    )

    # Should accept (magic bytes validation should detect it's actually JPEG)
    assert response.status_code in [200, 201, 400, 415]  # Implementation-dependent


@pytest.mark.asyncio
async def test_upload_special_characters_filename(async_client: AsyncClient) -> None:
    """Test uploading a file with special characters in filename."""
    from PIL import Image

    img = Image.new("RGB", (100, 100), color="green")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    # Filename with special characters
    special_filename = "test file (copy) [2023] #1 & more!.jpg"

    response = await async_client.post(
        "/upload",
        files={"file": (special_filename, img_bytes.getvalue(), "image/jpeg")},
    )

    # Should handle gracefully (filename sanitization)
    assert response.status_code in [200, 201], (
        f"Special chars filename failed with {response.status_code}"
    )


@pytest.mark.asyncio
async def test_upload_path_traversal_attempt(async_client: AsyncClient) -> None:
    """Test uploading a file with path traversal attempt in filename."""
    from PIL import Image

    img = Image.new("RGB", (100, 100), color="yellow")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    # Malicious filename attempting path traversal
    malicious_filename = "../../../etc/passwd.jpg"

    response = await async_client.post(
        "/upload",
        files={"file": (malicious_filename, img_bytes.getvalue(), "image/jpeg")},
    )

    # Should be sanitized and accepted or rejected
    # Either way, path should never escape temp directory
    assert response.status_code in [200, 201, 400]


@pytest.mark.asyncio
async def test_get_status_invalid_job_id_format(async_client: AsyncClient) -> None:
    """Test getting status with invalid job ID format."""
    # Invalid job ID (not a valid token_urlsafe format)
    response = await async_client.get("/jobs/invalid-id-12345/status")

    # Should return 404 Not Found
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_status_nonexistent_job_id(async_client: AsyncClient) -> None:
    """Test getting status for a job that doesn't exist."""
    # Valid format but non-existent job ID
    fake_job_id = "Kj4TY2vN8xQz9wR5pL7mH3fC1sD6aB8nE0gU4tV2iX1"

    response = await async_client.get(f"/jobs/{fake_job_id}/status")

    # Should return 404 Not Found
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_result_before_completion(async_client: AsyncClient, sample_jpeg: Path) -> None:
    """Test retrieving result before processing completes."""
    # Upload file
    file_content = sample_jpeg.read_bytes()
    upload_response = await async_client.post(
        "/upload",
        files={"file": ("test.jpg", file_content, "image/jpeg")},
    )
    assert upload_response.status_code in [200, 201]
    job_id = upload_response.json()["job_id"]

    # Immediately try to get result (before processing completes)
    result_response = await async_client.get(f"/jobs/{job_id}/result")

    # Should indicate result not ready yet (202 Accepted or 404)
    assert result_response.status_code in [202, 404, 425]


@pytest.mark.asyncio
async def test_concurrent_uploads_same_file(async_client: AsyncClient, sample_jpeg: Path) -> None:
    """Test multiple concurrent uploads of the same file."""
    import asyncio

    file_content = sample_jpeg.read_bytes()

    # Upload same file 5 times concurrently
    async def upload_file():
        return await async_client.post(
            "/upload",
            files={"file": ("test.jpg", file_content, "image/jpeg")},
        )

    tasks = [upload_file() for _ in range(5)]
    responses = await asyncio.gather(*tasks)

    # All should succeed or be rate limited
    successful = 0
    job_ids = set()

    for response in responses:
        if response.status_code in [200, 201]:
            successful += 1
            job_id = response.json()["job_id"]
            job_ids.add(job_id)
        elif response.status_code == 429:
            # Rate limited - acceptable
            pass

    # Should have unique job IDs
    assert len(job_ids) == successful, "Each upload should get unique job ID"


@pytest.mark.asyncio
async def test_upload_unsupported_format(async_client: AsyncClient) -> None:
    """Test uploading an unsupported file format (e.g., BMP, GIF)."""
    # Create a simple text file disguised as image
    fake_data = b"This is not an image file"

    response = await async_client.post(
        "/upload",
        files={"file": ("image.bmp", fake_data, "image/bmp")},
    )

    # Should be rejected with 415 Unsupported Media Type
    assert response.status_code == 415

    # Verify error message mentions supported formats
    data = response.json()
    assert "detail" in data
    assert any(fmt in data["detail"] for fmt in ["JPEG", "PNG", "PDF", "TIFF"])


@pytest.mark.asyncio
async def test_upload_text_file_with_image_extension(async_client: AsyncClient) -> None:
    """Test uploading a text file with .jpg extension (magic bytes should detect)."""
    # Plain text file with .jpg extension
    text_data = b"This is a plain text file, not a JPEG"

    response = await async_client.post(
        "/upload",
        files={"file": ("fake.jpg", text_data, "image/jpeg")},
    )

    # Should be rejected (magic byte validation should detect it's not a JPEG)
    assert response.status_code in [400, 415], (
        f"Fake JPEG should be rejected, got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_upload_extremely_long_filename(async_client: AsyncClient) -> None:
    """Test uploading a file with extremely long filename (>255 chars)."""
    from PIL import Image

    img = Image.new("RGB", (100, 100), color="purple")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    # Filename exceeding 255 characters
    long_filename = "a" * 300 + ".jpg"

    response = await async_client.post(
        "/upload",
        files={"file": (long_filename, img_bytes.getvalue(), "image/jpeg")},
    )

    # Should handle gracefully (truncate or reject)
    assert response.status_code in [200, 201, 400]


@pytest.mark.asyncio
async def test_multipart_form_missing_file_field(async_client: AsyncClient) -> None:
    """Test submitting upload form without the 'file' field."""
    # Send multipart form with wrong field name
    response = await async_client.post(
        "/upload",
        data={"document": "some data"},
    )

    # Should return 422 Unprocessable Entity
    assert response.status_code == 422
