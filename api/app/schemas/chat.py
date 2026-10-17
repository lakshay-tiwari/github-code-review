import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CitationModel(BaseModel):
    """Normalized citation grounded in retrieved repository code."""

    file_path: str = Field(description="Relative path of file in repository")
    start_line: int = Field(description="1-indexed starting line")
    end_line: int = Field(description="1-indexed ending line")
    commit_sha: str = Field(description="Commit SHA indexed for this code chunk")
    symbol_name: str | None = Field(
        default=None, description="AST symbol name (function/class) if available"
    )
    snippet: str | None = Field(
        default=None, description="Exemplary excerpt of referenced code"
    )


class MessageResponse(BaseModel):
    """Normalized message representation."""

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    status: str
    citations: list[dict[str, Any]] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationCreate(BaseModel):
    """Request payload to initiate a new conversation grounded in a repository."""

    repository_id: uuid.UUID = Field(
        description="ID of the repository to query"
    )
    title: str = Field(
        default="New Conversation",
        max_length=255,
        description="Human-readable title",
    )


class ConversationResponse(BaseModel):
    """Normalized conversation representation."""

    id: uuid.UUID
    repository_id: uuid.UUID
    owner_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    """List response for user conversations."""

    items: list[ConversationResponse]
    total: int


class ChatMessageRequest(BaseModel):
    """User message submission to a conversation."""

    content: str = Field(
        min_length=1, max_length=10000, description="User query prompt"
    )
