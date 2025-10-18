# Quickstart: Multi-Engine OCR Support

**Feature**: 003-multi-engine-ocr
**Date**: 2025-10-18

## Overview

This guide provides a quick introduction to using the multi-engine OCR feature, which allows you to choose between Tesseract and ocrmac OCR engines with engine-specific parameters.

## What's New

### Dedicated Engine Endpoints

Instead of a single `/upload` endpoint with an `engine` parameter, this feature provides dedicated endpoints for each engine:

- **`POST /upload/tesseract`** - Upload documents for Tesseract OCR processing
- **`POST /upload/ocrmac`** - Upload documents for ocrmac OCR processing (macOS only)
- **`POST /upload`** - Existing endpoint (backward compatible, defaults to Tesseract)

### Engine-Specific Parameters

Each engine supports its own parameters:

**Tesseract** (ISO 639-3 language codes):
- `lang` - Language code(s): eng, fra, deu, etc. (max 5, e.g., `eng+fra`)
- `psm` - Page Segmentation Mode (0-13)
- `oem` - OCR Engine Mode (0-3)
- `dpi` - Image DPI (70-2400)

**ocrmac** (IETF BCP 47 language codes):
- `languages` - Language codes: en-US, fr-FR, zh-Hans, etc. (max 5, array format)
- `recognition_level` - fast, balanced, accurate (default: balanced)

## Quick Examples

### Example 1: Upload with Tesseract (English document)

```bash
curl -X POST http://localhost:8000/upload/tesseract \
  -F "file=@invoice.pdf" \
  -F "lang=eng" \
  -F "psm=6" \
  -F "oem=1" \
  -F "dpi=300"
```

**Response**:
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending"
}
```

### Example 2: Upload with Tesseract (Multiple languages)

```bash
curl -X POST http://localhost:8000/upload/tesseract \
  -F "file=@multilingual_doc.pdf" \
  -F "lang=eng+fra+deu"
```

### Example 3: Upload with ocrmac (macOS only, English document)

```bash
curl -X POST http://localhost:8000/upload/ocrmac \
  -F "file=@receipt.jpg" \
  -F "languages=en-US" \
  -F "recognition_level=fast"
```

### Example 4: Upload with ocrmac (Multiple languages, maximum accuracy)

```bash
curl -X POST http://localhost:8000/upload/ocrmac \
  -F "file=@document.pdf" \
  -F "languages=en-US" \
  -F "languages=fr-FR" \
  -F "languages=de-DE" \
  -F "recognition_level=accurate"
```

### Example 5: Upload with ocrmac (Automatic language detection)

```bash
# Omit languages parameter for automatic detection
curl -X POST http://localhost:8000/upload/ocrmac \
  -F "file=@document.jpg"
```

### Example 6: Backward compatibility (existing /upload endpoint)

```bash
# Still works, defaults to Tesseract
curl -X POST http://localhost:8000/upload \
  -F "file=@document.pdf" \
  -F "lang=eng"
```

## Python Client Examples

### Using Tesseract

```python
import requests

# Upload with Tesseract (invoice processing)
with open('invoice.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/upload/tesseract',
        files={'file': f},
        data={
            'lang': 'eng',
            'psm': 6,  # Single uniform block (good for forms)
            'oem': 1,  # LSTM neural network
            'dpi': 300
        }
    )

job = response.json()
print(f"Job ID: {job['job_id']}")
print(f"Status: {job['status']}")
```

### Using ocrmac (macOS)

```python
import requests

# Upload with ocrmac (multilingual document)
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/upload/ocrmac',
        files={'file': f},
        data={
            'languages': ['en-US', 'fr-FR'],
            'recognition_level': 'balanced'
        }
    )

job = response.json()
print(f"Job ID: {job['job_id']}")
```

### Using ocrmac with automatic language detection

```python
import requests

# Automatic language detection (no languages parameter)
with open('unknown_language.jpg', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/upload/ocrmac',
        files={'file': f},
        data={'recognition_level': 'accurate'}
    )

job = response.json()
```

## Polling for Results

Once you have a `job_id`, poll the status endpoint to check progress:

```bash
curl http://localhost:8000/jobs/{job_id}
```

**Response (pending)**:
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "upload": {
    "file_name": "invoice.pdf",
    "file_format": "application/pdf",
    "file_size": 245632,
    "upload_timestamp": "2025-10-18T10:30:00Z"
  }
}
```

**Response (completed)**:
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "result_url": "/results/123e4567-e89b-12d3-a456-426614174000",
  "completion_time": "2025-10-18T10:30:15Z"
}
```

## Retrieve HOCR Results

```bash
curl http://localhost:8000/results/{job_id}
```

**Response**: HOCR XML content (same format for both engines)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" ...>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta name="ocr-system" content="tesseract 5.3.0" />
  <!-- or -->
  <meta name="ocr-system" content="ocrmac via restful-ocr" />
</head>
<body>
  <div class='ocr_page' id='page_1' title='bbox 0 0 800 600'>
    <span class='ocrx_word' id='word_1_1' title='bbox 10 10 100 30; x_wconf 95'>Hello</span>
    ...
  </div>
</body>
</html>
```

## Language Code Reference

### Tesseract (ISO 639-3, 3-letter codes)

| Language | Code | Example |
|----------|------|---------|
| English | eng | `lang=eng` |
| French | fra | `lang=fra` |
| German | deu | `lang=deu` |
| Spanish | spa | `lang=spa` |
| Italian | ita | `lang=ita` |
| Portuguese | por | `lang=por` |
| Russian | rus | `lang=rus` |
| Arabic | ara | `lang=ara` |
| Chinese (Simplified) | chi_sim | `lang=chi_sim` |
| Chinese (Traditional) | chi_tra | `lang=chi_tra` |
| Japanese | jpn | `lang=jpn` |
| Korean | kor | `lang=kor` |

**Multiple languages**: `lang=eng+fra+deu` (max 5)

### ocrmac (IETF BCP 47 format)

| Language | Code | Example |
|----------|------|---------|
| English (US) | en-US | `languages=en-US` |
| French (France) | fr-FR | `languages=fr-FR` |
| German (Germany) | de-DE | `languages=de-DE` |
| Spanish (Spain) | es-ES | `languages=es-ES` |
| Italian (Italy) | it-IT | `languages=it-IT` |
| Portuguese (Portugal) | pt-PT | `languages=pt-PT` |
| Russian | ru | `languages=ru` |
| Arabic | ar | `languages=ar` |
| Chinese (Simplified) | zh-Hans | `languages=zh-Hans` |
| Chinese (Traditional) | zh-Hant | `languages=zh-Hant` |
| Japanese (Japan) | ja-JP | `languages=ja-JP` |
| Korean (Korea) | ko-KR | `languages=ko-KR` |

**Multiple languages**: Array format, max 5

## Common Use Cases

### Invoice/Form Processing (Tesseract)

```bash
curl -X POST http://localhost:8000/upload/tesseract \
  -F "file=@invoice.pdf" \
  -F "lang=eng" \
  -F "psm=6" \
  -F "oem=1" \
  -F "dpi=300"
```

**Why these parameters**:
- `psm=6`: Single uniform block (best for structured forms)
- `oem=1`: LSTM neural network (best accuracy)
- `dpi=300`: Standard scan resolution

### Receipt Processing (Tesseract)

```bash
curl -X POST http://localhost:8000/upload/tesseract \
  -F "file=@receipt.jpg" \
  -F "lang=eng" \
  -F "psm=11" \
  -F "oem=1" \
  -F "dpi=300"
```

**Why these parameters**:
- `psm=11`: Sparse text (best for receipts with scattered text)

### Fast Processing (ocrmac, macOS)

```bash
curl -X POST http://localhost:8000/upload/ocrmac \
  -F "file=@simple_document.jpg" \
  -F "languages=en-US" \
  -F "recognition_level=fast"
```

**When to use**: Simple documents with clear text, need for speed

### Maximum Accuracy (ocrmac, macOS)

```bash
curl -X POST http://localhost:8000/upload/ocrmac \
  -F "file=@complex_document.pdf" \
  -F "languages=en-US" \
  -F "recognition_level=accurate"
```

**When to use**: Complex documents, poor quality scans, handwriting

### Multilingual Documents

**Tesseract**:
```bash
curl -X POST http://localhost:8000/upload/tesseract \
  -F "file=@document.pdf" \
  -F "lang=eng+fra+deu"
```

**ocrmac**:
```bash
curl -X POST http://localhost:8000/upload/ocrmac \
  -F "file=@document.pdf" \
  -F "languages=en-US" \
  -F "languages=fr-FR" \
  -F "languages=de-DE"
```

## Error Handling

### Platform Incompatibility (ocrmac on non-macOS)

**Request**:
```bash
curl -X POST http://localhost:8000/upload/ocrmac \
  -F "file=@document.pdf"
```

**Response (HTTP 400)**:
```json
{
  "detail": "ocrmac engine is only available on darwin (macOS) systems. Current platform: linux"
}
```

### Invalid Language Code

**Tesseract** (HTTP 400):
```json
{
  "detail": "Invalid language format: 'english'. Expected ISO 639-3 codes (e.g., eng, fra, deu)"
}
```

**ocrmac** (HTTP 400):
```json
{
  "detail": "Invalid IETF BCP 47 language code: 'eng'. Expected format: 'en-US', 'fr-FR', 'zh-Hans'"
}
```

### Too Many Languages (HTTP 400)

```json
{
  "detail": "Maximum 5 languages allowed"
}
```

### Unsupported Language

**Tesseract** (HTTP 400):
```json
{
  "detail": "Tesseract language 'ara' not installed. Available: eng, fra, deu, spa"
}
```

**ocrmac** (HTTP 400):
```json
{
  "detail": "Unsupported language codes for ocrmac: hi-IN. Supported: en, fr, de, es, it, pt, ru, ar, zh-Hans, zh-Hant, ja, ko, th, vi"
}
```

## Performance Tips

1. **Choose the right engine**:
   - Tesseract: Cross-platform, extensive language support, highly configurable
   - ocrmac (macOS): Faster on Apple Silicon, GPU-accelerated, simpler API

2. **Optimize Tesseract parameters**:
   - Use `oem=1` (LSTM) for best accuracy on modern systems
   - Choose appropriate `psm` for your document type (6 for forms, 11 for receipts)
   - Set `dpi=300` for standard scans, 600 for small text

3. **Optimize ocrmac parameters**:
   - Use `recognition_level=fast` for simple, clear documents
   - Use `recognition_level=accurate` for complex or poor-quality scans
   - Omit `languages` for automatic detection (handles unknown languages)

4. **Document preparation**:
   - Higher DPI improves accuracy but increases processing time
   - Clean, high-contrast images work best
   - Rotate images to correct orientation before upload

## Migration from Previous Version

### Before (single `/upload` endpoint)

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@document.pdf" \
  -F "lang=eng"
```

### After (dedicated endpoints)

**Option 1**: Continue using `/upload` (backward compatible)
```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@document.pdf" \
  -F "lang=eng"
```

**Option 2**: Use dedicated Tesseract endpoint (recommended)
```bash
curl -X POST http://localhost:8000/upload/tesseract \
  -F "file=@document.pdf" \
  -F "lang=eng"
```

**Option 3**: Use ocrmac endpoint (macOS only, new capability)
```bash
curl -X POST http://localhost:8000/upload/ocrmac \
  -F "file=@document.pdf" \
  -F "languages=en-US"
```

**No breaking changes**: Existing clients continue to work without modification.

## Next Steps

- See [API Contracts](./contracts/) for detailed OpenAPI specifications
- See [Data Model](./data-model.md) for entity schemas and validation rules
- See [Research](./research.md) for technical implementation details
- See [Plan](./plan.md) for implementation phases and architecture decisions
