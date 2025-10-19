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


def get_easyocr_device() -> Tuple[bool, str]:
    """
    Automatically detect and determine the best device for EasyOCR.

    Automatically uses GPU if CUDA is available, otherwise falls back to CPU.
    No user intervention required.

    Returns:
        Tuple of (use_gpu, device_name)
        - use_gpu: True if GPU will be used, False for CPU
        - device_name: PyTorch device string (e.g., "cuda:0" or "cpu")
    """
    if detect_gpu_availability():
        import torch

        device_name = f"cuda:{torch.cuda.current_device()}"
        logger.info(f"GPU detected and will be used: {device_name}")
        return True, device_name
    else:
        logger.info("No GPU detected, using CPU for EasyOCR processing")
        return False, "cpu"
