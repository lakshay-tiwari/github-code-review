import logging

from app.core.config import settings
from app.infrastructure.vector.interfaces import BaseVectorStore
from app.infrastructure.vector.qdrant_adapter import QdrantVectorStoreAdapter

logger = logging.getLogger("cortex.vector.factory")

_vector_store_instance: BaseVectorStore | None = None


def get_vector_store(force_new: bool = False) -> BaseVectorStore:
    """Resolve and return an initialized BaseVectorStore instance.

    Uses settings.QDRANT_URL and settings.QDRANT_COLLECTION_NAME.
    Caches the adapter instance as a singleton.
    """
    global _vector_store_instance

    if not force_new and _vector_store_instance is not None:
        return _vector_store_instance

    instance = QdrantVectorStoreAdapter(
        url=settings.QDRANT_URL,
        api_key=settings.QDRANT_API_KEY,
        collection_name=settings.QDRANT_COLLECTION_NAME,
        prefer_grpc=settings.QDRANT_PREFER_GRPC,
    )
    _vector_store_instance = instance
    return instance


async def reset_vector_store_instance() -> None:
    """Close and clear cached vector store instance (for test cleanup)."""
    global _vector_store_instance
    if _vector_store_instance is not None:
        await _vector_store_instance.close()
        _vector_store_instance = None
