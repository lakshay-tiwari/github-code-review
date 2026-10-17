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


class SearchRequest(BaseModel):
    """Schema for semantic code search request."""

    query: str = Field(description="Search query string")
    limit: int = Field(default=10, ge=1, le=50, description="Max results")
    score_threshold: float | None = Field(
        default=0.4, description="Minimum cosine similarity score"
    )


class SearchResultItem(BaseModel):
    """Schema for a single retrieved code chunk with citations."""

    chunk_id: str
    score: float
    file_path: str
    start_line: int
    end_line: int
    language: str
    symbol_name: str | None = None
    symbol_type: str | None = None
    content: str
    commit_sha: str


class SearchResponse(BaseModel):
    """Schema for semantic search response."""

    query: str
    repository_id: uuid.UUID
    commit_sha: str | None = None
    results: list[SearchResultItem]
    total: int
