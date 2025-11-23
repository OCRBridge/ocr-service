"""Contract tests for synchronous OCR endpoint OpenAPI compliance."""

import pytest
from fastapi.testclient import TestClient

# ============================================================================
# Tesseract Endpoint OpenAPI Tests
# ============================================================================


def test_sync_tesseract_openapi_endpoint_exists(client: TestClient):
    """Test that /sync/tesseract endpoint is registered in OpenAPI schema."""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    openapi_schema = response.json()
    assert "/sync/tesseract" in openapi_schema["paths"]
    assert "post" in openapi_schema["paths"]["/sync/tesseract"]


def test_sync_tesseract_openapi_request_parameters(client: TestClient):
    """Test that /sync/tesseract has correct request parameters in OpenAPI schema."""
    response = client.get("/openapi.json")
    openapi_schema = response.json()

    endpoint_schema = openapi_schema["paths"]["/sync/tesseract"]["post"]
    schema_ref = endpoint_schema["requestBody"]["content"]["multipart/form-data"]["schema"]["$ref"]
    schema_name = schema_ref.split("/")[-1]
    request_body = openapi_schema["components"]["schemas"][schema_name]

    # Check required file parameter
    assert "file" in request_body["properties"]
    assert request_body["required"] == ["file"]

    # Check optional parameters
    assert "lang" in request_body["properties"]
    assert "psm" in request_body["properties"]
    assert "oem" in request_body["properties"]
    assert "dpi" in request_body["properties"]


def test_sync_tesseract_openapi_response_schema(client: TestClient):
    """Test that /sync/tesseract has correct response schema in OpenAPI."""
    response = client.get("/openapi.json")
    openapi_schema = response.json()

    endpoint_schema = openapi_schema["paths"]["/sync/tesseract"]["post"]

    # Check 200 response schema
    assert "200" in endpoint_schema["responses"]
    response_schema = endpoint_schema["responses"]["200"]
    assert "content" in response_schema
    assert "application/json" in response_schema["content"]

    # Check response model has required fields
    schema_ref = response_schema["content"]["application/json"]["schema"]["$ref"]
    model_name = schema_ref.split("/")[-1]
    model_schema = openapi_schema["components"]["schemas"][model_name]

    assert "hocr" in model_schema["properties"]
    assert "processing_duration_seconds" in model_schema["properties"]
    assert "engine" in model_schema["properties"]
    assert "pages" in model_schema["properties"]
    assert set(model_schema["required"]) == {
        "hocr",
        "processing_duration_seconds",
        "engine",
        "pages",
    }


def test_sync_tesseract_parameter_validation_lang(client: TestClient, sample_jpeg):
    """Test lang parameter validation matches OpenAPI spec."""
    # Valid language code
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": f}, data={"lang": "eng"})
    assert response.status_code == 200

    # Invalid language code format (should fail pattern validation)
    # FastAPI may return 400 or 422 for pattern validation failures
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": f}, data={"lang": "INVALID"})
    assert response.status_code in [400, 422]


def test_sync_tesseract_parameter_validation_psm(client: TestClient, sample_jpeg):
    """Test psm parameter validation matches OpenAPI spec (0-13)."""
    # Valid PSM values (skip 0 as it may not be supported by all Tesseract versions)
    for psm in [3, 6, 13]:
        with open(sample_jpeg, "rb") as f:
            response = client.post("/sync/tesseract", files={"file": f}, data={"psm": psm})
        assert response.status_code == 200, f"PSM {psm} should be valid"

    # Invalid PSM values
    for psm in [-1, 14, 100]:
        with open(sample_jpeg, "rb") as f:
            response = client.post("/sync/tesseract", files={"file": f}, data={"psm": psm})
        assert response.status_code in [400, 422], f"PSM {psm} should be invalid"


def test_sync_tesseract_parameter_validation_oem(client: TestClient, sample_jpeg):
    """Test oem parameter validation matches OpenAPI spec (0-3)."""
    # Valid OEM values (test only 1=LSTM and 3=Default which are commonly available)
    for oem in [1, 3]:
        with open(sample_jpeg, "rb") as f:
            response = client.post("/sync/tesseract", files={"file": f}, data={"oem": oem})
        assert response.status_code == 200, f"OEM {oem} should be valid"

    # Invalid OEM values
    for oem in [-1, 4, 10]:
        with open(sample_jpeg, "rb") as f:
            response = client.post("/sync/tesseract", files={"file": f}, data={"oem": oem})
        assert response.status_code in [400, 422], f"OEM {oem} should be invalid"


def test_sync_tesseract_parameter_validation_dpi(client: TestClient, sample_jpeg):
    """Test dpi parameter validation matches OpenAPI spec (70-2400)."""
    # Valid DPI values
    for dpi in [70, 150, 300, 600, 2400]:
        with open(sample_jpeg, "rb") as f:
            response = client.post("/sync/tesseract", files={"file": f}, data={"dpi": dpi})
        assert response.status_code == 200, f"DPI {dpi} should be valid"

    # Invalid DPI values
    for dpi in [69, 2401, 5000]:
        with open(sample_jpeg, "rb") as f:
            response = client.post("/sync/tesseract", files={"file": f}, data={"dpi": dpi})
        assert response.status_code in [400, 422], f"DPI {dpi} should be invalid"


def test_sync_tesseract_error_responses_in_openapi(client: TestClient):
    """Test that error responses are documented in OpenAPI schema."""
    response = client.get("/openapi.json")
    openapi_schema = response.json()

    endpoint_schema = openapi_schema["paths"]["/sync/tesseract"]["post"]
    responses = endpoint_schema["responses"]

    # Check that common error codes are documented
    # Note: OpenAPI may not document all error codes, but 422 is typically included
    assert "422" in responses or "default" in responses


# ============================================================================
# EasyOCR Endpoint OpenAPI Tests
# ============================================================================


def test_sync_easyocr_openapi_endpoint_exists(client: TestClient):
    """Test that /sync/easyocr endpoint is registered in OpenAPI schema."""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    openapi_schema = response.json()
    assert "/sync/easyocr" in openapi_schema["paths"]
    assert "post" in openapi_schema["paths"]["/sync/easyocr"]


def test_sync_easyocr_openapi_request_parameters(client: TestClient):
    """Test that /sync/easyocr has correct request parameters in OpenAPI schema."""
    response = client.get("/openapi.json")
    openapi_schema = response.json()

    endpoint_schema = openapi_schema["paths"]["/sync/easyocr"]["post"]
    schema_ref = endpoint_schema["requestBody"]["content"]["multipart/form-data"]["schema"]["$ref"]
    schema_name = schema_ref.split("/")[-1]
    request_body = openapi_schema["components"]["schemas"][schema_name]

    # Check required file parameter
    assert "file" in request_body["properties"]
    assert request_body["required"] == ["file"]

    # Check optional parameters (actual EasyOCR parameters)
    assert "languages" in request_body["properties"]
    assert "text_threshold" in request_body["properties"]
    assert "link_threshold" in request_body["properties"]


def test_sync_easyocr_openapi_response_schema(client: TestClient):
    """Test that /sync/easyocr has correct response schema in OpenAPI."""
    response = client.get("/openapi.json")
    openapi_schema = response.json()

    endpoint_schema = openapi_schema["paths"]["/sync/easyocr"]["post"]

    # Check 200 response schema
    assert "200" in endpoint_schema["responses"]
    response_schema = endpoint_schema["responses"]["200"]
    assert "content" in response_schema
    assert "application/json" in response_schema["content"]

    # Check response model has required fields (same as Tesseract - SyncOCRResponse)
    schema_ref = response_schema["content"]["application/json"]["schema"]["$ref"]
    model_name = schema_ref.split("/")[-1]
    model_schema = openapi_schema["components"]["schemas"][model_name]

    assert "hocr" in model_schema["properties"]
    assert "processing_duration_seconds" in model_schema["properties"]
    assert "engine" in model_schema["properties"]
    assert "pages" in model_schema["properties"]
    assert set(model_schema["required"]) == {
        "hocr",
        "processing_duration_seconds",
        "engine",
        "pages",
    }


# ============================================================================
# OCRmac Endpoint OpenAPI Tests
# ============================================================================


@pytest.mark.macos
def test_sync_ocrmac_openapi_endpoint_exists(client: TestClient):
    """Test that /sync/ocrmac endpoint is registered in OpenAPI schema."""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    openapi_schema = response.json()
    assert "/sync/ocrmac" in openapi_schema["paths"]
    assert "post" in openapi_schema["paths"]["/sync/ocrmac"]


@pytest.mark.macos
def test_sync_ocrmac_openapi_request_parameters(client: TestClient):
    """Test that /sync/ocrmac has correct request parameters in OpenAPI schema."""
    response = client.get("/openapi.json")
    openapi_schema = response.json()

    endpoint_schema = openapi_schema["paths"]["/sync/ocrmac"]["post"]
    schema_ref = endpoint_schema["requestBody"]["content"]["multipart/form-data"]["schema"]["$ref"]
    schema_name = schema_ref.split("/")[-1]
    request_body = openapi_schema["components"]["schemas"][schema_name]

    # Check required file parameter
    assert "file" in request_body["properties"]
    assert request_body["required"] == ["file"]

    # Check optional parameters (ocrmac parameters)
    assert "languages" in request_body["properties"]
    assert "recognition_level" in request_body["properties"]


@pytest.mark.macos
def test_sync_ocrmac_openapi_response_schema(client: TestClient):
    """Test that /sync/ocrmac has correct response schema in OpenAPI."""
    response = client.get("/openapi.json")
    openapi_schema = response.json()

    endpoint_schema = openapi_schema["paths"]["/sync/ocrmac"]["post"]

    # Check 200 response schema
    assert "200" in endpoint_schema["responses"]
    response_schema = endpoint_schema["responses"]["200"]
    assert "content" in response_schema
    assert "application/json" in response_schema["content"]

    # Check response model has required fields (same as others - SyncOCRResponse)
    schema_ref = response_schema["content"]["application/json"]["schema"]["$ref"]
    model_name = schema_ref.split("/")[-1]
    model_schema = openapi_schema["components"]["schemas"][model_name]

    assert "hocr" in model_schema["properties"]
    assert "processing_duration_seconds" in model_schema["properties"]
    assert "engine" in model_schema["properties"]
    assert "pages" in model_schema["properties"]
    assert set(model_schema["required"]) == {
        "hocr",
        "processing_duration_seconds",
        "engine",
        "pages",
    }


# ============================================================================
# LiveText Recognition Level OpenAPI Tests
# ============================================================================


@pytest.mark.macos
def test_sync_ocrmac_openapi_recognition_level_includes_livetext(client: TestClient):
    """Test that OpenAPI schema includes 'livetext' in recognition_level pattern."""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    openapi_schema = response.json()

    # Find the sync ocrmac endpoint schema
    sync_ocrmac_path = openapi_schema["paths"]["/sync/ocrmac"]["post"]

    # Get the request body schema reference
    request_body_ref = sync_ocrmac_path["requestBody"]["content"]["multipart/form-data"]["schema"][
        "$ref"
    ]
    schema_name = request_body_ref.split("/")[-1]

    # Get the Body schema
    body_schema = openapi_schema["components"]["schemas"][schema_name]

    # Check recognition_level field
    assert "recognition_level" in body_schema["properties"], (
        "recognition_level not found in request schema"
    )

    recognition_level_prop = body_schema["properties"]["recognition_level"]

    # Should have a pattern that includes all four recognition levels
    # The field is anyOf [pattern string, null] due to Form(None, pattern=...)
    if "anyOf" in recognition_level_prop:
        # Find the pattern in anyOf options
        pattern_found = None
        for option in recognition_level_prop["anyOf"]:
            if "pattern" in option:
                pattern_found = option["pattern"]
                break

        assert pattern_found is not None, "Pattern not found in recognition_level anyOf options"

        # Verify the pattern includes all four values
        assert "fast" in pattern_found, "fast not in recognition_level pattern"
        assert "balanced" in pattern_found, "balanced not in recognition_level pattern"
        assert "accurate" in pattern_found, "accurate not in recognition_level pattern"
        assert "livetext" in pattern_found, "livetext not in recognition_level pattern"

        # Verify the exact pattern format
        assert pattern_found == "^(fast|balanced|accurate|livetext)$", (
            f"Expected pattern '^(fast|balanced|accurate|livetext)$', got '{pattern_found}'"
        )
    elif "pattern" in recognition_level_prop:
        # Direct pattern field
        pattern = recognition_level_prop["pattern"]
        assert (
            "fast" in pattern
            and "balanced" in pattern
            and "accurate" in pattern
            and "livetext" in pattern
        )
        assert pattern == "^(fast|balanced|accurate|livetext)$"
    else:
        raise AssertionError("recognition_level field does not have a pattern constraint")
