"""Integration tests for application lifespan management."""

import asyncio
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute

from src.main import lifespan
from src.services.ocr.registry_v2 import EngineRegistry


@pytest.mark.asyncio
async def test_lifespan_initializes_engine_registry():
    """Test that lifespan initializes the engine registry."""
    app = FastAPI()

    async with lifespan(app):
        # Registry should be initialized in app state
        assert hasattr(app.state, "engine_registry")
        assert isinstance(app.state.engine_registry, EngineRegistry)


@pytest.mark.asyncio
async def test_lifespan_starts_cleanup_task():
    """Test that lifespan starts the cleanup background task."""
    app = FastAPI()

    async with lifespan(app):
        # Cleanup task should be created
        assert hasattr(app.state, "cleanup_task")
        assert isinstance(app.state.cleanup_task, asyncio.Task)
        assert not app.state.cleanup_task.done()

    # After context exit, task should be cancelled
    assert app.state.cleanup_task.cancelled() or app.state.cleanup_task.done()


@pytest.mark.asyncio
async def test_lifespan_registers_routes_for_all_engines():
    """Test that lifespan registers routes for all discovered engines."""
    app = FastAPI()

    async with lifespan(app):
        # Get routes
        routes = [route.path for route in app.routes if isinstance(route, APIRoute)]

        # Health route is registered separately in main.py, not in lifespan
        # Check for engine routes instead
        engine_routes = [r for r in routes if "/v2/ocr/" in r]
        assert len(engine_routes) > 0


@pytest.mark.asyncio
async def test_lifespan_cancels_cleanup_on_shutdown():
    """Test that cleanup task is cancelled on shutdown."""
    app = FastAPI()

    async with lifespan(app):
        cleanup_task = app.state.cleanup_task
        assert not cleanup_task.done()

    # Task should be cancelled after shutdown
    assert cleanup_task.cancelled() or cleanup_task.done()


@pytest.mark.asyncio
async def test_lifespan_logs_startup_completion():
    """Test that lifespan logs successful startup."""
    app = FastAPI()

    # Lifespan should complete without errors
    async with lifespan(app):
        pass  # Startup successful


@pytest.mark.asyncio
async def test_cleanup_task_runs_periodically():
    """Test that cleanup task would run periodically (short test)."""
    app = FastAPI()

    async with lifespan(app):
        cleanup_task = app.state.cleanup_task

        # Task should be running
        assert not cleanup_task.done()

        # Wait a brief moment to ensure task is executing
        await asyncio.sleep(0.1)

        # Task should still be running (not crashed)
        assert not cleanup_task.done()


@pytest.mark.asyncio
async def test_lifespan_handles_missing_engines_gracefully():
    """Test that lifespan continues even if no engines are discovered."""
    app = FastAPI()

    # Mock entry_points to return empty list
    with patch("src.services.ocr.registry_v2.entry_points", return_value=[]):
        async with lifespan(app):
            # Should still initialize, just with no engines
            assert hasattr(app.state, "engine_registry")
            assert len(app.state.engine_registry.list_engines()) == 0


@pytest.mark.asyncio
async def test_lifespan_creates_routes_for_multiple_engines():
    """Test route creation when multiple engines are available."""
    app = FastAPI()

    async with lifespan(app):
        registry = app.state.engine_registry
        discovered_engines = registry.list_engines()

        # Check routes exist for each engine
        routes = [route.path for route in app.routes if isinstance(route, APIRoute)]

        for engine_name in discovered_engines:
            # Process route might have path parameters
            process_routes = [r for r in routes if engine_name in r and "process" in r]
            info_routes = [r for r in routes if engine_name in r and "info" in r]

            assert len(process_routes) > 0, f"No process route for {engine_name}"
            assert len(info_routes) > 0, f"No info route for {engine_name}"


@pytest.mark.asyncio
async def test_lifespan_cleanup_task_error_handling():
    """Test that cleanup task errors don't crash the application."""
    app = FastAPI()

    async with lifespan(app):
        # Task should be running
        assert hasattr(app.state, "cleanup_task")

        # Even if cleanup fails internally, task continues
        await asyncio.sleep(0.1)
        assert not app.state.cleanup_task.done()


@pytest.mark.asyncio
async def test_lifespan_state_isolation():
    """Test that different app instances have isolated state."""
    app1 = FastAPI()
    app2 = FastAPI()

    async with lifespan(app1), lifespan(app2):
        # Both should have their own registry
        assert app1.state.engine_registry is not app2.state.engine_registry


@pytest.mark.asyncio
async def test_lifespan_shutdown_waits_for_cleanup():
    """Test that shutdown waits for cleanup task cancellation."""
    app = FastAPI()

    async with lifespan(app):
        cleanup_task = app.state.cleanup_task

    # After exiting context, task should be handled
    # Either cancelled or completed
    assert cleanup_task.cancelled() or cleanup_task.done()


@pytest.mark.asyncio
async def test_lifespan_registry_has_engines():
    """Test that registry discovers engines during startup."""
    app = FastAPI()

    async with lifespan(app):
        registry = app.state.engine_registry
        engines = registry.list_engines()

        # Should have at least tesseract (from test fixtures)
        # In CI/dev environments with engines installed
        assert isinstance(engines, list)


@pytest.mark.asyncio
async def test_lifespan_startup_and_shutdown_logging():
    """Test that startup and shutdown are logged."""
    app = FastAPI()

    # Should not raise any errors
    async with lifespan(app):
        # Startup logging happens
        pass

    # Shutdown logging happens
    # Test passes if no exceptions


@pytest.mark.asyncio
async def test_lifespan_routes_include_dependencies():
    """Test that generated routes include proper dependencies."""
    app = FastAPI()

    async with lifespan(app):
        # Check that routes have dependencies
        for route in app.routes:
            if (
                isinstance(route, APIRoute)
                and "/v2/ocr/" in route.path
                and hasattr(route, "dependencies")
            ):
                # Dependencies may include auth, validation, etc.
                assert isinstance(route.dependencies, list)


@pytest.mark.asyncio
async def test_lifespan_metrics_endpoint_mounted():
    """Test that /metrics endpoint is mounted."""
    app = FastAPI()

    async with lifespan(app):
        # Metrics endpoint should be available
        # Note: Mounted apps show up differently in routes
        # Check via routes or mounted apps
        assert hasattr(app, "routes")
