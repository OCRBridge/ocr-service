"""GPU detection and management utilities for EasyOCR."""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def detect_gpu_availability() -> bool:
    """
    Detect if CUDA GPU is available for EasyOCR.

    Returns:
        bool: True if CUDA GPU is available, False otherwise
    """
    try:
        import torch

        return torch.cuda.is_available()
    except ImportError:
        logger.warning("PyTorch not installed, GPU support unavailable")
        return False
    except Exception as e:
        logger.warning(f"GPU detection failed: {e}")
        return False


def get_easyocr_device(gpu_requested: bool) -> Tuple[bool, str]:
    """
    Determine device for EasyOCR based on request and availability.

    Implements graceful fallback: if GPU requested but unavailable,
    falls back to CPU with warning logged.

    Args:
        gpu_requested: Whether GPU was requested by user

    Returns:
        Tuple of (use_gpu, device_name)
        - use_gpu: True if GPU will be used, False for CPU
        - device_name: PyTorch device string (e.g., "cuda:0" or "cpu")
    """
    if gpu_requested and detect_gpu_availability():
        import torch

        device_name = f"cuda:{torch.cuda.current_device()}"
        logger.info(f"Using GPU device: {device_name}")
        return True, device_name
    elif gpu_requested and not detect_gpu_availability():
        logger.warning("GPU requested but not available, falling back to CPU")
        return False, "cpu"
    else:
        return False, "cpu"
