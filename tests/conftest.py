"""Pytest fixtures for testing the OCR API."""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from redis import asyncio as aioredis

from src.config import settings
from src.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create synchronous test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def redis_client() -> AsyncGenerator[aioredis.Redis, None]:
    """Create Redis client for testing."""
    client = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        await client.ping()
        yield client
    finally:
        await client.flushdb()  # Clean up test data
        await client.close()


@pytest.fixture
def temp_upload_dir() -> Generator[Path, None, None]:
    """Create temporary upload directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        upload_dir = Path(tmpdir) / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(upload_dir, 0o700)
        yield upload_dir


@pytest.fixture
def temp_results_dir() -> Generator[Path, None, None]:
    """Create temporary results directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        results_dir = Path(tmpdir) / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(results_dir, 0o700)
        yield results_dir


@pytest.fixture
def samples_dir() -> Path:
    """Get path to samples directory."""
    return Path(__file__).parent.parent / "samples"


@pytest.fixture
def sample_jpeg(samples_dir: Path) -> Path:
    """Get path to sample JPEG file."""
    return samples_dir / "numbers_gs150.jpg"


@pytest.fixture
def sample_png(samples_dir: Path) -> Path:
    """Get path to sample PNG file (using JPEG as substitute)."""
    return samples_dir / "stock_gs200.jpg"


@pytest.fixture
def sample_pdf(samples_dir: Path) -> Path:
    """Get path to sample PDF file."""
    return samples_dir / "mietvertrag.pdf"
