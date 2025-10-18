# Research: Configurable Tesseract OCR Parameters

**Date**: 2025-10-18
**Feature**: 002-tesseract-params

## Overview

This document consolidates research findings for implementing configurable Tesseract OCR parameters (language, PSM, OEM, DPI) as API parameters. Research was conducted using Context7 for up-to-date library documentation.

---

## 1. Pytesseract Parameter Configuration

### Decision: Use `lang` as function parameter, others in `config` string

**Rationale**:
- `pytesseract.image_to_pdf_or_hocr()` has dedicated `lang` parameter
- PSM, OEM, and DPI must be passed via `config` string parameter
- This follows pytesseract's API design pattern

**API Pattern**:
```python
hocr_output = pytesseract.image_to_pdf_or_hocr(
    image_path,
    lang='eng+fra',                          # Language as parameter
    config='--psm 6 --oem 1 --dpi 300',     # Others in config string
    extension='hocr'
)
```

**Alternatives Considered**:
- Using Tesseract CLI directly via subprocess - Rejected: More error-prone, loses pytesseract's error handling and type safety
- Passing all parameters via config string including language - Rejected: Less idiomatic, pytesseract provides `lang` parameter for better type checking

---

## 2. Language Code Handling

### Decision: Accept language codes as `+`-separated string, validate against installed languages

**Rationale**:
- Tesseract's native format is `lang1+lang2+lang3`
- Can validate each component against `pytesseract.get_languages()`
- Simple string manipulation, no complex parsing needed
- Maximum 5 languages as specified in requirements

**Implementation Pattern**:
```python
import pytesseract

# Get installed languages (should be cached)
installed_langs = pytesseract.get_languages()  # Returns: ['eng', 'fra', 'deu', 'osd', ...]

# Validate user input
user_lang = 'eng+fra'
requested = user_lang.split('+')

# Check each language
invalid = [lang for lang in requested if lang not in installed_langs]
if invalid:
    raise ValueError(
        f"Language(s) not installed: {', '.join(invalid)}. "
        f"Available: {', '.join(sorted(installed_langs))}"
    )
```

**Validation Rules**:
- Format: `^[a-z]{3}(\+[a-z]{3})*$` (lowercase 3-letter codes separated by +)
- Count: Maximum 5 languages per request (FR-011b)
- Existence: Each code must exist in `pytesseract.get_languages()`

**Alternatives Considered**:
- Accept array of strings and join internally - Rejected: Adds API complexity, Tesseract uses string format natively
- Auto-detect language from document - Rejected: Out of scope, requires ML, less deterministic

---

## 3. Page Segmentation Mode (PSM) Values

### Decision: Accept integer 0-13, use Literal type for validation performance

**Valid PSM Values**:

| PSM | Mode | Primary Use Case |
|-----|------|------------------|
| 0 | OSD only | Orientation detection (no OCR) |
| 1 | Auto + OSD | Full auto with orientation |
| 2 | Auto segmentation | Layout analysis only |
| **3** | **Fully automatic** | **DEFAULT - Most documents** |
| 4 | Single column | Newspaper columns, receipts |
| 5 | Single vertical block | Simple documents |
| 6 | Single uniform block | **Tables, invoices, forms** |
| 7 | Single text line | **Form fields, single lines** |
| 8 | Single word | Labels, isolated words |
| 9 | Single word (circle) | Circular text |
| 10 | Single character | License plates |
| 11 | Sparse text | **Receipts with scattered text** |
| 12 | Sparse text + OSD | Sparse with orientation |
| 13 | Raw line | Single line, bypass heuristics |

**Rationale**:
- PSM 3 (auto) is Tesseract's default and works for 80% of cases
- PSM 6, 7, 11 are most useful for specialized documents
- PSM 0 doesn't perform OCR, should still be allowed (user's choice)
- Using Python `Literal` type gives better performance than range validation

**Implementation Pattern**:
```python
from typing import Literal, Optional
from pydantic import Field

psm: Optional[Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]] = Field(
    default=None,
    description="Page segmentation mode (0-13)"
)
```

**Alternatives Considered**:
- Enum class for PSM values - Rejected: Literal is more performant, less boilerplate
- Restrict to "safe" PSM values only - Rejected: Users may have valid reasons for any mode
- String names instead of integers - Rejected: Tesseract uses integers, would require mapping

---

## 4. OCR Engine Mode (OEM) Values

### Decision: Accept integer 0-3, use Field constraints

**Valid OEM Values**:

| OEM | Engine | Speed | Accuracy | Traineddata Required |
|-----|--------|-------|----------|---------------------|
| 0 | Legacy only | Faster | Lower | tessdata (legacy models) |
| **1** | **LSTM only** | Moderate | **Highest** | tessdata_best/fast |
| 2 | Legacy + LSTM | Slower | High | tessdata (both models) |
| 3 | Default | Varies | Varies | Any |

**Rationale**:
- OEM 1 (LSTM) is recommended for modern Tesseract 5.x installations
- Most Docker images use `tessdata_best` which only supports OEM 1
- OEM 3 is auto-select based on available traineddata
- No incompatibility between PSM and OEM values

**Implementation Pattern**:
```python
from pydantic import Field

oem: Optional[int] = Field(
    default=None,
    ge=0,
    le=3,
    description="OCR Engine mode: 0=Legacy, 1=LSTM, 2=Both, 3=Default"
)
```

**Configuration String**:
```python
config = f'--psm {psm} --oem {oem}'
```

**Alternatives Considered**:
- Validate OEM against installed traineddata type - Rejected: Complex to detect, Tesseract handles gracefully with error
- Default to OEM 1 instead of letting Tesseract decide - Rejected: Better to use Tesseract's default (OEM 3) unless user specifies

---

## 5. DPI Configuration

### Decision: Accept integer 70-2400, add to config string

**Rationale**:
- DPI overrides missing/incorrect image metadata
- 300 DPI is standard for document scanning
- Valid range: 70 (Tesseract minimum) to 2400 (practical maximum)
- Most impactful when image lacks DPI metadata

**Implementation Pattern**:
```python
from pydantic import Field

dpi: Optional[int] = Field(
    default=None,
    ge=70,
    le=2400,
    description="Image DPI (70-2400, typical: 300)"
)

# Add to config string
config = f'--psm {psm} --oem {oem} --dpi {dpi}'
```

**When DPI Matters**:
- Image file lacks DPI metadata (Tesseract warns: "Invalid resolution 0 dpi. Using 70 instead")
- Override incorrect metadata
- Standardize processing across images with inconsistent metadata

**Alternatives Considered**:
- Use separate `pdf_dpi` parameter for PDF conversion - Rejected: DPI should apply consistently to all image processing
- Auto-detect optimal DPI - Rejected: Complex heuristic, less deterministic

---

## 6. Parameter Validation Strategy

### Decision: Use Pydantic 2.x Field constraints + custom validators

**Validation Layers**:

1. **Type & Format** (Field constraints - fastest)
   ```python
   lang: Optional[str] = Field(default=None, pattern=r'^[a-z]{3}(\+[a-z]{3})*$')
   psm: Optional[Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]] = None
   oem: Optional[int] = Field(default=None, ge=0, le=3)
   dpi: Optional[int] = Field(default=None, ge=70, le=2400)
   ```

2. **Business Rules** (Custom validators)
   ```python
   @field_validator('lang', mode='after')
   @classmethod
   def validate_language_count_and_availability(cls, v):
       if v is None:
           return v

       # Max 5 languages
       langs = v.split('+')
       if len(langs) > 5:
           raise ValueError(f"Maximum 5 languages allowed, got {len(langs)}")

       # Check installed
       installed = get_installed_languages()  # Cached
       invalid = [lang for lang in langs if lang not in installed]
       if invalid:
           raise ValueError(
               f"Language(s) not installed: {', '.join(invalid)}. "
               f"Available: {', '.join(sorted(installed)[:10])}"
           )

       return v
   ```

**Caching Strategy**:
```python
import functools
import subprocess

@functools.lru_cache(maxsize=1)
def get_installed_languages() -> set[str]:
    """Cache installed Tesseract languages (expensive subprocess call)."""
    try:
        result = subprocess.run(
            ['tesseract', '--list-langs'],
            capture_output=True,
            text=True,
            timeout=5
        )
        langs = result.stdout.strip().split('\n')[1:]  # Skip header
        return set(lang.strip() for lang in langs if lang.strip())
    except Exception:
        # Fallback to pytesseract
        import pytesseract
        return set(pytesseract.get_languages())
```

**Rationale**:
- Pydantic Field constraints are 10-100x faster (Rust implementation)
- Custom validators for business logic that can't be expressed in Field
- LRU cache reduces language check from ~50ms to ~0.001ms
- Clear error messages with actionable suggestions

**Performance Target**:
- Parameter validation: <100ms (FR-006, SC-006)
- Breakdown: Type validation <1ms, language check <1ms (cached), custom validators <5ms

**Alternatives Considered**:
- All validation in custom validators - Rejected: Much slower, Pydantic Field constraints are highly optimized
- Separate validation function instead of Pydantic - Rejected: Pydantic provides automatic API documentation and error formatting
- Skip installed language check - Rejected: Better UX to fail fast during upload than during processing

---

## 7. Error Message Design

### Decision: Provide structured error responses with available options

**Error Response Format**:
```json
{
  "detail": [
    {
      "field": "lang",
      "message": "Language(s) not installed: xyz. Available: ara, chi_sim, deu, eng, fra, hin, ita, jpn, por, rus...",
      "type": "value_error",
      "input": "eng+xyz"
    }
  ]
}
```

**Error Message Patterns**:

| Validation Failure | Error Message Template |
|-------------------|------------------------|
| Invalid language format | `"Language code must be 3-letter ISO codes separated by '+' (e.g., 'eng', 'fra', 'eng+fra')"` |
| Too many languages | `"Maximum 5 languages allowed, got {count}: {langs}"` |
| Language not installed | `"Language(s) not installed: {invalid}. Available: {installed_sample}..."` |
| PSM out of range | `"PSM must be between 0 and 13, got {value}"` |
| OEM out of range | `"OEM must be between 0 and 3, got {value}. (0=Legacy, 1=LSTM, 2=Both, 3=Default)"` |
| DPI out of range | `"DPI must be between 70 and 2400, got {value}. Typical values: 300 (standard), 600 (high quality)"` |

**Rationale**:
- List available options to guide users
- Include examples of correct format
- Provide context about typical values
- Keep messages concise but actionable

**Alternatives Considered**:
- Minimal error messages - Rejected: Poor UX, increases support burden
- Verbose documentation in each error - Rejected: Too much information, clutters response

---

## 8. Default Values Strategy

### Decision: Use `None` for all optional parameters, apply defaults in service layer

**Rationale**:
- API accepts `None` → service uses Tesseract defaults
- Explicit user values → passed to Tesseract
- Maintains backward compatibility (no parameters = current behavior)
- Service layer controls actual defaults, not API schema

**Default Values** (when parameter is `None`):
- `lang`: `None` → Tesseract uses `'eng'` (current behavior)
- `psm`: `None` → Tesseract uses PSM 3 (auto)
- `oem`: `None` → Tesseract uses OEM 3 (default based on traineddata)
- `dpi`: `None` → Tesseract auto-detects from image metadata or uses 70

**Implementation Pattern**:
```python
# API Model
class TesseractParams(BaseModel):
    lang: Optional[str] = None
    psm: Optional[Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]] = None
    oem: Optional[int] = Field(default=None, ge=0, le=3)
    dpi: Optional[int] = Field(default=None, ge=70, le=2400)

# Service Layer
def build_tesseract_config(params: TesseractParams) -> tuple[str, str]:
    """Build Tesseract configuration from validated parameters."""
    lang = params.lang or 'eng'  # Default to English

    config_parts = []
    if params.psm is not None:
        config_parts.append(f'--psm {params.psm}')
    if params.oem is not None:
        config_parts.append(f'--oem {params.oem}')
    if params.dpi is not None:
        config_parts.append(f'--dpi {params.dpi}')

    config = ' '.join(config_parts) if config_parts else ''

    return lang, config
```

**Alternatives Considered**:
- Set explicit defaults in Pydantic model - Rejected: Hides Tesseract's defaults, harder to change
- Require all parameters - Rejected: Poor UX, most users only need language
- Use different defaults than Tesseract - Rejected: Violates least surprise principle

---

## 9. Logging and Observability

### Decision: Log all parameter values in structured JSON with job ID correlation

**Rationale**:
- Required by Constitution Principle 5 and FR-010a
- Enables debugging parameter-related issues
- Supports reproducibility (same params + same image = same result)
- Structured format allows log aggregation and analysis

**Log Entry Format**:
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "ocr_processing_started",
    job_id=job_id,
    lang=params.lang or 'eng',
    psm=params.psm,
    oem=params.oem,
    dpi=params.dpi,
    image_format=file_format,
    file_size=file_size_bytes
)
```

**Example Output**:
```json
{
  "event": "ocr_processing_started",
  "timestamp": "2025-10-18T14:23:45.123Z",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "lang": "eng+fra",
  "psm": 6,
  "oem": 1,
  "dpi": 300,
  "image_format": "jpeg",
  "file_size": 2458240
}
```

**Job Metadata Storage**:
```python
# Store in Redis job state
job_state = {
    "job_id": job_id,
    "status": "processing",
    "parameters": {
        "lang": params.lang or 'eng',
        "psm": params.psm,
        "oem": params.oem,
        "dpi": params.dpi
    },
    "created_at": datetime.utcnow().isoformat()
}
```

**Alternatives Considered**:
- Only log non-default parameters - Rejected: Makes log analysis harder, default vs explicit unclear
- Separate parameter log entries - Rejected: Increases log volume, harder to correlate
- Log config string instead of individual parameters - Rejected: Harder to aggregate and analyze

---

## 10. Security Considerations

### Decision: Use strict whitelist validation with regex patterns (FR-005a)

**Security Requirements**:
- Prevent command injection through parameter values
- Prevent path traversal attempts
- Reject special characters outside allowed patterns
- Validate format before any processing

**Validation Patterns**:
```python
# Language codes: only lowercase letters and +
LANG_PATTERN = r'^[a-z]{3}(\+[a-z]{3})*$'

# PSM, OEM, DPI: only integers (Pydantic handles this)
# Using Literal/Field(ge, le) ensures no injection via numeric values
```

**Protection Mechanisms**:
1. Pydantic validates types and formats before any business logic
2. pytesseract library sanitizes config string parameters
3. No user input directly interpolated into shell commands
4. Subprocess calls (for language detection) use list args, not shell=True

**Attack Vectors Prevented**:
```python
# Command injection attempts - REJECTED by regex
lang = "eng; rm -rf /"         # Fails pattern validation
lang = "eng && malicious"      # Fails pattern validation
lang = "eng`whoami`"           # Fails pattern validation

# Path traversal - REJECTED by regex
lang = "../../../etc/passwd"   # Fails pattern validation

# Special characters - REJECTED by regex
lang = "eng' OR '1'='1"       # Fails pattern validation
```

**Rationale**:
- Regex validation catches malicious input before any processing
- Type-safe API (integers for PSM/OEM/DPI) prevents many injection vectors
- pytesseract abstracts away direct shell calls
- Defense in depth: multiple validation layers

**Alternatives Considered**:
- Validate after accepting input - Rejected: Fail fast principle, better to reject immediately
- Rely only on pytesseract validation - Rejected: Defense in depth requires multiple layers
- Blacklist approach - Rejected: Whitelist is more secure, rejects unknown threats

---

## 11. Backward Compatibility

### Decision: All parameters optional, defaults match current behavior

**Compatibility Matrix**:

| Current Behavior | With Feature | Backward Compatible? |
|-----------------|--------------|---------------------|
| No parameters specified | Uses `lang='eng'`, PSM 3, OEM 1 (from config.py) | ✅ Yes - same behavior |
| Upload endpoint path | `/api/v1/upload` (unchanged) | ✅ Yes - same endpoint |
| Request format | `multipart/form-data` with `file` field | ✅ Yes - adds optional fields |
| Response format | Job ID with status URL | ✅ Yes - unchanged |
| HOCR output format | Standard HOCR XML | ✅ Yes - content identical for same inputs |

**Migration Path**:
- Existing clients continue to work without changes
- New clients can gradually adopt parameters as needed
- No versioning required (additive change only)

**Alternatives Considered**:
- New endpoint `/api/v1/upload-advanced` - Rejected: Unnecessary API split, adds complexity
- Require version header for new parameters - Rejected: Overengineering for simple additive change
- Change defaults to differ from current behavior - Rejected: Would break compatibility

---

## Implementation Checklist

Based on research findings:

- [ ] Add Pydantic models with Field constraints (lang, psm, oem, dpi)
- [ ] Implement `@field_validator` for language count and availability checks
- [ ] Create `get_installed_languages()` function with `@lru_cache`
- [ ] Update `OCRProcessor` to accept TesseractParams and build config string
- [ ] Update upload endpoint to accept optional query/form parameters
- [ ] Add structured logging for all parameter values with job ID
- [ ] Store parameters in Redis job metadata for reproducibility
- [ ] Write comprehensive tests for each validation rule
- [ ] Update OpenAPI schema with parameter descriptions and examples
- [ ] Document common PSM/OEM combinations in API docs

---

## References

- pytesseract documentation via Context7
- Pydantic 2.5+ documentation via Context7
- Tesseract OCR documentation (PSM/OEM modes)
- Constitution Principle 5 (Observability)
- Constitution Principle 8 (Documentation & Library Reference)
- Feature spec: `/specs/002-tesseract-params/spec.md`
