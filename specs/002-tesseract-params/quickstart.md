# Quickstart: Configurable Tesseract OCR Parameters

**Feature**: 002-tesseract-params
**Date**: 2025-10-18

## Overview

This guide shows how to use the configurable Tesseract parameters feature to customize OCR processing for specific languages, document types, and image resolutions.

---

## Quick Examples

### Default Behavior (No Parameters)

Process a document using default settings (English, automatic segmentation):

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@document.jpg"
```

**Response**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "status_url": "/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000"
}
```

---

### French Document

Process a French document with optimal language settings:

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@document_fr.jpg" \
  -F "lang=fra"
```

**Why**: Specifying the correct language dramatically improves recognition accuracy for non-English text.

---

### Invoice or Form

Process an invoice with optimal settings for structured documents:

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@invoice.jpg" \
  -F "lang=eng" \
  -F "psm=6" \
  -F "oem=1" \
  -F "dpi=300"
```

**Parameters explained**:
- `psm=6`: Single uniform block - best for tables, invoices, structured forms
- `oem=1`: LSTM neural network - best accuracy
- `dpi=300`: Standard document scan resolution

---

### Receipt with Scattered Text

Process a receipt where text is not in uniform blocks:

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@receipt.jpg" \
  -F "lang=eng" \
  -F "psm=11" \
  -F "dpi=300"
```

**Why PSM 11**: Sparse text mode finds text in any order, ideal for receipts and forms with scattered text.

---

### Multi-Language Document

Process a document containing both English and French text:

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@document_mixed.jpg" \
  -F "lang=eng+fra" \
  -F "psm=3" \
  -F "oem=1"
```

**Max languages**: Up to 5 languages can be specified using `+` separator.

---

## Parameter Reference

### Language (`lang`)

**Format**: `[a-z]{3}(\+[a-z]{3})*`
**Example**: `eng`, `fra`, `eng+fra+deu`
**Default**: English (`eng`)

**Common language codes**:
- `eng` - English
- `fra` - French
- `deu` - German
- `spa` - Spanish
- `ita` - Italian
- `por` - Portuguese
- `rus` - Russian
- `ara` - Arabic
- `chi_sim` - Simplified Chinese
- `chi_tra` - Traditional Chinese
- `jpn` - Japanese
- `hin` - Hindi

**Multiple languages**:
```bash
# English + French
-F "lang=eng+fra"

# English + French + German
-F "lang=eng+fra+deu"

# Maximum 5 languages
-F "lang=eng+fra+deu+spa+ita"
```

**Check available languages**:
```bash
curl http://localhost:8000/api/v1/languages
```

---

### Page Segmentation Mode (`psm`)

**Type**: Integer (0-13)
**Default**: 3 (automatic)

**Most useful modes**:

| PSM | Mode | Best For | Example |
|-----|------|----------|---------|
| **3** | Fully automatic | **Most documents** | `-F "psm=3"` |
| **6** | Single uniform block | **Invoices, tables, forms** | `-F "psm=6"` |
| **7** | Single text line | **Form fields, single lines** | `-F "psm=7"` |
| **11** | Sparse text | **Receipts, scattered text** | `-F "psm=11"` |

**All modes**:
- `0` - Orientation detection only (no OCR)
- `1` - Auto with orientation detection
- `2` - Auto segmentation (layout only)
- `3` - **Fully automatic (default)**
- `4` - Single column
- `5` - Single vertical block
- `6` - **Single uniform block**
- `7` - **Single text line**
- `8` - Single word
- `9` - Single word in circle
- `10` - Single character
- `11` - **Sparse text**
- `12` - Sparse text with orientation
- `13` - Raw line

---

### OCR Engine Mode (`oem`)

**Type**: Integer (0-3)
**Default**: 3 (auto-select)

**Modes**:

| OEM | Engine | Accuracy | Speed | Best For |
|-----|--------|----------|-------|----------|
| **0** | Legacy only | Lower | Faster | Tesseract 3 compatibility |
| **1** | LSTM only | **Highest** | Moderate | **Modern OCR (recommended)** |
| **2** | Legacy + LSTM | High | Slower | Rarely needed |
| **3** | Default | Varies | Varies | Auto-select |

**Recommendation**: Use `oem=1` for best accuracy with modern Tesseract 5.x.

```bash
# Best accuracy (recommended)
-F "oem=1"

# Legacy engine for compatibility
-F "oem=0"

# Auto-select (default)
-F "oem=3"
```

---

### DPI (`dpi`)

**Type**: Integer (70-2400)
**Default**: Auto-detect or 70

**Typical values**:
- `150` - Low resolution scans
- `300` - **Standard documents (recommended)**
- `600` - High-quality scans, small text

**When to specify**:
- Image lacks DPI metadata
- Override incorrect metadata
- Standardize across inconsistent images

```bash
# Standard resolution
-F "dpi=300"

# High-quality scan
-F "dpi=600"

# Low-resolution image
-F "dpi=150"
```

---

## Common Use Cases

### 1. Standard English Document

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@document.jpg"
```

No parameters needed - defaults work well.

---

### 2. Non-English Document

```bash
# Spanish document
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@documento.jpg" \
  -F "lang=spa"

# German document
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@dokument.jpg" \
  -F "lang=deu"
```

---

### 3. Invoice Processing

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@invoice.pdf" \
  -F "lang=eng" \
  -F "psm=6" \
  -F "oem=1" \
  -F "dpi=300"
```

**Why these settings**:
- `psm=6`: Structured layout (tables, line items)
- `oem=1`: Best accuracy for numbers and amounts
- `dpi=300`: Standard scan resolution

---

### 4. Business Card

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@card.jpg" \
  -F "lang=eng" \
  -F "psm=6" \
  -F "oem=1"
```

**Why PSM 6**: Business cards typically have uniform blocks of text.

---

### 5. Receipt

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@receipt.jpg" \
  -F "lang=eng" \
  -F "psm=11" \
  -F "oem=1" \
  -F "dpi=300"
```

**Why PSM 11**: Receipts have scattered text that's not in uniform blocks.

---

### 6. Form with Single-Line Fields

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@form.jpg" \
  -F "lang=eng" \
  -F "psm=7" \
  -F "oem=1"
```

**Why PSM 7**: Treats as single line, best for form field values.

---

### 7. Multi-Language Document

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@document.jpg" \
  -F "lang=eng+fra" \
  -F "psm=3" \
  -F "oem=1"
```

**Order matters**: First language has priority for ambiguous characters.

---

### 8. Low-Resolution Scan

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@scan_lowres.jpg" \
  -F "lang=eng" \
  -F "dpi=150"
```

**Specify DPI**: Helps Tesseract correctly interpret character sizes.

---

## Error Handling

### Language Not Installed

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@document.jpg" \
  -F "lang=xyz"
```

**Response** (HTTP 400):
```json
{
  "detail": [
    {
      "field": "lang",
      "message": "Language(s) not installed: xyz. Available: ara, chi_sim, deu, eng, fra...",
      "type": "value_error",
      "input": "xyz"
    }
  ]
}
```

---

### Too Many Languages

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@document.jpg" \
  -F "lang=eng+fra+deu+spa+ita+por"
```

**Response** (HTTP 400):
```json
{
  "detail": [
    {
      "field": "lang",
      "message": "Maximum 5 languages allowed, got 6",
      "type": "value_error",
      "input": "eng+fra+deu+spa+ita+por"
    }
  ]
}
```

---

### Invalid PSM Value

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@document.jpg" \
  -F "psm=99"
```

**Response** (HTTP 400):
```json
{
  "detail": [
    {
      "field": "psm",
      "message": "Input should be 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 or 13",
      "type": "literal_error",
      "input": 99
    }
  ]
}
```

---

### DPI Out of Range

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@document.jpg" \
  -F "dpi=50"
```

**Response** (HTTP 400):
```json
{
  "detail": [
    {
      "field": "dpi",
      "message": "Input should be greater than or equal to 70",
      "type": "greater_than_equal",
      "input": 50
    }
  ]
}
```

---

## Checking Job Status

After uploading, check job status and retrieve results:

```bash
# Get job status
curl http://localhost:8000/api/v1/jobs/{job_id}
```

**Response**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "result": {
    "hocr": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>...",
    "text": "Extracted text content..."
  },
  "parameters": {
    "lang": "eng+fra",
    "psm": 6,
    "oem": 1,
    "dpi": 300
  },
  "created_at": "2025-10-18T14:23:45.123Z",
  "completed_at": "2025-10-18T14:23:48.456Z"
}
```

**Note**: Parameters used for processing are included in the response for reproducibility.

---

## Python Client Example

```python
import requests
from pathlib import Path

def ocr_document(
    file_path: Path,
    lang: str = None,
    psm: int = None,
    oem: int = None,
    dpi: int = None
) -> dict:
    """Upload document for OCR with optional parameters."""

    url = "http://localhost:8000/api/v1/upload"

    # Build form data
    files = {'file': open(file_path, 'rb')}
    data = {}

    if lang:
        data['lang'] = lang
    if psm is not None:
        data['psm'] = psm
    if oem is not None:
        data['oem'] = oem
    if dpi is not None:
        data['dpi'] = dpi

    # Upload
    response = requests.post(url, files=files, data=data)
    response.raise_for_status()

    return response.json()

# Examples
# Default (English, automatic)
result = ocr_document(Path('document.jpg'))

# French document
result = ocr_document(Path('document_fr.jpg'), lang='fra')

# Invoice with optimal settings
result = ocr_document(
    Path('invoice.pdf'),
    lang='eng',
    psm=6,
    oem=1,
    dpi=300
)

# Multi-language document
result = ocr_document(
    Path('document.jpg'),
    lang='eng+fra',
    psm=3,
    oem=1
)

print(f"Job ID: {result['job_id']}")
print(f"Status URL: {result['status_url']}")
```

---

## Testing Locally

### Start the Server

```bash
# Using Docker
docker compose up -d

# Using uvicorn
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Check Available Languages

```bash
# List installed Tesseract languages
docker exec -it restful-ocr-api tesseract --list-langs

# Or via Python
docker exec -it restful-ocr-api python -c "import pytesseract; print(pytesseract.get_languages())"
```

### Test Parameter Validation

```bash
# Valid request
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@samples/test.jpg" \
  -F "lang=eng" \
  -F "psm=6" \
  -F "oem=1" \
  -F "dpi=300"

# Invalid language
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@samples/test.jpg" \
  -F "lang=INVALID"

# Invalid PSM
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@samples/test.jpg" \
  -F "psm=999"
```

---

## Tips for Best Results

### Language Selection

1. **Single language documents**: Always specify the language for best accuracy
2. **Multi-language documents**: List languages in order of prevalence
3. **Maximum 5 languages**: More languages = slower processing
4. **Check availability**: Use `/api/v1/languages` endpoint to see installed languages

### PSM Selection

1. **Start with PSM 3** (auto) - works for 80% of documents
2. **Use PSM 6** for invoices, forms, tables with structured layout
3. **Use PSM 11** for receipts, documents with scattered text
4. **Use PSM 7** for single-line text (form fields)
5. **Experiment** if results aren't satisfactory

### OEM Selection

1. **Use OEM 1** (LSTM) for best accuracy on modern Tesseract
2. **Use OEM 0** (legacy) only for Tesseract 3 compatibility
3. **Use OEM 3** (default) to let Tesseract decide

### DPI Settings

1. **300 DPI** is optimal for most document scans
2. **Only specify** if image lacks DPI metadata or has incorrect metadata
3. **Higher DPI** (600) for fine print, doesn't automatically improve results
4. **Lower DPI** (150) if image is low resolution

### Performance Considerations

1. **More languages = slower**: Each language adds processing time
2. **OEM 1 (LSTM)**: Slower than legacy but much more accurate
3. **PSM 0**: Doesn't perform OCR, only detects orientation
4. **Parameters have minimal validation overhead**: <100ms

---

## Next Steps

- See [data-model.md](./data-model.md) for detailed entity definitions
- See [contracts/openapi-extension.yaml](./contracts/openapi-extension.yaml) for full API specification
- See [research.md](./research.md) for technical implementation details
- Check the main [spec.md](./spec.md) for complete requirements and success criteria
