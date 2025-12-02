"""End-to-end tests with real OCR engines.

These tests use actual OCR engines (not mocks) to validate complete
processing pipelines. Tests are skipped if engines are not installed.

Test Markers:
- @pytest.mark.tesseract: Tests for Tesseract engine
- @pytest.mark.easyocr: Tests for EasyOCR engine
- @pytest.mark.ocrmac: Tests for Ocrmac engine (macOS only)
- @pytest.mark.skipif: Auto-skipped when engine not available
"""
