import logging

from app.infrastructure.embeddings.factory import get_embedding_provider
from app.infrastructure.vector.factory import get_vector_store
from app.infrastructure.vector.interfaces import VectorSearchResult

logger = logging.getLogger(__name__)


class SemanticRetrievalService:
    """Retrieval service for semantic search over indexed code vectors."""

    async def search(
        self,
        query: str,
        repository_id: str,
        commit_sha: str | None = None,
        limit: int = 10,
        score_threshold: float | None = None,
        file_path_prefix: str | None = None,
    ) -> list[VectorSearchResult]:
        """Perform semantic code search strictly scoped by repository and commit."""
        embedding_provider = get_embedding_provider()
        vector_store = get_vector_store()

        # Vectorize search query
        query_vector = await embedding_provider.embed_query(query)

        # Execute scoped vector search in Qdrant
        results = await vector_store.search(
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            repository_id=repository_id,
            commit_sha=commit_sha,
            file_path_prefix=file_path_prefix,
        )

        return results

    async def get_indexed_files(
        self,
        repository_id: str,
        commit_sha: str | None = None,
        limit: int = 500,
    ) -> list[str]:
        """Return sorted list of distinct file paths indexed for a repository.

        Delegates to the vector store's payload-only scroll so no embeddings
        are computed. Results are scoped to the repository (and commit when
        provided) and never cross repository boundaries.
        """
        vector_store = get_vector_store()
        return await vector_store.scroll_distinct_files(
            repository_id=repository_id,
            commit_sha=commit_sha,
            limit=limit,
        )
