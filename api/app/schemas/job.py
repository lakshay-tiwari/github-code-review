import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IngestionJobResponse(BaseModel):
    """Schema for ingestion job status responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    status: str
    progress: int
    current_step: str | None = None
    attempts: int
    max_attempts: int
    commit_sha: str | None = None
    error_details: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
