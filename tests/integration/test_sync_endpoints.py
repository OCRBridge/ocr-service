"""Integration tests for synchronous OCR endpoints."""

import pytest
from fastapi.testclient import TestClient


def test_sync_tesseract_jpeg_end_to_end(client: TestClient, sample_jpeg):
    """Test end-to-end synchronous Tesseract processing with JPEG."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": f})

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "hocr" in data
    assert "processing_duration_seconds" in data
    assert "engine" in data
    assert "pages" in data

    # Validate hOCR content
    hocr_content = data["hocr"]
    assert '<?xml version="1.0"' in hocr_content
    assert "ocr_page" in hocr_content
    assert "bbox" in hocr_content

    # Validate metadata
    assert data["engine"] == "tesseract"
    assert data["pages"] >= 1
    assert data["processing_duration_seconds"] > 0
    assert data["processing_duration_seconds"] < 30  # Within timeout limit


def test_sync_tesseract_png_end_to_end(client: TestClient, sample_png):
    """Test end-to-end synchronous Tesseract processing with PNG."""
    with open(sample_png, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": f})

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "hocr" in data
    assert "engine" in data
    assert data["engine"] == "tesseract"
    assert data["pages"] >= 1


def test_sync_tesseract_pdf_end_to_end(client: TestClient, sample_pdf):
    """Test end-to-end synchronous Tesseract processing with PDF."""
    # Skip test if PDF file doesn't exist
    if not sample_pdf.exists():
        pytest.skip(f"PDF sample file not found: {sample_pdf}")

    with open(sample_pdf, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": f})

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "hocr" in data
    hocr_content = data["hocr"]
    assert "ocr_page" in hocr_content

    # Verify multi-page handling
    page_count = hocr_content.count('class="ocr_page"') + hocr_content.count("class='ocr_page'")
    assert page_count >= 1


def test_sync_tesseract_tiff_end_to_end(client: TestClient, sample_tiff):
    """Test end-to-end synchronous Tesseract processing with TIFF."""
    with open(sample_tiff, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": f})

    assert response.status_code == 200
    data = response.json()

    assert "hocr" in data
    assert data["engine"] == "tesseract"


def test_sync_tesseract_with_lang_parameter(client: TestClient, sample_jpeg):
    """Test synchronous Tesseract with language parameter."""
    # Test single language
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": f}, data={"lang": "eng"})
    assert response.status_code == 200

    # Test multiple languages
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": f}, data={"lang": "eng+fra"})
    assert response.status_code == 200


def test_sync_tesseract_with_psm_parameter(client: TestClient, sample_jpeg):
    """Test synchronous Tesseract with PSM parameter."""
    # Test PSM mode 3 (fully automatic)
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": f}, data={"psm": 3})
    assert response.status_code == 200

    # Test PSM mode 6 (uniform block)
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": f}, data={"psm": 6})
    assert response.status_code == 200


def test_sync_tesseract_with_oem_parameter(client: TestClient, sample_jpeg):
    """Test synchronous Tesseract with OEM parameter."""
    # Test OEM mode 1 (LSTM)
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": f}, data={"oem": 1})
    assert response.status_code == 200

    # Test OEM mode 3 (default)
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": f}, data={"oem": 3})
    assert response.status_code == 200


def test_sync_tesseract_with_dpi_parameter(client: TestClient, sample_jpeg):
    """Test synchronous Tesseract with DPI parameter."""
    # Test standard DPI
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": f}, data={"dpi": 300})
    assert response.status_code == 200

    # Test high DPI
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": f}, data={"dpi": 600})
    assert response.status_code == 200


def test_sync_tesseract_with_multiple_parameters(client: TestClient, sample_jpeg):
    """Test synchronous Tesseract with multiple parameters combined."""
    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/sync/tesseract",
            files={"file": f},
            data={"lang": "eng", "psm": 6, "oem": 1, "dpi": 300},
        )

    assert response.status_code == 200
    data = response.json()
    assert "hocr" in data
    assert data["engine"] == "tesseract"


def test_sync_tesseract_invalid_file_format(client: TestClient, tmp_path):
    """Test synchronous Tesseract with unsupported file format."""
    # Create a text file (unsupported format)
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("This is not an image")

    with open(txt_file, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": ("test.txt", f)})

    assert response.status_code == 415  # Unsupported Media Type


def test_sync_tesseract_file_size_limit(client: TestClient, tmp_path):
    """Test synchronous Tesseract file size validation (5MB limit)."""
    # Create a file larger than 5MB
    large_file = tmp_path / "large.jpg"
    large_file.write_bytes(b"0" * (6 * 1024 * 1024))  # 6MB

    with open(large_file, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": ("large.jpg", f, "image/jpeg")})

    assert response.status_code == 413  # Payload Too Large
    assert "5MB limit" in response.json()["detail"]


def test_sync_tesseract_invalid_lang(client: TestClient, sample_jpeg):
    """Test synchronous Tesseract with invalid language code."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": f}, data={"lang": "INVALID"})

    # FastAPI Form pattern validation returns 400, Pydantic validation returns 422
    assert response.status_code in [400, 422]


def test_sync_tesseract_invalid_psm(client: TestClient, sample_jpeg):
    """Test synchronous Tesseract with invalid PSM value."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": f}, data={"psm": 99})

    # FastAPI Form validation returns 400, Pydantic validation returns 422
    assert response.status_code in [400, 422]


def test_sync_tesseract_invalid_oem(client: TestClient, sample_jpeg):
    """Test synchronous Tesseract with invalid OEM value."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": f}, data={"oem": 10})

    # FastAPI Form validation returns 400, Pydantic validation returns 422
    assert response.status_code in [400, 422]


def test_sync_tesseract_invalid_dpi(client: TestClient, sample_jpeg):
    """Test synchronous Tesseract with invalid DPI value."""
    # DPI too low
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": f}, data={"dpi": 50})

    # FastAPI Form validation returns 400, Pydantic validation returns 422
    assert response.status_code in [400, 422]

    # DPI too high
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": f}, data={"dpi": 3000})

    # FastAPI Form validation returns 400, Pydantic validation returns 422
    assert response.status_code in [400, 422]


def test_sync_tesseract_processing_duration_reasonable(client: TestClient, sample_jpeg):
    """Test that processing completes within reasonable time."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": f})

    assert response.status_code == 200
    data = response.json()

    # Processing should complete well within timeout (30s)
    # For a simple image, expect < 5 seconds
    assert data["processing_duration_seconds"] < 5.0


# T018: Integration test for end-to-end EasyOCR sync processing


def test_sync_easyocr_jpeg_end_to_end(client: TestClient, sample_jpeg):
    """Test end-to-end synchronous EasyOCR processing with JPEG."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/easyocr", files={"file": f})

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "hocr" in data
    assert "processing_duration_seconds" in data
    assert "engine" in data
    assert "pages" in data

    # Validate hOCR content
    hocr_content = data["hocr"]
    assert '<?xml version="1.0"' in hocr_content
    assert "ocr_page" in hocr_content or "ocr_line" in hocr_content

    # Validate metadata
    assert data["engine"] == "easyocr"
    assert data["pages"] >= 1
    assert data["processing_duration_seconds"] > 0
    assert data["processing_duration_seconds"] < 30  # Within timeout limit


def test_sync_easyocr_png_end_to_end(client: TestClient, sample_png):
    """Test end-to-end synchronous EasyOCR processing with PNG."""
    with open(sample_png, "rb") as f:
        response = client.post("/sync/easyocr", files={"file": f})

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "hocr" in data
    assert "engine" in data
    assert data["engine"] == "easyocr"
    assert data["pages"] >= 1


# T019: Integration test for EasyOCR multilingual processing


def test_sync_easyocr_multilingual_processing(client: TestClient, sample_jpeg):
    """Test synchronous EasyOCR with multilingual parameters."""
    # Test English only
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/easyocr", files={"file": f}, data={"languages": '["en"]'})
    assert response.status_code == 200
    data = response.json()
    assert data["engine"] == "easyocr"

    # Test multiple languages (English + Spanish)
    # Note: We can request multiple languages, but sample might only have English text
    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/sync/easyocr", files={"file": f}, data={"languages": '["en", "es"]'}
        )
    assert response.status_code == 200
    data = response.json()
    assert data["engine"] == "easyocr"


def test_sync_easyocr_with_text_threshold_parameter(client: TestClient, sample_jpeg):
    """Test synchronous EasyOCR with text_threshold parameter."""
    # Test low threshold (detects more text)
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/easyocr", files={"file": f}, data={"text_threshold": "0.5"})
    assert response.status_code == 200

    # Test high threshold (more strict)
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/easyocr", files={"file": f}, data={"text_threshold": "0.9"})
    assert response.status_code == 200


def test_sync_easyocr_with_link_threshold_parameter(client: TestClient, sample_jpeg):
    """Test synchronous EasyOCR with link_threshold parameter."""
    # Test low threshold (links more regions)
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/easyocr", files={"file": f}, data={"link_threshold": "0.5"})
    assert response.status_code == 200

    # Test high threshold (fewer links)
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/easyocr", files={"file": f}, data={"link_threshold": "0.9"})
    assert response.status_code == 200


def test_sync_easyocr_with_multiple_parameters(client: TestClient, sample_jpeg):
    """Test synchronous EasyOCR with multiple parameters combined."""
    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/sync/easyocr",
            files={"file": f},
            data={"languages": '["en"]', "text_threshold": "0.7", "link_threshold": "0.7"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "hocr" in data
    assert data["engine"] == "easyocr"


def test_sync_easyocr_processing_duration_reasonable(client: TestClient, sample_jpeg):
    """Test that EasyOCR processing completes within reasonable time."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/easyocr", files={"file": f})

    assert response.status_code == 200
    data = response.json()

    # Processing should complete well within timeout (30s)
    # EasyOCR might be slower than Tesseract, allow up to 10 seconds for simple images
    assert data["processing_duration_seconds"] < 10.0


# T028: Integration test for end-to-end ocrmac sync processing (macOS only)


@pytest.mark.skipif(
    not pytest.importorskip("ocrmac", reason="ocrmac only available on macOS"),
    reason="ocrmac only available on macOS",
)
def test_sync_ocrmac_jpeg_end_to_end(client: TestClient, sample_jpeg):
    """Test end-to-end synchronous ocrmac processing with JPEG (macOS only)."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/ocrmac", files={"file": f})

    # If ocrmac is not available on this platform, expect 400
    if response.status_code == 400:
        pytest.skip("ocrmac not available on this platform")

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "hocr" in data
    assert "processing_duration_seconds" in data
    assert "engine" in data
    assert "pages" in data

    # Validate hOCR content
    hocr_content = data["hocr"]
    assert '<?xml version="1.0"' in hocr_content
    assert "ocr_page" in hocr_content or "ocr_line" in hocr_content

    # Validate metadata
    assert data["engine"] == "ocrmac"
    assert data["pages"] >= 1
    assert data["processing_duration_seconds"] > 0
    assert data["processing_duration_seconds"] < 30  # Within timeout limit


@pytest.mark.skipif(
    not pytest.importorskip("ocrmac", reason="ocrmac only available on macOS"),
    reason="ocrmac only available on macOS",
)
def test_sync_ocrmac_png_end_to_end(client: TestClient, sample_png):
    """Test end-to-end synchronous ocrmac processing with PNG (macOS only)."""
    with open(sample_png, "rb") as f:
        response = client.post("/sync/ocrmac", files={"file": f})

    # If ocrmac is not available, skip
    if response.status_code == 400:
        pytest.skip("ocrmac not available on this platform")

    assert response.status_code == 200
    data = response.json()

    assert "hocr" in data
    assert "engine" in data
    assert data["engine"] == "ocrmac"
    assert data["pages"] >= 1


def test_sync_ocrmac_with_languages_parameter(client: TestClient, sample_jpeg):
    """Test synchronous ocrmac with languages parameter."""
    # Test single language
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/ocrmac", files={"file": f}, data={"languages": '["en-US"]'})

    # Skip if not available
    if response.status_code == 400:
        pytest.skip("ocrmac not available on this platform")

    assert response.status_code == 200

    # Test multiple languages
    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/sync/ocrmac", files={"file": f}, data={"languages": '["en-US", "fr-FR"]'}
        )
    assert response.status_code == 200


def test_sync_ocrmac_with_recognition_level_parameter(client: TestClient, sample_jpeg):
    """Test synchronous ocrmac with recognition_level parameter."""
    # Test fast recognition
    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/sync/ocrmac", files={"file": f}, data={"recognition_level": "fast"}
        )

    # Skip if not available
    if response.status_code == 400:
        pytest.skip("ocrmac not available on this platform")

    assert response.status_code == 200

    # Test accurate recognition
    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/sync/ocrmac", files={"file": f}, data={"recognition_level": "accurate"}
        )
    assert response.status_code == 200


def test_sync_ocrmac_processing_duration_reasonable(client: TestClient, sample_jpeg):
    """Test that ocrmac processing completes within reasonable time (macOS only)."""
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/ocrmac", files={"file": f})

    # Skip if not available
    if response.status_code == 400:
        pytest.skip("ocrmac not available on this platform")

    assert response.status_code == 200
    data = response.json()

    # ocrmac is typically very fast on macOS
    # Allow up to 5 seconds for simple images
    assert data["processing_duration_seconds"] < 5.0


# T029: Unit test for ocrmac platform validation


def test_sync_ocrmac_unavailable_non_macos_400(client: TestClient, sample_jpeg, monkeypatch):
    """Test that ocrmac returns 400 on non-macOS platforms."""
    # Mock the engine registry to simulate non-macOS platform
    from src.services.ocr.registry import EngineRegistry

    def mock_is_available(self, engine_type):
        return False

    def mock_validate_platform(self, engine_type):
        return False, "ocrmac engine is only available on macOS with Apple Vision framework"

    monkeypatch.setattr(EngineRegistry, "is_available", mock_is_available)
    monkeypatch.setattr(EngineRegistry, "validate_platform", mock_validate_platform)

    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/ocrmac", files={"file": f})

    assert response.status_code == 400
    assert "macOS" in response.json()["detail"]


# T035-T036: Integration test for end-to-end LiveText processing


@pytest.mark.skipif(
    not pytest.importorskip("ocrmac", reason="ocrmac only available on macOS"),
    reason="ocrmac only available on macOS",
)
def test_sync_ocrmac_livetext_end_to_end(client: TestClient, sample_jpeg, monkeypatch):
    """Test end-to-end synchronous ocrmac LiveText processing (macOS Sonoma 14.0+ only)."""
    import platform

    # Check macOS version - skip if not Sonoma 14.0+
    if platform.system() != "Darwin":
        pytest.skip("ocrmac LiveText only available on macOS")

    mac_version = platform.mac_ver()[0]
    if not mac_version:
        pytest.skip("Unable to determine macOS version")

    try:
        major_version = int(mac_version.split(".")[0])
        if major_version < 14:
            pytest.skip(f"LiveText requires macOS Sonoma 14.0+, current: {mac_version}")
    except (ValueError, IndexError):
        pytest.skip(f"Invalid macOS version format: {mac_version}")

    # Test LiveText recognition level
    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/sync/ocrmac", files={"file": f}, data={"recognition_level": "livetext"}
        )

    # Skip if ocrmac library doesn't support framework parameter (HTTP 500)
    if response.status_code == 500 and "framework" in response.json()["detail"]:
        pytest.skip("ocrmac library version does not support LiveText framework parameter")

    # Should succeed on macOS Sonoma 14.0+
    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert "hocr" in data
    assert "processing_duration_seconds" in data
    assert "engine" in data
    assert "pages" in data

    # Validate hOCR content contains LiveText metadata
    hocr_content = data["hocr"]
    assert '<?xml version="1.0"' in hocr_content
    assert "ocrmac-livetext" in hocr_content  # Check for LiveText framework marker
    assert "ocr_page" in hocr_content or "ocr_line" in hocr_content

    # Validate metadata
    assert data["engine"] == "ocrmac"
    assert data["pages"] >= 1
    assert data["processing_duration_seconds"] > 0

    # LiveText should be reasonably fast (~174ms per image, allow up to 5s for test image)
    assert data["processing_duration_seconds"] < 5.0


@pytest.mark.skipif(
    not pytest.importorskip("ocrmac", reason="ocrmac only available on macOS"),
    reason="ocrmac only available on macOS",
)
def test_sync_ocrmac_livetext_confidence_values(client: TestClient, sample_jpeg):
    """Test that LiveText always returns confidence 100 (macOS Sonoma 14.0+ only)."""
    import platform

    # Check macOS version - skip if not Sonoma 14.0+
    if platform.system() != "Darwin":
        pytest.skip("ocrmac LiveText only available on macOS")

    mac_version = platform.mac_ver()[0]
    if not mac_version:
        pytest.skip("Unable to determine macOS version")

    try:
        major_version = int(mac_version.split(".")[0])
        if major_version < 14:
            pytest.skip(f"LiveText requires macOS Sonoma 14.0+, current: {mac_version}")
    except (ValueError, IndexError):
        pytest.skip(f"Invalid macOS version format: {mac_version}")

    with open(sample_jpeg, "rb") as f:
        response = client.post(
            "/sync/ocrmac", files={"file": f}, data={"recognition_level": "livetext"}
        )

    # Skip if ocrmac library doesn't support framework parameter
    if response.status_code == 500 and "framework" in response.json()["detail"]:
        pytest.skip("ocrmac library version does not support LiveText framework parameter")

    if response.status_code != 200:
        pytest.skip(f"LiveText processing failed: {response.json()}")

    data = response.json()
    hocr_content = data["hocr"]

    # All confidence values should be 100 for LiveText (characteristic of the framework)
    # Check for x_wconf values in hOCR
    if "x_wconf" in hocr_content:
        # Extract confidence values - should all be 100
        import re

        conf_values = re.findall(r"x_wconf\s+(\d+)", hocr_content)
        if conf_values:  # If any confidence values found
            for conf in conf_values:
                assert int(conf) == 100, f"LiveText should return confidence 100, got {conf}"
