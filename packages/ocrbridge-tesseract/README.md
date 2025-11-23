# OCR Bridge - Tesseract Engine

Tesseract OCR engine implementation for OCR Bridge.

## Overview

This package provides a Tesseract OCR engine that integrates with the OCR Bridge architecture. Tesseract is a popular open-source OCR engine developed by Google.

## Features

- **Multiple Formats**: JPEG, PNG, TIFF, PDF
- **Multi-page PDFs**: Automatic page splitting and merging
- **Language Support**: 100+ languages via Tesseract language packs
- **Configurable**: PSM, OEM, and DPI settings
- **HOCR Output**: Structured XML with bounding boxes

## Installation

```bash
pip install ocrbridge-tesseract
```

Note: Tesseract binary must be installed separately:

```bash
# Ubuntu/Debian
apt-get install tesseract-ocr tesseract-ocr-eng

# macOS
brew install tesseract

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

## Usage

The engine is automatically discovered by OCR Bridge via entry points.

### Parameters

- `lang` (str): Language code(s), e.g., "eng", "eng+fra" (default: "eng")
- `psm` (int): Page segmentation mode 0-13 (default: 3)
- `oem` (int): OCR engine mode 0-3 (default: 1)
- `dpi` (int): DPI for PDF conversion, 70-2400 (default: 300)

### Example

```python
from pathlib import Path
from ocrbridge.engines.tesseract import TesseractEngine, TesseractParams

engine = TesseractEngine()

# Process with defaults
hocr = engine.process(Path("document.pdf"))

# Process with custom parameters
params = TesseractParams(
    lang="eng+fra",
    psm=6,
    oem=1,
    dpi=300
)
hocr = engine.process(Path("document.pdf"), params)
```

## Version

0.1.0
