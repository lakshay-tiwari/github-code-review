import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.domain.models.message import Message
    from app.domain.models.repository import Repository


class Conversation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a conversational session grounded in a specific repository."""

    __tablename__ = "conversations"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # Owner Clerk Subject ID (enforces cross-tenant isolation)
    owner_id: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        default="New Conversation",
        nullable=False,
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(
        "Repository",
        back_populates="conversations",
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at.asc()",
    )

    __table_args__ = (
        Index("ix_conversations_owner_repo", "owner_id", "repository_id"),
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.id} (Owner: {self.owner_id}, Title: {self.title})>"
