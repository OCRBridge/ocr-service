"""Integration tests for file handler with actual file I/O.

Tests async file operations, streaming uploads, temporary file management,
and file permissions.
"""

import os

import pytest

from src.services.file_handler import FileHandler


@pytest.fixture
def file_handler(temp_upload_dir, temp_results_dir, monkeypatch):
    """Create FileHandler with temporary directories."""
    monkeypatch.setenv("UPLOAD_DIR", str(temp_upload_dir))
    monkeypatch.setenv("RESULTS_DIR", str(temp_results_dir))

    # Reload config
    import importlib

    import src.config

    importlib.reload(src.config)

    handler = FileHandler()
    return handler


@pytest.mark.asyncio
async def test_save_upload_creates_file(file_handler, sample_upload_file):
    """Test that save_upload creates file in upload directory."""
    upload = await file_handler.save_upload(sample_upload_file)

    assert upload.temp_file_path.exists()
    assert upload.temp_file_path.is_file()
    assert upload.temp_file_path.parent == file_handler.upload_dir


@pytest.mark.asyncio
async def test_save_upload_preserves_content(file_handler, create_upload_file, sample_jpeg_bytes):
    """Test that uploaded file content is preserved."""
    upload_file = create_upload_file(sample_jpeg_bytes, "test.jpg")

    upload = await file_handler.save_upload(upload_file)

    # Read back content
    saved_content = upload.temp_file_path.read_bytes()
    assert saved_content == sample_jpeg_bytes


@pytest.mark.asyncio
async def test_save_upload_sets_file_permissions(file_handler, sample_upload_file):
    """Test that uploaded files have restrictive permissions (0o600)."""
    upload = await file_handler.save_upload(sample_upload_file)

    # Check file permissions
    file_mode = os.stat(upload.temp_file_path).st_mode
    # Mask to get permission bits
    permissions = file_mode & 0o777

    # Should be 0o600 (owner read/write only)
    assert permissions == 0o600


@pytest.mark.asyncio
async def test_save_upload_unique_filenames(file_handler, create_upload_file, sample_jpeg_bytes):
    """Test that multiple uploads get unique filenames."""
    upload1 = await file_handler.save_upload(create_upload_file(sample_jpeg_bytes, "test.jpg"))
    upload2 = await file_handler.save_upload(create_upload_file(sample_jpeg_bytes, "test.jpg"))

    # Should have different filenames
    assert upload1.temp_file_path != upload2.temp_file_path
    # Both should exist
    assert upload1.temp_file_path.exists()
    assert upload2.temp_file_path.exists()


@pytest.mark.asyncio
async def test_save_upload_extension_from_mime_type(
    file_handler, create_upload_file, sample_jpeg_bytes, sample_png_bytes, sample_pdf_bytes
):
    """Test that file extension is determined from MIME type."""
    jpeg_upload = await file_handler.save_upload(create_upload_file(sample_jpeg_bytes, "image.jpg"))
    assert jpeg_upload.temp_file_path.suffix == ".jpg"

    png_upload = await file_handler.save_upload(create_upload_file(sample_png_bytes, "image.png"))
    assert png_upload.temp_file_path.suffix == ".png"

    pdf_upload = await file_handler.save_upload(create_upload_file(sample_pdf_bytes, "doc.pdf"))
    assert pdf_upload.temp_file_path.suffix == ".pdf"


@pytest.mark.asyncio
async def test_save_upload_validates_format(file_handler, create_upload_file, invalid_file_bytes):
    """Test that save_upload validates file format."""
    from src.utils.validators import UnsupportedFormatError

    invalid_file = create_upload_file(invalid_file_bytes, "invalid.txt")

    with pytest.raises(UnsupportedFormatError):
        await file_handler.save_upload(invalid_file)


@pytest.mark.asyncio
async def test_save_upload_validates_size(file_handler, create_upload_file):
    """Test that save_upload validates file size."""
    from src.config import settings
    from src.utils.validators import FileTooLargeError

    # Create file larger than max_upload_size_bytes
    huge_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * (settings.max_upload_size_bytes + 1000)
    huge_file = create_upload_file(huge_bytes, "huge.jpg")

    with pytest.raises(FileTooLargeError):
        await file_handler.save_upload(huge_file)


@pytest.mark.asyncio
async def test_save_upload_returns_document_upload(file_handler, sample_upload_file):
    """Test that save_upload returns DocumentUpload model."""
    from src.models.upload import DocumentUpload

    upload = await file_handler.save_upload(sample_upload_file)

    assert isinstance(upload, DocumentUpload)
    assert upload.file_name == "test.jpg"
    assert upload.file_format.value == "image/jpeg"
    assert upload.file_size > 0
    assert upload.content_type == "image/jpeg"


@pytest.mark.asyncio
async def test_delete_temp_file(file_handler, temp_upload_dir):
    """Test deleting temporary file."""
    # Create temp file
    temp_file = temp_upload_dir / "temp_to_delete.jpg"
    temp_file.write_text("temporary content")

    assert temp_file.exists()

    # Delete it
    await file_handler.delete_temp_file(temp_file)

    # Should be deleted
    assert not temp_file.exists()


@pytest.mark.asyncio
async def test_delete_temp_file_nonexistent(file_handler, temp_upload_dir):
    """Test that deleting non-existent file doesn't raise error."""
    nonexistent = temp_upload_dir / "does_not_exist.jpg"

    # Should not raise exception
    await file_handler.delete_temp_file(nonexistent)


@pytest.mark.asyncio
async def test_save_result(file_handler):
    """Test saving HOCR result."""
    job_id = "test_job_123"
    hocr_content = '<?xml version="1.0"?><html><body>Test HOCR</body></html>'

    result_path = await file_handler.save_result(job_id, hocr_content)

    # Should exist
    assert result_path.exists()
    assert result_path.is_file()
    # Should have .hocr extension
    assert result_path.suffix == ".hocr"
    # Should be in results directory
    assert result_path.parent == file_handler.results_dir
    # Content should match
    assert result_path.read_text() == hocr_content


@pytest.mark.asyncio
async def test_save_result_sets_permissions(file_handler):
    """Test that result files have restrictive permissions."""
    job_id = "test_job_permissions"
    hocr_content = "<html></html>"

    result_path = await file_handler.save_result(job_id, hocr_content)

    # Check permissions
    file_mode = os.stat(result_path).st_mode
    permissions = file_mode & 0o777

    # Should be 0o600
    assert permissions == 0o600


@pytest.mark.asyncio
async def test_read_result(file_handler):
    """Test reading HOCR result."""
    job_id = "test_job_read"
    original_content = '<?xml version="1.0"?><html><body>HOCR Result</body></html>'

    # Save result
    result_path = await file_handler.save_result(job_id, original_content)

    # Read it back
    read_content = await file_handler.read_result(result_path)

    assert read_content == original_content


@pytest.mark.asyncio
async def test_save_and_read_large_result(file_handler):
    """Test saving and reading large HOCR result."""
    job_id = "test_large_result"
    # Create large HOCR (1MB+)
    large_hocr = '<?xml version="1.0"?><html><body>'
    large_hocr += '<span class="word">TEST</span>' * 100000
    large_hocr += "</body></html>"

    # Save
    result_path = await file_handler.save_result(job_id, large_hocr)

    # Read back
    read_content = await file_handler.read_result(result_path)

    assert read_content == large_hocr
    assert len(read_content) > 1_000_000


@pytest.mark.asyncio
async def test_file_handler_directory_creation(temp_upload_dir, temp_results_dir, monkeypatch):
    """Test that FileHandler creates directories if they don't exist."""
    # Use non-existent directories
    new_upload_dir = temp_upload_dir / "new_uploads"
    new_results_dir = temp_results_dir / "new_results"

    monkeypatch.setenv("UPLOAD_DIR", str(new_upload_dir))
    monkeypatch.setenv("RESULTS_DIR", str(new_results_dir))

    import importlib

    import src.config

    importlib.reload(src.config)

    # Create handler - should create directories
    handler = FileHandler()

    assert handler.upload_dir.exists()
    assert handler.results_dir.exists()
    assert handler.upload_dir.is_dir()
    assert handler.results_dir.is_dir()


@pytest.mark.asyncio
async def test_file_handler_directory_permissions(file_handler):
    """Test that created directories have secure permissions."""
    # Check upload directory permissions
    upload_mode = os.stat(file_handler.upload_dir).st_mode
    upload_perms = upload_mode & 0o777
    assert upload_perms == 0o700  # Owner only

    # Check results directory permissions
    results_mode = os.stat(file_handler.results_dir).st_mode
    results_perms = results_mode & 0o777
    assert results_perms == 0o700  # Owner only


@pytest.mark.asyncio
async def test_save_upload_concurrent(file_handler, create_upload_file, sample_jpeg_bytes):
    """Test that concurrent uploads work correctly."""
    import asyncio

    # Create multiple upload tasks
    tasks = [
        file_handler.save_upload(create_upload_file(sample_jpeg_bytes, f"test_{i}.jpg"))
        for i in range(10)
    ]

    # Execute concurrently
    uploads = await asyncio.gather(*tasks)

    # All should succeed
    assert len(uploads) == 10
    # All should have unique paths
    paths = [u.temp_file_path for u in uploads]
    assert len(set(paths)) == 10
    # All files should exist
    assert all(p.exists() for p in paths)


@pytest.mark.asyncio
async def test_delete_temp_file_error_handling(file_handler, temp_upload_dir):
    """Test that delete_temp_file handles errors gracefully."""
    # Create file with restricted parent directory permissions
    restricted_dir = temp_upload_dir / "restricted"
    restricted_dir.mkdir()  # Create with normal permissions first

    problem_file = restricted_dir / "file.txt"
    problem_file.write_text("content")  # Create file

    # Make directory read-only (can't delete files)
    os.chmod(restricted_dir, 0o500)

    try:
        # Should not raise exception even if deletion fails
        await file_handler.delete_temp_file(problem_file)
    finally:
        # Restore permissions for cleanup
        os.chmod(restricted_dir, 0o700)


@pytest.mark.asyncio
async def test_save_upload_filename_with_unknown_extension(
    file_handler, create_upload_file, sample_jpeg_bytes
):
    """Test handling of files with unknown/no filename."""
    upload_file = create_upload_file(sample_jpeg_bytes, None)  # No filename

    upload = await file_handler.save_upload(upload_file)

    # Should still work and determine extension from MIME type
    assert upload.temp_file_path.exists()
    assert upload.file_name == "unknown"
    assert upload.temp_file_path.suffix == ".jpg"  # From JPEG magic bytes
