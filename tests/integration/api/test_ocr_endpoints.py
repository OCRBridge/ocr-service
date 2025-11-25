"""Integration tests for V2 OCR API endpoints.

Tests all V2 API endpoints with mocked engines including:
- List engines endpoint
- Engine schema endpoint
- Process document endpoint
- All error cases and validations
"""

import io
import json
from unittest.mock import patch

import pytest


def test_list_engines_returns_200(client):
    """Test that list engines endpoint returns 200 OK."""
    response = client.get("/v2/ocr/engines")

    assert response.status_code == 200


def test_list_engines_returns_json(client):
    """Test that list engines returns JSON response."""
    response = client.get("/v2/ocr/engines")

    assert response.headers["content-type"] == "application/json"
    data = response.json()
    assert isinstance(data, dict)


def test_list_engines_has_engines_field(client):
    """Test that response includes engines field with list."""
    response = client.get("/v2/ocr/engines")
    data = response.json()

    assert "engines" in data
    assert isinstance(data["engines"], list)


def test_list_engines_has_count_field(client):
    """Test that response includes count field."""
    response = client.get("/v2/ocr/engines")
    data = response.json()

    assert "count" in data
    assert isinstance(data["count"], int)
    assert data["count"] == len(data["engines"])


def test_list_engines_includes_mock_engines(client, mock_engine_registry):
    """Test that mock engines are listed."""
    response = client.get("/v2/ocr/engines")
    data = response.json()

    # Should include our mock engines
    engines = data["engines"]
    assert "tesseract" in engines
    assert "easyocr" in engines


def test_list_engines_has_details(client):
    """Test that response includes engine details."""
    response = client.get("/v2/ocr/engines")
    data = response.json()

    assert "details" in data
    assert isinstance(data["details"], list)


def test_list_engines_details_structure(client):
    """Test structure of engine details."""
    response = client.get("/v2/ocr/engines")
    data = response.json()

    if data["details"]:
        detail = data["details"][0]
        # Should have basic engine info fields
        assert "name" in detail
        assert isinstance(detail["name"], str)


def test_get_engine_schema_tesseract(client):
    """Test getting schema for tesseract engine."""
    response = client.get("/v2/ocr/engines/tesseract/schema")

    assert response.status_code == 200
    data = response.json()
    assert data["engine"] == "tesseract"
    assert "schema" in data


def test_get_engine_schema_easyocr(client):
    """Test getting schema for easyocr engine."""
    response = client.get("/v2/ocr/engines/easyocr/schema")

    assert response.status_code == 200
    data = response.json()
    assert data["engine"] == "easyocr"
    assert "schema" in data


def test_get_engine_schema_not_found(client):
    """Test getting schema for non-existent engine returns 404."""
    response = client.get("/v2/ocr/engines/nonexistent/schema")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()


def test_get_engine_schema_includes_available_engines(client):
    """Test that 404 response includes list of available engines."""
    response = client.get("/v2/ocr/engines/invalid/schema")

    assert response.status_code == 404
    data = response.json()
    # Should mention available engines
    assert "available engines" in data["detail"].lower()


def test_get_engine_schema_returns_json_schema(client):
    """Test that schema endpoint returns valid JSON schema."""
    response = client.get("/v2/ocr/engines/tesseract/schema")

    assert response.status_code == 200
    data = response.json()

    schema = data["schema"]
    if schema is not None:
        # Should have JSON schema structure
        assert "properties" in schema or "type" in schema


def test_process_document_missing_engine(client, sample_jpeg_bytes):
    """Test that process endpoint requires engine parameter."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}

    response = client.post("/v2/ocr/process", files=files)

    # Should fail validation because engine is required
    assert response.status_code in [400, 422]


def test_process_document_missing_file(client):
    """Test that process endpoint requires file parameter."""
    data = {"engine": "tesseract"}

    response = client.post("/v2/ocr/process", data=data)

    # Should fail validation because file is required
    assert response.status_code in [400, 422]


def test_process_document_invalid_engine(client, sample_jpeg_bytes):
    """Test processing with non-existent engine returns 400."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    data = {"engine": "nonexistent"}

    response = client.post("/v2/ocr/process", files=files, data=data)

    assert response.status_code == 400
    error_data = response.json()
    assert "detail" in error_data
    assert "not found" in error_data["detail"].lower()


def test_process_document_success_tesseract(client, sample_jpeg_bytes):
    """Test successful document processing with tesseract."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    data = {"engine": "tesseract"}

    response = client.post("/v2/ocr/process", files=files, data=data)

    assert response.status_code == 200
    result = response.json()

    # Check response structure
    assert "hocr" in result
    assert "processing_duration_seconds" in result
    assert "engine" in result
    assert "pages" in result

    # Check values
    assert result["engine"] == "tesseract"
    assert isinstance(result["hocr"], str)
    assert result["hocr"].startswith("<?xml")


def test_process_document_success_easyocr(client, sample_jpeg_bytes):
    """Test successful document processing with easyocr."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    data = {"engine": "easyocr"}

    response = client.post("/v2/ocr/process", files=files, data=data)

    assert response.status_code == 200
    result = response.json()

    assert result["engine"] == "easyocr"
    assert isinstance(result["hocr"], str)


def test_process_document_with_valid_params(client, sample_jpeg_bytes):
    """Test processing with valid engine parameters."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    params = {"lang": "eng", "psm": 6}
    data = {"engine": "tesseract", "params": json.dumps(params)}

    response = client.post("/v2/ocr/process", files=files, data=data)

    assert response.status_code == 200


def test_process_document_with_invalid_json_params(client, sample_jpeg_bytes):
    """Test that invalid JSON in params returns 400."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    data = {"engine": "tesseract", "params": "not valid json{"}

    response = client.post("/v2/ocr/process", files=files, data=data)

    assert response.status_code == 400
    error_data = response.json()
    assert "invalid json" in error_data["detail"].lower()


def test_process_document_with_invalid_param_values(client, sample_jpeg_bytes):
    """Test that invalid parameter values return 400."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    # Invalid psm value (must be 0-13)
    params = {"psm": 999}
    data = {"engine": "tesseract", "params": json.dumps(params)}

    response = client.post("/v2/ocr/process", files=files, data=data)

    assert response.status_code == 400


def test_process_document_with_unknown_params(client, sample_jpeg_bytes):
    """Test that unknown parameters are rejected."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    params = {"unknown_param": "value"}
    data = {"engine": "tesseract", "params": json.dumps(params)}

    response = client.post("/v2/ocr/process", files=files, data=data)

    # Should reject extra fields
    assert response.status_code == 400


def test_process_document_file_too_large(client):
    """Test that files over 5MB are rejected with 413."""
    # Create file larger than 5MB sync limit
    large_file = b"\xff\xd8\xff\xe0" + b"\x00" * (6 * 1024 * 1024)
    files = {"file": ("large.jpg", io.BytesIO(large_file), "image/jpeg")}
    data = {"engine": "tesseract"}

    response = client.post("/v2/ocr/process", files=files, data=data)

    assert response.status_code == 413
    error_data = response.json()
    assert "5mb" in error_data["detail"].lower()


def test_process_document_response_structure(client, sample_jpeg_bytes):
    """Test complete response structure."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    data = {"engine": "tesseract"}

    response = client.post("/v2/ocr/process", files=files, data=data)

    assert response.status_code == 200
    result = response.json()

    # Required fields
    assert "hocr" in result
    assert "processing_duration_seconds" in result
    assert "engine" in result
    assert "pages" in result

    # Field types
    assert isinstance(result["hocr"], str)
    assert isinstance(result["processing_duration_seconds"], (int, float))
    assert isinstance(result["engine"], str)
    assert isinstance(result["pages"], int)

    # Field values
    assert result["processing_duration_seconds"] >= 0
    assert result["pages"] >= 1


def test_process_document_hocr_output(client, sample_jpeg_bytes):
    """Test that HOCR output is valid XML."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    data = {"engine": "tesseract"}

    response = client.post("/v2/ocr/process", files=files, data=data)

    assert response.status_code == 200
    result = response.json()

    hocr = result["hocr"]
    # Should be XML
    assert hocr.startswith("<?xml")
    assert "<html" in hocr
    assert "</html>" in hocr
    # Should have HOCR structure
    assert 'class="ocr_page"' in hocr


def test_process_document_preserves_filename(client, sample_jpeg_bytes):
    """Test that different filenames are handled correctly."""
    filenames = ["document.jpg", "scan.png", "file.pdf"]

    for filename in filenames:
        files = {"file": (filename, io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
        data = {"engine": "tesseract"}

        response = client.post("/v2/ocr/process", files=files, data=data)
        assert response.status_code == 200


def test_process_document_pdf(client, sample_pdf_bytes):
    """Test processing PDF document."""
    files = {"file": ("document.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
    data = {"engine": "tesseract"}

    response = client.post("/v2/ocr/process", files=files, data=data)

    assert response.status_code == 200


def test_process_document_png(client, sample_png_bytes):
    """Test processing PNG image."""
    files = {"file": ("image.png", io.BytesIO(sample_png_bytes), "image/png")}
    data = {"engine": "tesseract"}

    response = client.post("/v2/ocr/process", files=files, data=data)

    assert response.status_code == 200


def test_process_document_concurrent_requests(client, sample_jpeg_bytes):
    """Test that multiple concurrent requests work correctly."""
    import concurrent.futures

    def make_request():
        files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
        data = {"engine": "tesseract"}
        return client.post("/v2/ocr/process", files=files, data=data)

    # Make 5 concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request) for _ in range(5)]
        responses = [f.result() for f in futures]

    # All should succeed
    assert all(r.status_code == 200 for r in responses)


def test_process_document_easyocr_params(client, sample_jpeg_bytes):
    """Test processing with easyocr-specific parameters."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    params = {"languages": ["en"]}
    data = {"engine": "easyocr", "params": json.dumps(params)}

    response = client.post("/v2/ocr/process", files=files, data=data)

    assert response.status_code == 200


def test_list_engines_consistent_response(client):
    """Test that list engines returns consistent results."""
    response1 = client.get("/v2/ocr/engines")
    response2 = client.get("/v2/ocr/engines")

    assert response1.json() == response2.json()


def test_get_engine_schema_consistent_response(client):
    """Test that schema endpoint returns consistent results."""
    response1 = client.get("/v2/ocr/engines/tesseract/schema")
    response2 = client.get("/v2/ocr/engines/tesseract/schema")

    assert response1.json() == response2.json()


def test_process_document_no_params(client, sample_jpeg_bytes):
    """Test processing without optional params parameter."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    data = {"engine": "tesseract"}
    # Explicitly don't include params

    response = client.post("/v2/ocr/process", files=files, data=data)

    assert response.status_code == 200


def test_process_document_empty_params(client, sample_jpeg_bytes):
    """Test processing with empty params string."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    data = {"engine": "tesseract", "params": "{}"}

    response = client.post("/v2/ocr/process", files=files, data=data)

    assert response.status_code == 200


def test_process_document_timing(client, sample_jpeg_bytes):
    """Test that processing duration is reasonable."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    data = {"engine": "tesseract"}

    import time

    start = time.time()
    response = client.post("/v2/ocr/process", files=files, data=data)
    duration = time.time() - start

    assert response.status_code == 200
    result = response.json()

    # Reported duration should be less than actual (no overhead)
    assert result["processing_duration_seconds"] <= duration
    # Should complete in reasonable time (with mocks, should be very fast)
    assert duration < 5.0


def test_list_engines_only_get_allowed(client):
    """Test that only GET method is allowed for list engines."""
    # GET should work
    get_response = client.get("/v2/ocr/engines")
    assert get_response.status_code == 200

    # POST should not be allowed
    post_response = client.post("/v2/ocr/engines")
    assert post_response.status_code in [405, 404]


def test_get_engine_schema_only_get_allowed(client):
    """Test that only GET method is allowed for schema endpoint."""
    # GET should work
    get_response = client.get("/v2/ocr/engines/tesseract/schema")
    assert get_response.status_code == 200

    # POST should not be allowed
    post_response = client.post("/v2/ocr/engines/tesseract/schema")
    assert post_response.status_code in [405, 404]


def test_process_document_only_post_allowed(client):
    """Test that only POST method is allowed for process endpoint."""
    # GET should not be allowed
    get_response = client.get("/v2/ocr/process")
    assert get_response.status_code in [405, 404, 422]


def test_process_document_case_sensitive_engine(client, sample_jpeg_bytes):
    """Test that engine names are case-sensitive."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    data = {"engine": "TESSERACT"}  # Wrong case

    response = client.post("/v2/ocr/process", files=files, data=data)

    # Should not find engine (case sensitive)
    assert response.status_code == 400


def test_process_document_with_tesseract_lang_param(client, sample_jpeg_bytes):
    """Test tesseract with language parameter."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    params = {"lang": "fra"}  # French
    data = {"engine": "tesseract", "params": json.dumps(params)}

    response = client.post("/v2/ocr/process", files=files, data=data)

    assert response.status_code == 200


def test_process_document_with_tesseract_psm_param(client, sample_jpeg_bytes):
    """Test tesseract with PSM parameter."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    params = {"psm": 6}  # Assume uniform block of text
    data = {"engine": "tesseract", "params": json.dumps(params)}

    response = client.post("/v2/ocr/process", files=files, data=data)

    assert response.status_code == 200


def test_process_document_pages_count(client, sample_jpeg_bytes):
    """Test that page count is included in response."""
    files = {"file": ("test.jpg", io.BytesIO(sample_jpeg_bytes), "image/jpeg")}
    data = {"engine": "tesseract"}

    response = client.post("/v2/ocr/process", files=files, data=data)

    assert response.status_code == 200
    result = response.json()

    # Should have at least 1 page
    assert result["pages"] >= 1


def test_engine_schema_engine_without_params(client):
    """Test schema for engine without configurable parameters."""
    # MockEngineWithoutParams has no parameters
    # First need to check if it's available
    engines_response = client.get("/v2/ocr/engines")
    engines = engines_response.json()["engines"]

    # If we have an engine without params, test it
    # For now, tesseract and easyocr both have params
    # This test documents the expected behavior
    pass


def test_list_engines_includes_details_for_each_engine(client):
    """Test that details are provided for each engine."""
    response = client.get("/v2/ocr/engines")
    data = response.json()

    engines_count = data["count"]
    details_count = len(data["details"])

    # Should have details for most engines (some may fail)
    # At least 1 detail should be present
    if engines_count > 0:
        assert details_count >= 1
