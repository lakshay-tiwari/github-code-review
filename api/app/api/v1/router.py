from fastapi import APIRouter
from pydantic import BaseModel

from app import __version__
from app.core.config import settings

api_v1_router = APIRouter()


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
