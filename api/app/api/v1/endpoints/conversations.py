import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    get_current_user,
    get_db,
    require_conversation_ownership,
)
from app.core.security import UserContext
from app.domain.models import Conversation, Message, Repository
from app.schemas.chat import (
    ChatMessageRequest,
    ConversationCreate,
    ConversationListResponse,
    ConversationResponse,
    MessageResponse,
)
from app.services.chat_stream import ChatStreamingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["Conversations & Chat"])


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Conversation",
    description="Initialize a new conversational session grounded in a repository.",
)
async def create_conversation(
    payload: ConversationCreate,
    current_user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConversationResponse:
    """Create conversation verifying repository ownership."""
    # Verify repository exists and belongs to current user
    repo_res = await db.execute(
        select(Repository).where(Repository.id == payload.repository_id)
    )
    repo = repo_res.scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )
    if repo.owner_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not own this repository",
        )

    conversation = Conversation(
        repository_id=repo.id,
        owner_id=current_user.user_id,
        title=payload.title,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    return ConversationResponse(
        id=conversation.id,
        repository_id=conversation.repository_id,
        owner_id=conversation.owner_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[],
    )


@router.get(
    "",
    response_model=ConversationListResponse,
    summary="List Conversations",
    description="List all conversations owned by the authenticated user.",
)
async def list_conversations(
    current_user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    repository_id: uuid.UUID | None = Query(default=None),
) -> ConversationListResponse:
    """List conversations scoped by user and optional repository filter."""
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.owner_id == current_user.user_id)
        .order_by(desc(Conversation.created_at))
    )
    if repository_id is not None:
        stmt = stmt.where(Conversation.repository_id == repository_id)

    res = await db.execute(stmt)
    conversations = res.scalars().all()

    items = [
        ConversationResponse.model_validate(conv)
        for conv in conversations
    ]
    return ConversationListResponse(items=items, total=len(items))


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get Conversation",
    description="Retrieve conversation with full message history.",
)
async def get_conversation(
    conversation: Annotated[Conversation, Depends(require_conversation_ownership)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ConversationResponse:
    """Retrieve full conversation and messages."""
    res = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation.id)
    )
    conv_loaded = res.scalar_one()
    return ConversationResponse.model_validate(conv_loaded)


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Conversation",
    description="Delete conversation and associated messages/checkpoints.",
)
async def delete_conversation(
    conversation: Annotated[Conversation, Depends(require_conversation_ownership)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a conversation cascade-deleting its messages."""
    await db.delete(conversation)
    await db.commit()


@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessageResponse],
    summary="Get Conversation Messages",
)
async def get_conversation_messages(
    conversation: Annotated[Conversation, Depends(require_conversation_ownership)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MessageResponse]:
    """Retrieve ordered message history for a conversation."""
    res = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
    )
    messages = res.scalars().all()
    return [MessageResponse.model_validate(m) for m in messages]


@router.post(
    "/{conversation_id}/messages",
    summary="Send Message & Stream SSE Response",
    description="Submit user question and receive real-time streaming answer.",
)
async def send_message_stream(
    conversation_id: uuid.UUID,
    payload: ChatMessageRequest,
    current_user: Annotated[UserContext, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    """Submit question, persist user turn, and stream assistant answer via SSE."""
    # Verify ownership of conversation and load repository
    conv_res = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.repository))
        .where(Conversation.id == conversation_id)
    )
    conv = conv_res.scalar_one_or_none()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    if conv.owner_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not own this conversation",
        )

    # Persist user message
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=payload.content,
        status="completed",
    )
    db.add(user_msg)
    await db.commit()
    await db.refresh(user_msg)

    # Fetch prior history for context window
    hist_res = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
    )
    prior_messages = hist_res.scalars().all()
    history = [
        {"role": m.role, "content": m.content}
        for m in prior_messages[:-1]
    ]

    service = ChatStreamingService()
    stream_generator = service.stream_chat_response(
        conversation_id=str(conv.id),
        repository_id=str(conv.repository_id),
        commit_sha=conv.repository.latest_commit_sha if conv.repository else None,
        question=payload.content,
        history=history,
        user_message_id=str(user_msg.id),
    )

    return StreamingResponse(
        stream_generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
