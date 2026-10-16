import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import (
    get_current_user,
    require_conversation_ownership,
    require_job_ownership,
    require_message_ownership,
    require_repository_ownership,
)
from app.core.security import UserContext
from app.domain.models import Conversation, IngestionJob, Message, Repository

router = APIRouter(prefix="/auth", tags=["Authentication & Authorization"])


class MeResponse(BaseModel):
    user_id: str
    session_id: str | None = None
    email: str | None = None
    authorized_party: str | None = None
    claims: dict[str, Any]


class ProtectedRepoResponse(BaseModel):
    id: uuid.UUID
    owner_id: str
    github_url: str
    status: str


class ProtectedJobResponse(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
    status: str
    progress: int


class ProtectedConversationResponse(BaseModel):
    id: uuid.UUID
    owner_id: str
    title: str


class ProtectedMessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    status: str


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Get Current User",
    description="Returns verified user identity context from Clerk session token.",
)
async def get_me(
    current_user: UserContext = Depends(get_current_user),
) -> MeResponse:
    """Returns the verified user context derived strictly from verified claims."""
    return MeResponse(
        user_id=current_user.user_id,
        session_id=current_user.session_id,
        email=current_user.email,
        authorized_party=current_user.authorized_party,
        claims=current_user.claims,
    )


@router.get(
    "/test/repositories/{repository_id}",
    response_model=ProtectedRepoResponse,
    summary="Test Repository Ownership",
    description="Protected test seam verifying repository ownership enforcement.",
)
async def test_repository_ownership(
    repo: Repository = Depends(require_repository_ownership),
) -> ProtectedRepoResponse:
    """Verifies user ownership of repository."""
    return ProtectedRepoResponse(
        id=repo.id,
        owner_id=repo.owner_id,
        github_url=repo.github_url,
        status=repo.status,
    )


@router.get(
    "/test/jobs/{job_id}",
    response_model=ProtectedJobResponse,
    summary="Test Ingestion Job Ownership",
    description="Protected test seam verifying job ownership enforcement.",
)
async def test_job_ownership(
    job: IngestionJob = Depends(require_job_ownership),
) -> ProtectedJobResponse:
    """Verifies user ownership of ingestion job."""
    return ProtectedJobResponse(
        id=job.id,
        repository_id=job.repository_id,
        status=job.status,
        progress=job.progress,
    )


@router.get(
    "/test/conversations/{conversation_id}",
    response_model=ProtectedConversationResponse,
    summary="Test Conversation Ownership",
    description="Protected test seam verifying conversation ownership enforcement.",
)
async def test_conversation_ownership(
    conv: Conversation = Depends(require_conversation_ownership),
) -> ProtectedConversationResponse:
    """Verifies user ownership of conversation."""
    return ProtectedConversationResponse(
        id=conv.id,
        owner_id=conv.owner_id,
        title=conv.title,
    )


@router.get(
    "/test/messages/{message_id}",
    response_model=ProtectedMessageResponse,
    summary="Test Message Ownership",
    description="Protected test seam verifying message ownership enforcement.",
)
async def test_message_ownership(
    msg: Message = Depends(require_message_ownership),
) -> ProtectedMessageResponse:
    """Verifies user ownership of message."""
    return ProtectedMessageResponse(
        id=msg.id,
        conversation_id=msg.conversation_id,
        role=msg.role,
        content=msg.content,
        status=msg.status,
    )
