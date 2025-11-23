"""Unit tests for synchronous OCR route handlers."""

import asyncio
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient

from src.api.routes.sync import temporary_upload


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "engine,endpoint,needs_registry_mock",
    [
        ("tesseract", "/sync/tesseract", False),
        ("easyocr", "/sync/easyocr", False),
        pytest.param("ocrmac", "/sync/ocrmac", True, marks=pytest.mark.macos),
    ],
)
async def test_sync_engine_timeout_handling_and_metrics(
    client: TestClient, sample_jpeg, engine, endpoint, needs_registry_mock
):
    """Test that sync endpoints raise 408 on timeout and increment timeout metrics."""
    # Mock OCRProcessor to simulate timeout
    with patch("src.api.routes.sync.OCRProcessor") as mock_processor_class:
        mock_processor = MagicMock()

        # Simulate timeout by making process_document never complete
        async def slow_process(*args, **kwargs):
            await asyncio.sleep(100)  # Longer than timeout
            return "<html></html>"

        mock_processor.process_document = slow_process
        mock_processor_class.return_value = mock_processor

        # Setup context managers for registry mocking if needed
        registry_context = (
            patch("src.api.routes.sync.EngineRegistry") if needs_registry_mock else nullcontext()
        )

        with registry_context as mock_registry_class:
            # Configure registry mock if needed
            if needs_registry_mock:
                assert mock_registry_class is not None
                mock_registry = MagicMock()
                mock_registry.is_available.return_value = True
                mock_registry_class.return_value = mock_registry

            # Patch metrics
            with (
                patch("src.api.routes.sync.sync_ocr_timeouts_total") as mock_timeout_metric,
                patch("src.api.routes.sync.sync_ocr_requests_total"),
            ):
                # Make request
                with open(sample_jpeg, "rb") as f:
                    response = client.post(endpoint, files={"file": f})

                # Should return 408 Request Timeout
                assert response.status_code == 408
                assert "timeout" in response.json()["detail"].lower()
                assert "30s" in response.json()["detail"]  # Mentions timeout limit

                # Verify timeout metric was incremented
                mock_timeout_metric.labels.assert_called_with(engine=engine)
                mock_timeout_metric.labels.return_value.inc.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "engine,endpoint,needs_registry_mock,error_msg",
    [
        ("tesseract", "/sync/tesseract", False, "OCR processing failed"),
        ("easyocr", "/sync/easyocr", False, "EasyOCR processing failed"),
        pytest.param(
            "ocrmac", "/sync/ocrmac", True, "ocrmac processing failed", marks=pytest.mark.macos
        ),
    ],
)
async def test_sync_engine_processing_error_handling(
    client: TestClient, sample_jpeg, engine, endpoint, needs_registry_mock, error_msg
):
    """Test that processing errors return 500."""
    with patch("src.api.routes.sync.OCRProcessor") as mock_processor_class:
        mock_processor = MagicMock()

        # Simulate processing error
        async def failing_process(*args, **kwargs):
            raise RuntimeError(error_msg)

        mock_processor.process_document = failing_process
        mock_processor_class.return_value = mock_processor

        # Setup context managers for registry mocking if needed
        registry_context = (
            patch("src.api.routes.sync.EngineRegistry") if needs_registry_mock else nullcontext()
        )

        with registry_context as mock_registry_class:
            # Configure registry mock if needed
            if needs_registry_mock:
                assert mock_registry_class is not None
                mock_registry = MagicMock()
                mock_registry.is_available.return_value = True
                mock_registry_class.return_value = mock_registry

            # Make request
            with open(sample_jpeg, "rb") as f:
                response = client.post(endpoint, files={"file": f})

            # Should return 500 Internal Server Error
            assert response.status_code == 500
            assert error_msg in response.json()["detail"]


@pytest.mark.asyncio
async def test_sync_tesseract_validation_error_handling(client: TestClient, sample_jpeg):
    """Test that validation errors return 4xx status code."""
    # Invalid PSM parameter
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": f}, data={"psm": "999"})

    # FastAPI Form validation returns 400, Pydantic validation returns 422
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario,exception_type,exception_to_raise",
    [
        ("success", None, None),
        ("error", RuntimeError, RuntimeError("Test error")),
        ("timeout", asyncio.TimeoutError, TimeoutError()),
    ],
)
async def test_temporary_upload_cleanup(scenario, exception_type, exception_to_raise):
    """Test that temporary_upload cleans up file in all scenarios (success, error, timeout)."""
    # Create mock upload file
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "test.jpg"

    # Mock FileHandler
    with patch("src.api.routes.sync.FileHandler") as mock_handler_class:
        mock_handler = MagicMock()
        mock_handler_class.return_value = mock_handler

        # Mock temp file path
        mock_temp_path = MagicMock(spec=Path)
        mock_temp_path.exists.return_value = True

        mock_document_upload = MagicMock()
        mock_document_upload.temp_file_path = mock_temp_path
        mock_document_upload.file_format = "jpeg"

        mock_handler.save_upload = AsyncMock(return_value=mock_document_upload)

        # Use context manager with or without exception
        if exception_type:
            with pytest.raises(exception_type):
                async with temporary_upload(mock_file) as (file_path, file_format):
                    raise exception_to_raise
        else:
            async with temporary_upload(mock_file) as (file_path, file_format):
                assert file_path == mock_temp_path
                assert file_format == "jpeg"

        # Verify cleanup was called in all cases
        mock_temp_path.unlink.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "engine,endpoint",
    [
        ("tesseract", "/sync/tesseract"),
        ("easyocr", "/sync/easyocr"),
    ],
)
async def test_sync_engine_success_metrics(client: TestClient, sample_jpeg, engine, endpoint):
    """Test that successful processing increments success metrics."""
    with (
        patch("src.api.routes.sync.sync_ocr_requests_total") as mock_requests_metric,
        patch("src.api.routes.sync.sync_ocr_duration_seconds") as mock_duration_metric,
    ):
        # Make successful request
        with open(sample_jpeg, "rb") as f:
            response = client.post(endpoint, files={"file": f})

        assert response.status_code == 200

        # Verify success metric was incremented
        calls = list(mock_requests_metric.labels.call_args_list)
        success_call = [call for call in calls if "success" in str(call)]
        assert len(success_call) > 0

        # Verify duration was recorded
        mock_duration_metric.labels.assert_called_with(engine=engine)
        mock_duration_metric.labels.return_value.observe.assert_called()


# ============================================================================
# EasyOCR Timeout Handling Tests
# ============================================================================


# ============================================================================
# OCRmac Timeout Handling Tests
# ============================================================================


@pytest.mark.macos
@pytest.mark.asyncio
async def test_sync_ocrmac_success_metrics(client: TestClient, sample_jpeg):
    """Test that successful ocrmac processing increments success metrics."""
    # Only test if ocrmac is actually available
    from src.services.ocr.registry import EngineRegistry, EngineType

    registry = EngineRegistry()
    if not registry.is_available(EngineType.OCRMAC):
        pytest.skip("ocrmac not available on this platform")

    with (
        patch("src.api.routes.sync.sync_ocr_requests_total") as mock_requests_metric,
        patch("src.api.routes.sync.sync_ocr_duration_seconds") as mock_duration_metric,
    ):
        # Make successful request
        with open(sample_jpeg, "rb") as f:
            response = client.post("/sync/ocrmac", files={"file": f})

        assert response.status_code == 200

        # Verify success metric was incremented
        calls = list(mock_requests_metric.labels.call_args_list)
        success_call = [call for call in calls if "success" in str(call)]
        assert len(success_call) > 0

        # Verify duration was recorded for ocrmac
        mock_duration_metric.labels.assert_called_with(engine="ocrmac")
        mock_duration_metric.labels.return_value.observe.assert_called()
