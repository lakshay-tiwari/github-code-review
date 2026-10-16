import logging

from app.core.config import settings
from app.infrastructure.embeddings.interfaces import BaseEmbeddingProvider
from app.infrastructure.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddingProvider,
)

logger = logging.getLogger("cortex.embeddings.factory")

_embedding_instances: dict[str, BaseEmbeddingProvider] = {}


def get_embedding_provider(
    provider: str | None = None,
    force_new: bool = False,
) -> BaseEmbeddingProvider:
    """Resolve and return an initialized BaseEmbeddingProvider instance.

    Uses settings.EMBEDDING_PROVIDER ('sentence-transformers') as default.
    Caches provider instances to ensure model weights are loaded at most once.
    """
    provider_name = (provider or settings.EMBEDDING_PROVIDER).lower().strip()

    if not force_new and provider_name in _embedding_instances:
        return _embedding_instances[provider_name]

    if provider_name in ("sentence-transformers", "sentence_transformers"):
        instance = SentenceTransformerEmbeddingProvider(
            model_name=settings.EMBEDDING_MODEL,
            dimension=settings.EMBEDDING_DIMENSION,
            lazy_load=True,
        )
    else:
        raise ValueError(
            f"Unsupported embedding provider '{provider_name}'. "
            "Supported providers: ['sentence-transformers']"
        )

    _embedding_instances[provider_name] = instance
    return instance


def reset_embedding_provider_instances() -> None:
    """Clear cached embedding provider instances (for test isolation)."""
    for instance in _embedding_instances.values():
        if hasattr(instance, "close"):
            instance.close()
    _embedding_instances.clear()
