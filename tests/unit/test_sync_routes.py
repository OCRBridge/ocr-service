"""Unit tests for synchronous OCR route handlers."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient

from src.api.routes.sync import temporary_upload


@pytest.mark.asyncio
async def test_sync_tesseract_timeout_handling(client: TestClient, sample_jpeg):
    """Test that sync_tesseract raises 408 on timeout."""
    # Mock OCRProcessor to simulate timeout
    with patch("src.api.routes.sync.OCRProcessor") as mock_processor_class:
        mock_processor = MagicMock()

        # Simulate timeout by making process_document never complete
        async def slow_process(*args, **kwargs):
            await asyncio.sleep(100)  # Longer than timeout
            return "<html></html>"

        mock_processor.process_document = slow_process
        mock_processor_class.return_value = mock_processor

        # Make request
        with open(sample_jpeg, "rb") as f:
            response = client.post("/sync/tesseract", files={"file": f})

        # Should return 408 Request Timeout
        assert response.status_code == 408
        assert "timeout" in response.json()["detail"].lower()
        assert "30s" in response.json()["detail"]  # Mentions timeout limit


@pytest.mark.asyncio
async def test_sync_tesseract_timeout_metrics(client: TestClient, sample_jpeg):
    """Test that timeout increments timeout metrics."""
    with patch("src.api.routes.sync.OCRProcessor") as mock_processor_class:
        mock_processor = MagicMock()

        # Simulate timeout
        async def slow_process(*args, **kwargs):
            await asyncio.sleep(100)
            return "<html></html>"

        mock_processor.process_document = slow_process
        mock_processor_class.return_value = mock_processor

        # Patch metrics
        with (
            patch("src.api.routes.sync.sync_ocr_timeouts_total") as mock_timeout_metric,
            patch("src.api.routes.sync.sync_ocr_requests_total"),
            open(sample_jpeg, "rb") as f,
        ):
            # Make request
            response = client.post("/sync/tesseract", files={"file": f})

            # Verify timeout metric was incremented
            assert response.status_code == 408
            mock_timeout_metric.labels.assert_called_with(engine="tesseract")
            mock_timeout_metric.labels.return_value.inc.assert_called_once()


@pytest.mark.asyncio
async def test_sync_tesseract_processing_error_handling(client: TestClient, sample_jpeg):
    """Test that processing errors return 500."""
    with patch("src.api.routes.sync.OCRProcessor") as mock_processor_class:
        mock_processor = MagicMock()

        # Simulate processing error
        async def failing_process(*args, **kwargs):
            raise RuntimeError("OCR processing failed")

        mock_processor.process_document = failing_process
        mock_processor_class.return_value = mock_processor

        # Make request
        with open(sample_jpeg, "rb") as f:
            response = client.post("/sync/tesseract", files={"file": f})

        # Should return 500 Internal Server Error
        assert response.status_code == 500
        assert "OCR processing failed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_sync_tesseract_validation_error_handling(client: TestClient, sample_jpeg):
    """Test that validation errors return 4xx status code."""
    # Invalid PSM parameter
    with open(sample_jpeg, "rb") as f:
        response = client.post("/sync/tesseract", files={"file": f}, data={"psm": 999})

    # FastAPI Form validation returns 400, Pydantic validation returns 422
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_temporary_upload_cleanup_on_success():
    """Test that temporary_upload cleans up file on success."""
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

        # Use context manager
        async with temporary_upload(mock_file) as (file_path, file_format):
            assert file_path == mock_temp_path
            assert file_format == "jpeg"

        # Verify cleanup was called
        mock_temp_path.unlink.assert_called_once()


@pytest.mark.asyncio
async def test_temporary_upload_cleanup_on_error():
    """Test that temporary_upload cleans up file even on error."""
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

        # Use context manager with error
        with pytest.raises(RuntimeError):
            async with temporary_upload(mock_file) as (file_path, file_format):
                raise RuntimeError("Test error")

        # Verify cleanup was still called
        mock_temp_path.unlink.assert_called_once()


@pytest.mark.asyncio
async def test_temporary_upload_cleanup_on_timeout():
    """Test that temporary_upload cleans up file even on timeout."""
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

        # Use context manager with timeout
        with pytest.raises(asyncio.TimeoutError):
            async with temporary_upload(mock_file) as (file_path, file_format):
                raise TimeoutError()

        # Verify cleanup was still called
        mock_temp_path.unlink.assert_called_once()


@pytest.mark.asyncio
async def test_sync_tesseract_success_metrics(client: TestClient, sample_jpeg):
    """Test that successful processing increments success metrics."""
    with (
        patch("src.api.routes.sync.sync_ocr_requests_total") as mock_requests_metric,
        patch("src.api.routes.sync.sync_ocr_duration_seconds") as mock_duration_metric,
    ):
        # Make successful request
        with open(sample_jpeg, "rb") as f:
            response = client.post("/sync/tesseract", files={"file": f})

        assert response.status_code == 200

        # Verify success metric was incremented
        calls = list(mock_requests_metric.labels.call_args_list)
        success_call = [call for call in calls if "success" in str(call)]
        assert len(success_call) > 0

        # Verify duration was recorded
        mock_duration_metric.labels.assert_called_with(engine="tesseract")
        mock_duration_metric.labels.return_value.observe.assert_called()


# T020: Unit test for EasyOCR timeout handling


@pytest.mark.asyncio
async def test_sync_easyocr_timeout_handling(client: TestClient, sample_jpeg):
    """Test that sync_easyocr raises 408 on timeout."""
    # Mock OCRProcessor to simulate timeout
    with patch("src.api.routes.sync.OCRProcessor") as mock_processor_class:
        mock_processor = MagicMock()

        # Simulate timeout by making process_document never complete
        async def slow_process(*args, **kwargs):
            await asyncio.sleep(100)  # Longer than timeout
            return "<html></html>"

        mock_processor.process_document = slow_process
        mock_processor_class.return_value = mock_processor

        # Make request
        with open(sample_jpeg, "rb") as f:
            response = client.post("/sync/easyocr", files={"file": f})

        # Should return 408 Request Timeout
        assert response.status_code == 408
        assert "timeout" in response.json()["detail"].lower()
        assert "30s" in response.json()["detail"]  # Mentions timeout limit


@pytest.mark.asyncio
async def test_sync_easyocr_timeout_metrics(client: TestClient, sample_jpeg):
    """Test that timeout increments timeout metrics for EasyOCR."""
    with patch("src.api.routes.sync.OCRProcessor") as mock_processor_class:
        mock_processor = MagicMock()

        # Simulate timeout
        async def slow_process(*args, **kwargs):
            await asyncio.sleep(100)
            return "<html></html>"

        mock_processor.process_document = slow_process
        mock_processor_class.return_value = mock_processor

        # Patch metrics
        with (
            patch("src.api.routes.sync.sync_ocr_timeouts_total") as mock_timeout_metric,
            patch("src.api.routes.sync.sync_ocr_requests_total"),
        ):
            # Make request
            with open(sample_jpeg, "rb") as f:
                response = client.post("/sync/easyocr", files={"file": f})

            # Verify timeout metric was incremented for easyocr
            assert response.status_code == 408
            mock_timeout_metric.labels.assert_called_with(engine="easyocr")
            mock_timeout_metric.labels.return_value.inc.assert_called_once()


@pytest.mark.asyncio
async def test_sync_easyocr_processing_error_handling(client: TestClient, sample_jpeg):
    """Test that EasyOCR processing errors return 500."""
    with patch("src.api.routes.sync.OCRProcessor") as mock_processor_class:
        mock_processor = MagicMock()

        # Simulate processing error
        async def failing_process(*args, **kwargs):
            raise RuntimeError("EasyOCR processing failed")

        mock_processor.process_document = failing_process
        mock_processor_class.return_value = mock_processor

        # Make request
        with open(sample_jpeg, "rb") as f:
            response = client.post("/sync/easyocr", files={"file": f})

        # Should return 500 Internal Server Error
        assert response.status_code == 500
        assert "EasyOCR processing failed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_sync_easyocr_success_metrics(client: TestClient, sample_jpeg):
    """Test that successful EasyOCR processing increments success metrics."""
    with (
        patch("src.api.routes.sync.sync_ocr_requests_total") as mock_requests_metric,
        patch("src.api.routes.sync.sync_ocr_duration_seconds") as mock_duration_metric,
    ):
        # Make successful request
        with open(sample_jpeg, "rb") as f:
            response = client.post("/sync/easyocr", files={"file": f})

        assert response.status_code == 200

        # Verify success metric was incremented
        calls = list(mock_requests_metric.labels.call_args_list)
        success_call = [call for call in calls if "success" in str(call)]
        assert len(success_call) > 0

        # Verify duration was recorded for easyocr
        mock_duration_metric.labels.assert_called_with(engine="easyocr")
        mock_duration_metric.labels.return_value.observe.assert_called()


# T030: Unit test for ocrmac timeout handling


@pytest.mark.asyncio
async def test_sync_ocrmac_timeout_handling(client: TestClient, sample_jpeg):
    """Test that sync_ocrmac raises 408 on timeout."""
    # Mock OCRProcessor to simulate timeout
    with patch("src.api.routes.sync.OCRProcessor") as mock_processor_class:
        mock_processor = MagicMock()

        # Simulate timeout by making process_document never complete
        async def slow_process(*args, **kwargs):
            await asyncio.sleep(100)  # Longer than timeout
            return "<html></html>"

        mock_processor.process_document = slow_process
        mock_processor_class.return_value = mock_processor

        # Mock engine registry to show ocrmac is available
        with patch("src.api.routes.sync.EngineRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.is_available.return_value = True
            mock_registry_class.return_value = mock_registry

            # Make request
            with open(sample_jpeg, "rb") as f:
                response = client.post("/sync/ocrmac", files={"file": f})

            # Should return 408 Request Timeout
            assert response.status_code == 408
            assert "timeout" in response.json()["detail"].lower()
            assert "30s" in response.json()["detail"]


@pytest.mark.asyncio
async def test_sync_ocrmac_timeout_metrics(client: TestClient, sample_jpeg):
    """Test that timeout increments timeout metrics for ocrmac."""
    with patch("src.api.routes.sync.OCRProcessor") as mock_processor_class:
        mock_processor = MagicMock()

        # Simulate timeout
        async def slow_process(*args, **kwargs):
            await asyncio.sleep(100)
            return "<html></html>"

        mock_processor.process_document = slow_process
        mock_processor_class.return_value = mock_processor

        # Mock engine registry
        with patch("src.api.routes.sync.EngineRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.is_available.return_value = True
            mock_registry_class.return_value = mock_registry

            # Patch metrics
            with (
                patch("src.api.routes.sync.sync_ocr_timeouts_total") as mock_timeout_metric,
                patch("src.api.routes.sync.sync_ocr_requests_total"),
                open(sample_jpeg, "rb") as f,
            ):
                # Make request
                response = client.post("/sync/ocrmac", files={"file": f})

                # Verify timeout metric was incremented for ocrmac
                assert response.status_code == 408
                mock_timeout_metric.labels.assert_called_with(engine="ocrmac")
                mock_timeout_metric.labels.return_value.inc.assert_called_once()


@pytest.mark.asyncio
async def test_sync_ocrmac_processing_error_handling(client: TestClient, sample_jpeg):
    """Test that ocrmac processing errors return 500."""
    with patch("src.api.routes.sync.OCRProcessor") as mock_processor_class:
        mock_processor = MagicMock()

        # Simulate processing error
        async def failing_process(*args, **kwargs):
            raise RuntimeError("ocrmac processing failed")

        mock_processor.process_document = failing_process
        mock_processor_class.return_value = mock_processor

        # Mock engine registry
        with patch("src.api.routes.sync.EngineRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.is_available.return_value = True
            mock_registry_class.return_value = mock_registry

            # Make request
            with open(sample_jpeg, "rb") as f:
                response = client.post("/sync/ocrmac", files={"file": f})

            # Should return 500 Internal Server Error
            assert response.status_code == 500
            assert "ocrmac processing failed" in response.json()["detail"]


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
