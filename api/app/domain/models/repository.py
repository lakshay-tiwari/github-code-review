from typing import TYPE_CHECKING

from sqlalchemy import Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.domain.models.conversation import Conversation
    from app.domain.models.job import IngestionJob


class Repository(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a public GitHub codebase submitted for indexing."""

    __tablename__ = "repositories"

    # Owner Clerk Subject ID (never client-supplied trust)
    owner_id: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )

    # Repository Identity
    github_url: Mapped[str] = mapped_column(
        String(512),
        index=True,
        nullable=False,
    )
    owner: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    default_branch: Mapped[str] = mapped_column(
        String(128),
        default="main",
        nullable=False,
    )

    # Commit pinning for reproducible retrieval & line citations
    latest_commit_sha: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    # Indexing status: 'pending', 'indexing', 'ready', 'failed'
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        index=True,
        nullable=False,
    )

    # Sanitized error message (no secrets)
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    jobs: Mapped[list["IngestionJob"]] = relationship(
        "IngestionJob",
        back_populates="repository",
        cascade="all, delete-orphan",
        order_by="IngestionJob.created_at.desc()",
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="repository",
        cascade="all, delete-orphan",
        order_by="Conversation.created_at.desc()",
    )

    __table_args__ = (
        UniqueConstraint("owner_id", "github_url", name="uq_repositories_owner_url"),
        Index("ix_repositories_owner_status", "owner_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Repository {self.owner}/{self.name} ({self.status})>"
