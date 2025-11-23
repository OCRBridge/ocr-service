# OCR Bridge - EasyOCR Engine

EasyOCR engine implementation for OCR Bridge.

## Overview

This package provides an EasyOCR engine that integrates with the OCR Bridge architecture. EasyOCR is a deep learning-based OCR engine with excellent support for Asian scripts and automatic GPU acceleration.

## Features

- **80+ Languages**: Excellent support for Asian scripts (Chinese, Japanese, Korean, Thai, etc.)
- **GPU Acceleration**: Automatic GPU detection and usage with graceful CPU fallback
- **Multiple Formats**: JPEG, PNG, TIFF, PDF
- **Deep Learning**: Advanced neural network models for high accuracy
- **HOCR Output**: Structured XML with bounding boxes

## Installation

```bash
pip install ocrbridge-easyocr
```

Note: This will install PyTorch and EasyOCR dependencies (~2GB).

For GPU support, install CUDA-compatible PyTorch first:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip install ocrbridge-easyocr
```

## Usage

The engine is automatically discovered by OCR Bridge via entry points.

### Parameters

- `languages` (list[str]): Language codes, e.g., ["en"], ["ch_sim", "en"] (default: ["en"])
- `text_threshold` (float): Confidence threshold for text detection 0.0-1.0 (default: 0.7)
- `link_threshold` (float): Threshold for linking text regions 0.0-1.0 (default: 0.7)

### Example

```python
from pathlib import Path
from ocrbridge.engines.easyocr import EasyOCREngine, EasyOCRParams

engine = EasyOCREngine()

# Process with defaults (English)
hocr = engine.process(Path("document.pdf"))

# Process with custom parameters
params = EasyOCRParams(
    languages=["ch_sim", "en"],
    text_threshold=0.7,
    link_threshold=0.7
)
hocr = engine.process(Path("chinese_document.pdf"), params)
```

## GPU Support

The engine automatically detects and uses GPU if available. No configuration needed!

## Version

0.1.0
