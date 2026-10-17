from fastapi import APIRouter, Depends

from app.api.deps import require_job_ownership
from app.domain.models import IngestionJob
from app.schemas.job import IngestionJobResponse

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get(
    "/{job_id}",
    response_model=IngestionJobResponse,
    summary="Get Ingestion Job Status",
    description="Retrieve the current status, progress, and stage of an indexing job.",
)
async def get_job_status(
    job: IngestionJob = Depends(require_job_ownership),
) -> IngestionJobResponse:
    """Retrieve detailed job status strictly scoped by user repository ownership."""
    return IngestionJobResponse.model_validate(job)
