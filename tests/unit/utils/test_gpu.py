"""Unit tests for GPU detection utilities.

Tests for CUDA availability detection and EasyOCR device selection.
"""

from unittest.mock import patch

from src.utils.gpu import detect_gpu_availability, get_easyocr_device


def test_detect_gpu_availability_cuda_available():
    """Test GPU detection when CUDA is available."""
    with patch("torch.cuda.is_available", return_value=True):
        result = detect_gpu_availability()
        assert result is True


def test_detect_gpu_availability_cuda_not_available():
    """Test GPU detection when CUDA is not available."""
    with patch("torch.cuda.is_available", return_value=False):
        result = detect_gpu_availability()
        assert result is False


def test_detect_gpu_availability_torch_not_installed():
    """Test graceful handling when PyTorch is not installed."""
    # Mock ImportError when trying to import torch
    with (
        patch.dict("sys.modules", {"torch": None}),
        patch("builtins.__import__", side_effect=ImportError("No module named 'torch'")),
    ):
        result = detect_gpu_availability()
        # Should return False when torch is not available
        assert result is False


def test_detect_gpu_availability_import_error():
    """Test handling of import errors when checking CUDA."""
    with patch("torch.cuda.is_available", side_effect=ImportError("CUDA not available")):
        result = detect_gpu_availability()
        assert result is False


def test_get_easyocr_device_gpu_available():
    """Test device selection when GPU is available."""
    with patch("src.utils.gpu.detect_gpu_availability", return_value=True):
        use_gpu, device_name = get_easyocr_device()

        assert use_gpu is True
        assert "cuda" in device_name.lower()


def test_get_easyocr_device_gpu_not_available():
    """Test device selection when GPU is not available (CPU fallback)."""
    with patch("src.utils.gpu.detect_gpu_availability", return_value=False):
        use_gpu, device_name = get_easyocr_device()

        assert use_gpu is False
        assert device_name == "cpu"


def test_get_easyocr_device_returns_tuple():
    """Test that get_easyocr_device returns a tuple of (bool, str)."""
    with patch("src.utils.gpu.detect_gpu_availability", return_value=True):
        result = get_easyocr_device()

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)


def test_get_easyocr_device_consistent_results():
    """Test that device selection is consistent with GPU availability."""
    # When GPU available
    with patch("src.utils.gpu.detect_gpu_availability", return_value=True):
        use_gpu1, _ = get_easyocr_device()
        assert use_gpu1 is True

    # When GPU not available
    with patch("src.utils.gpu.detect_gpu_availability", return_value=False):
        use_gpu2, device2 = get_easyocr_device()
        assert use_gpu2 is False
        assert device2 == "cpu"


def test_detect_gpu_availability_torch_cuda_exception():
    """Test handling when torch.cuda raises unexpected exception."""
    with patch("torch.cuda.is_available", side_effect=RuntimeError("CUDA error")):
        result = detect_gpu_availability()
        # Should gracefully handle and return False
        assert result is False


def test_gpu_module_imports():
    """Test that GPU module has expected exports."""
    from src.utils import gpu

    assert hasattr(gpu, "detect_gpu_availability")
    assert hasattr(gpu, "get_easyocr_device")
    assert callable(gpu.detect_gpu_availability)
    assert callable(gpu.get_easyocr_device)


def test_get_easyocr_device_device_string_format():
    """Test that device string has expected format."""
    # GPU available
    with patch("src.utils.gpu.detect_gpu_availability", return_value=True):
        _, device_name = get_easyocr_device()
        # Should be something like "cuda:0" or "cuda"
        assert device_name.startswith("cuda")

    # CPU fallback
    with patch("src.utils.gpu.detect_gpu_availability", return_value=False):
        _, device_name = get_easyocr_device()
        assert device_name == "cpu"
