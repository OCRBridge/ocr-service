# Quickstart Guide: Synchronous OCR Endpoints

**Feature**: Direct OCR Processing Endpoints
**Date**: 2025-10-19

## Overview

This guide demonstrates how to use the synchronous OCR endpoints to process documents and receive hOCR output directly in the HTTP response.

**When to use synchronous endpoints:**
- ✅ Single-page documents
- ✅ Small files (< 5MB)
- ✅ Quick processing needs (< 30 seconds)
- ✅ Real-time integrations (chat bots, mobile apps)
- ✅ Simple request-response workflows

**When to use async endpoints:**
- ✅ Multi-page documents
- ✅ Large files (> 5MB, up to 25MB)
- ✅ Batch processing
- ✅ Long-running jobs (> 30 seconds)
- ✅ Fire-and-forget workflows

---

## Synchronous vs Async Comparison

| Feature | Synchronous (`/sync/*`) | Async (`/upload/*`) |
|---------|------------------------|---------------------|
| **Requests** | 1 request | 3+ requests (upload → status → result) |
| **Timeout** | 30 seconds (hard limit) | No timeout |
| **File size** | 5MB max | 25MB max |
| **Job persistence** | None (ephemeral) | 48-hour TTL in Redis |
| **Response** | hOCR in response body | Job ID, poll for result |
| **Use case** | Quick, single-page docs | Multi-page, batch processing |
| **Error handling** | HTTP 408 timeout | Job status: FAILED |

---

## Quick Examples

### Example 1: Synchronous Tesseract (English document)

**Request:**
```bash
curl -X POST http://localhost:8000/sync/tesseract \
  -F "file=@sample.png" \
  -F "lang=eng" \
  -F "psm=3" \
  -F "oem=1" \
  -F "dpi=300"
```

**Response (HTTP 200):**
```json
{
  "hocr": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Transitional//EN\" \"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd\"><html xmlns=\"http://www.w3.org/1999/xhtml\" xml:lang=\"en\" lang=\"en\"><head><title></title><meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\" /><meta name='ocr-system' content='tesseract 5.3.0' /><meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_par ocr_line ocrx_word ocrp_wconf'/></head><body><div class='ocr_page' id='page_1' title='bbox 0 0 2480 3508'><div class='ocr_carea' id='carea_1_1' title='bbox 150 200 2330 400'><p class='ocr_par' id='par_1_1' title='bbox 150 200 2330 400'><span class='ocr_line' id='line_1_1' title='bbox 150 200 2330 400; baseline 0 -10'><span class='ocrx_word' id='word_1_1' title='bbox 150 200 450 390; x_wconf 95'>Sample</span> <span class='ocrx_word' id='word_1_2' title='bbox 500 200 800 390; x_wconf 96'>Text</span></span></p></div></div></body></html>",
  "processing_duration_seconds": 2.34,
  "engine": "tesseract",
  "pages": 1
}
```

**Processing time:** ~2.3 seconds (single request)

---

### Example 2: Synchronous EasyOCR (Multilingual document)

**Request:**
```bash
curl -X POST http://localhost:8000/sync/easyocr \
  -F "file=@chinese_english_doc.jpg" \
  -F "languages=[\"en\", \"zh\"]" \
  -F "gpu=true" \
  -F "paragraph=false"
```

**Response (HTTP 200):**
```json
{
  "hocr": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Transitional//EN\" \"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd\"><html xmlns=\"http://www.w3.org/1999/xhtml\" xml:lang=\"en\" lang=\"en\"><head><title></title><meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\" /><meta name='ocr-system' content='easyocr' /><meta name='ocr-capabilities' content='ocr_page ocr_line ocrx_word ocrp_wconf'/></head><body><div class='ocr_page' id='page_1' title='bbox 0 0 2480 3508'><span class='ocr_line' id='line_1_1' title='bbox 150 200 2330 400'><span class='ocrx_word' id='word_1_1' title='bbox 150 200 450 390; x_wconf 98'>你好</span> <span class='ocrx_word' id='word_1_2' title='bbox 500 200 800 390; x_wconf 97'>World</span></span></div></body></html>",
  "processing_duration_seconds": 3.12,
  "engine": "easyocr",
  "pages": 1
}
```

**Processing time:** ~3.1 seconds (single request)

---

### Example 3: Synchronous ocrmac (macOS only)

**Request:**
```bash
curl -X POST http://localhost:8000/sync/ocrmac \
  -F "file=@document.pdf" \
  -F "recognition_level=accurate" \
  -F "languages=[\"en-US\"]"
```

**Response (HTTP 200):**
```json
{
  "hocr": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Transitional//EN\" \"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd\"><html xmlns=\"http://www.w3.org/1999/xhtml\" xml:lang=\"en\" lang=\"en\"><head><title></title><meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\" /><meta name='ocr-system' content='ocrmac' /><meta name='ocr-capabilities' content='ocr_page ocr_line ocrx_word ocrp_wconf'/></head><body><div class='ocr_page' id='page_1' title='bbox 0 0 2480 3508'><span class='ocr_line' id='line_1_1' title='bbox 150 200 2330 400'><span class='ocrx_word' id='word_1_1' title='bbox 150 200 450 390; x_wconf 99'>Sample</span> <span class='ocrx_word' id='word_1_2' title='bbox 500 200 800 390; x_wconf 99'>Text</span></span></div></body></html>",
  "processing_duration_seconds": 1.45,
  "engine": "ocrmac",
  "pages": 1
}
```

**Processing time:** ~1.5 seconds (single request)
**Note:** Only available on macOS, NOT in Docker containers

---

## Error Handling Examples

### Timeout Error (HTTP 408)

**Request:**
```bash
curl -X POST http://localhost:8000/sync/tesseract \
  -F "file=@large_multipage.pdf"  # Takes > 30 seconds
```

**Response (HTTP 408):**
```json
{
  "detail": "Processing exceeded 30s timeout. Document may be too complex. Use async endpoints (/upload/tesseract) for large or multi-page documents.",
  "status_code": 408
}
```

**Solution:** Use async endpoint for this document:
```bash
# Step 1: Upload
curl -X POST http://localhost:8000/upload/tesseract \
  -F "file=@large_multipage.pdf" \
  -F "lang=eng"

# Response: {"job_id": "abc123", "status": "PENDING"}

# Step 2: Check status
curl http://localhost:8000/jobs/abc123

# Response: {"job_id": "abc123", "status": "COMPLETED"}

# Step 3: Get result
curl http://localhost:8000/jobs/abc123/result

# Response: hOCR XML file
```

---

### File Too Large Error (HTTP 413)

**Request:**
```bash
curl -X POST http://localhost:8000/sync/easyocr \
  -F "file=@huge_document.pdf"  # 7MB file
```

**Response (HTTP 413):**
```json
{
  "detail": "File size (7.2MB) exceeds 5MB limit. Use async endpoints (/upload/easyocr) for larger files.",
  "status_code": 413
}
```

**Solution:** Use async endpoint for files > 5MB

---

### Platform Unsupported Error (HTTP 400)

**Request (on Linux):**
```bash
curl -X POST http://localhost:8000/sync/ocrmac \
  -F "file=@document.png"
```

**Response (HTTP 400):**
```json
{
  "detail": "ocrmac engine is only available on macOS with Apple Vision framework. Platform: Linux. Use Tesseract or EasyOCR for cross-platform processing.",
  "status_code": 400
}
```

**Solution:** Use Tesseract or EasyOCR instead

---

## Python Client Examples

### Using `requests` library

```python
import requests
import json

# Synchronous Tesseract
def ocr_sync_tesseract(file_path: str, lang: str = "eng") -> dict:
    """Process document with synchronous Tesseract endpoint."""
    url = "http://localhost:8000/sync/tesseract"

    with open(file_path, "rb") as f:
        files = {"file": f}
        data = {"lang": lang, "psm": 3, "oem": 1, "dpi": 300}

        response = requests.post(url, files=files, data=data, timeout=35)

    response.raise_for_status()  # Raise exception for 4xx/5xx
    return response.json()

# Example usage
try:
    result = ocr_sync_tesseract("sample.png", lang="eng")
    print(f"Processing took {result['processing_duration_seconds']:.2f}s")
    print(f"Pages processed: {result['pages']}")
    print(f"hOCR length: {len(result['hocr'])} characters")

    # Save hOCR to file
    with open("output.hocr", "w", encoding="utf-8") as f:
        f.write(result["hocr"])

except requests.exceptions.HTTPError as e:
    if e.response.status_code == 408:
        print("Timeout! Use async endpoint for this document.")
    elif e.response.status_code == 413:
        print("File too large! Use async endpoint.")
    else:
        print(f"Error: {e.response.json()}")
except requests.exceptions.Timeout:
    print("Request timeout (network issue)")
```

### Using `httpx` library (async)

```python
import httpx
import asyncio

async def ocr_sync_easyocr(file_path: str, languages: list[str]) -> dict:
    """Process document with synchronous EasyOCR endpoint (async HTTP client)."""
    url = "http://localhost:8000/sync/easyocr"

    async with httpx.AsyncClient(timeout=35.0) as client:
        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {
                "languages": json.dumps(languages),
                "gpu": "true",
                "paragraph": "false"
            }

            response = await client.post(url, files=files, data=data)

    response.raise_for_status()
    return response.json()

# Example usage
async def main():
    try:
        result = await ocr_sync_easyocr(
            "multilingual.jpg",
            languages=["en", "zh"]
        )
        print(f"Engine: {result['engine']}")
        print(f"Duration: {result['processing_duration_seconds']:.2f}s")
        print(f"Pages: {result['pages']}")

    except httpx.HTTPStatusError as e:
        error_detail = e.response.json()
        print(f"HTTP {e.response.status_code}: {error_detail['detail']}")

asyncio.run(main())
```

---

## JavaScript/TypeScript Examples

### Using `fetch` (browser or Node.js 18+)

```javascript
async function ocrSyncTesseract(file, options = {}) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('lang', options.lang || 'eng');
  formData.append('psm', options.psm || 3);
  formData.append('oem', options.oem || 1);
  formData.append('dpi', options.dpi || 300);

  const response = await fetch('http://localhost:8000/sync/tesseract', {
    method: 'POST',
    body: formData,
    signal: AbortSignal.timeout(35000) // 35s timeout
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`HTTP ${response.status}: ${error.detail}`);
  }

  return await response.json();
}

// Example usage (browser)
document.getElementById('uploadForm').addEventListener('submit', async (e) => {
  e.preventDefault();

  const fileInput = document.getElementById('fileInput');
  const file = fileInput.files[0];

  try {
    const result = await ocrSyncTesseract(file, { lang: 'eng' });
    console.log(`Processing took ${result.processing_duration_seconds}s`);
    console.log(`hOCR:`, result.hocr);

    // Display results
    document.getElementById('output').textContent = result.hocr;

  } catch (error) {
    if (error.message.includes('408')) {
      alert('Timeout! Document is too complex. Try the async endpoint.');
    } else if (error.message.includes('413')) {
      alert('File too large! Maximum 5MB for sync endpoints.');
    } else {
      alert(`Error: ${error.message}`);
    }
  }
});
```

### Using `axios`

```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

async function ocrSyncEasyOCR(filePath, languages = ['en']) {
  const form = new FormData();
  form.append('file', fs.createReadStream(filePath));
  form.append('languages', JSON.stringify(languages));
  form.append('gpu', 'true');
  form.append('paragraph', 'false');

  try {
    const response = await axios.post(
      'http://localhost:8000/sync/easyocr',
      form,
      {
        headers: form.getHeaders(),
        timeout: 35000 // 35s timeout
      }
    );

    return response.data;

  } catch (error) {
    if (error.response) {
      // HTTP error (4xx, 5xx)
      const { status, data } = error.response;
      throw new Error(`HTTP ${status}: ${data.detail}`);
    } else if (error.code === 'ECONNABORTED') {
      // Timeout
      throw new Error('Request timeout (network issue)');
    } else {
      throw error;
    }
  }
}

// Example usage
(async () => {
  try {
    const result = await ocrSyncEasyOCR('document.jpg', ['en', 'zh']);
    console.log(`Engine: ${result.engine}`);
    console.log(`Duration: ${result.processing_duration_seconds}s`);
    console.log(`Pages: ${result.pages}`);

    // Save hOCR
    fs.writeFileSync('output.hocr', result.hocr, 'utf-8');
    console.log('hOCR saved to output.hocr');

  } catch (error) {
    console.error('Error:', error.message);
  }
})();
```

---

## Decision Flowchart: Sync vs Async

```
Start
  │
  ▼
File size > 5MB? ────Yes────> Use Async Endpoint (/upload/*)
  │ No
  ▼
Multi-page document? ────Yes────> Use Async Endpoint (/upload/*)
  │ No
  ▼
Processing likely > 30s? ────Yes────> Use Async Endpoint (/upload/*)
  │ No
  ▼
Need job persistence? ────Yes────> Use Async Endpoint (/upload/*)
  │ No
  ▼
Batch processing? ────Yes────> Use Async Endpoint (/upload/*)
  │ No
  ▼
Use Sync Endpoint (/sync/*)
```

---

## Performance Expectations

| Document Type | Engine | Typical Duration | Recommendation |
|---------------|--------|------------------|----------------|
| Single-page receipt | Tesseract | 1-3s | ✅ Sync |
| Single-page form | EasyOCR | 2-4s | ✅ Sync |
| Single-page scan (macOS) | ocrmac | 1-2s | ✅ Sync |
| 3-page PDF | Tesseract | 5-10s | ✅ Sync (borderline) |
| 10-page PDF | Any | 20-60s | ❌ Async (timeout risk) |
| Large image (> 5MB) | Any | Varies | ❌ Async (size limit) |
| Multi-language scan | EasyOCR | 3-8s | ✅ Sync |

---

## Environment Setup

### Local Development

```bash
# Start API server
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Test sync endpoint
curl -X POST http://localhost:8000/sync/tesseract \
  -F "file=@samples/sample.png" \
  -F "lang=eng"
```

### Docker

```bash
# Start services (API + Redis)
docker compose up -d

# Note: ocrmac NOT available in Docker (even on macOS)
# Use Tesseract or EasyOCR in containers

# Test sync endpoint
curl -X POST http://localhost:8000/sync/tesseract \
  -F "file=@samples/sample.png" \
  -F "lang=eng"
```

---

## Next Steps

1. **Try the examples** above with your own documents
2. **Review the OpenAPI specs** in `contracts/` for full API details
3. **Implement error handling** based on the error examples
4. **Monitor metrics** (Prometheus) for timeout rates and performance
5. **Read the implementation tasks** in `tasks.md` (generated by `/speckit.tasks`)

---

## FAQ

**Q: What happens if processing exceeds 30 seconds?**
A: The request returns HTTP 408 (Request Timeout) immediately. No partial results are returned. Use async endpoints for complex documents.

**Q: Are results cached?**
A: No. Each sync request processes the document fresh. No caching or persistence.

**Q: Can I increase the timeout limit?**
A: Currently fixed at 30 seconds. This can be configured via environment variable `SYNC_TIMEOUT_SECONDS` (range: 5-60 seconds).

**Q: Can I process multiple files in one request?**
A: No. Sync endpoints accept one file per request. For batch processing, use async endpoints or make multiple sync requests.

**Q: What's the difference between sync and async hOCR output?**
A: None. Identical hOCR for same document + parameters (deterministic processing, per FR-013).

**Q: Why use sync endpoints if async endpoints can do everything?**
A: Simplicity. Sync endpoints eliminate job queue complexity for simple use cases (1 request vs 3+).

**Q: Can I cancel a sync request?**
A: Yes. Client can abort the HTTP connection. Server will detect disconnect and cleanup resources.

**Q: Are sync endpoints faster than async?**
A: No. Processing speed is identical (same OCRProcessor). Sync eliminates job queue overhead (~50-100ms) but that's negligible compared to OCR processing time.
