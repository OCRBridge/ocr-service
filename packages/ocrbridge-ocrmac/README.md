# OCR Bridge - ocrmac Engine

ocrmac (Apple Vision Framework) OCR engine for OCR Bridge.

## Overview

This package provides an ocrmac engine that integrates with the OCR Bridge architecture. ocrmac uses Apple's Vision framework for OCR, providing excellent performance and accuracy on macOS systems.

## Features

- **Native macOS**: Uses Apple's Vision framework (macOS 10.15+)
- **LiveText Support**: macOS Sonoma 14.0+ for enhanced accuracy
- **Multiple Formats**: JPEG, PNG, TIFF, PDF
- **Fast Performance**: ~131-207ms per image depending on mode
- **HOCR Output**: Structured XML with bounding boxes

## Platform Requirements

- macOS 10.15+ for Vision framework (fast/balanced/accurate modes)
- macOS Sonoma 14.0+ for LiveText framework

## Installation

```bash
pip install ocrbridge-ocrmac
```

**Note**: macOS only! This package will not work on Windows or Linux.

## Usage

The engine is automatically discovered by OCR Bridge via entry points.

### Parameters

- `languages` (list[str] | None): IETF BCP 47 codes (e.g., ["en-US"], ["zh-Hans"])  (default: None = auto-detect)
- `recognition_level` (RecognitionLevel): fast/balanced/accurate/livetext (default: balanced)

### Example

```python
from pathlib import Path
from ocrbridge.engines.ocrmac import OcrmacEngine, OcrmacParams, RecognitionLevel

engine = OcrmacEngine()

# Process with defaults
hocr = engine.process(Path("document.pdf"))

# Process with custom parameters
params = OcrmacParams(
    languages=["en-US", "fr-FR"],
    recognition_level=RecognitionLevel.ACCURATE
)
hocr = engine.process(Path("document.pdf"), params)

# Use LiveText (macOS Sonoma 14.0+ only)
params_livetext = OcrmacParams(
    languages=["en-US"],
    recognition_level=RecognitionLevel.LIVETEXT
)
hocr = engine.process(Path("document.pdf"), params_livetext)
```

## Version

0.1.0
