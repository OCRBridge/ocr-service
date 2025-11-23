"""Unit tests for OCRProcessor service - PDF handling."""

from pathlib import Path

import pytest

from src.models.upload import FileFormat
from src.services.ocr_processor import OCRProcessor, OCRProcessorError


@pytest.fixture
def ocr_processor():
    """Create OCRProcessor instance."""
    return OCRProcessor()


@pytest.fixture
def sample_pdf_path():
    """Get path to sample PDF."""
    return Path(__file__).parent.parent.parent / "samples" / "contract_en_scan.pdf"


def test_pdf_page_count_detection(sample_pdf_path):
    """Test PDF page count detection (T078)."""
    # Import pdf2image to count pages
    from pdf2image import convert_from_path

    # Convert PDF to images to get page count
    images = convert_from_path(str(sample_pdf_path), dpi=150)

    # Verify PDF has multiple pages
    assert len(images) > 0, "PDF should have at least one page"

    # contract_en_scan.pdf is a multi-page document
    # This test verifies we can detect page count correctly
    page_count = len(images)
    assert isinstance(page_count, int)
    assert page_count >= 1


@pytest.mark.asyncio
async def test_pdf_to_image_conversion(ocr_processor, sample_pdf_path):
    """Test PDF to image conversion functionality (T079)."""
    # This test verifies the _process_pdf method can convert PDF to images
    # and process them with Tesseract

    # Process the PDF
    try:
        hocr_output = await ocr_processor._process_pdf(sample_pdf_path)

        # Verify HOCR output is generated
        assert hocr_output is not None
        assert isinstance(hocr_output, str)
        assert len(hocr_output) > 0

        # Verify HOCR structure
        assert '<?xml version="1.0"' in hocr_output or "<html" in hocr_output
        assert "ocr_page" in hocr_output

    except OCRProcessorError as e:
        pytest.fail(f"PDF processing failed: {e}")


@pytest.mark.asyncio
async def test_merge_hocr_pages_single_page(ocr_processor):
    """Test merging HOCR pages with single page."""
    # Single page HOCR
    single_page_hocr = [
        """<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml">
        <head><title>OCR</title></head>
        <body><div class='ocr_page'>Test content</div></body>
        </html>"""
    ]

    # Merge should return the single page as-is (or properly wrapped)
    merged = ocr_processor._merge_hocr_pages(single_page_hocr)

    assert merged is not None
    assert "<body>" in merged
    assert "Test content" in merged


@pytest.mark.asyncio
async def test_merge_hocr_pages_multiple_pages(ocr_processor):
    """Test merging HOCR pages with multiple pages."""
    # Multiple page HOCR fragments
    page1_hocr = """<?xml version="1.0" encoding="UTF-8"?>
    <html xmlns="http://www.w3.org/1999/xhtml">
    <head><title>Page 1</title></head>
    <body><div class='ocr_page' id='page_1'>Page 1 content</div></body>
    </html>"""

    page2_hocr = """<?xml version="1.0" encoding="UTF-8"?>
    <html xmlns="http://www.w3.org/1999/xhtml">
    <head><title>Page 2</title></head>
    <body><div class='ocr_page' id='page_2'>Page 2 content</div></body>
    </html>"""

    multi_page_hocr = [page1_hocr, page2_hocr]

    # Merge pages
    merged = ocr_processor._merge_hocr_pages(multi_page_hocr)

    assert merged is not None
    assert "<body>" in merged
    assert "Page 1 content" in merged
    assert "Page 2 content" in merged

    # Both pages should be in the merged output
    assert "ocr_page" in merged


@pytest.mark.asyncio
async def test_process_document_pdf_format(ocr_processor, sample_pdf_path):
    """Test process_document with PDF format."""
    # Process PDF document
    hocr_output = await ocr_processor.process_document(sample_pdf_path, FileFormat.PDF)

    # Verify output
    assert hocr_output is not None
    assert isinstance(hocr_output, str)
    assert len(hocr_output) > 0
    assert "ocr_page" in hocr_output


@pytest.mark.asyncio
async def test_process_document_corrupted_pdf(ocr_processor, tmp_path):
    """Test process_document with corrupted PDF."""
    # Create a fake corrupted PDF file
    corrupted_pdf = tmp_path / "corrupted.pdf"
    corrupted_pdf.write_text("This is not a valid PDF file")

    # Processing should raise OCRProcessorError
    with pytest.raises(OCRProcessorError) as exc_info:
        await ocr_processor.process_document(corrupted_pdf, FileFormat.PDF)

    assert exc_info.value.error_code is not None
