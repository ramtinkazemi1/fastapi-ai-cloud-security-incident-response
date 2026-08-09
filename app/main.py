"""FastAPI application entry point and operational middleware."""

import logging
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, make_asgi_app
from sqlalchemy import text

from app.api.routes.alerts import router as alerts_router
from app.api.routes.auth import router as auth_router
from app.api.routes.incidents import audit_router
from app.api.routes.incidents import router as incidents_router
from app.core.config import get_settings
from app.core.rate_limit import RateLimiter
from app.db.session import engine

settings = get_settings()
logger = logging.getLogger("uvicorn.access")
rate_limiter = RateLimiter(
    requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)
request_count = Counter(
    "cir_http_requests_total",
    "HTTP requests handled by the API.",
    ["method", "route", "status"],
)
request_duration = Histogram(
    "cir_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "route"],
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Release pooled database connections during application shutdown."""
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
)

app.include_router(
    alerts_router,
    prefix=settings.api_v1_prefix,
)
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(incidents_router, prefix=settings.api_v1_prefix)
app.include_router(audit_router, prefix=settings.api_v1_prefix)
app.mount("/metrics", make_asgi_app())


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    """Attach a safe request ID and emit one completion log per request."""
    supplied_id = request.headers.get("X-Request-ID")
    try:
        request_id = str(UUID(supplied_id)) if supplied_id else str(uuid4())
    except ValueError:
        request_id = str(uuid4())

    if request.url.path.startswith(settings.api_v1_prefix):
        client = request.client.host if request.client else "unknown"
        retry_after = await rate_limiter.retry_after(client)
        if retry_after is not None:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={
                    "Retry-After": str(retry_after),
                    "X-Request-ID": request_id,
                },
            )

    started_at = perf_counter()
    response = await call_next(request)
    duration_seconds = perf_counter() - started_at
    duration_ms = round(duration_seconds * 1000, 2)
    route = request.scope.get("route")
    route_path = getattr(route, "path", request.url.path)
    request_count.labels(
        method=request.method,
        route=route_path,
        status=response.status_code,
    ).inc()
    request_duration.labels(
        method=request.method,
        route=route_path,
    ).observe(duration_seconds)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_complete method=%s path=%s status=%s duration_ms=%s request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    return response


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Confirm that the API process is running."""

    return {"status": "healthy"}


@app.get("/ready")
async def readiness_check() -> dict[str, str]:
    """Confirm that the API can execute a database query."""
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"status": "ready"}
