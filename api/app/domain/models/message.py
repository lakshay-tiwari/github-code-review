import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.domain.models.conversation import Conversation


class Message(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents an individual chat message with verified citations."""

    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # Message role: 'user', 'assistant', 'system'
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    # Actual message text content
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Status: 'pending', 'streaming', 'completed', 'failed'
    status: Mapped[str] = mapped_column(
        String(32),
        default="completed",
        nullable=False,
    )

    # Structured citations: [{"file_path": "...", "start_line": 10}]
    citations: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )

    __table_args__ = (
        Index("ix_messages_conv_created", "conversation_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Message {self.id} (Role: {self.role}, Conv: {self.conversation_id})>"
