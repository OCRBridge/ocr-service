# OCR Bridge Core

Core interfaces and utilities for OCR Bridge engine packages.

## Overview

`ocrbridge-core` provides the foundational abstract base classes, models, and utilities that all OCR engine packages must implement. This package enables a modular, plugin-based architecture where OCR engines can be dynamically discovered and loaded at runtime.

## Installation

```bash
pip install ocrbridge-core
```

For local development:

```bash
cd packages/ocrbridge-core
pip install -e .
```

## Core Components

### OCREngine Base Class

All OCR engines must inherit from `OCREngine` and implement:

- `process(file_path, params)` - Process a document and return HOCR XML
- `name` property - Engine identifier (e.g., 'tesseract', 'easyocr')
- `supported_formats` property - Set of supported file extensions

### OCREngineParams

Base model for engine-specific parameters using Pydantic validation.

### Exceptions

- `OCRBridgeError` - Base exception
- `OCRProcessingError` - Processing failures
- `UnsupportedFormatError` - Unsupported file format
- `EngineNotAvailableError` - Engine not installed/available
- `InvalidParametersError` - Invalid parameters

### HOCR Utilities

Helper functions for HOCR XML parsing, validation, and conversion:

- `parse_hocr()` - Parse and extract HOCR information
- `validate_hocr()` - Validate HOCR structure
- `extract_bbox()` - Extract bounding box coordinates
- `easyocr_to_hocr()` - Convert EasyOCR results to HOCR format

## Implementing a New Engine

See the engine packages for examples:
- `ocrbridge-tesseract` - Simple reference implementation
- `ocrbridge-easyocr` - Deep learning with GPU support
- `ocrbridge-ocrmac` - Platform-specific (macOS only)

## Version

0.1.0
