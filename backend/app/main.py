"""FastAPI main application entrypoint."""

from contextlib import asynccontextmanager
import logging
import time
from typing import AsyncGenerator
import uuid
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path

# Ensure project root and backend directories are in sys.path
_current_dir = Path(__file__).resolve().parent
_backend_dir = _current_dir.parent
_root_dir = _backend_dir.parent
for _p in [str(_root_dir), str(_backend_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

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

    # Pre-warm local Ollama model in memory in background so first user query has zero load delay
    import asyncio
    async def warmup_ollama():
        try:
            import httpx
            async with httpx.AsyncClient(timeout=35.0) as client:
                logger.info("Pre-warming Ollama model '%s' in memory...", settings.OLLAMA_DEFAULT_MODEL)
                await client.post(
                    f"{settings.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": settings.OLLAMA_DEFAULT_MODEL,
                        "prompt": "Hi",
                        "stream": False,
                        "keep_alive": -1,
                        "options": {"num_predict": 1, "num_ctx": 1024, "num_thread": 8},
                    },
                )
                logger.info("Ollama model '%s' is pre-warmed and resident in memory.", settings.OLLAMA_DEFAULT_MODEL)
        except Exception as e:
            logger.debug("Ollama warmup notice: %s", e)

    asyncio.create_task(warmup_ollama())

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


@app.get("/health", include_in_schema=False)
def health_alias():
    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/healthz")


@app.get("/api/v1/health", include_in_schema=False)
def api_v1_health_alias():
    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/healthz")


@app.get("/health/db", include_in_schema=False)
def health_db_alias():
    ok = ping_db()
    return {"status": "healthy" if ok else "unhealthy", "database": ok}


@app.get("/health/llm", include_in_schema=False)
def health_llm_alias():
    return {"status": "healthy", "providers": ["ollama", "gemini", "groq", "openai", "anthropic"]}


@app.get("/", tags=["Root"])
def root():
    """Root health and version metadata."""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs",
        "health_url": "/healthz",
    }
