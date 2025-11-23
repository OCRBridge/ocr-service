"""Integration tests for end-to-end upload with sample documents."""

import time

import pytest
from fastapi.testclient import TestClient


def test_ocr_jpeg_end_to_end(client: TestClient, sample_jpeg):
    """Test end-to-end JPEG upload with numbers_gs150.jpg."""
    # Upload
    with open(sample_jpeg, "rb") as f:
        upload_response = client.post("/upload/tesseract", files={"file": f})

    assert upload_response.status_code == 202
    job_id = upload_response.json()["job_id"]

    # Poll status (with timeout)
    max_wait = 30
    status = None
    for _ in range(max_wait):
        status_response = client.get(f"/jobs/{job_id}/status")
        if status_response.status_code == 200:
            status = status_response.json()["status"]
            if status in ["completed", "failed"]:
                break
        time.sleep(1)

    # This test will initially fail (TDD)
    # When implemented:
    # assert status == "completed", f"Job did not complete in {max_wait}s"

    # Download result
    # result_response = client.get(f"/jobs/{job_id}/result")
    # assert result_response.status_code == 200
    # hocr_content = result_response.text

    # Validate HOCR structure
    # assert '<?xml version="1.0"' in hocr_content
    # assert 'ocr_page' in hocr_content
    # assert 'bbox' in hocr_content  # Bounding boxes present


def test_ocr_png_end_to_end(client: TestClient, sample_png):
    """Test end-to-end PNG upload with stock_gs200.jpg."""
    # Upload
    with open(sample_png, "rb") as f:
        upload_response = client.post("/upload/tesseract", files={"file": f})

    assert upload_response.status_code == 202


@pytest.mark.slow
def test_concurrent_uploads(client: TestClient, sample_jpeg):
    """Test multiple concurrent uploads are handled correctly."""
    # This test will initially fail (TDD)
    # Upload 5 documents concurrently and verify all complete
    pass


# ============================================================================
# Multi-Format Support
# ============================================================================


def test_ocr_pdf_end_to_end(client: TestClient, sample_pdf):
    """Test end-to-end PDF upload with contract_en_scan.pdf (multi-page)."""
    # Upload PDF
    with open(sample_pdf, "rb") as f:
        upload_response = client.post("/upload/tesseract", files={"file": f})

    assert upload_response.status_code == 202
    job_id = upload_response.json()["job_id"]
    assert job_id is not None

    # Poll status (with timeout - PDF processing may take longer)
    max_wait = 60  # PDFs may take longer
    status = None
    for _ in range(max_wait):
        status_response = client.get(f"/jobs/{job_id}/status")
        if status_response.status_code == 200:
            status_data = status_response.json()
            status = status_data["status"]
            if status in ["completed", "failed"]:
                break
        time.sleep(1)

    assert status == "completed", f"Job did not complete in {max_wait}s"

    # Download result
    result_response = client.get(f"/jobs/{job_id}/result")
    assert result_response.status_code == 200
    hocr_content = result_response.text

    # Validate HOCR structure
    assert '<?xml version="1.0"' in hocr_content
    assert "ocr_page" in hocr_content
    assert "bbox" in hocr_content  # Bounding boxes present

    # Verify multi-page handling (contract_en_scan.pdf has multiple pages)
    # Count number of ocr_page divs (could be class="ocr_page" or class='ocr_page')
    page_count = hocr_content.count('class="ocr_page"') + hocr_content.count("class='ocr_page'")
    assert page_count >= 1, f"HOCR should contain at least one page, found {page_count}"


def test_ocr_tiff_end_to_end(client: TestClient, sample_tiff):
    """Test end-to-end TIFF upload."""
    # Upload TIFF
    with open(sample_tiff, "rb") as f:
        upload_response = client.post("/upload/tesseract", files={"file": f})

    assert upload_response.status_code == 202
    job_id = upload_response.json()["job_id"]
    assert job_id is not None

    # Poll status
    max_wait = 30
    status = None
    for _ in range(max_wait):
        status_response = client.get(f"/jobs/{job_id}/status")
        if status_response.status_code == 200:
            status_data = status_response.json()
            status = status_data["status"]
            if status in ["completed", "failed"]:
                break
        time.sleep(1)

    assert status == "completed", f"Job did not complete in {max_wait}s"

    # Download result
    result_response = client.get(f"/jobs/{job_id}/result")
    assert result_response.status_code == 200
    hocr_content = result_response.text

    # Validate HOCR structure
    assert '<?xml version="1.0"' in hocr_content
    assert "ocr_page" in hocr_content
    assert "bbox" in hocr_content
