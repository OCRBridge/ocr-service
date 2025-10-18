"""Background cleanup service for expired files and Redis keys."""

import time
from pathlib import Path

import structlog

from src.config import settings

logger = structlog.get_logger()


class CleanupService:
    """Handles cleanup of expired temporary files and results."""

    def __init__(self):
        """Initialize cleanup service."""
        self.upload_dir = Path(settings.upload_dir)
        self.results_dir = Path(settings.results_dir)
        self.expiration_seconds = settings.job_expiration_hours * 3600

    async def cleanup_expired_files(self) -> None:
        """Delete files older than expiration time."""
        current_time = time.time()
        deleted_count = 0

        # Clean upload directory
        for file_path in self.upload_dir.glob("*"):
            if file_path.is_file():
                age = current_time - file_path.stat().st_mtime
                if age > self.expiration_seconds:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception as e:
                        logger.error("cleanup_failed", path=str(file_path), error=str(e))

        # Clean results directory
        for file_path in self.results_dir.glob("*.hocr"):
            if file_path.is_file():
                age = current_time - file_path.stat().st_mtime
                if age > self.expiration_seconds:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception as e:
                        logger.error("cleanup_failed", path=str(file_path), error=str(e))

        if deleted_count > 0:
            logger.info("cleanup_completed", deleted_files=deleted_count)
