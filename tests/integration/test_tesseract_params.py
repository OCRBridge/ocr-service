"""Integration tests for Tesseract parameter end-to-end processing."""

import time

import pytest
from fastapi.testclient import TestClient


def test_language_parameter_end_to_end(client: TestClient, sample_jpeg):
    """Test that language parameter is used throughout OCR processing pipeline (T017)."""
    # Upload with specific language
    with open(sample_jpeg, "rb") as f:
        upload_response = client.post("/upload", files={"file": f}, data={"lang": "eng"})

    assert upload_response.status_code == 202
    job_id = upload_response.json()["job_id"]

    # Poll status until completion
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

    # Verify job completed successfully
    assert status == "completed", f"Job did not complete in {max_wait}s, status: {status}"

    # Download result
    result_response = client.get(f"/jobs/{job_id}/result")
    assert result_response.status_code == 200
    hocr_content = result_response.text

    # Validate HOCR structure
    assert '<?xml version="1.0"' in hocr_content
    assert "ocr_page" in hocr_content or "ocr_line" in hocr_content
    assert "bbox" in hocr_content  # Bounding boxes present


def test_multiple_languages_end_to_end(client: TestClient, sample_jpeg):
    """Test that multiple languages work in OCR processing (US1)."""
    # Upload with multiple languages
    with open(sample_jpeg, "rb") as f:
        upload_response = client.post(
            "/upload", files={"file": f}, data={"lang": "eng+fra"}
        )

    assert upload_response.status_code == 202
    job_id = upload_response.json()["job_id"]

    # Poll status until completion
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

    # Verify job completed successfully
    assert status == "completed", f"Job did not complete in {max_wait}s, status: {status}"

    # Download result
    result_response = client.get(f"/jobs/{job_id}/result")
    assert result_response.status_code == 200
    hocr_content = result_response.text

    # Validate HOCR output
    assert '<?xml version="1.0"' in hocr_content
    assert "ocr_page" in hocr_content or "ocr_line" in hocr_content


def test_all_parameters_end_to_end(client: TestClient, sample_jpeg):
    """Test that all Tesseract parameters work together (US1-US4)."""
    # Upload with all parameters
    with open(sample_jpeg, "rb") as f:
        upload_response = client.post(
            "/upload",
            files={"file": f},
            data={"lang": "eng", "psm": 6, "oem": 1, "dpi": 300},
        )

    assert upload_response.status_code == 202
    job_id = upload_response.json()["job_id"]

    # Poll status until completion
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

    # Verify job completed successfully
    assert status == "completed", f"Job did not complete in {max_wait}s, status: {status}"

    # Download result
    result_response = client.get(f"/jobs/{job_id}/result")
    assert result_response.status_code == 200
    hocr_content = result_response.text

    # Validate HOCR output
    assert '<?xml version="1.0"' in hocr_content
    assert "ocr_page" in hocr_content or "ocr_line" in hocr_content
    assert "bbox" in hocr_content
