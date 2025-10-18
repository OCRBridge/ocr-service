"""File handling service for streaming uploads and temp file management."""

import os
import uuid
from pathlib import Path

import aiofiles
import structlog
from fastapi import UploadFile

from src.config import settings
from src.models.upload import DocumentUpload, FileFormat
from src.utils.validators import validate_upload_file

logger = structlog.get_logger()


class FileHandler:
    """Manages temporary file uploads and cleanup."""

    def __init__(self):
        """Initialize file handler."""
        self.upload_dir = Path(settings.upload_dir)
        self.results_dir = Path(settings.results_dir)

        # Ensure directories exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Set permissions
        os.chmod(self.upload_dir, 0o700)
        os.chmod(self.results_dir, 0o700)

    async def save_upload(self, file: UploadFile) -> DocumentUpload:
        """
        Save uploaded file to temp directory with streaming.

        Args:
            file: FastAPI UploadFile instance

        Returns:
            DocumentUpload model with file metadata

        Raises:
            UnsupportedFormatError: If file format not supported
            FileTooLargeError: If file too large
        """
        # Validate file
        mime_type, file_size = validate_upload_file(file.file)

        # Generate unique filename
        file_id = uuid.uuid4()
        extension = self._get_extension(mime_type)
        temp_filename = f"{file_id}{extension}"
        temp_path = self.upload_dir / temp_filename

        # Stream file to disk
        chunk_size = 8192
        bytes_written = 0

        async with aiofiles.open(temp_path, "wb") as f:
            while chunk := await file.read(chunk_size):
                await f.write(chunk)
                bytes_written += len(chunk)

        # Set file permissions
        os.chmod(temp_path, 0o600)

        logger.info(
            "file_saved",
            filename=file.filename,
            size=file_size,
            mime_type=mime_type,
            temp_path=str(temp_path),
        )

        return DocumentUpload(
            file_name=file.filename or "unknown",
            file_format=FileFormat(mime_type),
            file_size=file_size,
            content_type=mime_type,
            temp_file_path=temp_path,
        )

    async def delete_temp_file(self, file_path: Path) -> None:
        """
        Delete temporary upload file.

        Args:
            file_path: Path to file to delete
        """
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info("temp_file_deleted", path=str(file_path))
        except Exception as e:
            logger.error("temp_file_deletion_failed", path=str(file_path), error=str(e))

    async def save_result(self, job_id: str, hocr_content: str) -> Path:
        """
        Save HOCR result to results directory.

        Args:
            job_id: Job identifier
            hocr_content: HOCR XML content

        Returns:
            Path to saved result file
        """
        result_filename = f"{job_id}.hocr"
        result_path = self.results_dir / result_filename

        async with aiofiles.open(result_path, "w") as f:
            await f.write(hocr_content)

        # Set file permissions
        os.chmod(result_path, 0o600)

        logger.info("result_saved", job_id=job_id, path=str(result_path))

        return result_path

    async def read_result(self, file_path: Path) -> str:
        """
        Read HOCR result file.

        Args:
            file_path: Path to result file

        Returns:
            HOCR content string
        """
        async with aiofiles.open(file_path) as f:
            return await f.read()

    def _get_extension(self, mime_type: str) -> str:
        """Get file extension from MIME type."""
        extensions = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "application/pdf": ".pdf",
            "image/tiff": ".tiff",
        }
        return extensions.get(mime_type, ".bin")
