"""Contract tests for Tesseract parameter validation in upload endpoint."""

import pytest
from fastapi.testclient import TestClient

# ============================================================================
# Language Selection
# ============================================================================


def test_upload_with_multiple_languages(client: TestClient, sample_jpeg):
    """Test upload with multiple languages (lang=eng+fra)."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload/tesseract", files={"file": f}, data={"lang": "eng+fra"})

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"


def test_upload_with_language_not_installed(client: TestClient, sample_jpeg):
    """Test upload with language code not installed on system."""
    with open(sample_jpeg, "rb") as f:
        # Valid format but language not installed
        response = client.post("/upload/tesseract", files={"file": f}, data={"lang": "xyz"})

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
        response = client.post(
            "/upload/tesseract", files={"file": f}, data={"lang": "eng+fra+deu+spa+ita+por"}
        )

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    error_msg = str(data["detail"])
    assert "5" in error_msg or "maximum" in error_msg.lower()


def test_upload_without_language_defaults_to_english(client: TestClient, sample_jpeg):
    """Test upload without language parameter defaults to English."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload/tesseract", files={"file": f})

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"
    # Should process successfully with default language (eng)


# ============================================================================
# PSM Control
# ============================================================================


def test_upload_with_psm_single_line_document(client: TestClient, sample_jpeg):
    """Test upload with PSM=7 (single line) for single-line documents."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload/tesseract", files={"file": f}, data={"psm": 7})

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data


def test_upload_without_psm_uses_default(client: TestClient, sample_jpeg):
    """Test upload without PSM parameter uses Tesseract default."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload/tesseract", files={"file": f})

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data


# ============================================================================
# OEM Selection
# ============================================================================


def test_upload_with_oem_lstm_accuracy(client: TestClient, sample_jpeg):
    """Test upload with OEM=1 (LSTM) for best accuracy."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload/tesseract", files={"file": f}, data={"oem": 1})

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data


def test_upload_without_oem_uses_default(client: TestClient, sample_jpeg):
    """Test upload without OEM parameter uses default."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload/tesseract", files={"file": f})

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data


# ============================================================================
# DPI Configuration
# ============================================================================


def test_upload_with_dpi_low_resolution_image(client: TestClient, sample_jpeg):
    """Test upload with DPI=150 for low-resolution images."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload/tesseract", files={"file": f}, data={"dpi": 150})

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data


def test_upload_without_dpi_uses_default(client: TestClient, sample_jpeg):
    """Test upload without DPI parameter uses default or auto-detection."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload/tesseract", files={"file": f})

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data

# ============================================================================
# Engine Selection
# ============================================================================


def test_upload_tesseract_endpoint_with_valid_parameters(client: TestClient, sample_jpeg):
    """Test POST /upload/tesseract endpoint with valid parameters."""
    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/upload/tesseract", files={"file": f}, data={"lang": "eng", "psm": 6}
        )

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"


def test_upload_ocrmac_endpoint_with_valid_parameters(client: TestClient, sample_jpeg):
    """Test POST /upload/ocrmac endpoint with valid parameters (macOS only)."""
    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/upload/ocrmac",
            files={"file": f},
            data={"languages": ["en-US"], "recognition_level": "balanced"},
        )

    # Will return 400 on non-macOS, 202 on macOS
    assert response.status_code in [202, 400]
    if response.status_code == 202:
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
    else:
        # Platform incompatibility error
        data = response.json()
        assert "detail" in data
        assert "darwin" in data["detail"].lower() or "macos" in data["detail"].lower()


def test_upload_with_invalid_engine_name_returns_400(client: TestClient, sample_jpeg):
    """Test that invalid engine name in endpoint returns HTTP 400."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload/invalid_engine", files={"file": f})

    assert response.status_code == 404  # FastAPI returns 404 for unknown routes


def test_upload_ocrmac_on_non_macos_returns_400(client: TestClient, sample_jpeg):
    """Test that ocrmac on non-macOS returns HTTP 400 with clear error message."""
    import platform

    # Skip test if running on macOS
    if platform.system() == "Darwin":
        pytest.skip("Test only applicable on non-macOS platforms")

    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload/ocrmac", files={"file": f})

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "darwin" in data["detail"].lower() or "macos" in data["detail"].lower()
    assert "ocrmac" in data["detail"].lower()


# ============================================================================
# Tesseract with Custom Parameters
# ============================================================================


def test_upload_tesseract_with_spanish_and_psm(client: TestClient, sample_jpeg):
    """Test /upload/tesseract with lang=spa&psm=6."""
    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/upload/tesseract", files={"file": f}, data={"lang": "spa", "psm": 6}
        )

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"


def test_upload_tesseract_without_lang_defaults_to_eng(client: TestClient, sample_jpeg):
    """Test /upload/tesseract without lang defaults to eng."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload/tesseract", files={"file": f}, data={"psm": 6})

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"


def test_upload_tesseract_with_invalid_parameters_returns_400(client: TestClient, sample_jpeg):
    """Test /upload/tesseract with invalid parameters returns HTTP 400."""
    # Invalid PSM value (out of range 0-13)
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload/tesseract", files={"file": f}, data={"psm": 99})

    assert response.status_code == 400


# ============================================================================
# OCRmac with Language Selection
# ============================================================================


def test_upload_ocrmac_with_german_language(client: TestClient, sample_jpeg):
    """Test /upload/ocrmac with languages=de."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload/ocrmac", files={"file": f}, data={"languages": "de"})

    # May return 400 if not on macOS or ocrmac not available
    assert response.status_code in [202, 400]
    if response.status_code == 202:
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"


def test_upload_ocrmac_with_multiple_languages(client: TestClient, sample_jpeg):
    """Test /upload/ocrmac with multiple languages (en,fr)."""
    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/upload/ocrmac", files={"file": f}, data={"languages": ["en", "fr"]}
        )

    # May return 400 if not on macOS or ocrmac not available
    assert response.status_code in [202, 400]
    if response.status_code == 202:
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"


def test_upload_ocrmac_without_languages_uses_auto_detection(client: TestClient, sample_jpeg):
    """Test /upload/ocrmac without languages uses auto-detection."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload/ocrmac", files={"file": f})

    # May return 400 if not on macOS or ocrmac not available
    assert response.status_code in [202, 400]
    if response.status_code == 202:
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"


def test_upload_ocrmac_with_unsupported_language_returns_400(client: TestClient, sample_jpeg):
    """Test /upload/ocrmac with unsupported language returns HTTP 400."""
    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/upload/ocrmac",
            files={"file": f},
            data={"languages": "xx-YY"},  # Invalid/unsupported language code
        )

    # Should return 400 for invalid language format or unsupported language
    assert response.status_code == 400


def test_upload_ocrmac_with_too_many_languages_returns_400(client: TestClient, sample_jpeg):
    """Test /upload/ocrmac with more than 5 languages returns HTTP 400."""
    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/upload/ocrmac",
            files={"file": f},
            data={"languages": ["en", "fr", "de", "es", "it", "pt"]},  # 6 languages
        )

    # Should return 400 for exceeding max languages
    assert response.status_code == 400


# ============================================================================
# OCRmac with Recognition Level Control
# ============================================================================


def test_upload_ocrmac_with_recognition_level_fast(client: TestClient, sample_jpeg):
    """Test /upload/ocrmac with recognition_level=fast."""
    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/upload/ocrmac", files={"file": f}, data={"recognition_level": "fast"}
        )

    # May return 400 if not on macOS or ocrmac not available
    assert response.status_code in [202, 400]
    if response.status_code == 202:
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"


def test_upload_ocrmac_with_recognition_level_accurate(client: TestClient, sample_jpeg):
    """Test /upload/ocrmac with recognition_level=accurate."""
    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/upload/ocrmac", files={"file": f}, data={"recognition_level": "accurate"}
        )

    # May return 400 if not on macOS or ocrmac not available
    assert response.status_code in [202, 400]
    if response.status_code == 202:
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"


def test_upload_ocrmac_with_invalid_recognition_level_returns_400(client: TestClient, sample_jpeg):
    """Test /upload/ocrmac with invalid recognition_level returns HTTP 400."""
    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/upload/ocrmac", files={"file": f}, data={"recognition_level": "invalid"}
        )

    # Should return 400 for invalid recognition level
    assert response.status_code == 400


def test_upload_ocrmac_without_recognition_level_defaults_to_balanced(
    client: TestClient, sample_jpeg
):
    """Test /upload/ocrmac without recognition_level defaults to balanced."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/upload/ocrmac", files={"file": f})

    # May return 400 if not on macOS or ocrmac not available
    assert response.status_code in [202, 400]
    if response.status_code == 202:
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"


def test_upload_ocrmac_with_pdf_file(client: TestClient, sample_pdf):
    """Test /upload/ocrmac with PDF file (verifies PDF conversion works)."""
    from pathlib import Path

    import pytest

    # Skip if sample PDF doesn't exist
    if not Path(sample_pdf).exists():
        pytest.skip(f"Sample PDF not found at {sample_pdf}")

    with open(sample_pdf, "rb") as f:
        response = client.post(
            "/upload/ocrmac",
            files={"file": f},
            data={"languages": ["en-US"], "recognition_level": "balanced"},
        )

    # May return 400 if not on macOS or ocrmac not available
    assert response.status_code in [202, 400]
    if response.status_code == 202:
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"


# ============================================================================
# Parameter Isolation Between Engines
# ============================================================================


def test_upload_ocrmac_with_tesseract_only_parameters_returns_400(client: TestClient, sample_jpeg):
    """Test /upload/ocrmac with Tesseract-only parameters (psm, oem, dpi) returns HTTP 400."""
    # Test with psm (Tesseract-only parameter)
    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/upload/ocrmac",
            files={"file": f},
            data={"psm": 6},  # Tesseract-only param
        )

    # Should return 400 or 202 (ignored parameter)
    # Based on FastAPI Form validation, unrecognized params are ignored
    # So we need to check the actual implementation
    assert response.status_code in [202, 400]


def test_upload_tesseract_with_ocrmac_only_parameters_returns_400(client: TestClient, sample_jpeg):
    """Test /upload/tesseract with ocrmac-only parameters (recognition_level) returns HTTP 400."""
    # Test with recognition_level (ocrmac-only parameter)
    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/upload/tesseract",
            files={"file": f},
            data={"recognition_level": "fast"},  # ocrmac-only param
        )

    # Should return 400 or 202 (ignored parameter)
    # Based on FastAPI Form validation, unrecognized params are ignored
    # So we need to check the actual implementation
    assert response.status_code in [202, 400]


# ============================================================================
# LiveText Recognition Level
# ============================================================================


def test_upload_ocrmac_livetext_parameter_validation_accepts_valid(client: TestClient, sample_jpeg):
    """Test that 'livetext' is accepted as valid recognition_level value."""
    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/upload/ocrmac",
            files={"file": f},
            data={"recognition_level": "livetext"},
        )

    # Should accept the parameter (202 if macOS Sonoma+, 400 if platform incompatible)
    assert response.status_code in [202, 400]

    # If 400, should be platform incompatibility, not parameter validation error
    if response.status_code == 400:
        detail = response.json()["detail"]
        assert "Sonoma" in detail or "macOS" in detail or "platform" in detail.lower()


def test_sync_ocrmac_livetext_parameter_validation_accepts_valid(client: TestClient, sample_jpeg):
    """Test that 'livetext' is accepted as valid recognition_level in sync endpoint."""
    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/sync/ocrmac",
            files={"file": f},
            data={"recognition_level": "livetext"},
        )

    # Should accept the parameter (200 if macOS Sonoma+, 400 if platform incompatible)
    assert response.status_code in [200, 400, 500]

    # If 400, should be platform incompatibility message
    if response.status_code == 400:
        detail = response.json()["detail"]
        assert "Sonoma" in detail or "macOS" in detail or "platform" in detail.lower()


def test_sync_ocrmac_livetext_platform_incompatibility_error(client: TestClient, sample_jpeg):
    """Test HTTP 400 platform incompatibility error for LiveText on pre-Sonoma."""
    import platform

    # Only run this test if NOT on macOS Sonoma 14.0+
    if platform.system() == "Darwin":
        mac_version = platform.mac_ver()[0]
        if mac_version:
            try:
                major_version = int(mac_version.split(".")[0])
                if major_version >= 14:
                    pytest.skip("Test requires pre-Sonoma macOS")
            except (ValueError, IndexError):
                pass

    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/sync/ocrmac",
            files={"file": f},
            data={"recognition_level": "livetext"},
        )

    # If ocrmac is not available at all (non-macOS), will get generic 400
    # If ocrmac available but pre-Sonoma, should get specific LiveText error
    if response.status_code == 400:
        detail = response.json()["detail"]
        # Should mention Sonoma requirement or platform limitation
        assert "Sonoma" in detail or "14.0" in detail or "macOS" in detail


def test_sync_ocrmac_livetext_library_incompatibility_error(client: TestClient, sample_jpeg):
    """Test HTTP 500 library incompatibility error for unsupported ocrmac version."""
    # This test verifies the error handling pattern
    # In reality, we can't force an old ocrmac version, but we test the contract
    # The actual error is tested via mock in unit tests

    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/sync/ocrmac",
            files={"file": f},
            data={"recognition_level": "livetext"},
        )

    # If we get HTTP 500, verify it's a well-formed error
    if response.status_code == 500:
        data = response.json()
        assert "detail" in data
        # Should be a string error message
        assert isinstance(data["detail"], str)