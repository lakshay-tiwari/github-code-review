import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import settings
from app.infrastructure.vector.interfaces import (
    ChunkPayload,
    VectorDimensionMismatchError,
    VectorSearchResult,
)
from app.infrastructure.vector.qdrant_adapter import QdrantVectorStoreAdapter

# ==============================================================================
# Mocked Unit Tests (No Network / Total Isolation)
# ==============================================================================


def test_chunk_payload_model_validation():
    """Verify validation and serialization of ChunkPayload."""
    payload = ChunkPayload(
        chunk_id="chunk-abc-123",
        repository_id=str(uuid.uuid4()),
        commit_sha="a1b2c3d4e5f6",
        file_path="src/main.py",
        start_line=1,
        end_line=25,
        language="python",
        symbol_name="start_app",
        symbol_type="function",
        content_hash="hash987654321",
        content="def start_app():\n    pass",
        embedding_model="all-MiniLM-L6-v2",
        embedding_version="v1",
    )
    assert payload.chunk_id == "chunk-abc-123"
    assert payload.start_line == 1
    assert payload.end_line == 25
    assert payload.language == "python"

    data = payload.model_dump()
    assert data["chunk_id"] == "chunk-abc-123"
    assert data["symbol_name"] == "start_app"


@pytest.mark.asyncio
async def test_upsert_chunks_mocked():
    """Verify upsert_chunks creates deterministic UUIDs and PointStruct."""
    adapter = QdrantVectorStoreAdapter(collection_name="test_mock_coll")
    mock_client = MagicMock()
    mock_client.upsert = AsyncMock(return_value=True)
    adapter._client = mock_client

    payload = ChunkPayload(
        chunk_id="stable-chunk-id-1",
        repository_id="repo-123",
        commit_sha="commit-abc",
        file_path="app/core.py",
        start_line=10,
        end_line=30,
        content_hash="chash123",
        content="print('core')",
    )
    vector = [0.05] * 384

    count = await adapter.upsert_chunks([(payload, vector)])
    assert count == 1

    mock_client.upsert.assert_awaited_once()
    call_kwargs = mock_client.upsert.await_args.kwargs
    assert call_kwargs["collection_name"] == "test_mock_coll"
    points = call_kwargs["points"]
    assert len(points) == 1
    # Check deterministic UUID derived from chunk_id
    expected_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, "stable-chunk-id-1"))
    assert points[0].id == expected_uuid
    assert points[0].vector == vector
    assert points[0].payload["chunk_id"] == "stable-chunk-id-1"


@pytest.mark.asyncio
async def test_search_filter_construction_mocked():
    """Verify search builds the required repository and commit filter conditions."""
    adapter = QdrantVectorStoreAdapter(collection_name="test_mock_coll")
    mock_client = MagicMock()

    mock_hit = MagicMock()
    mock_hit.id = "point-1"
    mock_hit.score = 0.92
    mock_hit.payload = {
        "chunk_id": "chunk-found-1",
        "repository_id": "repo-xyz",
        "commit_sha": "sha-999",
        "file_path": "lib/utils.py",
        "start_line": 5,
        "end_line": 15,
        "content_hash": "hash_val",
        "content": "def util(): pass",
        "language": "python",
        "embedding_model": "all-MiniLM-L6-v2",
        "embedding_version": "v1",
        "extra_metadata": {},
    }
    mock_client.search = AsyncMock(return_value=[mock_hit])
    adapter._client = mock_client

    results = await adapter.search(
        query_vector=[0.1] * 384,
        limit=5,
        repository_id="repo-xyz",
        commit_sha="sha-999",
    )

    assert len(results) == 1
    assert isinstance(results[0], VectorSearchResult)
    assert results[0].chunk_id == "chunk-found-1"
    assert results[0].score == 0.92
    assert results[0].payload.file_path == "lib/utils.py"

    call_kwargs = mock_client.search.await_args.kwargs
    assert call_kwargs["limit"] == 5
    filter_obj = call_kwargs["query_filter"]
    assert filter_obj is not None
    assert len(filter_obj.must) == 2


@pytest.mark.asyncio
async def test_dimension_mismatch_error_mocked():
    """Verify ensure_collection detects incompatible vector dimensions."""
    adapter = QdrantVectorStoreAdapter(collection_name="test_mock_coll")
    mock_client = MagicMock()
    mock_client.collection_exists = AsyncMock(return_value=True)

    mock_info = MagicMock()
    mock_vectors = MagicMock()
    mock_vectors.size = 512  # Mismatched dimension
    mock_info.config.params.vectors = mock_vectors
    mock_client.get_collection = AsyncMock(return_value=mock_info)
    adapter._client = mock_client

    with pytest.raises(VectorDimensionMismatchError, match="dimension 512"):
        await adapter.ensure_collection(dimension=384, recreate=False)


# ==============================================================================
# Real Docker Integration Tests (Connecting to Local cortex-qdrant Container)
# ==============================================================================


@pytest.fixture
async def qdrant_test_collection():
    """Fixture providing an isolated Qdrant collection for integration tests."""
    coll_name = f"cortex_test_{uuid.uuid4().hex[:8]}"
    adapter = QdrantVectorStoreAdapter(
        url=settings.QDRANT_URL,
        collection_name=coll_name,
    )
    await adapter.ensure_collection(dimension=384, recreate=True)
    yield adapter, coll_name
    # Cleanup after test
    try:
        await adapter._client.delete_collection(coll_name)
    except Exception:
        pass
    await adapter.close()


@pytest.mark.asyncio
async def test_docker_qdrant_health_check():
    """Verify connectivity to the running Docker Qdrant container."""
    adapter = QdrantVectorStoreAdapter()
    try:
        health = await adapter.health_check()
        assert health["status"] == "ok"
        assert "url" in health
        assert "total_collections" in health
    finally:
        await adapter.close()


@pytest.mark.asyncio
async def test_docker_qdrant_dimension_mismatch_detection(
    qdrant_test_collection,
):
    """Verify live Qdrant container rejects conflicting dimension configuration."""
    adapter, _ = qdrant_test_collection
    # Existing collection has dimension 384; attempting ensure with 512 must raise
    with pytest.raises(VectorDimensionMismatchError, match="dimension 384"):
        await adapter.ensure_collection(dimension=512, recreate=False)


@pytest.mark.asyncio
async def test_docker_qdrant_upsert_and_filtered_search(qdrant_test_collection):
    """Verify real vector upsert, cosine search, and repository/commit filtering."""
    adapter, _ = qdrant_test_collection

    repo_a = f"repo_a_{uuid.uuid4().hex[:6]}"
    repo_b = f"repo_b_{uuid.uuid4().hex[:6]}"

    # Chunk 1: Repo A, Commit 1
    p1 = ChunkPayload(
        chunk_id=f"chunk_a_1_{uuid.uuid4().hex[:6]}",
        repository_id=repo_a,
        commit_sha="commit_sha_1",
        file_path="src/auth.py",
        start_line=1,
        end_line=20,
        content_hash="h1",
        content="def authenticate_user(): pass",
    )
    # Unit vector along axis 0
    v1 = [1.0] + [0.0] * 383

    # Chunk 2: Repo A, Commit 2
    p2 = ChunkPayload(
        chunk_id=f"chunk_a_2_{uuid.uuid4().hex[:6]}",
        repository_id=repo_a,
        commit_sha="commit_sha_2",
        file_path="src/router.py",
        start_line=1,
        end_line=30,
        content_hash="h2",
        content="def setup_routes(): pass",
    )
    # Unit vector along axis 1
    v2 = [0.0, 1.0] + [0.0] * 382

    # Chunk 3: Repo B, Commit 3
    p3 = ChunkPayload(
        chunk_id=f"chunk_b_1_{uuid.uuid4().hex[:6]}",
        repository_id=repo_b,
        commit_sha="commit_sha_3",
        file_path="src/db.py",
        start_line=1,
        end_line=15,
        content_hash="h3",
        content="def connect_db(): pass",
    )
    # Vector equal to v1 (similar direction)
    v3 = [1.0] + [0.0] * 383

    upserted = await adapter.upsert_chunks([(p1, v1), (p2, v2), (p3, v3)])
    assert upserted == 3

    # 1. Unfiltered search with query v1 -> matches p1 and p3 with high score
    unfiltered = await adapter.search(query_vector=v1, limit=5)
    assert len(unfiltered) >= 2
    chunk_ids = [res.chunk_id for res in unfiltered]
    assert p1.chunk_id in chunk_ids
    assert p3.chunk_id in chunk_ids

    # 2. Filtered by repository_id = Repo A -> must NOT return p3 (Repo B)
    filtered_repo_a = await adapter.search(
        query_vector=v1,
        limit=5,
        repository_id=repo_a,
    )
    assert len(filtered_repo_a) >= 1
    filtered_ids = [res.chunk_id for res in filtered_repo_a]
    assert p1.chunk_id in filtered_ids
    assert p3.chunk_id not in filtered_ids

    # 3. Filtered by repository_id = Repo A AND commit_sha = "commit_sha_2"
    filtered_commit = await adapter.search(
        query_vector=v2,
        limit=5,
        repository_id=repo_a,
        commit_sha="commit_sha_2",
    )
    assert len(filtered_commit) == 1
    assert filtered_commit[0].chunk_id == p2.chunk_id


@pytest.mark.asyncio
async def test_docker_qdrant_scoped_deletion(qdrant_test_collection):
    """Verify scoped deletion removes only target repository points."""
    adapter, _ = qdrant_test_collection

    repo_x = f"repo_x_{uuid.uuid4().hex[:6]}"
    repo_y = f"repo_y_{uuid.uuid4().hex[:6]}"

    px = ChunkPayload(
        chunk_id=f"cx_{uuid.uuid4().hex[:6]}",
        repository_id=repo_x,
        commit_sha="sha_x",
        file_path="x.py",
        start_line=1,
        end_line=5,
        content_hash="hx",
        content="repo x code",
    )
    py_payload = ChunkPayload(
        chunk_id=f"cy_{uuid.uuid4().hex[:6]}",
        repository_id=repo_y,
        commit_sha="sha_y",
        file_path="y.py",
        start_line=1,
        end_line=5,
        content_hash="hy",
        content="repo y code",
    )

    vec = [0.1] * 384
    await adapter.upsert_chunks([(px, vec), (py_payload, vec)])

    # Delete Repo X points
    await adapter.delete_by_repository(repository_id=repo_x)

    # Verify Repo X has 0 results
    res_x = await adapter.search(query_vector=vec, repository_id=repo_x)
    assert len(res_x) == 0

    # Verify Repo Y still has its point
    res_y = await adapter.search(query_vector=vec, repository_id=repo_y)
    assert len(res_y) == 1
    assert res_y[0].chunk_id == py_payload.chunk_id
