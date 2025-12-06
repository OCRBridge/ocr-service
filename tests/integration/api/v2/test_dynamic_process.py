"""Integration tests for dynamic per-engine OCR endpoints.

These tests hit the dynamically generated endpoints:
- /v2/ocr/tesseract/process
"""

import io


def test_tesseract_process_success(client, sample_jpeg_bytes):
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}

    resp = client.post("/v2/ocr/tesseract/process", files=files)
    assert resp.status_code == 200

    data = resp.json()
    assert data["engine"] == "tesseract"
    assert isinstance(data.get("hocr"), str)
    assert data.get("hocr", "").startswith("<?xml")
    assert data.get("pages", 0) >= 1


def test_tesseract_invalid_param_returns_400(client, sample_jpeg_bytes):
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    # psm must be <= 13
    data = {"psm": 99}

    resp = client.post("/v2/ocr/tesseract/process", files=files, data=data)
    assert resp.status_code == 400
    err = resp.json()
    assert err.get("error_code") == "validation_error"
    assert isinstance(err.get("errors"), list)
    assert len(err.get("errors")) > 0


def test_tesseract_process_with_params(client, sample_jpeg_bytes):
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    data = {"lang": "eng", "psm": 3, "oem": 1, "dpi": 300}

    resp = client.post("/v2/ocr/tesseract/process", files=files, data=data)
    assert resp.status_code == 200

    data = resp.json()
    assert data["engine"] == "tesseract"
    assert isinstance(data.get("hocr"), str)


def test_file_too_large_returns_413(client, large_file_bytes):
    files = {"file": ("large.jpg", io.BytesIO(large_file_bytes), "image/jpeg")}

    resp = client.post("/v2/ocr/tesseract/process", files=files)
    assert resp.status_code == 413
    err = resp.json()
    assert "5mb" in err.get("detail", "").lower()


def test_missing_file_returns_422_or_400(client):
    resp = client.post("/v2/ocr/tesseract/process")
    assert resp.status_code in [400, 422]
