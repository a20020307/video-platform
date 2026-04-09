import logging
import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.database import create_tables, init_engine
from app.routers import auth, videos, upload, admin
from app.utils.rate_limit import limiter

settings = get_settings()

# ── Structured logging ────────────────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)
logger = structlog.get_logger()

# ── Prometheus metrics ─────────────────────────────────────────────────────────
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_engine(settings.DATABASE_URL, echo=settings.DEBUG)
    await create_tables()
    logger.info("startup", app=settings.APP_NAME)
    yield
    # Shutdown
    logger.info("shutdown")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_and_metrics(request: Request, call_next):
    start = time.perf_counter()
    response: Response = await call_next(request)
    duration = time.perf_counter() - start

    endpoint = request.url.path
    REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
    REQUEST_LATENCY.labels(request.method, endpoint).observe(duration)

    logger.info(
        "request",
        method=request.method,
        path=endpoint,
        status=response.status_code,
        duration_ms=round(duration * 1000, 2),
    )
    return response


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(videos.router)
app.include_router(upload.router)
app.include_router(admin.router)


@app.get("/health", tags=["ops"])
async def health():
    return {"status": "ok"}


@app.get("/metrics", tags=["ops"])
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
