import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db, require_repository_ownership
from app.core.security import UserContext
from app.domain.models import IngestionJob, Repository
from app.infrastructure.graph.factory import get_graph_store
from app.infrastructure.vector.factory import get_vector_store
from app.schemas.job import IngestionJobResponse
from app.schemas.repository import (
    RepositoryCreate,
    RepositoryListResponse,
    RepositoryResponse,
)
from app.services.github import GitHubError, GitHubService
from app.workers.tasks import enqueue_index_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repositories", tags=["Repositories"])


def _to_repo_response(repo: Repository) -> RepositoryResponse:
    """Helper to convert a Repository model to RepositoryResponse schema."""
    latest_job = None
    if repo.jobs:
        # jobs are sorted descending by created_at in model definition
        latest_job = IngestionJobResponse.model_validate(repo.jobs[0])

    return RepositoryResponse(
        id=repo.id,
        owner_id=repo.owner_id,
        github_url=repo.github_url,
        owner=repo.owner,
        name=repo.name,
        default_branch=repo.default_branch,
        latest_commit_sha=repo.latest_commit_sha,
        status=repo.status,
        error_message=repo.error_message,
        created_at=repo.created_at,
        updated_at=repo.updated_at,
        latest_job=latest_job,
    )


@router.post(
    "",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Repository for Indexing",
    description=(
        "Validate a public GitHub repository, persist metadata, and enqueue "
        "background indexing."
    ),
)
async def submit_repository(
    payload: RepositoryCreate,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RepositoryResponse:
    """Submit a public GitHub repository for background indexing."""
    github_service = GitHubService()

    # 1. Parse and validate GitHub URL syntax
    try:
        owner, repo_name, canonical_url = github_service.parse_github_url(
            payload.github_url
        )
    except GitHubError as err:
        raise HTTPException(status_code=err.status_code, detail=err.message) from err

    # 2. Check for duplicate repository under the same owner
    stmt = (
        select(Repository)
        .options(selectinload(Repository.jobs))
        .where(
            Repository.owner_id == current_user.user_id,
            Repository.github_url == canonical_url,
        )
    )
    result = await db.execute(stmt)
    existing_repo = result.scalar_one_or_none()

    if existing_repo:
        # Idempotent handling: if already indexing, return current state
        if existing_repo.status == "indexing":
            return _to_repo_response(existing_repo)

        # If previous indexing failed or succeeded, submit a new indexing job
        existing_repo.status = "pending"
        existing_repo.error_message = None

        new_job = IngestionJob(
            repository_id=existing_repo.id,
            status="queued",
            progress=0,
            current_step="queued",
            commit_sha=existing_repo.latest_commit_sha,
        )
        db.add(new_job)
        await db.commit()
        await db.refresh(existing_repo)

        enqueue_index_repository(str(new_job.id))
        return _to_repo_response(existing_repo)

    # 3. Verify public accessibility and resource limits on GitHub
    try:
        meta = await github_service.get_repository_details(owner, repo_name)
        default_branch = meta.get("default_branch") or "main"
        commit_sha = await github_service.get_latest_commit_sha(
            owner, repo_name, default_branch
        )
    except GitHubError as err:
        raise HTTPException(status_code=err.status_code, detail=err.message) from err

    # 4. Persist Repository and initial IngestionJob
    new_repo = Repository(
        owner_id=current_user.user_id,
        github_url=canonical_url,
        owner=owner,
        name=repo_name,
        default_branch=default_branch,
        latest_commit_sha=commit_sha,
        status="pending",
    )
    db.add(new_repo)
    await db.flush()

    new_job = IngestionJob(
        repository_id=new_repo.id,
        status="queued",
        progress=0,
        current_step="queued",
        commit_sha=commit_sha,
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_repo, attribute_names=["jobs"])

    # 5. Enqueue background ingestion worker task
    enqueue_index_repository(str(new_job.id))

    return _to_repo_response(new_repo)


@router.get(
    "",
    response_model=RepositoryListResponse,
    summary="List Repositories",
    description="Retrieve all repositories registered by the authenticated user.",
)
async def list_repositories(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RepositoryListResponse:
    """Retrieve all repositories owned by the authenticated user."""
    stmt = (
        select(Repository)
        .options(selectinload(Repository.jobs))
        .where(Repository.owner_id == current_user.user_id)
        .order_by(Repository.created_at.desc())
    )
    result = await db.execute(stmt)
    repos = result.scalars().all()

    return RepositoryListResponse(
        repositories=[_to_repo_response(r) for r in repos],
        total=len(repos),
    )


@router.get(
    "/{repository_id}",
    response_model=RepositoryResponse,
    summary="Get Repository Details",
    description="Retrieve repository metadata and latest indexing status.",
)
async def get_repository(
    repo: Repository = Depends(require_repository_ownership),
    db: AsyncSession = Depends(get_db),
) -> RepositoryResponse:
    """Retrieve a single repository scoped to the authenticated owner."""
    # Ensure jobs relationship is loaded
    stmt = (
        select(Repository)
        .options(selectinload(Repository.jobs))
        .where(Repository.id == repo.id)
    )
    result = await db.execute(stmt)
    full_repo = result.scalar_one()

    return _to_repo_response(full_repo)


@router.post(
    "/{repository_id}/reindex",
    response_model=RepositoryResponse,
    summary="Re-index Repository",
    description="Trigger a new background indexing job for the repository.",
)
async def reindex_repository(
    repo: Repository = Depends(require_repository_ownership),
    db: AsyncSession = Depends(get_db),
) -> RepositoryResponse:
    """Trigger re-indexing for an existing repository."""
    if repo.status == "indexing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repository is currently undergoing an active indexing job",
        )

    repo.status = "pending"
    repo.error_message = None

    new_job = IngestionJob(
        repository_id=repo.id,
        status="queued",
        progress=0,
        current_step="queued",
        commit_sha=repo.latest_commit_sha,
    )
    db.add(new_job)
    await db.commit()

    enqueue_index_repository(str(new_job.id))

    stmt = (
        select(Repository)
        .options(selectinload(Repository.jobs))
        .where(Repository.id == repo.id)
    )
    result = await db.execute(stmt)
    full_repo = result.scalar_one()

    return _to_repo_response(full_repo)


@router.delete(
    "/{repository_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Repository",
    description="Delete a repository and all associated ingestion jobs and indices.",
)
async def delete_repository(
    repo: Repository = Depends(require_repository_ownership),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete repository record and purge associated vector/graph data."""
    repo_id_str = str(repo.id)

    # Clean up vector store chunks
    try:
        vector_store = get_vector_store()
        await vector_store.delete_by_repository(repo_id_str)
    except Exception as exc:
        logger.warning("Vector store deletion failed for repo %s: %s", repo.id, exc)

    # Clean up graph store nodes & relationships
    try:
        graph_store = get_graph_store()
        await graph_store.delete_by_repository(repo_id_str)
    except Exception as exc:
        logger.warning("Graph store deletion failed for repo %s: %s", repo.id, exc)

    # Delete repository from PostgreSQL (cascades to jobs, conversations, messages)
    await db.delete(repo)
    await db.commit()
