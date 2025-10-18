"""FastAPI application entry point with lifecycle management."""

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from prometheus_client import make_asgi_app
from redis import asyncio as aioredis

from src.api.middleware.error_handler import add_exception_handlers
from src.api.middleware.logging import LoggingMiddleware
from src.config import settings
from src.models.job import EngineType
from src.services.cleanup import CleanupService
from src.services.ocr.registry import EngineRegistry

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
        if settings.log_format == "json"
        else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(settings.log_level)),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


async def cleanup_task_runner():
    """Background task to periodically clean expired files."""
    cleanup_service = CleanupService()
    logger.info("cleanup_task_started", interval_hours=1)

    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            await cleanup_service.cleanup_expired_files()
        except asyncio.CancelledError:
            logger.info("cleanup_task_cancelled")
            break
        except Exception as e:
            logger.error("cleanup_task_error", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    logger.info("application_starting", version="1.0.0")

    # Initialize EngineRegistry (detect OCR engines at startup)
    registry = EngineRegistry()
    app.state.engine_registry = registry
    logger.info(
        "engine_registry_initialized",
        tesseract_available=registry.is_available(EngineType.TESSERACT),
        ocrmac_available=registry.is_available(EngineType.OCRMAC),
    )

    # Initialize Redis connection
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    app.state.redis = redis_client

    # Verify Redis connection
    try:
        await redis_client.ping()
        logger.info("redis_connected", url=settings.redis_url)
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))
        raise

    # Start cleanup background task (US3 - T096)
    cleanup_task = asyncio.create_task(cleanup_task_runner())
    app.state.cleanup_task = cleanup_task

    logger.info("application_ready")

    yield

    # Shutdown
    logger.info("application_shutting_down")

    # Cancel cleanup task
    cleanup_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await cleanup_task

    await redis_client.close()
    logger.info("application_shutdown_complete")


# Create FastAPI application
app = FastAPI(
    title="RESTful OCR API",
    description="OCR document processing service with HOCR output",
    version="1.0.0",
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(LoggingMiddleware)

# Add exception handlers
add_exception_handlers(app)

# Mount Prometheus metrics at /metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# Import and register routes
from src.api.routes import health, jobs, upload  # noqa: E402

app.include_router(upload.router, tags=["upload"])
app.include_router(jobs.router, tags=["jobs"])
app.include_router(health.router, tags=["health"])
