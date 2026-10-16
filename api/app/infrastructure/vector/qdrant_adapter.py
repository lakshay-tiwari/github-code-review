import logging
import uuid
from typing import Any

from qdrant_client import AsyncQdrantClient, models

from app.core.config import settings
from app.infrastructure.vector.interfaces import (
    BaseVectorStore,
    ChunkPayload,
    VectorDimensionMismatchError,
    VectorSearchResult,
)

logger = logging.getLogger("cortex.vector.qdrant")


class QdrantVectorStoreAdapter(BaseVectorStore):
    """Qdrant vector store adapter encapsulating all Qdrant-specific operations."""

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        collection_name: str | None = None,
        prefer_grpc: bool | None = None,
    ) -> None:
        self._url = url or settings.QDRANT_URL
        self._api_key = api_key or settings.QDRANT_API_KEY
        self._collection_name = (
            collection_name or settings.QDRANT_COLLECTION_NAME
        )
        self._prefer_grpc = (
            prefer_grpc
            if prefer_grpc is not None
            else settings.QDRANT_PREFER_GRPC
        )
        self._client = AsyncQdrantClient(
            url=self._url,
            api_key=self._api_key,
            prefer_grpc=self._prefer_grpc,
        )

    @property
    def collection_name(self) -> str:
        return self._collection_name

    async def ensure_collection(
        self, dimension: int, recreate: bool = False
    ) -> None:
        """Ensure the target collection exists with the specified dimension."""
        exists = await self._client.collection_exists(self._collection_name)

        if exists:
            if recreate:
                logger.info(
                    "Recreating existing Qdrant collection '%s'...",
                    self._collection_name,
                )
                await self._client.delete_collection(self._collection_name)
                exists = False
            else:
                info = await self._client.get_collection(self._collection_name)
                vectors_config = info.config.params.vectors

                existing_dim = None
                if hasattr(vectors_config, "size"):
                    existing_dim = vectors_config.size
                elif isinstance(vectors_config, dict) and "size" in vectors_config:
                    existing_dim = vectors_config["size"]

                if existing_dim is not None and existing_dim != dimension:
                    raise VectorDimensionMismatchError(
                        f"Qdrant collection '{self._collection_name}' has "
                        f"dimension {existing_dim}, which does not match "
                        f"required embedding dimension {dimension}."
                    )
                return

        # Create collection with Cosine distance and HNSW indexing threshold
        logger.info(
            "Creating Qdrant collection '%s' with dimension %d...",
            self._collection_name,
            dimension,
        )
        await self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config=models.VectorParams(
                size=dimension,
                distance=models.Distance.COSINE,
            ),
            optimizers_config=models.OptimizersConfigDiff(
                indexing_threshold=10000,
            ),
        )

        # Create payload indexes for fast filtered searches
        for field in ["repository_id", "commit_sha", "file_path", "language"]:
            try:
                await self._client.create_payload_index(
                    collection_name=self._collection_name,
                    field_name=field,
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
            except Exception as err:
                logger.warning(
                    "Could not create payload index on '%s': %s", field, err
                )

    async def upsert_chunks(
        self, chunks: list[tuple[ChunkPayload, list[float]]]
    ) -> int:
        """Upsert a list of (payload, vector) tuples with deterministic point IDs."""
        if not chunks:
            return 0

        points: list[models.PointStruct] = []
        for payload, vector in chunks:
            # Deterministic UUIDv5 based on stable chunk identifier
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, payload.chunk_id))
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload.model_dump(),
                )
            )

        await self._client.upsert(
            collection_name=self._collection_name,
            points=points,
            wait=True,
        )
        return len(points)

    async def search(
        self,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float | None = None,
        repository_id: str | None = None,
        commit_sha: str | None = None,
        file_path_prefix: str | None = None,
    ) -> list[VectorSearchResult]:
        """Search nearest neighbor vectors with scoped repository and commit filters."""
        conditions: list[models.FieldCondition] = []

        if repository_id:
            conditions.append(
                models.FieldCondition(
                    key="repository_id",
                    match=models.MatchValue(value=str(repository_id)),
                )
            )

        if commit_sha:
            conditions.append(
                models.FieldCondition(
                    key="commit_sha",
                    match=models.MatchValue(value=commit_sha),
                )
            )

        if file_path_prefix:
            conditions.append(
                models.FieldCondition(
                    key="file_path",
                    match=models.MatchText(text=file_path_prefix),
                )
            )

        query_filter = (
            models.Filter(must=conditions) if conditions else None  # type: ignore
        )

        hits = await self._client.search(
            collection_name=self._collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
        )

        results: list[VectorSearchResult] = []
        for hit in hits:
            if not hit.payload:
                continue
            chunk_payload = ChunkPayload.model_validate(hit.payload)
            results.append(
                VectorSearchResult(
                    chunk_id=chunk_payload.chunk_id,
                    score=float(hit.score),
                    payload=chunk_payload,
                )
            )

        return results

    async def delete_by_repository(
        self,
        repository_id: str,
        commit_sha: str | None = None,
    ) -> int:
        """Delete points belonging to a repository and optionally specific commit."""
        must_conditions: list[models.FieldCondition] = [
            models.FieldCondition(
                key="repository_id",
                match=models.MatchValue(value=str(repository_id)),
            )
        ]

        if commit_sha:
            must_conditions.append(
                models.FieldCondition(
                    key="commit_sha",
                    match=models.MatchValue(value=commit_sha),
                )
            )

        delete_filter = models.Filter(must=must_conditions)  # type: ignore

        await self._client.delete(
            collection_name=self._collection_name,
            points_selector=models.FilterSelector(filter=delete_filter),
            wait=True,
        )
        return len(must_conditions)

    async def health_check(self) -> dict[str, Any]:
        """Check connection health and verify collection existence."""
        collections_response = await self._client.get_collections()
        exists = await self._client.collection_exists(self._collection_name)
        return {
            "status": "ok",
            "url": self._url,
            "collection": self._collection_name,
            "collection_exists": exists,
            "total_collections": len(collections_response.collections),
        }

    async def close(self) -> None:
        """Close the underlying client connection."""
        await self._client.close()
