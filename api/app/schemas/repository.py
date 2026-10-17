import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.job import IngestionJobResponse


class RepositoryCreate(BaseModel):
    """Schema for repository submission request."""

    github_url: str = Field(
        description="Public GitHub repository URL (e.g. https://github.com/psf/requests)",
        examples=["https://github.com/fastapi/fastapi"],
    )


class RepositoryResponse(BaseModel):
    """Schema for repository details and indexing status."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: str
    github_url: str
    owner: str
    name: str
    default_branch: str
    latest_commit_sha: str | None = None
    status: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    latest_job: IngestionJobResponse | None = None


class RepositoryListResponse(BaseModel):
    """Schema for paginated/listed repositories."""

    repositories: list[RepositoryResponse]
    total: int
