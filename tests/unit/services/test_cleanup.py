"""Unit tests for cleanup service.

Tests for background file cleanup including expired file deletion,
directory iteration, and error handling.
"""

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from src.services.cleanup import CleanupService


@pytest.fixture
def cleanup_service(temp_upload_dir, temp_results_dir, monkeypatch):
    """Create CleanupService with temporary directories."""
    monkeypatch.setenv("UPLOAD_DIR", str(temp_upload_dir))
    monkeypatch.setenv("RESULTS_DIR", str(temp_results_dir))
    monkeypatch.setenv("JOB_EXPIRATION_HOURS", "1")  # 1 hour expiration

    # Reload config to pick up new env vars
    import importlib

    from src import config
    from src.services import cleanup

    importlib.reload(config)
    # Also reload cleanup module to pick up new settings reference
    importlib.reload(cleanup)

    from src.services.cleanup import CleanupService

    service = CleanupService()
    return service


@pytest.mark.asyncio
async def test_cleanup_service_initialization(cleanup_service, temp_upload_dir, temp_results_dir):
    """Test that cleanup service initializes with correct directories."""
    assert cleanup_service.upload_dir == temp_upload_dir
    assert cleanup_service.results_dir == temp_results_dir
    assert cleanup_service.expiration_seconds == 3600  # 1 hour in seconds


@pytest.mark.asyncio
async def test_cleanup_expired_files_removes_old_files(cleanup_service, temp_upload_dir):
    """Test that expired files are deleted."""
    # Create old file (modify timestamp to 2 hours ago)
    old_file = temp_upload_dir / "old_upload.jpg"
    old_file.write_text("old content")

    # Set modification time to 2 hours ago
    two_hours_ago = time.time() - (2 * 3600)
    import os

    os.utime(old_file, (two_hours_ago, two_hours_ago))

    # Run cleanup
    await cleanup_service.cleanup_expired_files()

    # Old file should be deleted
    assert not old_file.exists()


@pytest.mark.asyncio
async def test_cleanup_keeps_recent_files(cleanup_service, temp_upload_dir):
    """Test that recent files are not deleted."""
    # Create recent file
    recent_file = temp_upload_dir / "recent_upload.jpg"
    recent_file.write_text("recent content")

    # Run cleanup
    await cleanup_service.cleanup_expired_files()

    # Recent file should still exist
    assert recent_file.exists()


@pytest.mark.asyncio
async def test_cleanup_both_directories(cleanup_service, temp_upload_dir, temp_results_dir):
    """Test that cleanup processes both upload and results directories."""
    # Create old files in both directories
    old_upload = temp_upload_dir / "old_upload.jpg"
    old_upload.write_text("old upload")

    old_result = temp_results_dir / "old_result.hocr"
    old_result.write_text("<html>old result</html>")

    # Set modification times to 2 hours ago
    two_hours_ago = time.time() - (2 * 3600)
    import os

    os.utime(old_upload, (two_hours_ago, two_hours_ago))
    os.utime(old_result, (two_hours_ago, two_hours_ago))

    # Run cleanup
    await cleanup_service.cleanup_expired_files()

    # Both old files should be deleted
    assert not old_upload.exists()
    assert not old_result.exists()


@pytest.mark.asyncio
async def test_cleanup_handles_file_deletion_errors(cleanup_service, temp_upload_dir):
    """Test graceful error handling when file deletion fails."""
    # Create file
    problem_file = temp_upload_dir / "problem.jpg"
    problem_file.write_text("content")

    # Set modification time to 2 hours ago
    two_hours_ago = time.time() - (2 * 3600)
    import os

    os.utime(problem_file, (two_hours_ago, two_hours_ago))

    # Mock unlink to raise exception
    original_unlink = Path.unlink

    def failing_unlink(self, *args, **kwargs):
        if self.name == "problem.jpg":
            raise PermissionError("Cannot delete file")
        return original_unlink(self, *args, **kwargs)

    with patch.object(Path, "unlink", failing_unlink):
        # Should not raise exception
        await cleanup_service.cleanup_expired_files()

    # File should still exist (deletion failed)
    assert problem_file.exists()


@pytest.mark.asyncio
async def test_cleanup_only_deletes_files_not_directories(cleanup_service, temp_upload_dir):
    """Test that cleanup only deletes files, not subdirectories."""
    # Create old subdirectory
    old_subdir = temp_upload_dir / "old_subdir"
    old_subdir.mkdir()

    # Set modification time to 2 hours ago
    two_hours_ago = time.time() - (2 * 3600)
    import os

    os.utime(old_subdir, (two_hours_ago, two_hours_ago))

    # Run cleanup
    await cleanup_service.cleanup_expired_files()

    # Directory should still exist (cleanup only handles files)
    assert old_subdir.exists()
    assert old_subdir.is_dir()


@pytest.mark.asyncio
async def test_cleanup_results_only_hocr_files(cleanup_service, temp_results_dir):
    """Test that results cleanup only deletes .hocr files."""
    # Create old .hocr file
    old_hocr = temp_results_dir / "old.hocr"
    old_hocr.write_text("<html></html>")

    # Create old non-hocr file
    old_other = temp_results_dir / "old.txt"
    old_other.write_text("text")

    # Set modification times to 2 hours ago
    two_hours_ago = time.time() - (2 * 3600)
    import os

    os.utime(old_hocr, (two_hours_ago, two_hours_ago))
    os.utime(old_other, (two_hours_ago, two_hours_ago))

    # Run cleanup
    await cleanup_service.cleanup_expired_files()

    # .hocr file should be deleted
    assert not old_hocr.exists()
    # Non-hocr file should remain (results cleanup is selective)
    assert old_other.exists()


@pytest.mark.asyncio
async def test_cleanup_with_no_files(cleanup_service):
    """Test cleanup with empty directories."""
    # Run cleanup on empty directories
    await cleanup_service.cleanup_expired_files()
    # Should complete without errors


@pytest.mark.asyncio
async def test_cleanup_mixed_old_and_recent_files(cleanup_service, temp_upload_dir):
    """Test cleanup with mix of old and recent files."""
    # Create old file
    old_file = temp_upload_dir / "old.jpg"
    old_file.write_text("old")

    # Create recent file
    recent_file = temp_upload_dir / "recent.jpg"
    recent_file.write_text("recent")

    # Set old file timestamp
    two_hours_ago = time.time() - (2 * 3600)
    import os

    os.utime(old_file, (two_hours_ago, two_hours_ago))

    # Run cleanup
    await cleanup_service.cleanup_expired_files()

    # Only old file should be deleted
    assert not old_file.exists()
    assert recent_file.exists()


@pytest.mark.asyncio
async def test_cleanup_expiration_threshold(cleanup_service, temp_upload_dir):
    """Test that cleanup respects expiration threshold exactly."""
    # Create file at exactly expiration time (1 hour + 1 second ago)
    expired_file = temp_upload_dir / "expired.jpg"
    expired_file.write_text("expired")

    # Create file just under expiration (1 hour - 1 second ago)
    not_expired_file = temp_upload_dir / "not_expired.jpg"
    not_expired_file.write_text("not expired")

    import os

    # 1 hour + 1 second ago (should be deleted)
    os.utime(expired_file, (time.time() - 3601, time.time() - 3601))

    # 1 hour - 1 second ago (should be kept)
    os.utime(not_expired_file, (time.time() - 3599, time.time() - 3599))

    # Run cleanup
    await cleanup_service.cleanup_expired_files()

    # Expired file should be deleted
    assert not expired_file.exists()
    # Not-yet-expired file should remain
    assert not_expired_file.exists()


@pytest.mark.asyncio
async def test_cleanup_service_custom_expiration():
    """Test cleanup service with custom expiration time."""
    from src.config import Settings

    # Create service with 24 hour expiration
    settings = Settings(job_expiration_hours=24)

    with patch("src.services.cleanup.settings", settings):
        service = CleanupService()

        # Should calculate 24 hours in seconds
        assert service.expiration_seconds == 24 * 3600


@pytest.mark.asyncio
async def test_cleanup_logs_deleted_count(cleanup_service, temp_upload_dir):
    """Test that cleanup logs the number of deleted files."""
    # Create multiple old files
    for i in range(3):
        old_file = temp_upload_dir / f"old_{i}.jpg"
        old_file.write_text(f"old {i}")

        two_hours_ago = time.time() - (2 * 3600)
        import os

        os.utime(old_file, (two_hours_ago, two_hours_ago))

    # Mock logger to capture log calls
    with patch("src.services.cleanup.logger") as mock_logger:
        await cleanup_service.cleanup_expired_files()

        # Should log cleanup completion with count
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "cleanup_completed" in call_args[0]
        assert call_args[1]["deleted_files"] == 3


@pytest.mark.asyncio
async def test_cleanup_no_log_when_nothing_deleted(cleanup_service, temp_upload_dir):
    """Test that cleanup doesn't log when no files are deleted."""
    # Create recent file
    recent_file = temp_upload_dir / "recent.jpg"
    recent_file.write_text("recent")

    # Mock logger
    with patch("src.services.cleanup.logger") as mock_logger:
        await cleanup_service.cleanup_expired_files()

        # Should not log info (nothing deleted)
        mock_logger.info.assert_not_called()
