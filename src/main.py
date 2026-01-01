"""FastAPI application entry point with lifecycle management."""

import asyncio
import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.api.middleware.error_handler import add_exception_handlers
from src.api.middleware.logging import LoggingMiddleware
from src.api.routes import health
from src.api.routes.v2.dynamic_routes import register_engine_routes
from src.config import settings
from src.services.cleanup import CleanupService
from src.services.ocr.registry_v2 import EngineRegistry

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

# Initialize rate limiter (conditionally used based on settings)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.rate_limit_default] if settings.rate_limit_enabled else [],
    storage_uri=settings.rate_limit_storage_uri,
)

# Warn about multi-worker deployments with in-memory rate limiting
if (
    settings.rate_limit_enabled
    and settings.api_workers > 1
    and settings.rate_limit_storage_uri == "memory://"
):
    logger.warning(
        "rate_limiter_multi_worker_warning",
        workers=settings.api_workers,
        storage_uri=settings.rate_limit_storage_uri,
        message="In-memory rate limiting is not shared across workers. Use Redis for accurate limiting.",
    )


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
    logger.info("application_starting", version="2.0.0")

    # Initialize EngineRegistry with entry point discovery
    registry = EngineRegistry()
    app.state.engine_registry = registry

    # Log discovered engines
    discovered_engines = registry.list_engines()
    logger.info(
        "ocr_engines_discovered",
        discovered_engines=discovered_engines,
        count=len(discovered_engines),
    )

    # Dynamically register engine routes
    register_engine_routes(app, registry)

    # Start cleanup background task
    cleanup_task = asyncio.create_task(cleanup_task_runner())
    app.state.cleanup_task = cleanup_task

    logger.info("application_ready")

    yield

    # Shutdown
    logger.info("application_shutting_down")

    # Cancel cleanup task with timeout to ensure graceful shutdown
    cleanup_task.cancel()
    try:
        # Wait up to 5 seconds for cleanup task to finish
        await asyncio.wait_for(cleanup_task, timeout=5.0)
    except asyncio.CancelledError:
        logger.debug("cleanup_task_cancelled_successfully")
    except asyncio.TimeoutError:
        logger.warning(
            "cleanup_task_shutdown_timeout", message="Cleanup task did not finish within 5 seconds"
        )

    logger.info("application_shutdown_complete")


# Create FastAPI application
app = FastAPI(
    title="RESTful OCR API",
    description="OCR document processing service with modular engine architecture",
    version="2.0.0",
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(LoggingMiddleware)  # type: ignore[reportInvalidArgumentType]

# Add rate limiting (disabled in test mode)
if settings.rate_limit_enabled and not settings.testing:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore
    logger.info(
        "rate_limiting_enabled",
        default_limit=settings.rate_limit_default,
        ocr_process_limit=settings.rate_limit_ocr_process,
        ocr_info_limit=settings.rate_limit_ocr_info,
    )
elif settings.testing:
    logger.info("rate_limiting_disabled_testing_mode")
else:
    logger.warning(
        "rate_limiting_disabled",
        message="Rate limiting is disabled - not recommended for production",
    )

# Add CORS middleware if enabled
if settings.cors_enabled:
    origins = []
    if settings.cors_origins:
        if settings.cors_origins == "*":
            origins = ["*"]
        else:
            origins = [
                origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()
            ]

    logger.info(
        "cors_enabled",
        origins=origins if origins != ["*"] else ["* (all origins)"],
        allow_credentials=settings.cors_allow_credentials,
    )

    app.add_middleware(
        CORSMiddleware,  # type: ignore[reportInvalidArgumentType]
        allow_origins=origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST"],  # Only allow needed methods
        allow_headers=["Content-Type", settings.api_key_header_name],  # Explicit headers
        max_age=3600,  # Cache preflight for 1 hour
    )

# Add exception handlers
add_exception_handlers(app)

# Mount Prometheus metrics at /metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Register health routes
app.include_router(health.router, tags=["health"])
