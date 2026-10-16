from abc import ABC, abstractmethod


class BaseEmbeddingProvider(ABC):
    """Abstract interface hiding embedding model implementations from application code.

    Decoupled from LLM chat providers so changing LLMs never forces re-embedding.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identifier of the embedding provider (e.g., 'sentence-transformers')."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the specific embedding model (e.g., 'all-MiniLM-L6-v2')."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Fixed vector dimension produced by this model (e.g. 384)."""
        ...

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Asynchronously compute an embedding vector for a single search query."""
        ...

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Asynchronously compute embedding vectors for a batch of document chunks."""
        ...
