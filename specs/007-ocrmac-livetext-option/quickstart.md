# Quickstart: LiveText Recognition Level

**Feature**: Add LiveText Recognition Level to ocrmac Engine
**Date**: 2025-10-20
**Audience**: API users, developers, QA testers

## Overview

This guide shows how to use the new `livetext` recognition level for Apple's LiveText framework on macOS Sonoma (14.0+). LiveText provides enhanced OCR accuracy with performance comparable to existing recognition levels (~174ms per image).

---

## Prerequisites

### System Requirements
- **Operating System**: macOS Sonoma 14.0 or later
- **Platform**: Native macOS (not Docker - Apple Vision framework unavailable in containers)
- **Memory**: Standard requirements (no additional memory needed beyond existing ocrmac)

### Software Requirements
- **Python**: 3.11+
- **ocrmac Library**: Version with `framework` parameter support (≥1.0.0 recommended)
- **API Access**: Access to RESTful OCR API endpoints

### Verification
Check your macOS version:
```bash
sw_vers
# ProductVersion: 14.x.x (Sonoma) or higher required for LiveText
```

Check ocrmac installation:
```bash
python3 -c "import ocrmac; print(ocrmac.__version__ if hasattr(ocrmac, '__version__') else 'installed')"
```

---

## Quick Start

### 1. Synchronous OCR with LiveText (Recommended for Testing)

**Endpoint**: `POST /sync/ocrmac`

**Example Request**:
```bash
curl -X POST "http://localhost:8000/sync/ocrmac" \
  -F "file=@test_image.jpg" \
  -F "recognition_level=livetext"
```

**Expected Response** (HTTP 200):
```json
{
  "hocr": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>...<meta name=\"ocr-system\" content=\"ocrmac-livetext via restful-ocr\" />...",
  "engine": "ocrmac",
  "pages": 1,
  "processing_duration_seconds": 0.174
}
```

**Response Time**: ~174ms for standard 1MP image (faster than "accurate" mode, slower than "fast" mode)

---

### 2. Asynchronous OCR with LiveText (Production Use)

**Endpoint**: `POST /upload/ocrmac`

**Example Request**:
```bash
curl -X POST "http://localhost:8000/upload/ocrmac" \
  -F "file=@document.pdf" \
  -F "recognition_level=livetext" \
  -F "languages=en-US" \
  -F "languages=es-ES"
```

**Expected Response** (HTTP 202):
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Job created successfully"
}
```

**Check Status**:
```bash
curl "http://localhost:8000/jobs/550e8400-e29b-41d4-a716-446655440000"
```

---

### 3. With Language Preferences

LiveText honors language preferences just like Vision framework:

```bash
curl -X POST "http://localhost:8000/sync/ocrmac" \
  -F "file=@multilingual_doc.png" \
  -F "recognition_level=livetext" \
  -F "languages=en-US" \
  -F "languages=fr-FR" \
  -F "languages=de-DE"
```

**Supported Languages**: All IETF BCP 47 language codes supported by Apple's LiveText framework (same as Vision framework)

---

## Understanding hOCR Output

### Metadata Differences

**Vision Framework** (fast/balanced/accurate):
```xml
<meta name="ocr-system" content="ocrmac via restful-ocr" />
```

**LiveText Framework**:
```xml
<meta name="ocr-system" content="ocrmac-livetext via restful-ocr" />
```

### Confidence Scores

**Vision Framework**: Returns quantized confidence values (0, 50, or 100)
```xml
<span class="ocrx_word" id="word_1_1_1" title="bbox 80 50 160 80; x_wconf 50">Hello</span>
```

**LiveText Framework**: Always returns confidence 100
```xml
<span class="ocrx_word" id="word_1_1_1" title="bbox 80 50 160 80; x_wconf 100">Hello</span>
```

**Note**: LiveText's fixed confidence=1.0 is a framework characteristic, not a quality indicator.

---

## Error Handling

### Error 1: Platform Incompatibility (HTTP 400)

**Scenario**: Requesting `livetext` on macOS < 14.0 or non-macOS system

**Request**:
```bash
curl -X POST "http://localhost:8000/sync/ocrmac" \
  -F "file=@test.jpg" \
  -F "recognition_level=livetext"
```

**Response** (HTTP 400):
```json
{
  "detail": "LiveText recognition requires macOS Sonoma (14.0) or later. Available recognition levels: fast, balanced, accurate"
}
```

**Solution**: Use `fast`, `balanced`, or `accurate` recognition levels on pre-Sonoma systems.

---

### Error 2: Invalid Recognition Level (HTTP 422)

**Scenario**: Typo in recognition level value

**Request**:
```bash
curl -X POST "http://localhost:8000/sync/ocrmac" \
  -F "file=@test.jpg" \
  -F "recognition_level=livetextt"  # Typo: extra 't'
```

**Response** (HTTP 422):
```json
{
  "detail": [
    {
      "loc": ["body", "recognition_level"],
      "msg": "value is not a valid enumeration member; permitted: 'fast', 'balanced', 'accurate', 'livetext'",
      "type": "value_error.enum"
    }
  ]
}
```

**Solution**: Use exact value `"livetext"` (lowercase, no typos).

---

### Error 3: Library Incompatibility (HTTP 500)

**Scenario**: ocrmac library version doesn't support `framework` parameter

**Request**:
```bash
curl -X POST "http://localhost:8000/sync/ocrmac" \
  -F "file=@test.jpg" \
  -F "recognition_level=livetext"
```

**Response** (HTTP 500):
```json
{
  "detail": "ocrmac library version does not support LiveText framework. Please upgrade to a newer version of ocrmac that supports the framework parameter."
}
```

**Solution**: Upgrade ocrmac library:
```bash
pip install --upgrade ocrmac
```

**Check Version**:
```bash
pip show ocrmac | grep Version
```

---

### Error 4: Processing Timeout (HTTP 408)

**Scenario**: Image processing exceeds 30-second timeout (sync endpoint only)

**Response** (HTTP 408):
```json
{
  "detail": "Request processing timed out after 30 seconds"
}
```

**Solution**:
- Use async endpoint (`/upload/ocrmac`) for large files
- Reduce file size (compress images, reduce DPI for PDFs)
- Expected performance: ~174ms per image for LiveText

---

## Performance Expectations

### Recognition Level Comparison

| Recognition Level | Average Time | Use Case |
|-------------------|-------------|----------|
| `fast` | ~131ms | Quick scans, high-volume processing |
| `balanced` (default) | ~150ms | General-purpose OCR |
| `accurate` | ~207ms | High-accuracy requirements |
| `livetext` | ~174ms | **NEW** Enhanced accuracy on Sonoma+ |

**Benchmark**: MacBook Pro (Apple M3 Max), 1MP grayscale image

### Timeout Limits

- **Sync Endpoint** (`/sync/ocrmac`): 30 seconds maximum
- **Async Endpoint** (`/upload/ocrmac`): No hard timeout (processed in background)
- **File Size Limit**: 5MB for both sync and async

### Performance Tips

1. **Use Async for Large Files**: PDFs or multi-page documents → `/upload/ocrmac`
2. **Optimize Images**: Compress before upload (JPEG quality 85, PNG compression)
3. **Monitor Metrics**: Check Prometheus metrics for `sync_ocr_duration_seconds{recognition_level="livetext"}`

---

## Advanced Usage

### Python Client Example

```python
import requests

# Synchronous LiveText OCR
url = "http://localhost:8000/sync/ocrmac"
files = {"file": open("test.jpg", "rb")}
data = {
    "recognition_level": "livetext",
    "languages": ["en-US", "es-ES"]
}

response = requests.post(url, files=files, data=data)

if response.status_code == 200:
    result = response.json()
    print(f"Processing time: {result['processing_duration_seconds']}s")
    print(f"Pages: {result['pages']}")
    # Parse hOCR XML
    from xml.etree import ElementTree as ET
    root = ET.fromstring(result['hocr'])
    # Extract text from <span class="ocrx_word">
    words = [word.text for word in root.findall(".//*[@class='ocrx_word']")]
    print(f"Extracted words: {words}")
else:
    print(f"Error {response.status_code}: {response.json()['detail']}")
```

---

### Comparing Recognition Levels

**Test Script**: Process same image with all recognition levels

```bash
#!/bin/bash
IMAGE="test.jpg"
LEVELS=("fast" "balanced" "accurate" "livetext")

for level in "${LEVELS[@]}"; do
    echo "Testing $level..."
    time curl -s -X POST "http://localhost:8000/sync/ocrmac" \
        -F "file=@$IMAGE" \
        -F "recognition_level=$level" \
        | jq '.processing_duration_seconds'
done
```

**Expected Output**:
```
Testing fast...
0.131
Testing balanced...
0.150
Testing accurate...
0.207
Testing livetext...
0.174
```

---

## Troubleshooting

### Issue: "LiveText requires macOS Sonoma 14.0+"

**Symptoms**: HTTP 400 error when requesting `livetext`

**Diagnosis**:
```bash
sw_vers  # Check macOS version
```

**Resolution**:
- Upgrade to macOS Sonoma 14.0+ (if possible)
- Use `balanced` or `accurate` recognition levels on older macOS

---

### Issue: "ocrmac library version does not support LiveText"

**Symptoms**: HTTP 500 error when requesting `livetext`

**Diagnosis**:
```bash
pip show ocrmac
python3 -c "from ocrmac import ocrmac; ocrmac.OCR('test.png', framework='livetext')"
```

**Resolution**:
```bash
pip install --upgrade ocrmac
# Or reinstall
pip uninstall ocrmac
pip install ocrmac
```

---

### Issue: Unexpected output format

**Symptoms**: HTTP 500 with "unexpected output format" message

**Diagnosis**: Check server logs for annotation sample (first 500 chars logged)

**Resolution**:
- Verify image file is valid (not corrupted)
- Try different image format (PNG instead of JPEG, or vice versa)
- Report issue with image sample to maintainers

---

## Migration from Vision Framework

### No Code Changes Required

Existing applications using `balanced` or `accurate` recognition levels continue working unchanged. LiveText is an optional enhancement.

### Gradual Adoption

**Option 1: Client-Side Feature Detection**
```python
# Try livetext, fall back to balanced
for level in ["livetext", "balanced"]:
    response = requests.post(url, files=files, data={"recognition_level": level})
    if response.status_code == 200:
        break  # Success
    # HTTP 400 means livetext unavailable, try next level
```

**Option 2: Environment-Based Configuration**
```python
import platform

# Use livetext on Sonoma+, balanced otherwise
mac_version = platform.mac_ver()[0]
recognition_level = "livetext" if mac_version.startswith(("14.", "15.")) else "balanced"

response = requests.post(url, files=files, data={"recognition_level": recognition_level})
```

---

## Best Practices

1. **Default to Balanced**: Keep `balanced` as default for backward compatibility
2. **Use LiveText Explicitly**: Opt-in to `livetext` when macOS Sonoma is guaranteed
3. **Handle Errors Gracefully**: Catch HTTP 400/500 errors and fall back to other levels
4. **Monitor Performance**: Track `processing_duration_seconds` across recognition levels
5. **Test on Target Platform**: Verify LiveText availability on deployment environment

---

## Next Steps

- **Read Specification**: [spec.md](./spec.md) - Full feature requirements
- **Review Data Model**: [data-model.md](./data-model.md) - RecognitionLevel enum details
- **Check OpenAPI Changes**: [contracts/openapi-diff.md](./contracts/openapi-diff.md) - API schema updates
- **Implementation Tasks**: Wait for `/speckit.tasks` output for development checklist

---

## Support

- **Platform Requirements**: macOS Sonoma 14.0+ (native, not Docker)
- **API Documentation**: `/docs` endpoint (FastAPI auto-generated docs)
- **Metrics**: Prometheus metrics at `/metrics` endpoint
- **Health Check**: `/health` endpoint includes ocrmac engine availability

---

## Appendix: Complete curl Examples

### Minimal Request (Defaults to Balanced)
```bash
curl -X POST "http://localhost:8000/sync/ocrmac" -F "file=@test.jpg"
```

### With LiveText and Languages
```bash
curl -X POST "http://localhost:8000/sync/ocrmac" \
  -F "file=@test.jpg" \
  -F "recognition_level=livetext" \
  -F "languages=en-US" \
  -F "languages=zh-Hans"
```

### Async Upload with LiveText
```bash
curl -X POST "http://localhost:8000/upload/ocrmac" \
  -F "file=@document.pdf" \
  -F "recognition_level=livetext"
```

### Check Job Status
```bash
JOB_ID="550e8400-e29b-41d4-a716-446655440000"
curl "http://localhost:8000/jobs/$JOB_ID"
```

### Fetch Results
```bash
curl "http://localhost:8000/jobs/$JOB_ID/result"
```
