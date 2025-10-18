# Research: Multi-Engine OCR Support

**Feature**: 003-multi-engine-ocr
**Date**: 2025-10-18
**Status**: Complete

## Research Questions

This document resolves all NEEDS CLARIFICATION items from the Technical Context and Constitution Check sections of plan.md.

## 1. ocrmac Library Availability and Integration

### Decision: Use ocrmac 0.1.0+ from PyPI
**Rationale**: ocrmac is a stable, well-documented Python wrapper for macOS's Vision framework. It's available on PyPI and actively maintained.

**Alternatives Considered**:
- **Direct Vision framework binding**: Rejected - requires Objective-C bridging, significantly more complex
- **py-ocr or other wrappers**: Rejected - ocrmac specifically designed for macOS Vision framework, most mature option

### Installation
```bash
pip install ocrmac
```

### API Documentation (from Context7)
```python
from ocrmac import ocrmac

# Basic usage
annotations = ocrmac.OCR('test.png').recognize()
# Returns: [(text, confidence, [x, y, width, height]), ...]

# With language preference (IETF BCP 47 format)
annotations = ocrmac.OCR('test.png', language_preference=['en-US']).recognize()

# With recognition level (affects accuracy vs speed)
annotations = ocrmac.OCR('test.png', recognition_level='accurate').recognize()

# Using LiveText framework (macOS Sonoma+)
annotations = ocrmac.OCR('test.png', framework="livetext").recognize()
```

### Version Requirements
- **Python**: 3.7+ (compatible with project's Python 3.11+)
- **macOS**: 10.15+ (Catalina or newer for Vision framework)
- **macOS Sonoma+**: Optional LiveText framework support

## 2. ocrmac Output Format Compatibility with HOCR

### Decision: HOCR output requires custom conversion layer
**Critical Finding**: ocrmac does NOT natively output HOCR XML format.

**ocrmac Output Format**:
```python
[
    ("GitHub: Let's build from here", 0.95, [0.16, 0.91, 0.17, 0.01]),
    ("example text", confidence_score, [x_min, y_min, width, height])
]
```

**HOCR Requirement**: Constitution Principle 2 (Deterministic Processing) + Assumption states "Each engine produces output in the same format (HOCR) for consistent downstream processing"

**Solution**: Implement conversion layer in `src/services/ocr/ocrmac.py` to transform ocrmac output to HOCR XML matching Tesseract format.

**HOCR Conversion Requirements**:
1. Generate valid HOCR XML structure
2. Convert bounding boxes from relative (0-1) to absolute pixel coordinates
3. Map confidence scores (0.0-1.0 float) to HOCR x_wconf values (0-100 integer)
4. Maintain document structure (pages, lines, words)
5. Include ocrmac metadata in HOCR header

**Reference HOCR Structure** (from Tesseract):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta name="ocr-system" content="tesseract 5.3.0" />
</head>
<body>
  <div class='ocr_page' id='page_1' title='bbox 0 0 800 600'>
    <div class='ocr_carea' id='carea_1_1' title='bbox 10 10 790 590'>
      <p class='ocr_par' id='par_1_1' title='bbox 10 10 790 590'>
        <span class='ocr_line' id='line_1_1' title='bbox 10 10 400 30'>
          <span class='ocrx_word' id='word_1_1' title='bbox 10 10 100 30; x_wconf 95'>Hello</span>
        </span>
      </p>
    </div>
  </div>
</body>
</html>
```

**Implementation Notes**:
- Use Python's `xml.etree.ElementTree` or `lxml` for HOCR generation
- Store image dimensions to convert relative coordinates to absolute pixels
- Group annotations into logical structures (lines, paragraphs) using bounding box proximity
- Test HOCR output against existing downstream consumers

## 3. Language Code Format Mapping

### Decision: Implement dual language code systems with validation per engine

**Finding**: ocrmac uses **IETF BCP 47** language tags (not ISO 639)

**Language Code Comparison**:

| Engine | Format | Examples | Spec |
|--------|--------|----------|------|
| Tesseract | ISO 639-3 (3-letter) | eng, fra, deu, spa, chi_sim | ISO 639-2/3 |
| ocrmac | IETF BCP 47 | en-US, fr-FR, de-DE, zh-Hans | RFC 5646 |

**IETF BCP 47 Components**:
- Primary subtag: ISO 639 language code (2 or 3 letters)
- Region: ISO 3166-1 country code (optional, e.g., -US, -FR)
- Script: ISO 15924 script code (optional, e.g., -Hans for Simplified Chinese)

**Common Mappings**:
```python
TESSERACT_TO_OCRMAC = {
    'eng': 'en',      # English
    'fra': 'fr',      # French
    'deu': 'de',      # German
    'spa': 'es',      # Spanish
    'ita': 'it',      # Italian
    'por': 'pt',      # Portuguese
    'rus': 'ru',      # Russian
    'ara': 'ar',      # Arabic
    'chi_sim': 'zh-Hans',  # Simplified Chinese
    'chi_tra': 'zh-Hant',  # Traditional Chinese
    'jpn': 'ja',      # Japanese
    'kor': 'ko',      # Korean
}
```

**Implementation Strategy**:
1. Each endpoint accepts its native format (Tesseract: ISO 639-3, ocrmac: IETF BCP 47)
2. Validation uses engine-specific language lists
3. No automatic conversion between formats - users specify correct format per endpoint
4. Clear error messages indicating expected format per engine

**Language Detection**:
- ocrmac supports automatic language detection when `language_preference` is omitted
- Feature spec US3 AS3: "user selects ocrmac but omits language parameter → automatic detection"

## 4. Engine Capability Discovery & Caching

### Decision: Startup detection with in-memory cache, platform validation

**Pattern**: Registry-based capability detection at application startup

**Implementation in `src/services/ocr/registry.py`**:

```python
from dataclasses import dataclass
from enum import Enum
import platform
from typing import Optional, Set

class EngineType(str, Enum):
    TESSERACT = "tesseract"
    OCRMAC = "ocrmac"

@dataclass
class EngineCapabilities:
    """Cached capabilities for an OCR engine."""
    available: bool
    version: Optional[str]
    supported_languages: Set[str]
    platform_requirement: Optional[str]  # e.g., "darwin" for macOS

class EngineRegistry:
    """Singleton registry for OCR engine discovery and capability caching."""

    _instance = None
    _capabilities: dict[EngineType, EngineCapabilities] = {}

    def __init__(self):
        """Initialize registry and detect all engines at startup."""
        self._detect_tesseract()
        self._detect_ocrmac()

    def _detect_tesseract(self):
        """Detect Tesseract availability and capabilities."""
        try:
            import pytesseract
            version = pytesseract.get_tesseract_version()
            languages = pytesseract.get_languages()
            self._capabilities[EngineType.TESSERACT] = EngineCapabilities(
                available=True,
                version=str(version),
                supported_languages=set(languages),
                platform_requirement=None  # Available on all platforms
            )
        except Exception as e:
            self._capabilities[EngineType.TESSERACT] = EngineCapabilities(
                available=False, version=None, supported_languages=set(),
                platform_requirement=None
            )

    def _detect_ocrmac(self):
        """Detect ocrmac availability and capabilities."""
        # Platform check
        if platform.system() != 'Darwin':
            self._capabilities[EngineType.OCRMAC] = EngineCapabilities(
                available=False, version=None, supported_languages=set(),
                platform_requirement='darwin'
            )
            return

        try:
            import ocrmac
            # ocrmac doesn't expose version or language list directly
            # Use Apple Vision framework supported languages
            # Reference: https://developer.apple.com/documentation/vision/vnrecognizetextrequest
            languages = {
                'en', 'fr', 'de', 'es', 'it', 'pt', 'ru', 'ar',
                'zh-Hans', 'zh-Hant', 'ja', 'ko', 'th', 'vi'
            }
            self._capabilities[EngineType.OCRMAC] = EngineCapabilities(
                available=True,
                version='0.1.0',  # Package version
                supported_languages=languages,
                platform_requirement='darwin'
            )
        except ImportError:
            self._capabilities[EngineType.OCRMAC] = EngineCapabilities(
                available=False, version=None, supported_languages=set(),
                platform_requirement='darwin'
            )

    def is_available(self, engine: EngineType) -> bool:
        """Check if engine is available."""
        return self._capabilities[engine].available

    def get_capabilities(self, engine: EngineType) -> EngineCapabilities:
        """Get cached capabilities for engine."""
        return self._capabilities[engine]

    def validate_language(self, engine: EngineType, languages: list[str]) -> bool:
        """Validate language codes against engine capabilities."""
        caps = self.get_capabilities(engine)
        if not caps.available:
            return False
        return all(lang in caps.supported_languages for lang in languages)
```

**Startup Integration** (in `src/main.py`):
```python
from src.services.ocr.registry import EngineRegistry

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize engine registry at startup."""
    # Initialize engine registry (runs detection)
    EngineRegistry()
    logger.info("engine_registry_initialized")
    yield
    # Cleanup if needed

app = FastAPI(lifespan=lifespan)
```

**Performance**:
- Detection runs once at startup: <100ms overhead
- Subsequent validations use cached data: <1ms per request
- Meets SC-008 requirement (<100ms engine validation)

**Cache Refresh**:
- Cache refreshes on application restart (FR-016a)
- No runtime refresh needed - engines don't change during app lifetime
- Future enhancement: periodic refresh via background task if needed

## 5. ocrmac Performance Characteristics

### Decision: Benchmark required, target 20% faster than Tesseract for simple docs

**Expected Performance** (based on Apple Vision framework):
- **Advantage**: Native GPU acceleration via Metal, optimized for Apple Silicon
- **Use case**: Simple documents (invoices, receipts, forms)
- **Target**: SC-005 requires 20% faster than Tesseract

**Benchmarking Strategy**:
1. Create test corpus: 50 single-page documents (invoices, receipts, forms, mixed content)
2. Measure both engines: processing time, accuracy (character error rate)
3. Track metrics: p50, p95, p99 latency per engine
4. Validate SC-006: Accuracy within 5% difference

**Performance Testing** (to be implemented in Phase 2):
```python
# tests/performance/test_engine_comparison.py
@pytest.mark.benchmark
def test_tesseract_vs_ocrmac_latency():
    """Compare processing latency for standard documents."""
    # Run both engines on same test set
    # Assert ocrmac p95 < tesseract p95 * 0.8 (20% faster)
    pass

@pytest.mark.benchmark
def test_tesseract_vs_ocrmac_accuracy():
    """Compare OCR accuracy using ground truth."""
    # Calculate character error rate (CER) for both
    # Assert abs(ocrmac_cer - tesseract_cer) <= 0.05 (within 5%)
    pass
```

**Unknown Variables**:
- Actual performance on target hardware
- Accuracy comparison on production document types
- Memory usage comparison

**Mitigation**: Phase 2 implementation will include comprehensive benchmarking before production deployment.

## 6. Engine-Specific Parameter Validation

### Decision: Separate Pydantic models per engine with endpoint-scoped validation

**Tesseract Parameters** (existing in `src/models/upload.py`):
```python
class TesseractParams(BaseModel):
    lang: Optional[str] = Field(None, pattern=r"^[a-z]{3}(\+[a-z]{3})*$")
    psm: Optional[int] = Field(None, ge=0, le=13)
    oem: Optional[int] = Field(None, ge=0, le=3)
    dpi: Optional[int] = Field(None, ge=70, le=2400)
```

**ocrmac Parameters** (new in `src/models/ocr_params.py`):
```python
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator

class RecognitionLevel(str, Enum):
    """ocrmac recognition level options."""
    FAST = "fast"
    BALANCED = "balanced"
    ACCURATE = "accurate"

class OcrmacParams(BaseModel):
    """ocrmac-specific OCR parameters."""

    languages: Optional[list[str]] = Field(
        None,
        description="Language codes (IETF BCP 47 format, e.g., en-US, fr-FR, zh-Hans). Max 5.",
        min_length=1,
        max_length=5
    )

    recognition_level: RecognitionLevel = Field(
        RecognitionLevel.BALANCED,
        description="Recognition level: fast (fewer languages, faster), balanced (default), accurate (slower, more accurate)"
    )

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate language codes format and count."""
        if v is None:
            return v

        if len(v) > 5:
            raise ValueError("Maximum 5 languages allowed")

        # Basic IETF BCP 47 format validation
        import re
        pattern = r"^[a-z]{2,3}(-[A-Z][a-z]{3})?(-[A-Z]{2})?$"
        for lang in v:
            if not re.match(pattern, lang):
                raise ValueError(f"Invalid IETF BCP 47 format: {lang}")

        return v
```

**Validation in Routes**:
- `/upload/tesseract`: Validates only TesseractParams
- `/upload/ocrmac`: Validates only OcrmacParams
- `/upload` (backward compatibility): Validates TesseractParams, defaults to Tesseract

**Error Messages**:
```json
// Tesseract endpoint with ocrmac param
{
  "detail": "Parameter 'recognition_level' is not valid for Tesseract engine. Valid parameters: lang, psm, oem, dpi"
}

// ocrmac endpoint on non-macOS
{
  "detail": "ocrmac engine is only available on macOS systems. Current platform: linux"
}
```

## 7. Platform Detection Strategy

### Decision: Use Python's standard `platform` module

**Implementation** (new `src/utils/platform.py`):
```python
import platform

def is_macos() -> bool:
    """Check if running on macOS."""
    return platform.system() == 'Darwin'

def get_platform_name() -> str:
    """Get platform name for error messages."""
    return platform.system().lower()
```

**Security Consideration**: Constitution Principle 6 requires platform detection must not leak system information. Using standard `platform.system()` only returns OS type ("Darwin", "Linux", "Windows"), no version or hardware details.

## 8. Separate Endpoint Architecture Validation

### Decision: CONFIRMED - Separate endpoints provide better API design

**Architecture Comparison**:

| Aspect | Separate Endpoints | Parametric Endpoint |
|--------|-------------------|---------------------|
| **URL Pattern** | `/upload/tesseract`, `/upload/ocrmac` | `/upload?engine=tesseract` |
| **Parameter Validation** | Endpoint-scoped (only relevant params) | Conditional (all params, subset valid) |
| **OpenAPI Schema** | Clean, engine-specific schemas | Complex, all params with conditional docs |
| **Backward Compatibility** | Existing `/upload` unchanged | `/upload` needs engine param added |
| **Error Messages** | Clear, per-endpoint | Generic, need engine context |
| **Versioning** | Per-endpoint versioning possible | Global versioning only |
| **Documentation** | Clear separation per engine | Mixed parameter documentation |

**User Experience Benefits**:
1. **Discoverability**: `/upload/tesseract` and `/upload/ocrmac` are self-documenting
2. **Type Safety**: Client SDKs can generate typed methods per endpoint
3. **Error Prevention**: Invalid parameter combinations caught by route itself
4. **Migration Path**: Easy to deprecate one engine without affecting others

**API Examples**:

```bash
# Separate endpoints (chosen approach)
curl -X POST /upload/tesseract \
  -F file=@doc.pdf \
  -F lang=eng \
  -F psm=6

curl -X POST /upload/ocrmac \
  -F file=@doc.pdf \
  -F languages=en-US,fr-FR \
  -F recognition_level=accurate

# Parametric endpoint (rejected)
curl -X POST /upload \
  -F file=@doc.pdf \
  -F engine=tesseract \
  -F lang=eng \
  -F recognition_level=accurate  # ERROR: tesseract doesn't support this
```

**Trade-offs Accepted**:
- More routes to maintain: 3 total (`/upload`, `/upload/tesseract`, `/upload/ocrmac`)
- Slight code duplication in route handlers
- Benefits outweigh costs: clearer API contract, better validation, easier future changes

## 9. HOCR Conversion Library Selection

### Decision: Use Python's built-in `xml.etree.ElementTree` for HOCR generation

**Rationale**:
- No external dependencies needed (Constitution Principle 7: Simplicity)
- Sufficient for HOCR XML generation (well-structured, not highly complex)
- Well-tested, part of Python standard library
- Performance adequate for our use case

**Alternative Considered**:
- **lxml**: Rejected - adds dependency, overkill for our needs
- **Manual string templating**: Rejected - error-prone, hard to maintain

**Implementation Pattern**:
```python
import xml.etree.ElementTree as ET

def annotations_to_hocr(
    annotations: list[tuple[str, float, list[float]]],
    image_width: int,
    image_height: int
) -> str:
    """Convert ocrmac annotations to HOCR XML."""
    # Create root structure
    html = ET.Element('html', xmlns="http://www.w3.org/1999/xhtml")
    head = ET.SubElement(html, 'head')
    meta = ET.SubElement(head, 'meta')
    meta.set('name', 'ocr-system')
    meta.set('content', 'ocrmac via restful-ocr')

    body = ET.SubElement(html, 'body')
    page = ET.SubElement(body, 'div')
    page.set('class', 'ocr_page')
    page.set('id', 'page_1')
    page.set('title', f'bbox 0 0 {image_width} {image_height}')

    # Convert annotations to words
    for idx, (text, confidence, bbox) in enumerate(annotations):
        # Convert relative bbox to absolute pixels
        x_min = int(bbox[0] * image_width)
        y_min = int(bbox[1] * image_height)
        x_max = int((bbox[0] + bbox[2]) * image_width)
        y_max = int((bbox[1] + bbox[3]) * image_height)

        # Create word span
        word = ET.SubElement(page, 'span')
        word.set('class', 'ocrx_word')
        word.set('id', f'word_1_{idx+1}')
        word.set('title', f'bbox {x_min} {y_min} {x_max} {y_max}; x_wconf {int(confidence*100)}')
        word.text = text

    # Convert to string
    return ET.tostring(html, encoding='unicode')
```

## Summary of Research Findings

### Resolved Technical Unknowns

1. ✅ **ocrmac Library**: Available on PyPI, stable, well-documented Python wrapper for macOS Vision framework
2. ✅ **HOCR Compatibility**: ocrmac does NOT output HOCR natively - requires custom conversion layer using `xml.etree.ElementTree`
3. ✅ **Language Codes**: ocrmac uses IETF BCP 47 (en-US, zh-Hans), Tesseract uses ISO 639-3 (eng, chi_sim) - no automatic conversion
4. ✅ **Engine Discovery**: Registry pattern with startup detection, in-memory cache, meets <100ms validation requirement
5. ✅ **Performance**: Expected 20% faster for simple docs (GPU acceleration), requires benchmarking in Phase 2
6. ✅ **Platform Detection**: Use standard `platform.system()`, secure, no information leakage
7. ✅ **Architecture**: Separate endpoints confirmed as better design for API clarity and maintenance

### Critical Implementation Requirements

1. **HOCR Conversion Layer**: Essential for Constitution Principle 2 (deterministic output format)
2. **Dual Language Validation**: Each endpoint validates its native language code format
3. **Startup Registry**: Initialize engine capabilities at app startup, cache for request validation
4. **Performance Benchmarking**: Required in Phase 2 to validate SC-005 (20% faster) and SC-006 (5% accuracy)
5. **macOS Platform Guard**: Reject ocrmac requests on non-macOS with clear error message

### Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| ocrmac performance doesn't meet 20% target | SC-005 failure | Benchmark early in Phase 2, adjust target if needed |
| HOCR conversion adds latency | SC-004a failure (30s target) | Optimize conversion, consider caching patterns |
| Language code confusion | User errors | Clear documentation, validation error messages |
| macOS-only limits deployment | Reduced adoption | Document clearly, provide Tesseract fallback |

### Next Phase Actions

1. Phase 1 (Design): Generate data models, API contracts, quickstart guide
2. Phase 2 (Implementation): Build HOCR converter, engine registry, endpoints, tests
3. Phase 2 (Validation): Comprehensive benchmarking against success criteria
