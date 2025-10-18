"""Unit tests for ocrmac hOCR generation and line grouping."""

import xml.etree.ElementTree as ET
import pytest
from src.services.ocr.ocrmac import OcrmacEngine


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
        assert len(lines[0]['words']) == 1
        assert lines[0]['words'][0]['text'] == "Hello"
        assert lines[0]['words'][0]['confidence'] == 0.95

    def test_group_words_into_lines_single_line_multiple_words(self):
        """Test grouping words on the same horizontal line."""
        engine = OcrmacEngine()
        # Words at same vertical position (y=0.2)
        annotations = [
            ("Hello", 0.95, [0.1, 0.2, 0.1, 0.05]),
            ("World", 0.93, [0.25, 0.2, 0.12, 0.05]),
            ("Test", 0.90, [0.4, 0.2, 0.08, 0.05])
        ]

        lines = engine._group_words_into_lines(annotations, 800, 600)

        assert len(lines) == 1
        assert len(lines[0]['words']) == 3
        # Verify words are sorted left-to-right
        assert lines[0]['words'][0]['text'] == "Hello"
        assert lines[0]['words'][1]['text'] == "World"
        assert lines[0]['words'][2]['text'] == "Test"

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
            ("Line", 0.94, [0.3, 0.4, 0.08, 0.05])
        ]

        lines = engine._group_words_into_lines(annotations, 800, 600)

        assert len(lines) == 2
        # First line (top of page, smallest y values after flip)
        assert len(lines[0]['words']) == 2
        assert lines[0]['words'][0]['text'] == "Second"
        assert lines[0]['words'][1]['text'] == "Line"
        # Second line (bottom of page, larger y values after flip)
        assert len(lines[1]['words']) == 2
        assert lines[1]['words'][0]['text'] == "First"
        assert lines[1]['words'][1]['text'] == "Line"

    def test_group_words_into_lines_calculates_correct_bbox(self):
        """Test that line bounding boxes are calculated correctly."""
        engine = OcrmacEngine()
        annotations = [
            # ocrmac coordinates: [x, y_from_bottom, width, height] (relative)
            # y=0.2 from bottom = 0.8 from top after flip
            ("Hello", 0.95, [0.1, 0.2, 0.1, 0.05]),  # bbox after flip: 80,450 -> 160,480
            ("World", 0.93, [0.25, 0.2, 0.12, 0.05])  # bbox after flip: 200,450 -> 296,480
        ]

        lines = engine._group_words_into_lines(annotations, 800, 600)

        assert len(lines) == 1
        line_bbox = lines[0]['bbox']
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
            ("short", 0.93, [0.25, 0.2, 0.1, 0.04])   # Shorter word, slightly lower
        ]

        lines = engine._group_words_into_lines(annotations, 800, 600)

        # Both should be grouped in same line despite different heights
        assert len(lines) == 1
        assert len(lines[0]['words']) == 2

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
            ("BottomWord", 0.95, [0.1, 0.85, 0.1, 0.05])
        ]

        lines = engine._group_words_into_lines(annotations, 800, 600)

        # Should create 2 lines (too far apart vertically)
        assert len(lines) == 2

        # First line should be the one that appears at TOP of page (small y value)
        # This is "BottomWord" in ocrmac coords (y=0.85 from bottom = 0.1 from top)
        top_line = lines[0]
        assert len(top_line['words']) == 1
        assert top_line['words'][0]['text'] == "BottomWord"
        # y should be small (near top of image)
        # y_min_from_bottom = 0.85 * 600 = 510
        # y_max_from_bottom = (0.85 + 0.05) * 600 = 540
        # After flip: y_min = 600 - 540 = 60, y_max = 600 - 510 = 90
        assert top_line['bbox'][1] == 60  # y_min near top
        assert top_line['bbox'][3] == 90  # y_max

        # Second line should be the one that appears at BOTTOM of page (large y value)
        # This is "TopWord" in ocrmac coords (y=0.05 from bottom = 0.95 from top)
        bottom_line = lines[1]
        assert len(bottom_line['words']) == 1
        assert bottom_line['words'][0]['text'] == "TopWord"
        # y should be large (near bottom of image)
        # y_min_from_bottom = 0.05 * 600 = 30
        # y_max_from_bottom = (0.05 + 0.05) * 600 = 60
        # After flip: y_min = 600 - 60 = 540, y_max = 600 - 30 = 570
        assert bottom_line['bbox'][1] == 540  # y_min near bottom
        assert bottom_line['bbox'][3] == 570  # y_max


class TestOcrmacHocrStructure:
    """Test hOCR XML structure generated by ocrmac."""

    def test_hocr_contains_standard_hierarchy(self):
        """Test that hOCR output has ocr_page → ocr_line → ocrx_word hierarchy."""
        engine = OcrmacEngine()
        annotations = [
            ("Hello", 0.95, [0.1, 0.2, 0.1, 0.05]),
            ("World", 0.93, [0.25, 0.2, 0.12, 0.05])
        ]

        hocr_xml = engine._convert_to_hocr(annotations, 800, 600, ["en-US"], "balanced")

        # Parse XML
        # Remove DOCTYPE for easier parsing
        xml_content = hocr_xml.split('\n', 2)[2]  # Skip XML declaration and DOCTYPE
        root = ET.fromstring(xml_content)

        # Find ocr_page
        body = root.find('.//{http://www.w3.org/1999/xhtml}body')
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
            words_in_line = line.findall('.//{http://www.w3.org/1999/xhtml}span[@class="ocrx_word"]')
            assert len(words_in_line) > 0, "ocr_line should contain ocrx_word elements"

    def test_hocr_line_has_correct_attributes(self):
        """Test that ocr_line elements have correct attributes."""
        engine = OcrmacEngine()
        annotations = [
            ("Test", 0.95, [0.1, 0.2, 0.1, 0.05])
        ]

        hocr_xml = engine._convert_to_hocr(annotations, 800, 600, ["en-US"], "balanced")

        # Parse XML
        xml_content = hocr_xml.split('\n', 2)[2]
        root = ET.fromstring(xml_content)

        # Find first ocr_line
        line = root.find('.//{http://www.w3.org/1999/xhtml}span[@class="ocr_line"]')
        assert line is not None

        # Check attributes
        assert line.get('id') is not None
        assert line.get('id').startswith('line_1_')
        assert line.get('title') is not None
        assert 'bbox' in line.get('title')

    def test_hocr_preserves_word_attributes(self):
        """Test that word attributes (bbox, confidence) are preserved."""
        engine = OcrmacEngine()
        annotations = [
            ("Test", 0.95, [0.1, 0.2, 0.1, 0.05])
        ]

        hocr_xml = engine._convert_to_hocr(annotations, 800, 600, ["en-US"], "balanced")

        # Parse XML
        xml_content = hocr_xml.split('\n', 2)[2]
        root = ET.fromstring(xml_content)

        # Find word
        word = root.find('.//{http://www.w3.org/1999/xhtml}span[@class="ocrx_word"]')
        assert word is not None
        assert word.text == "Test"

        # Check attributes
        assert word.get('id') is not None
        assert word.get('title') is not None
        assert 'bbox' in word.get('title')
        assert 'x_wconf' in word.get('title')
        # Confidence 0.95 should be converted to 95
        assert 'x_wconf 95' in word.get('title')

    def test_hocr_multiple_lines_structure(self):
        """Test hOCR structure with multiple lines."""
        engine = OcrmacEngine()
        annotations = [
            # Line 1
            ("First", 0.95, [0.1, 0.2, 0.1, 0.05]),
            ("Line", 0.93, [0.25, 0.2, 0.08, 0.05]),
            # Line 2
            ("Second", 0.92, [0.1, 0.4, 0.12, 0.05]),
            ("Line", 0.94, [0.3, 0.4, 0.08, 0.05])
        ]

        hocr_xml = engine._convert_to_hocr(annotations, 800, 600, ["en-US"], "balanced")

        # Parse XML
        xml_content = hocr_xml.split('\n', 2)[2]
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
        xml_content = hocr_xml.split('\n', 2)[2]
        root = ET.fromstring(xml_content)

        # Should have page but no lines
        page = root.find('.//{http://www.w3.org/1999/xhtml}div[@class="ocr_page"]')
        assert page is not None

        lines = root.findall('.//{http://www.w3.org/1999/xhtml}span[@class="ocr_line"]')
        assert len(lines) == 0
