import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.domain.models.repository import Repository


class IngestionJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks background repository ingestion and indexing tasks."""

    __tablename__ = "ingestion_jobs"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # Job lifecycle status: 'queued', 'in_progress', 'completed', 'failed'
    status: Mapped[str] = mapped_column(
        String(32),
        default="queued",
        index=True,
        nullable=False,
    )

    # Progress tracking (0 - 100)
    progress: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Current pipeline step (e.g., 'cloning', 'tree_sitter_parsing', 'qdrant_indexing')
    current_step: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    # Retry management
    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
    )

    # Immutable Git commit SHA indexed by this specific job run
    commit_sha: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    # Safe sanitized error details (no raw secrets, tokens, or private paths)
    error_details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Timing metrics
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(
        "Repository",
        back_populates="jobs",
    )

    __table_args__ = (
        Index("ix_ingestion_jobs_repo_status", "repository_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<IngestionJob {self.id} ({self.status})>"
