"""Unit tests for ocrmac hOCR generation and line grouping."""

import sys
import xml.etree.ElementTree as ET

import pytest

from src.services.ocr.ocrmac import OcrmacEngine

# Skip entire test file on non-macOS platforms
if sys.platform != "darwin":
    pytest.skip("OCRMac tests require macOS platform", allow_module_level=True)


@pytest.mark.macos
class TestOcrmacLineGrouping:
    """Test line grouping functionality for ocrmac annotations."""

    def test_group_words_into_lines_empty_annotations(self):
        """Test grouping with empty annotations list."""
        engine = OcrmacEngine()
        lines = engine._group_words_into_lines([], 800, 600)

        assert lines == []

    def test_group_words_into_lines_single_word(self):
        """Test grouping with a single word."""
        engine = OcrmacEngine()
        annotations = [
            ("Hello", 0.95, [0.1, 0.2, 0.1, 0.05])  # (text, confidence, [x, y, w, h])
        ]

        lines = engine._group_words_into_lines(annotations, 800, 600)

        assert len(lines) == 1
        assert len(lines[0]["words"]) == 1
        assert lines[0]["words"][0]["text"] == "Hello"
        assert lines[0]["words"][0]["confidence"] == 0.95

    def test_group_words_into_lines_single_line_multiple_words(self):
        """Test grouping words on the same horizontal line."""
        engine = OcrmacEngine()
        # Words at same vertical position (y=0.2)
        annotations = [
            ("Hello", 0.95, [0.1, 0.2, 0.1, 0.05]),
            ("World", 0.93, [0.25, 0.2, 0.12, 0.05]),
            ("Test", 0.90, [0.4, 0.2, 0.08, 0.05]),
        ]

        lines = engine._group_words_into_lines(annotations, 800, 600)

        assert len(lines) == 1
        assert len(lines[0]["words"]) == 3
        # Verify words are sorted left-to-right
        assert lines[0]["words"][0]["text"] == "Hello"
        assert lines[0]["words"][1]["text"] == "World"
        assert lines[0]["words"][2]["text"] == "Test"

    def test_group_words_into_lines_multiple_lines(self):
        """Test grouping words on multiple lines."""
        engine = OcrmacEngine()
        # Two lines of text (ocrmac uses bottom-left origin)
        annotations = [
            # Line at y=0.2 from bottom → after flip: y≈0.75 from top (bottom line)
            ("First", 0.95, [0.1, 0.2, 0.1, 0.05]),
            ("Line", 0.93, [0.25, 0.2, 0.08, 0.05]),
            # Line at y=0.4 from bottom → after flip: y≈0.55 from top (top line)
            ("Second", 0.92, [0.1, 0.4, 0.12, 0.05]),
            ("Line", 0.94, [0.3, 0.4, 0.08, 0.05]),
        ]

        lines = engine._group_words_into_lines(annotations, 800, 600)

        assert len(lines) == 2
        # First line (top of page, smallest y values after flip)
        assert len(lines[0]["words"]) == 2
        assert lines[0]["words"][0]["text"] == "Second"
        assert lines[0]["words"][1]["text"] == "Line"
        # Second line (bottom of page, larger y values after flip)
        assert len(lines[1]["words"]) == 2
        assert lines[1]["words"][0]["text"] == "First"
        assert lines[1]["words"][1]["text"] == "Line"

    def test_group_words_into_lines_calculates_correct_bbox(self):
        """Test that line bounding boxes are calculated correctly."""
        engine = OcrmacEngine()
        annotations = [
            # ocrmac coordinates: [x, y_from_bottom, width, height] (relative)
            # y=0.2 from bottom = 0.8 from top after flip
            ("Hello", 0.95, [0.1, 0.2, 0.1, 0.05]),  # bbox after flip: 80,450 -> 160,480
            ("World", 0.93, [0.25, 0.2, 0.12, 0.05]),  # bbox after flip: 200,450 -> 296,480
        ]

        lines = engine._group_words_into_lines(annotations, 800, 600)

        assert len(lines) == 1
        line_bbox = lines[0]["bbox"]
        # Line bbox should encompass both words
        # After y-flip: Min x = 80, Min y = 450, Max x = 296, Max y = 480
        assert line_bbox[0] == 80  # x_min
        assert line_bbox[1] == 450  # y_min (flipped)
        assert line_bbox[2] == 296  # x_max
        assert line_bbox[3] == 480  # y_max (flipped)

    def test_group_words_into_lines_handles_different_heights(self):
        """Test grouping words with different heights on same line."""
        engine = OcrmacEngine()
        annotations = [
            ("Tall", 0.95, [0.1, 0.18, 0.08, 0.08]),  # Taller word
            ("short", 0.93, [0.25, 0.2, 0.1, 0.04]),  # Shorter word, slightly lower
        ]

        lines = engine._group_words_into_lines(annotations, 800, 600)

        # Both should be grouped in same line despite different heights
        assert len(lines) == 1
        assert len(lines[0]["words"]) == 2

    def test_y_coordinate_flip_from_bottom_to_top_origin(self):
        """Test that y-coordinates are correctly flipped from bottom-left to top-left origin."""
        engine = OcrmacEngine()
        # Image dimensions: 800 x 600
        annotations = [
            # Word near bottom of image (ocrmac y=0.05 from bottom)
            # After flip should be near top (y ≈ 570 from top)
            ("TopWord", 0.95, [0.1, 0.05, 0.1, 0.05]),
            # Word near top of image (ocrmac y=0.85 from bottom)
            # After flip should be near bottom (y ≈ 60 from top)
            ("BottomWord", 0.95, [0.1, 0.85, 0.1, 0.05]),
        ]

        lines = engine._group_words_into_lines(annotations, 800, 600)

        # Should create 2 lines (too far apart vertically)
        assert len(lines) == 2

        # First line should be the one that appears at TOP of page (small y value)
        # This is "BottomWord" in ocrmac coords (y=0.85 from bottom = 0.1 from top)
        top_line = lines[0]
        assert len(top_line["words"]) == 1
        assert top_line["words"][0]["text"] == "BottomWord"
        # y should be small (near top of image)
        # y_min_from_bottom = 0.85 * 600 = 510
        # y_max_from_bottom = (0.85 + 0.05) * 600 = 540
        # After flip: y_min = 600 - 540 = 60, y_max = 600 - 510 = 90
        assert top_line["bbox"][1] == 60  # y_min near top
        assert top_line["bbox"][3] == 90  # y_max

        # Second line should be the one that appears at BOTTOM of page (large y value)
        # This is "TopWord" in ocrmac coords (y=0.05 from bottom = 0.95 from top)
        bottom_line = lines[1]
        assert len(bottom_line["words"]) == 1
        assert bottom_line["words"][0]["text"] == "TopWord"
        # y should be large (near bottom of image)
        # y_min_from_bottom = 0.05 * 600 = 30
        # y_max_from_bottom = (0.05 + 0.05) * 600 = 60
        # After flip: y_min = 600 - 60 = 540, y_max = 600 - 30 = 570
        assert bottom_line["bbox"][1] == 540  # y_min near bottom
        assert bottom_line["bbox"][3] == 570  # y_max


@pytest.mark.macos
class TestOcrmacHocrStructure:
    """Test hOCR XML structure generated by ocrmac."""

    def test_hocr_contains_standard_hierarchy(self):
        """Test that hOCR output has ocr_page → ocr_line → ocrx_word hierarchy."""
        engine = OcrmacEngine()
        annotations = [
            ("Hello", 0.95, [0.1, 0.2, 0.1, 0.05]),
            ("World", 0.93, [0.25, 0.2, 0.12, 0.05]),
        ]

        hocr_xml = engine._convert_to_hocr(annotations, 800, 600, ["en-US"], "balanced")

        # Parse XML
        # Remove DOCTYPE for easier parsing
        xml_content = hocr_xml.split("\n", 2)[2]  # Skip XML declaration and DOCTYPE
        root = ET.fromstring(xml_content)

        # Find ocr_page
        body = root.find(".//{http://www.w3.org/1999/xhtml}body")
        page = body.find('.//{http://www.w3.org/1999/xhtml}div[@class="ocr_page"]')
        assert page is not None, "ocr_page element not found"

        # Find ocr_line elements (direct children of page)
        lines = page.findall('.//{http://www.w3.org/1999/xhtml}span[@class="ocr_line"]')
        assert len(lines) > 0, "No ocr_line elements found"

        # Find ocrx_word elements (should be children of ocr_line, not page)
        words_in_page = page.findall('.//{http://www.w3.org/1999/xhtml}span[@class="ocrx_word"]')
        assert len(words_in_page) > 0, "No ocrx_word elements found"

        # Verify words are inside lines, not direct children of page
        for line in lines:
            words_in_line = line.findall(
                './/{http://www.w3.org/1999/xhtml}span[@class="ocrx_word"]'
            )
            assert len(words_in_line) > 0, "ocr_line should contain ocrx_word elements"

    def test_hocr_line_has_correct_attributes(self):
        """Test that ocr_line elements have correct attributes."""
        engine = OcrmacEngine()
        annotations = [("Test", 0.95, [0.1, 0.2, 0.1, 0.05])]

        hocr_xml = engine._convert_to_hocr(annotations, 800, 600, ["en-US"], "balanced")

        # Parse XML
        xml_content = hocr_xml.split("\n", 2)[2]
        root = ET.fromstring(xml_content)

        # Find first ocr_line
        line = root.find('.//{http://www.w3.org/1999/xhtml}span[@class="ocr_line"]')
        assert line is not None

        # Check attributes
        assert line.get("id") is not None
        assert line.get("id").startswith("line_1_")
        assert line.get("title") is not None
        assert "bbox" in line.get("title")

    def test_hocr_preserves_word_attributes(self):
        """Test that word attributes (bbox, confidence) are preserved."""
        engine = OcrmacEngine()
        annotations = [("Test", 0.95, [0.1, 0.2, 0.1, 0.05])]

        hocr_xml = engine._convert_to_hocr(annotations, 800, 600, ["en-US"], "balanced")

        # Parse XML
        xml_content = hocr_xml.split("\n", 2)[2]
        root = ET.fromstring(xml_content)

        # Find word
        word = root.find('.//{http://www.w3.org/1999/xhtml}span[@class="ocrx_word"]')
        assert word is not None
        assert word.text == "Test"

        # Check attributes
        assert word.get("id") is not None
        assert word.get("title") is not None
        assert "bbox" in word.get("title")
        assert "x_wconf" in word.get("title")
        # Confidence 0.95 should be converted to 95
        assert "x_wconf 95" in word.get("title")

    def test_hocr_multiple_lines_structure(self):
        """Test hOCR structure with multiple lines."""
        engine = OcrmacEngine()
        annotations = [
            # Line 1
            ("First", 0.95, [0.1, 0.2, 0.1, 0.05]),
            ("Line", 0.93, [0.25, 0.2, 0.08, 0.05]),
            # Line 2
            ("Second", 0.92, [0.1, 0.4, 0.12, 0.05]),
            ("Line", 0.94, [0.3, 0.4, 0.08, 0.05]),
        ]

        hocr_xml = engine._convert_to_hocr(annotations, 800, 600, ["en-US"], "balanced")

        # Parse XML
        xml_content = hocr_xml.split("\n", 2)[2]
        root = ET.fromstring(xml_content)

        # Find all lines
        lines = root.findall('.//{http://www.w3.org/1999/xhtml}span[@class="ocr_line"]')
        assert len(lines) == 2

        # Check first line has 2 words
        words_line1 = lines[0].findall('.//{http://www.w3.org/1999/xhtml}span[@class="ocrx_word"]')
        assert len(words_line1) == 2

        # Check second line has 2 words
        words_line2 = lines[1].findall('.//{http://www.w3.org/1999/xhtml}span[@class="ocrx_word"]')
        assert len(words_line2) == 2

    def test_hocr_empty_annotations_creates_valid_structure(self):
        """Test that empty annotations still create valid hOCR structure."""
        engine = OcrmacEngine()
        annotations = []

        hocr_xml = engine._convert_to_hocr(annotations, 800, 600, ["en-US"], "balanced")

        # Parse XML
        xml_content = hocr_xml.split("\n", 2)[2]
        root = ET.fromstring(xml_content)

        # Should have page but no lines
        page = root.find('.//{http://www.w3.org/1999/xhtml}div[@class="ocr_page"]')
        assert page is not None

        lines = root.findall('.//{http://www.w3.org/1999/xhtml}span[@class="ocr_line"]')
        assert len(lines) == 0

    def test_hocr_preserves_vision_framework_quantized_confidence_values(self):
        """
        Test that ocrmac confidence values are correctly preserved in hOCR output.

        Apple's Vision framework returns quantized confidence scores:
        - Fast mode: 0.3 (30%) or 0.5 (50%)
        - Accurate/Balanced: 0.5 (50%) or 1.0 (100%)

        This test verifies our implementation correctly converts these to x_wconf values.
        """
        engine = OcrmacEngine()

        # Test typical Vision framework confidence values
        annotations = [
            ("Text1", 1.0, [0.1, 0.2, 0.1, 0.05]),  # Accurate mode: 100%
            ("Text2", 0.5, [0.3, 0.2, 0.1, 0.05]),  # Common value: 50%
            ("Text3", 0.3, [0.5, 0.2, 0.1, 0.05]),  # Fast mode: 30%
        ]

        hocr_xml = engine._convert_to_hocr(annotations, 800, 600, ["en-US"], "balanced")

        # Parse XML
        xml_content = hocr_xml.split("\n", 2)[2]
        root = ET.fromstring(xml_content)

        # Find all words
        words = root.findall('.//{http://www.w3.org/1999/xhtml}span[@class="ocrx_word"]')
        assert len(words) == 3

        # Verify confidence conversion (float 0.0-1.0 → integer 0-100)
        assert "x_wconf 100" in words[0].get("title"), "Confidence 1.0 should convert to 100"
        assert "x_wconf 50" in words[1].get("title"), "Confidence 0.5 should convert to 50"
        assert "x_wconf 30" in words[2].get("title"), "Confidence 0.3 should convert to 30"

        # Verify text is preserved
        assert words[0].text == "Text1"
        assert words[1].text == "Text2"
        assert words[2].text == "Text3"

    def test_hocr_metadata_with_livetext_framework(self):
        """Test that hOCR metadata includes 'ocrmac-livetext' for LiveText framework (T033)."""
        engine = OcrmacEngine()
        annotations = [("Test", 1.0, [0.1, 0.2, 0.1, 0.05])]

        # Test with livetext recognition level
        hocr_xml_livetext = engine._convert_to_hocr(annotations, 800, 600, ["en-US"], "livetext")

        # Parse XML
        xml_content_livetext = hocr_xml_livetext.split("\n", 2)[2]
        root_livetext = ET.fromstring(xml_content_livetext)

        # Find ocr-system metadata
        meta_system = root_livetext.find(
            './/{http://www.w3.org/1999/xhtml}meta[@name="ocr-system"]'
        )
        assert meta_system is not None
        assert meta_system.get("content") == "ocrmac-livetext via restful-ocr"

        # Compare with Vision framework (other recognition levels)
        for recognition_level in ["fast", "balanced", "accurate"]:
            hocr_xml_vision = engine._convert_to_hocr(
                annotations, 800, 600, ["en-US"], recognition_level
            )
            xml_content_vision = hocr_xml_vision.split("\n", 2)[2]
            root_vision = ET.fromstring(xml_content_vision)

            meta_system_vision = root_vision.find(
                './/{http://www.w3.org/1999/xhtml}meta[@name="ocr-system"]'
            )
            assert meta_system_vision is not None
            assert meta_system_vision.get("content") == "ocrmac via restful-ocr"

    def test_hocr_confidence_always_100_for_livetext(self):
        """Test that LiveText always returns confidence 100 in hOCR output (T034)."""
        engine = OcrmacEngine()

        # LiveText framework always returns confidence 1.0
        annotations_livetext = [
            ("Word1", 1.0, [0.1, 0.2, 0.1, 0.05]),
            ("Word2", 1.0, [0.3, 0.2, 0.1, 0.05]),
            ("Word3", 1.0, [0.5, 0.2, 0.1, 0.05]),
        ]

        hocr_xml = engine._convert_to_hocr(annotations_livetext, 800, 600, ["en-US"], "livetext")

        # Parse XML
        xml_content = hocr_xml.split("\n", 2)[2]
        root = ET.fromstring(xml_content)

        # Find all words
        words = root.findall('.//{http://www.w3.org/1999/xhtml}span[@class="ocrx_word"]')
        assert len(words) == 3

        # Verify all words have confidence 100
        for word in words:
            title = word.get("title")
            assert "x_wconf 100" in title, (
                f"LiveText should always have confidence 100, got: {title}"
            )

        # Verify text is preserved
        assert words[0].text == "Word1"
        assert words[1].text == "Word2"
        assert words[2].text == "Word3"


@pytest.mark.macos
class TestAnnotationFormatValidation:
    """Test annotation format validation for LiveText output (T032)."""

    def test_annotation_format_validation_with_valid_annotations(self):
        """Test that valid annotation format passes validation (T032)."""
        engine = OcrmacEngine()

        # Valid annotations: [(text, confidence, bbox), ...]
        valid_annotations = [
            ("Hello", 1.0, [0.1, 0.2, 0.1, 0.05]),  # 3-tuple: text, conf, bbox
            ("World", 1.0, [0.25, 0.2, 0.12, 0.05]),  # bbox is 4-element list
        ]

        # Should not raise exception
        hocr_xml = engine._convert_to_hocr(valid_annotations, 800, 600, ["en-US"], "livetext")

        # Verify hOCR was generated
        assert '<?xml version="1.0"' in hocr_xml
        assert "Hello" in hocr_xml
        assert "World" in hocr_xml

    def test_annotation_format_validation_detects_invalid_tuple_length(self):
        """Test that invalid annotation tuple length is detected."""
        engine = OcrmacEngine()

        # Invalid annotations: 2-tuple instead of 3-tuple
        invalid_annotations = [
            ("Text", 1.0),  # Missing bbox!
        ]

        # Should raise ValueError or IndexError when trying to unpack
        with pytest.raises((ValueError, IndexError)):
            engine._convert_to_hocr(invalid_annotations, 800, 600, ["en-US"], "livetext")

    def test_annotation_format_validation_detects_invalid_bbox_length(self):
        """Test that invalid bbox length is detected."""
        engine = OcrmacEngine()

        # Invalid annotations: bbox has only 3 elements instead of 4
        invalid_annotations = [
            ("Text", 1.0, [0.1, 0.2, 0.1]),  # Missing height!
        ]

        # Should raise ValueError or IndexError when accessing bbox elements
        with pytest.raises((ValueError, IndexError)):
            engine._convert_to_hocr(invalid_annotations, 800, 600, ["en-US"], "livetext")

    def test_annotation_format_validation_with_non_list_bbox(self):
        """Test that non-list bbox format is handled."""
        engine = OcrmacEngine()

        # Invalid annotations: bbox is tuple instead of list (should still work)
        annotations_with_tuple_bbox = [
            ("Text", 1.0, (0.1, 0.2, 0.1, 0.05)),  # Tuple instead of list
        ]

        # Tuples should work the same as lists (both are sequences)
        hocr_xml = engine._convert_to_hocr(
            annotations_with_tuple_bbox, 800, 600, ["en-US"], "livetext"
        )

        assert "Text" in hocr_xml

    def test_annotation_format_validation_with_empty_text(self):
        """Test handling of annotations with empty text."""
        engine = OcrmacEngine()

        # Annotations with empty string
        annotations_empty_text = [
            ("", 1.0, [0.1, 0.2, 0.1, 0.05]),  # Empty text
            ("Valid", 1.0, [0.3, 0.2, 0.1, 0.05]),
        ]

        # Should still generate hOCR (empty words are valid in hOCR)
        hocr_xml = engine._convert_to_hocr(annotations_empty_text, 800, 600, ["en-US"], "livetext")

        assert "Valid" in hocr_xml
        # Empty text should create an element but with no text content
        assert '<span class="ocrx_word"' in hocr_xml
