# Data Model: LiveText Recognition Level

**Feature**: Add LiveText Recognition Level to ocrmac Engine
**Date**: 2025-10-20

## Overview

This feature extends an existing enumeration (`RecognitionLevel`) with one additional value. No new entities are created. All changes are additive and backward compatible.

---

## Modified Entities

### 1. RecognitionLevel Enum

**Location**: `src/models/ocr_params.py`

**Purpose**: Enumeration of OCR recognition quality levels for the ocrmac engine

**Current Definition**:
```python
class RecognitionLevel(str, Enum):
    """ocrmac recognition level options."""

    FAST = "fast"
    BALANCED = "balanced"
    ACCURATE = "accurate"
```

**Modified Definition**:
```python
class RecognitionLevel(str, Enum):
    """ocrmac recognition level options."""

    FAST = "fast"
    BALANCED = "balanced"
    ACCURATE = "accurate"
    LIVETEXT = "livetext"  # NEW: Apple LiveText framework (macOS Sonoma 14.0+)
```

**Changes**:
- **Added**: `LIVETEXT = "livetext"` enum member
- **Backward Compatibility**: ✓ Existing values unchanged; new value is additive
- **Validation**: Pydantic automatically validates enum values via `OcrmacParams` model
- **Default Behavior**: Default remains `BALANCED` (no change)

**Usage Locations**:
- `src/models/ocr_params.py`: `OcrmacParams.recognition_level` field
- `src/api/routes/sync.py`: `/sync/ocrmac` endpoint parameter
- `src/api/routes/upload.py`: `/upload/ocrmac` endpoint parameter
- OpenAPI schema: Auto-generated from Pydantic model

**Platform Constraints**:
- `FAST`, `BALANCED`, `ACCURATE`: macOS 10.15+ (Vision framework)
- `LIVETEXT`: macOS Sonoma 14.0+ (LiveText framework)

---

### 2. OcrmacParams Model

**Location**: `src/models/ocr_params.py`

**Purpose**: Parameter validation model for ocrmac engine requests

**Current Definition**:
```python
class OcrmacParams(BaseModel):
    """ocrmac OCR engine parameters."""

    languages: list[str] | None = Field(
        None,
        description="Language codes in IETF BCP 47 format (e.g., en-US, fr-FR, zh-Hans). Max 5.",
        min_length=1,
        max_length=5,
        examples=[["en-US"], ["en-US", "fr-FR"], ["zh-Hans"]],
    )

    recognition_level: RecognitionLevel = Field(
        RecognitionLevel.BALANCED,
        description="Recognition level: fast (fewer languages, faster), balanced (default), accurate (slower)",
    )

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, v: list[str] | None) -> list[str] | None:
        """Validate IETF BCP 47 language code format."""
        # ... existing validation logic ...
```

**Changes**:
- **Fields**: No changes to field definitions
- **Validators**: No changes to validation logic
- **Description Update**: `recognition_level` field description should be updated in code comments (not schema-breaking):
  ```python
  recognition_level: RecognitionLevel = Field(
      RecognitionLevel.BALANCED,
      description="Recognition level: fast (~131ms), balanced (default), accurate (~207ms), livetext (~174ms, requires macOS Sonoma 14.0+)",
  )
  ```

**Backward Compatibility**: ✓ Fully compatible - enum extension does not break existing parameter validation

---

## Runtime Data Structures

### 3. hOCR Output XML

**Type**: XML document (string)

**Purpose**: Standardized OCR output format with word-level bounding boxes and confidence scores

**Structure** (unchanged):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8" />
  <meta name="ocr-system" content="ocrmac via restful-ocr" />  <!-- MODIFIED for livetext -->
  <meta name="ocr-capabilities" content="ocr_page ocr_line ocrx_word" />
  <meta name="ocr-langs" content="en-US" />
</head>
<body>
  <div class="ocr_page" id="page_1" title="bbox 0 0 800 600">
    <div class="ocr_line" id="line_1_1" title="bbox 80 50 240 80">
      <span class="ocrx_word" id="word_1_1_1" title="bbox 80 50 160 80; x_wconf 100">Hello</span>
      <span class="ocrx_word" id="word_1_1_2" title="bbox 170 50 240 80; x_wconf 100">World</span>
    </div>
  </div>
</body>
</html>
```

**Changes for LiveText**:
1. **Metadata Update** (`<meta name="ocr-system">`):
   - Vision framework: `"ocrmac via restful-ocr"` (existing)
   - LiveText framework: `"ocrmac-livetext via restful-ocr"` (new)

2. **Confidence Values** (`x_wconf`):
   - Vision framework: 0, 50, or 100 (quantized from 0.0, 0.5, 1.0)
   - LiveText framework: Always 100 (from confidence 1.0)

3. **No Structural Changes**: Bounding box format, coordinate system, and hierarchy remain identical

**Implementation Location**: `src/services/ocr/ocrmac.py::_convert_to_hocr()`

**Code Modification**:
```python
def _convert_to_hocr(
    self,
    annotations,
    image_width,
    image_height,
    languages,
    recognition_level_str,  # NEW parameter
):
    """Convert ocrmac annotations to hOCR XML format."""
    # ... existing code ...

    # Metadata update
    meta_ocr_system = ET.SubElement(head, "meta")
    meta_ocr_system.set("name", "ocr-system")
    if recognition_level_str == "livetext":
        meta_ocr_system.set("content", "ocrmac-livetext via restful-ocr")
    else:
        meta_ocr_system.set("content", "ocrmac via restful-ocr")

    # ... rest of existing code ...
```

---

## Validation Rules

### RecognitionLevel Enum
- **Valid Values**: `"fast"`, `"balanced"`, `"accurate"`, `"livetext"`
- **Invalid Values**: Any other string (e.g., `"livetextt"`, `"slow"`) → HTTP 400 validation error
- **Validation Location**: Pydantic model validation (automatic)
- **Error Message**: Auto-generated by Pydantic with enum options listed

### Platform Validation (Runtime)
- **Rule**: `recognition_level == "livetext"` requires macOS Sonoma 14.0+
- **Validation Location**: `src/services/ocr/ocrmac.py::_process_image()` and `_process_pdf()`
- **Error**: HTTP 400 if Sonoma not available
- **Error Message**: `"LiveText recognition requires macOS Sonoma (14.0) or later. Available recognition levels: fast, balanced, accurate"`

### Library Compatibility (Runtime)
- **Rule**: `framework` parameter must be supported by ocrmac library
- **Validation Location**: Try/except around `ocrmac.OCR()` instantiation
- **Error**: HTTP 500 if parameter not supported
- **Error Message**: `"ocrmac library version does not support LiveText framework. Please upgrade ocrmac."`

---

## State Transitions

**None** - This feature does not introduce stateful entities or lifecycle transitions. Recognition level is a request parameter, not a persistent state.

---

## Relationships

### RecognitionLevel ↔ OcrmacParams
- **Type**: Composition (RecognitionLevel enum used as field type in OcrmacParams)
- **Cardinality**: 1:1 (one recognition_level per OcrmacParams instance)
- **Direction**: OcrmacParams contains RecognitionLevel enum value

### OcrmacParams ↔ API Endpoints
- **Type**: Usage (endpoints accept OcrmacParams as request parameters)
- **Cardinality**: N:1 (many requests can use same recognition_level value)
- **Endpoints**: `/sync/ocrmac`, `/upload/ocrmac`

### RecognitionLevel ↔ ocrmac Framework
- **Type**: Mapping (enum value determines framework parameter)
- **Mapping Logic**:
  - `FAST` → `framework="vision"` (implicit, not passed to ocrmac)
  - `BALANCED` → `framework="vision"` (implicit, not passed to ocrmac)
  - `ACCURATE` → `framework="vision"` (implicit, not passed to ocrmac)
  - `LIVETEXT` → `framework="livetext"` (explicit parameter)

---

## Data Persistence

**None** - Recognition level is a request parameter. No database changes, no persistent state.

**Affected Storage**:
- **Redis**: Job state for async requests includes `recognition_level` in serialized `OcrmacParams` (existing mechanism, no schema change)
- **Filesystem**: Temporary files (images, results) not affected by recognition level

---

## Migration Strategy

**Not Applicable** - No database migration required. Enum extension is additive and handled by Pydantic schema evolution.

**Rollback Safety**: ✓ If a client sends `recognition_level=livetext` to an older API version, Pydantic validation will reject it with HTTP 422 (Unprocessable Entity), clearly indicating the unsupported value.

---

## Performance Implications

### Data Model Changes
- **Enum Extension**: No performance impact (single string comparison)
- **Validation**: No performance impact (Pydantic validation overhead unchanged)

### Runtime Performance
- **LiveText Processing**: ~174ms per image (faster than "accurate" 207ms, slower than "fast" 131ms)
- **hOCR Conversion**: No performance impact (reuses existing logic)
- **Metadata Update**: Negligible (single string assignment)

---

## Testing Checklist

- [ ] RecognitionLevel enum includes LIVETEXT value
- [ ] Pydantic validation accepts "livetext" as valid recognition_level
- [ ] Pydantic validation rejects invalid values (e.g., "livetextt")
- [ ] OcrmacParams default remains BALANCED
- [ ] hOCR output includes correct metadata for livetext
- [ ] hOCR confidence values are 100 for livetext
- [ ] Backward compatibility: existing recognition levels unchanged
- [ ] OpenAPI schema includes "livetext" in enum documentation

---

## Summary

**Entities Modified**: 1 (RecognitionLevel enum)
**New Entities**: 0
**Breaking Changes**: 0
**Backward Compatible**: ✓ Yes
**Migration Required**: ✗ No
**Performance Impact**: Negligible (enum extension only)
**Testing Complexity**: Low (single enum value addition)
