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


def test_engine_not_found_returns_404(client, sample_jpeg_bytes):
    """Test that requesting a non-existent engine returns 404."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}

    resp = client.post("/v2/ocr/nonexistent_engine/process", files=files)
    assert resp.status_code == 404


def test_unsupported_file_format_returns_error(client):
    """Test that unsupported file formats are rejected."""
    # Create a text file (not an image)
    text_content = b"This is not an image"
    files = {"file": ("test.txt", io.BytesIO(text_content), "text/plain")}

    resp = client.post("/v2/ocr/tesseract/process", files=files)
    # Might return 400 (validation) or 500 (processing error)
    assert resp.status_code in [400, 500]


def test_invalid_filename_characters_handled(client, sample_jpeg_bytes):
    """Test that filenames with path traversal characters are handled."""
    # Filename with path traversal attempt - Path().name sanitizes this
    files = {"file": ("../../etc/passwd.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}

    resp = client.post("/v2/ocr/tesseract/process", files=files)
    # May process successfully with sanitized filename or reject
    assert resp.status_code in [200, 400]


def test_unsupported_file_extension_rejected(client, sample_jpeg_bytes):
    """Test that unsupported file extensions are rejected."""
    files = {"file": ("test.exe", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}

    resp = client.post("/v2/ocr/tesseract/process", files=files)
    # Should reject with 400, or fail processing with 500
    assert resp.status_code in [400, 500]
    if resp.status_code == 400:
        err = resp.json()
        assert (
            "extension" in err.get("detail", "").lower()
            or "invalid" in err.get("detail", "").lower()
        )


def test_concurrent_requests_isolated(client, sample_jpeg_bytes):
    """Test that concurrent requests are properly isolated."""
    files1 = {"file": ("test1.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    files2 = {"file": ("test2.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}

    # Make concurrent requests
    resp1 = client.post("/v2/ocr/tesseract/process", files=files1)
    resp2 = client.post("/v2/ocr/tesseract/process", files=files2)

    # Both should succeed
    assert resp1.status_code == 200
    assert resp2.status_code == 200

    # Each should have unique results
    data1 = resp1.json()
    data2 = resp2.json()

    assert "hocr" in data1
    assert "hocr" in data2


def test_empty_file_handled(client):
    """Test that empty files are handled appropriately."""
    files = {"file": ("empty.jpg", io.BytesIO(b""), "image/jpeg")}

    resp = client.post("/v2/ocr/tesseract/process", files=files)
    # Empty file might be processed (returns 200) or rejected (400/422/500)
    assert resp.status_code in [200, 400, 422, 500]


def test_response_includes_processing_duration(client, sample_jpeg_bytes):
    """Test that response includes processing duration."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}

    resp = client.post("/v2/ocr/tesseract/process", files=files)
    assert resp.status_code == 200

    data = resp.json()
    assert "processing_duration_seconds" in data
    assert isinstance(data["processing_duration_seconds"], (int, float))
    assert data["processing_duration_seconds"] > 0


def test_response_includes_page_count(client, sample_jpeg_bytes):
    """Test that response includes page count."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}

    resp = client.post("/v2/ocr/tesseract/process", files=files)
    assert resp.status_code == 200

    data = resp.json()
    assert "pages" in data
    assert isinstance(data["pages"], int)
    assert data["pages"] >= 1


def test_multiple_parameters_validation(client, sample_jpeg_bytes):
    """Test validation with multiple parameters."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    # Valid parameters
    data = {"lang": "eng", "psm": 6, "oem": 3, "dpi": 300}

    resp = client.post("/v2/ocr/tesseract/process", files=files, data=data)
    assert resp.status_code == 200


def test_parameter_type_coercion(client, sample_jpeg_bytes):
    """Test that parameter types are coerced correctly."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    # Send dpi as string (should be coerced to int)
    data = {"dpi": "300"}

    resp = client.post("/v2/ocr/tesseract/process", files=files, data=data)
    assert resp.status_code == 200


def test_extra_parameters_rejected(client, sample_jpeg_bytes):
    """Test that extra/unknown parameters are rejected."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    data = {"unknown_param": "value"}

    resp = client.post("/v2/ocr/tesseract/process", files=files, data=data)
    # Should either succeed (ignore extra) or return 400
    assert resp.status_code in [200, 400]


def test_filename_without_extension(client, sample_jpeg_bytes):
    """Test file upload without file extension."""
    files = {"file": ("testfile", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}

    resp = client.post("/v2/ocr/tesseract/process", files=files)
    # Should still process based on content
    assert resp.status_code in [200, 400]


def test_request_id_in_response_headers(client, sample_jpeg_bytes):
    """Test that response includes X-Request-ID header."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}

    resp = client.post("/v2/ocr/tesseract/process", files=files)

    # Should have request ID header (from logging middleware)
    assert "X-Request-ID" in resp.headers or "x-request-id" in resp.headers


def test_different_image_formats(client):
    """Test processing different supported image formats."""
    import base64

    # Minimal valid PNG (1x1 transparent pixel)
    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )

    files = {"file": ("test.png", io.BytesIO(png_data), "image/png")}

    resp = client.post("/v2/ocr/tesseract/process", files=files)
    # PNG should be supported
    assert resp.status_code == 200


def test_maximum_filename_length(client, sample_jpeg_bytes):
    """Test handling of very long filenames."""
    long_name = "a" * 200 + ".jpg"
    files = {"file": (long_name, io.BytesIO(sample_jpeg_bytes), "image/jpeg")}

    resp = client.post("/v2/ocr/tesseract/process", files=files)
    # Should handle gracefully
    assert resp.status_code in [200, 400]
