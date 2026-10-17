import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1.router import HealthResponse, api_v1_router
from app.core.config import settings
from app.infrastructure.checkpoint import close_checkpointer_pool

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for startup and shutdown."""
    # Startup: Initialize resources (DB connections, caches, etc.)
    if settings.LANGSMITH_TRACING and settings.LANGSMITH_API_KEY:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
        os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
        os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
        logger.info(
            "LangSmith tracing enabled for project '%s'",
            settings.LANGSMITH_PROJECT,
        )
    else:
        os.environ["LANGSMITH_TRACING"] = "false"

    yield
    # Shutdown: Clean up resources
    await close_checkpointer_pool()




app = FastAPI(
    title="Cortex API",
    description="Backend service and shared core for Cortex GitHub Codebase RAG",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 router under /api/v1
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Root Health Check",
    tags=["System"],
)
async def root_health() -> HealthResponse:
    """Convenience health check at the root level."""
    return HealthResponse(
        status="ok",
        app=settings.APP_NAME,
        version=__version__,
        environment=settings.APP_ENV,
    )


@app.get("/", tags=["System"])
async def root():
    """Service root endpoint."""
    return {
        "app": settings.APP_NAME,
        "version": __version__,
        "status": "operational",
        "docs": "/docs",
    }
