"""ocrmac OCR engine for OCR Bridge - macOS only."""

from .engine import OcrmacEngine
from .models import OcrmacParams, RecognitionLevel

__all__ = ["OcrmacEngine", "OcrmacParams", "RecognitionLevel"]

__version__ = "0.1.0"
