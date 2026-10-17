import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.security import (
    ClerkAuthenticationError,
    ClerkTokenVerifier,
    UserContext,
    get_token_verifier,
)
from app.domain.models import Conversation, IngestionJob, Message, Repository
from app.infrastructure.db.session import get_db

# Re-export get_db for unified dependency access
__all__ = [
    "get_current_user",
    "get_db",
    "get_token_verifier",
    "require_conversation_ownership",
    "require_job_ownership",
    "require_message_ownership",
    "require_repository_ownership",
]


async def get_current_user(
    request: Request,
    verifier: ClerkTokenVerifier = Depends(get_token_verifier),
) -> UserContext:
    """FastAPI dependency to extract and cryptographically verify Clerk Bearer tokens.

    Returns trusted UserContext derived strictly from verified claims.
    Rejects missing, malformed, expired, or invalid tokens with HTTP 401.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = auth_header.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme, expected Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token cannot be empty",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_context = await verifier.verify_token(token)
    except ClerkAuthenticationError as err:
        import logging

        logging.getLogger("cortex.auth").warning(
            "Clerk authentication failed: %s", err.detail
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=err.detail,
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

    return user_context


async def require_repository_ownership(
    repository_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Repository:
    """Enforces that the repository exists and belongs to the authenticated user."""
    result = await db.execute(
        select(Repository).where(Repository.id == repository_id)
    )
    repo = result.scalar_one_or_none()

    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    if repo.owner_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to access this repository",
        )

    return repo


async def require_job_ownership(
    job_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IngestionJob:
    """Enforces that the job exists and its repository is owned by the user."""
    result = await db.execute(
        select(IngestionJob)
        .options(joinedload(IngestionJob.repository))
        .where(IngestionJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingestion job not found",
        )

    if not job.repository or job.repository.owner_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not own the repository for this job",
        )

    return job


async def require_conversation_ownership(
    conversation_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Conversation:
    """Enforces that the conversation exists and belongs to the authenticated user."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()

    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    if conv.owner_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to access this conversation",
        )

    return conv


async def require_message_ownership(
    message_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Message:
    """Enforces that the message exists and its conversation is owned by the user."""
    result = await db.execute(
        select(Message)
        .options(joinedload(Message.conversation))
        .where(Message.id == message_id)
    )
    msg = result.scalar_one_or_none()

    if not msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    if not msg.conversation or msg.conversation.owner_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not own the conversation for this message",
        )

    return msg
