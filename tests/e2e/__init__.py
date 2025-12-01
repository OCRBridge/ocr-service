"""End-to-end tests with real OCR engines.

These tests use actual OCR engines (not mocks) to validate complete
processing pipelines. Tests are skipped if engines are not installed.

Test Markers:
- @pytest.mark.slow: Tests that take significant time (EasyOCR)
- @pytest.mark.skipif: Auto-skipped when engine not available
"""
