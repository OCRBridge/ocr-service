"""Contract tests for Tesseract parameter validation in upload endpoint."""

from fastapi.testclient import TestClient


# Phase 3: User Story 1 - Language Selection (T007-T012)


def test_upload_with_valid_single_language(client: TestClient, sample_jpeg):
    """Test upload with valid single language parameter (lang=fra)."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload", files={"file": f}, data={"lang": "fra"})

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"


def test_upload_with_multiple_languages(client: TestClient, sample_jpeg):
    """Test upload with multiple languages (lang=eng+fra)."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload", files={"file": f}, data={"lang": "eng+fra"})

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"


def test_upload_with_invalid_language_code(client: TestClient, sample_jpeg):
    """Test upload with invalid language code format."""
    with open(sample_jpeg, "rb") as f:
        # Invalid format (uppercase, wrong length, etc.)
        response = client.post("/upload", files={"file": f}, data={"lang": "INVALID"})

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    # Pydantic validation error for pattern mismatch
    assert any("pattern" in str(error).lower() or "string" in str(error).lower() for error in data["detail"])


def test_upload_with_language_not_installed(client: TestClient, sample_jpeg):
    """Test upload with language code not installed on system."""
    with open(sample_jpeg, "rb") as f:
        # Valid format but language not installed
        response = client.post("/upload", files={"file": f}, data={"lang": "xyz"})

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    # Should mention language not installed
    error_msg = str(data["detail"])
    assert "not installed" in error_msg.lower() or "available" in error_msg.lower()


def test_upload_with_too_many_languages(client: TestClient, sample_jpeg):
    """Test upload with more than 5 languages (should fail)."""
    with open(sample_jpeg, "rb") as f:
        # 6 languages (max is 5)
        response = client.post("/upload", files={"file": f}, data={"lang": "eng+fra+deu+spa+ita+por"})

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    error_msg = str(data["detail"])
    assert "5" in error_msg or "maximum" in error_msg.lower()


def test_upload_without_language_defaults_to_english(client: TestClient, sample_jpeg):
    """Test upload without language parameter defaults to English."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload", files={"file": f})

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"
    # Should process successfully with default language (eng)


# Phase 4: User Story 2 - PSM Control (T018-T021)


def test_upload_with_valid_psm_values(client: TestClient, sample_jpeg):
    """Test upload with valid PSM values (0-13)."""
    valid_psm_values = [0, 3, 6, 7, 11, 13]

    for psm in valid_psm_values:
        with open(sample_jpeg, "rb") as f:
            response = client.post("/upload", files={"file": f}, data={"psm": psm})

        assert response.status_code == 202, f"PSM {psm} should be valid"
        data = response.json()
        assert "job_id" in data


def test_upload_with_invalid_psm_value(client: TestClient, sample_jpeg):
    """Test upload with invalid PSM value (>13)."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload", files={"file": f}, data={"psm": 99})

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    error_msg = str(data["detail"])
    assert "psm" in error_msg.lower() or "literal" in error_msg.lower()


def test_upload_with_psm_single_line_document(client: TestClient, sample_jpeg):
    """Test upload with PSM=7 (single line) for single-line documents."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload", files={"file": f}, data={"psm": 7})

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data


def test_upload_without_psm_uses_default(client: TestClient, sample_jpeg):
    """Test upload without PSM parameter uses Tesseract default."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload", files={"file": f})

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data


# Phase 5: User Story 3 - OEM Selection (T026-T029)


def test_upload_with_valid_oem_values(client: TestClient, sample_jpeg):
    """Test upload with valid OEM values (0-3)."""
    valid_oem_values = [0, 1, 2, 3]

    for oem in valid_oem_values:
        with open(sample_jpeg, "rb") as f:
            response = client.post("/upload", files={"file": f}, data={"oem": oem})

        assert response.status_code == 202, f"OEM {oem} should be valid"
        data = response.json()
        assert "job_id" in data


def test_upload_with_invalid_oem_value(client: TestClient, sample_jpeg):
    """Test upload with invalid OEM value."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload", files={"file": f}, data={"oem": 99})

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


def test_upload_with_oem_lstm_accuracy(client: TestClient, sample_jpeg):
    """Test upload with OEM=1 (LSTM) for best accuracy."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload", files={"file": f}, data={"oem": 1})

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data


def test_upload_without_oem_uses_default(client: TestClient, sample_jpeg):
    """Test upload without OEM parameter uses default."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload", files={"file": f})

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data


# Phase 6: User Story 4 - DPI Configuration (T034-T037)


def test_upload_with_valid_dpi_values(client: TestClient, sample_jpeg):
    """Test upload with valid DPI values (70-2400)."""
    valid_dpi_values = [70, 150, 300, 600, 2400]

    for dpi in valid_dpi_values:
        with open(sample_jpeg, "rb") as f:
            response = client.post("/upload", files={"file": f}, data={"dpi": dpi})

        assert response.status_code == 202, f"DPI {dpi} should be valid"
        data = response.json()
        assert "job_id" in data


def test_upload_with_invalid_dpi_out_of_range(client: TestClient, sample_jpeg):
    """Test upload with DPI out of valid range."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload", files={"file": f}, data={"dpi": 50})

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


def test_upload_with_dpi_low_resolution_image(client: TestClient, sample_jpeg):
    """Test upload with DPI=150 for low-resolution images."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload", files={"file": f}, data={"dpi": 150})

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data


def test_upload_without_dpi_uses_default(client: TestClient, sample_jpeg):
    """Test upload without DPI parameter uses default or auto-detection."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload", files={"file": f})

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
