from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class ChunkPayload(BaseModel):
    """Normalized metadata stored with each vector chunk in the vector store."""

    chunk_id: str = Field(
        description="Deterministic stable chunk ID (e.g. hash of repo, path, lines)"
    )
    repository_id: str = Field(description="Repository UUID string")
    commit_sha: str = Field(
        description="Immutable Git commit SHA indexed by this chunk"
    )
    file_path: str = Field(
        description="Relative path of file within repository"
    )
    start_line: int = Field(description="1-indexed starting line number")
    end_line: int = Field(description="1-indexed ending line number")
    language: str = Field(
        default="text",
        description="Detected language (e.g., 'python', 'typescript')",
    )
    symbol_name: str | None = Field(
        default=None,
        description="AST symbol name (function, class, method) if extracted",
    )
    symbol_type: str | None = Field(
        default=None,
        description="Symbol type ('function', 'class', 'method', 'module')",
    )
    content_hash: str = Field(
        description="SHA256 hash of the exact code text content"
    )
    content: str = Field(
        description="Raw text content of chunk for retrieval grounding"
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Embedding model used to vectorize this chunk",
    )
    embedding_version: str = Field(
        default="v1", description="Versioning tag for embedding schema"
    )
    extra_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Arbitrary additional metadata"
    )


class VectorSearchResult(BaseModel):
    """Normalized search result returned by the vector store."""

    chunk_id: str = Field(description="Stable chunk identifier")
    score: float = Field(description="Similarity score (e.g. cosine similarity)")
    payload: ChunkPayload = Field(description="Stored chunk payload")


class VectorDimensionMismatchError(Exception):
    """Raised when an existing collection dimension conflicts with embedding model."""

    pass


class BaseVectorStore(ABC):
    """Abstract interface hiding vector store operations from application code."""

    @property
    @abstractmethod
    def collection_name(self) -> str:
        """Name of the vector collection."""
        ...

    @abstractmethod
    async def ensure_collection(
        self, dimension: int, recreate: bool = False
    ) -> None:
        """Ensure the target collection exists with the specified vector dimension.

        Validates that an existing collection's dimension matches `dimension`.
        Raises VectorDimensionMismatchError if dimensions differ.
        """
        ...

    @abstractmethod
    async def upsert_chunks(
        self, chunks: list[tuple[ChunkPayload, list[float]]]
    ) -> int:
        """Upsert a batch of (payload, vector) tuples into the vector store.

        Returns the count of points upserted.
        """
        ...

    @abstractmethod
    async def search(
        self,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float | None = None,
        repository_id: str | None = None,
        commit_sha: str | None = None,
        file_path_prefix: str | None = None,
    ) -> list[VectorSearchResult]:
        """Search for nearest neighbor vectors filtered by repository and commit SHA."""
        ...

    @abstractmethod
    async def delete_by_repository(
        self,
        repository_id: str,
        commit_sha: str | None = None,
    ) -> int:
        """Delete all points belonging to a repository (and optionally a commit)."""
        ...

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check operational health and reachability of the vector store."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close connection pools and background clients."""
        ...
