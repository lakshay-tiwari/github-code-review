from fastapi import APIRouter
from pydantic import BaseModel

from app import __version__
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.jobs import router as jobs_router
from app.api.v1.endpoints.repositories import router as repositories_router
from app.core.config import settings

api_v1_router = APIRouter()

# Register sub-routers
api_v1_router.include_router(auth_router)
api_v1_router.include_router(repositories_router)
api_v1_router.include_router(jobs_router)


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str


@api_v1_router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check the operational health of the Cortex API backend.",
    tags=["System"],
)
async def health_check() -> HealthResponse:
    """Return application operational status."""
    return HealthResponse(
        status="ok",
        app=settings.APP_NAME,
        version=__version__,
        environment=settings.APP_ENV,
    )

