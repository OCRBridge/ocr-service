# Research: LiveText Recognition Level Implementation

**Feature**: Add LiveText Recognition Level to ocrmac Engine
**Date**: 2025-10-20
**Researcher**: Claude Code (via Context7 and codebase analysis)

## Research Questions & Findings

### 1. ocrmac Library Framework Parameter Support

**Question**: What is the minimum ocrmac library version that supports the `framework` parameter?

**Research Method**:
- Consulted Context7 documentation for ocrmac library
- Reviewed README and usage examples
- Current pyproject.toml specifies: `ocrmac>=0.1.0; sys_platform == 'darwin'`

**Findings**:
- The `framework` parameter is supported in ocrmac for specifying either "vision" or "livetext"
- LiveText support was added for macOS Sonoma compatibility
- No explicit minimum version found in documentation, but LiveText examples are present in current docs
- The library uses `framework="livetext"` parameter in OCR class initialization

**Decision**:
- **Minimum Version**: Keep current `ocrmac>=0.1.0` requirement; actual LiveText support likely in versions 1.0+
- **Verification Strategy**: Attempt to pass `framework` parameter; catch TypeError/AttributeError if unsupported
- **Error Detection**: Wrap `ocrmac.OCR(..., framework="livetext")` in try/except to catch parameter not recognized

**Code Pattern**:
```python
try:
    ocr_instance = ocrmac.OCR(
        str(image_path),
        language_preference=languages,
        framework="livetext"  # New parameter
    )
except TypeError as e:
    # framework parameter not supported in this ocrmac version
    raise RuntimeError(f"ocrmac library version does not support LiveText framework. Please upgrade ocrmac: {str(e)}")
```

**Rationale**: Since exact version is undocumented, defensive programming with try/except provides graceful degradation and clear error messages.

---

### 2. macOS Version Detection for Sonoma

**Question**: How to reliably detect macOS Sonoma (14.0) or later in Python?

**Research Method**:
- Reviewed existing `src/services/ocr/registry.py` for platform detection patterns
- Checked Python `platform` module documentation
- Examined existing ocrmac platform checks

**Findings**:
- Current code uses `platform.system()` to detect "Darwin" (macOS)
- `platform.mac_ver()` returns tuple: `(release, versioninfo, machine)`
- macOS Sonoma is version 14.0+
- Existing code pattern: `if platform.system() != "Darwin": ...`

**Decision**:
- **Version Detection Method**: Use `platform.mac_ver()[0]` to get macOS version string (e.g., "14.2.0")
- **Comparison Logic**: Parse major version and compare: `int(version.split('.')[0]) >= 14`
- **Location**: Add check in `OcrmacEngine._process_image()` and `_process_pdf()` before creating OCR instance with livetext

**Code Pattern**:
```python
import platform

def _check_sonoma_requirement(recognition_level: str) -> tuple[bool, str]:
    """Check if macOS Sonoma is available for LiveText."""
    if recognition_level != "livetext":
        return True, ""

    if platform.system() != "Darwin":
        return False, "ocrmac is only available on macOS systems"

    mac_version = platform.mac_ver()[0]
    if not mac_version:
        return False, "Unable to determine macOS version"

    try:
        major_version = int(mac_version.split('.')[0])
        if major_version < 14:
            return False, f"LiveText recognition requires macOS Sonoma (14.0) or later. Current version: {mac_version}"
    except (ValueError, IndexError):
        return False, f"Invalid macOS version format: {mac_version}"

    return True, ""
```

**Rationale**: Explicit version checking provides clear error messages and prevents runtime failures. Matches existing platform detection patterns in the codebase.

---

### 3. LiveText Output Format Compatibility

**Question**: Does LiveText return the same annotation format as Vision framework?

**Research Method**:
- Reviewed Context7 documentation for ocrmac
- Examined existing `_convert_to_hocr()` method in `src/services/ocr/ocrmac.py`
- Analyzed annotation format from documentation

**Findings**:
- **Output Format**: Both Vision and LiveText return same annotation structure: `[(text, confidence, bbox), ...]`
- **Confidence Difference**: Vision returns quantized values (0.0, 0.5, 1.0); LiveText always returns 1.0
- **Bounding Box Format**: Same format: `[x_min, y_min, width, height]` in relative coordinates (0.0-1.0)
- **Coordinate System**: Same bottom-left origin requiring flip to hOCR top-left origin

**Decision**:
- **Format Compatibility**: ✓ CONFIRMED - LiveText uses identical annotation format
- **hOCR Conversion**: Reuse existing `_convert_to_hocr()` method without modifications
- **Metadata Update**: Change OCR system metadata to indicate framework used
- **Error Detection**: Validate annotation structure (length 3 tuple, bbox length 4) before conversion

**Code Pattern**:
```python
def _convert_to_hocr(self, annotations, image_width, image_height, languages, framework_type="vision"):
    """Convert ocrmac annotations to hOCR (works for both vision and livetext)."""
    # ... existing conversion logic ...

    # Update metadata to reflect framework
    meta_ocr_system = ET.SubElement(head, "meta")
    meta_ocr_system.set("name", "ocr-system")
    if framework_type == "livetext":
        meta_ocr_system.set("content", "ocrmac-livetext via restful-ocr")
    else:
        meta_ocr_system.set("content", "ocrmac via restful-ocr")
```

**Error Detection**:
```python
# Validate annotation format
for annotation in annotations:
    if not isinstance(annotation, tuple) or len(annotation) != 3:
        raise RuntimeError(f"LiveText processing returned unexpected output format: expected 3-tuple, got {type(annotation)}")
    text, confidence, bbox = annotation
    if not isinstance(bbox, list) or len(bbox) != 4:
        raise RuntimeError(f"LiveText processing returned unexpected bbox format: expected 4-element list, got {bbox}")
```

**Rationale**: Annotation format is stable across frameworks. Validation catches any unexpected changes and provides debugging information (first 500 chars logged per FR-014).

---

### 4. Framework Parameter Error Handling

**Question**: What exception does ocrmac raise when framework parameter is not supported?

**Research Method**:
- Analyzed Python TypeError/AttributeError patterns
- Reviewed existing error handling in `src/services/ocr/ocrmac.py`
- Considered library behavior with unknown parameters

**Findings**:
- **Likely Exception**: `TypeError` - "unexpected keyword argument 'framework'"
- **Alternative**: `AttributeError` - if framework parameter exists but livetext not supported
- **Current Error Handling**: Existing code wraps ocrmac calls in try/except with generic RuntimeError

**Decision**:
- **Exception Types**: Catch both `TypeError` and `AttributeError`
- **Error Message**: "ocrmac library version does not support LiveText framework. Please upgrade ocrmac."
- **Logging**: Log full exception details at ERROR level for debugging
- **HTTP Status**: Return 500 (Internal Server Error) with descriptive message per FR-013

**Code Pattern**:
```python
try:
    ocr_instance = ocrmac.OCR(
        str(image_path),
        language_preference=languages,
        framework=framework_type  # "livetext" or "vision"
    )
    annotations = ocr_instance.recognize()
except (TypeError, AttributeError) as e:
    if "framework" in str(e):
        logger.error("ocrmac_library_incompatible", error=str(e), recognition_level=recognition_level)
        raise RuntimeError(
            "ocrmac library version does not support LiveText framework. "
            "Please upgrade to a newer version of ocrmac that supports the framework parameter."
        )
    raise  # Re-raise if not framework-related
except Exception as e:
    logger.error("ocrmac_processing_failed", error=str(e), file=str(image_path))
    raise RuntimeError(f"ocrmac processing failed: {str(e)}")
```

**Rationale**: Specific error detection for framework parameter issues provides actionable guidance to system administrators. Distinguishes between library version issues and other processing errors.

---

## Testing Strategy

### Unit Tests
1. **RecognitionLevel Enum**: Verify "livetext" is valid value
2. **Version Detection**: Mock `platform.mac_ver()` to test Sonoma detection (>=14.0 pass, <14.0 fail)
3. **Framework Parameter**: Mock ocrmac to raise TypeError, verify error handling
4. **Annotation Validation**: Test unexpected format detection with malformed annotations

### Integration Tests
1. **End-to-End LiveText** (macOS Sonoma only): Process sample image with livetext, verify hOCR output
2. **Platform Validation** (mock version): Verify HTTP 400 on pre-Sonoma macOS
3. **Performance**: Verify processing time <30s for 5MB image, ~174ms for standard 1MP image

### Contract Tests
1. **OpenAPI Schema**: Verify "livetext" in RecognitionLevel enum
2. **Error Responses**: Verify HTTP 400/500 error formats match specification
3. **Backward Compatibility**: Verify fast/balanced/accurate still work unchanged

### Mocking Strategy
- `platform.mac_ver()`: Return various macOS versions for testing
- `ocrmac.OCR()`: Mock to raise TypeError for library version tests
- `pytest.mark.skipif`: Skip LiveText integration tests if not on Sonoma

---

## Alternatives Considered

### 1. Separate Framework Parameter (Rejected)
- **Proposal**: Add `framework` as separate parameter independent of `recognition_level`
- **Reason Rejected**: Out of scope per specification. Recognition level is the user-facing abstraction. Framework is implementation detail.
- **Tradeoff**: Less flexibility but simpler API and clearer user intent

### 2. Automatic Fallback (Rejected)
- **Proposal**: Automatically fall back to "balanced" if livetext unavailable
- **Reason Rejected**: Out of scope per specification. Users should explicitly choose recognition level.
- **Tradeoff**: Less user-friendly for platform transitions but more predictable behavior

### 3. Version Detection via ocrmac Library (Rejected)
- **Proposal**: Check ocrmac.__version__ for LiveText support
- **Reason Rejected**: Version attribute may not exist; try/except is more robust
- **Tradeoff**: Less precise version detection but more defensive against library changes

---

## Best Practices Applied

1. **Defensive Programming**: Try/except for framework parameter compatibility
2. **Clear Error Messages**: Specific error messages for each failure mode (version, library, format)
3. **Consistent Patterns**: Follow existing platform detection and error handling patterns
4. **Minimal Changes**: Reuse existing hOCR conversion logic
5. **Observable Failures**: Log all errors with context for debugging
6. **Backward Compatibility**: No changes to existing recognition levels

---

## Dependencies & Prerequisites

### External Dependencies
- **ocrmac**: Existing dependency (>=0.1.0), no version bump required
- **Python platform module**: Standard library, no additional dependency

### Platform Requirements
- **macOS Sonoma 14.0+**: For LiveText framework
- **macOS 10.15+**: For existing Vision framework (fast/balanced/accurate)
- **Native macOS**: Docker not supported (existing limitation)

### Internal Dependencies
- **Existing hOCR Conversion**: `_convert_to_hocr()` method in `src/services/ocr/ocrmac.py`
- **Platform Detection**: Pattern from `src/services/ocr/registry.py`
- **Error Handling**: Pattern from existing ocrmac engine methods

---

## Risks & Mitigations

### Risk 1: ocrmac Library API Changes
- **Likelihood**: Low
- **Impact**: High (feature breaks)
- **Mitigation**: Defensive try/except catches parameter changes; clear error messages guide upgrades

### Risk 2: macOS Version Detection Variability
- **Likelihood**: Medium
- **Impact**: Medium (false negatives/positives)
- **Mitigation**: Explicit version parsing with error handling; graceful failure with clear messages

### Risk 3: LiveText Output Format Changes
- **Likelihood**: Low
- **Impact**: Medium (hOCR conversion fails)
- **Mitigation**: Annotation validation before conversion; log unexpected formats (first 500 chars)

### Risk 4: Performance Regression
- **Likelihood**: Low
- **Impact**: Medium (timeout on sync endpoint)
- **Mitigation**: LiveText is faster than "accurate" (174ms vs 207ms); existing 30s timeout sufficient

---

## Open Questions Resolved

All research questions have been answered with concrete decisions and implementation patterns. No blocking unknowns remain.

**Proceed to Phase 1**: ✓ READY
