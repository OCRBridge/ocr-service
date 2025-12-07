import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.routes.v2.dynamic_routes import register_engine_routes
from src.services.ocr.registry_v2 import EngineRegistry

# ==============================================================================
# Resilience Tests (Timeouts, Circuit Breaker)
# ==============================================================================


@pytest.mark.asyncio
async def test_process_timeout_returns_504(app):
    """Test that OCR processing timeout returns 504 Gateway Timeout."""

    # Create a mock engine that simulates a timeout
    mock_engine = MagicMock()
    mock_engine.name = "slow_engine"
    mock_engine.supported_formats = {".jpg"}

    # process method that sleeps longer than timeout
    # Note: We mock asyncio.wait_for behavior by making the side_effect raise TimeoutError
    # or by relying on the actual timeout logic if we can control time.
    # Easiest is to mock the engine's process to be slow and let the real wait_for hit.
    # But wait_for wraps a thread run.

    # Let's mock the asyncio.wait_for in dynamic_routes.py directly to raise TimeoutError
    # This is more robust than relying on sleep timing in unit tests.

    with patch(
        "src.api.routes.v2.dynamic_routes.asyncio.wait_for", side_effect=asyncio.TimeoutError
    ):
        # Setup registry
        registry = EngineRegistry()
        registry.inject_engine_instance("slow_engine", mock_engine)
        registry.inject_engine_class("slow_engine", MagicMock)

        # Manually register routes
        register_engine_routes(app, registry)

        # Override dependency
        app.state.engine_registry = registry

        client = TestClient(app)

        # Prepare file
        files = {"file": ("test.jpg", b"fake content", "image/jpeg")}

        response = client.post("/v2/ocr/slow_engine/process", files=files)

        assert response.status_code == 504
        assert "timeout" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_circuit_breaker_open_returns_503(app):
    """Test that open circuit breaker returns 503 Service Unavailable."""

    mock_engine = MagicMock()
    mock_engine.name = "broken_engine"
    mock_engine.supported_formats = {".jpg"}

    registry = EngineRegistry()
    registry.inject_engine_instance("broken_engine", mock_engine)
    registry.inject_engine_class("broken_engine", MagicMock)

    # Mock is_engine_available to return False
    # We can't easily patch the instance method on the *instance* we just created if the route uses a dependency
    # that fetches it.
    # But we can patch the registry instance method.

    with patch.object(registry, "is_engine_available", return_value=False):
        register_engine_routes(app, registry)
        app.state.engine_registry = registry

        client = TestClient(app)
        files = {"file": ("test.jpg", b"fake content", "image/jpeg")}

        response = client.post("/v2/ocr/broken_engine/process", files=files)

        assert response.status_code == 503
        assert "temporarily unavailable" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_generic_exception_returns_500(app):
    """Test that unexpected errors return 500 Internal Server Error."""

    mock_engine = MagicMock()
    mock_engine.name = "exploding_engine"
    mock_engine.supported_formats = {".jpg"}
    mock_engine.process.side_effect = RuntimeError("Unexpected boom")

    registry = EngineRegistry()
    registry.inject_engine_instance("exploding_engine", mock_engine)
    registry.inject_engine_class("exploding_engine", MagicMock)

    register_engine_routes(app, registry)
    app.state.engine_registry = registry

    client = TestClient(app)
    files = {"file": ("test.jpg", b"fake content", "image/jpeg")}

    response = client.post("/v2/ocr/exploding_engine/process", files=files)

    assert response.status_code == 500
    assert "unexpected error" in response.json()["detail"].lower()


# ==============================================================================
# Route Registration Tests
# ==============================================================================


def test_route_registration_collision(app):
    """Test that registering routes twice doesn't crash (idempotency)."""

    mock_engine = MagicMock()
    mock_engine.name = "dup_engine"
    mock_engine.supported_formats = {".jpg"}

    registry = EngineRegistry()
    registry.inject_engine_instance("dup_engine", mock_engine)
    registry.inject_engine_class("dup_engine", MagicMock)

    # First registration
    register_engine_routes(app, registry)

    # Verify route exists
    routes_v1 = [r.path for r in app.router.routes]
    assert "/v2/ocr/dup_engine/process" in routes_v1

    # Second registration
    try:
        register_engine_routes(app, registry)
    except Exception as e:
        pytest.fail(f"Second registration raised exception: {e}")

    # Verify no duplicate routes (FastAPI APIRouter handles this or our logic should skip)
    # Our logic in dynamic_routes.py checks existing_paths

    # Count occurrences
    routes_v2 = [r.path for r in app.router.routes]
    count = routes_v2.count("/v2/ocr/dup_engine/process")

    # Should be 1 if our collision detection works
    assert count == 1
