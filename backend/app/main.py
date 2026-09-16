"""FastAPI main application entrypoint."""

from contextlib import asynccontextmanager
import logging
import time
from typing import AsyncGenerator
import uuid
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.routes import router as api_router
from backend.app.core.config import settings
from backend.app.core.llm_bridge import LLMBridgeError
from backend.app.db.session import init_db, ping_db

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("lenny_growth_api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager to verify database and services on startup."""
    logger.info("Initializing Lenny Growth Assistant API (%s)...", settings.VERSION)
    try:
        init_db(max_retries=2, initial_backoff=0.5)
        if ping_db():
            logger.info("Database connectivity established and verified.")
        else:
            logger.warning("Database ping returned False. Running in degraded state.")
    except Exception as err:
        logger.warning(
            "Could not connect to PostgreSQL on startup (%s). "
            "Routes requiring DB will retry or use fallback.",
            err,
        )

    yield

    logger.info("Shutting down Lenny Growth Assistant API.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API for Lenny Growth Assistant with Dual-LLM Bridge and Vector Retrieval",
    lifespan=lifespan,
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def structured_logging_middleware(request: Request, call_next):
    """Middleware capturing request telemetry, generating X-Request-ID, and logging latency."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start_time = time.time()

    response = await call_next(request)

    duration_ms = round((time.time() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = request_id

    logger.info(
        "HTTP_REQUEST: request_id=%s method=%s path=%s status=%d duration_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# Global Exception Handler for LLM Bridge Errors
@app.exception_handler(LLMBridgeError)
async def llm_bridge_exception_handler(request: Request, exc: LLMBridgeError) -> JSONResponse:
    """Handle custom LLM errors and map to clean JSON error payloads."""
    logger.error("LLMBridgeError captured on %s: %s", request.url.path, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "status_code": exc.status_code,
        },
    )


# Register API router
app.include_router(api_router)


@app.get("/", tags=["Root"])
def root():
    """Root health and version metadata."""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs",
        "health_url": "/healthz",
    }
