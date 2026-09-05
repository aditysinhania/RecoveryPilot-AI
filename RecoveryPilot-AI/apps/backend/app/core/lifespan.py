"""Application factory, lifespan, and exception handlers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_v1_router
from app.config.constants import (
    API_DESCRIPTION,
    API_DOCS_URL,
    API_OPENAPI_URL,
    API_PREFIX,
    API_REDOC_URL,
    API_TITLE,
    OPENAPI_TAGS,
)
from app.config.environment import validate_environment
from app.config.logging import configure_logging, get_logger
from app.config.settings import settings
from app.core.exceptions import ApplicationException, DatabaseUnavailableError
from app.core.metrics import render_metrics
from app.core.middleware import register_middleware
from app.core.responses import error_response
from app.core.scheduler_worker import start_scheduler, stop_scheduler
from app.core.sentry import init_sentry
from app.db.health import ping_database
from app.db.session import dispose_engine, get_engine
from app.utils.json import redact_mapping
from app.utils.request_id import get_correlation_id, get_request_id

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Startup: validate env, pool the engine, ping Postgres. Shutdown: dispose."""
    configure_logging()
    init_sentry(settings)
    validate_environment(settings)
    public_meta = redact_mapping(
        {
            "app_name": settings.app_name,
            "app_env": settings.app_env,
            "api_version": settings.api_version,
            "log_level": settings.log_level,
        }
    )
    logger.info("app.startup", extra=public_meta)
    database_ok = False
    try:
        get_engine()
        database_ok = ping_database()
    except Exception as exc:
        logger.warning(
            "app.startup.database.failed",
            extra={"error_type": type(exc).__name__},
        )
    if database_ok:
        logger.info("app.startup.database.ok")
    elif settings.is_production:
        raise DatabaseUnavailableError("PostgreSQL connectivity check failed")
    else:
        logger.warning("app.startup.database.skipped")
    start_scheduler(settings, database_ok=database_ok)
    yield
    stop_scheduler()
    dispose_engine()
    logger.info("app.shutdown")


def register_exception_handlers(app: FastAPI) -> None:
    """Map domain errors onto the standard JSON error envelope."""

    @app.exception_handler(ApplicationException)
    async def _app_exc(_request: Request, exc: ApplicationException) -> object:
        logger.warning(
            "app.error",
            extra={
                "code": exc.code,
                "status_code": exc.status_code,
                "request_id": get_request_id(),
                "correlation_id": get_correlation_id(),
            },
        )
        return error_response(exc.message, exc.code, exc.status_code)

    @app.exception_handler(StarletteHTTPException)
    async def _http_exc(_request: Request, exc: StarletteHTTPException) -> object:
        return error_response(str(exc.detail), "http_error", exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _valid_exc(_request: Request, exc: RequestValidationError) -> object:
        return error_response(str(exc.errors()), "validation_error", 422)

    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, exc: Exception) -> object:
        logger.error(
            "app.unhandled",
            extra={
                "error_type": type(exc).__name__,
                "request_id": get_request_id(),
                "correlation_id": get_correlation_id(),
            },
            exc_info=exc,
        )
        return error_response("Internal server error", "internal_error", 500)


def create_app() -> FastAPI:
    """Build the FastAPI application. Callers must not instantiate FastAPI elsewhere."""
    configure_logging()
    app = FastAPI(
        title=API_TITLE,
        description=API_DESCRIPTION,
        version=settings.api_version,
        docs_url=API_DOCS_URL,
        redoc_url=API_REDOC_URL,
        openapi_url=API_OPENAPI_URL,
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    register_middleware(app, settings)
    register_exception_handlers(app)
    app.include_router(api_v1_router, prefix=API_PREFIX)

    @app.get("/metrics", include_in_schema=False)
    def prometheus_metrics() -> Response:
        """Prometheus scrape endpoint. Plain text, not the JSON envelope."""
        body, content_type = render_metrics()
        return Response(content=body, media_type=content_type)

    logger.info(
        "app.created",
        extra={"app_name": settings.app_name, "api_prefix": API_PREFIX},
    )
    return app
