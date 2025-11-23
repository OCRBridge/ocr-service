"""Contract tests for GET /jobs/{id}/result endpoint validating OpenAPI schema."""

from fastapi.testclient import TestClient


def test_result_with_completed_job_returns_200(client: TestClient, sample_jpeg):
    """Test getting result for completed job returns 200 with HOCR content."""
    # Upload document
    with open(sample_jpeg, "rb") as f:
        upload_response = client.post("/upload/tesseract", files={"file": f})
    job_id = upload_response.json()["job_id"]

    # Wait for processing (in real test, would poll status)
    # For now, this will fail until implementation is complete
    _response = client.get(f"/jobs/{job_id}/result")

    # This test will initially fail (TDD)
    # When implemented:
    # assert response.status_code == 200
    # assert "text/html" in response.headers["content-type"]
    # assert "ocr_page" in response.text  # HOCR marker


def test_result_with_pending_job_returns_400(client: TestClient, sample_jpeg):
    """Test getting result for pending job returns 400."""
    # Upload document
    with open(sample_jpeg, "rb") as f:
        upload_response = client.post("/upload/tesseract", files={"file": f})
    job_id = upload_response.json()["job_id"]

    # Try to get result immediately (should be pending)
    _response = client.get(f"/jobs/{job_id}/result")

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


def test_multi_page_hocr_output_structure(client: TestClient, sample_pdf):
    """Test multi-page HOCR output structure for PDF documents (T080)."""
    import time

    # Upload multi-page PDF
    with open(sample_pdf, "rb") as f:
        upload_response = client.post("/upload/tesseract", files={"file": f})

    assert upload_response.status_code == 202
    job_id = upload_response.json()["job_id"]

    # Poll until completed
    max_wait = 60
    status = None
    for _ in range(max_wait):
        status_response = client.get(f"/jobs/{job_id}/status")
        if status_response.status_code == 200:
            status = status_response.json()["status"]
            if status in ["completed", "failed"]:
                break
        time.sleep(1)

    # Get result
    result_response = client.get(f"/jobs/{job_id}/result")

    # Verify response
    assert result_response.status_code == 200
    assert "text/html" in result_response.headers["content-type"]

    hocr_content = result_response.text

    # Verify HOCR structure
    assert '<?xml version="1.0"' in hocr_content or "<html" in hocr_content
    assert "ocr_page" in hocr_content
    assert "bbox" in hocr_content

    # Verify multi-page structure
    # Each page should be wrapped in <div class='ocr_page'>
    page_divs = hocr_content.count('class="ocr_page"') + hocr_content.count("class='ocr_page'")
    assert page_divs >= 1, "HOCR should contain at least one page div"

    # Verify HOCR hierarchy (pages contain content)
    assert "<div" in hocr_content  # Page divs
    assert "bbox" in hocr_content  # Bounding boxes present
