"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.v1.monitoring import router as monitoring_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.middleware.metrics import MetricsMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.services.background import background_manager
from app.ui import UI_HTML


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Handle application startup and shutdown concerns."""
    settings = get_settings()
    logger = get_logger(__name__)
    logger.info(
        "Starting %s version=%s environment=%s",
        settings.app_name,
        settings.app_version,
        settings.environment,
    )
    background_manager.configure(settings.background_worker_count, settings.background_queue_size)
    await background_manager.start()
    logger.info("background worker pool started", extra={"worker_count": settings.background_worker_count})
    try:
        yield
    finally:
        await background_manager.stop()
        from app.database.session import engine
        await engine.dispose()
        logger.info("Shutting down %s", settings.app_name)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RateLimitMiddleware, max_requests=settings.rate_limit_requests, window_seconds=settings.rate_limit_window_seconds)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    app.include_router(monitoring_router, prefix=settings.api_v1_prefix)

    @app.get("/ui", response_class=HTMLResponse, tags=["UI"], include_in_schema=False)
    async def web_ui() -> HTMLResponse:
        return HTMLResponse(content=UI_HTML)

    @app.get("/", tags=["System"])
    async def root(request: Request) -> Any:
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return HTMLResponse(content=UI_HTML)
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "status": "ok",
        }

    return app


app = create_app()
