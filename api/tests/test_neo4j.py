import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.infrastructure.graph.factory import (
    get_graph_store,
    reset_graph_store_instance,
)
from app.infrastructure.graph.neo4j_adapter import (
    RELATIONSHIP_TYPE_REGEX,
    Neo4jGraphStoreAdapter,
)

from app.infrastructure.graph.interfaces import (
    GraphNode,
    GraphRelationship,
)

# ==============================================================================
# Unit Tests (Models, Sanitization, Parameterization with Mocks)
# ==============================================================================


def test_graph_node_model():
    node = GraphNode(
        node_id="repo-1:sha-1:Function:main",
        repository_id="repo-1",
        commit_sha="sha-1",
        node_type="Function",
        name="main",
        qualified_name="app.main",
        file_path="app/main.py",
        start_line=10,
        end_line=25,
        properties={"async": True, "arg_count": 0},
    )
    assert node.node_id == "repo-1:sha-1:Function:main"
    assert node.properties["async"] is True
    assert node.start_line == 10


def test_graph_relationship_model():
    rel = GraphRelationship(
        source_id="node-1",
        target_id="node-2",
        type="CALLS",
        repository_id="repo-1",
        commit_sha="sha-1",
        properties={"call_line": 15},
    )
    assert rel.type == "CALLS"
    assert rel.properties["call_line"] == 15


def test_relationship_type_regex_sanitization():
    valid_types = ["CALLS", "IMPORTS", "DEFINES", "INHERITS", "USES_TYPE"]
    for t in valid_types:
        assert RELATIONSHIP_TYPE_REGEX.match(t) is not None

    invalid_types = [
        "CALLS; MATCH (n) DETACH DELETE n",
        "CALLS]->(m) MERGE (m",
        "CALLS ",
        "CALLS-REL",
        "CALLS$TYPE",
    ]
    for t in invalid_types:
        assert RELATIONSHIP_TYPE_REGEX.match(t) is None


@pytest.mark.asyncio
async def test_upsert_relationships_invalid_type_raises():
    adapter = Neo4jGraphStoreAdapter(driver=MagicMock())
    invalid_rel = GraphRelationship(
        source_id="src",
        target_id="dst",
        type="CALLS; DETACH DELETE",
        repository_id="repo-1",
        commit_sha="sha-1",
    )
    with pytest.raises(ValueError, match="Invalid relationship type"):
        await adapter.upsert_relationships([invalid_rel])


@pytest.mark.asyncio
async def test_mock_upsert_nodes_parameterization():
    mock_driver = MagicMock()
    mock_session = AsyncMock()
    mock_driver.session.return_value.__aenter__.return_value = mock_session

    mock_result = AsyncMock()
    mock_result.single.return_value = {"upserted_count": 1}
    mock_session.run.return_value = mock_result

    adapter = Neo4jGraphStoreAdapter(driver=mock_driver)
    node = GraphNode(
        node_id="n1",
        repository_id="r1",
        commit_sha="s1",
        node_type="Class",
        name="Engine",
        qualified_name="core.Engine",
        file_path="core/engine.py",
        properties={"docstring": "Core engine"},
    )

    count = await adapter.upsert_nodes([node])
    assert count == 1

    # Verify query uses parameterized batch
    assert mock_session.run.called
    query_call = mock_session.run.call_args
    query_text = query_call[0][0]
    params = query_call[0][1]

    assert "$batch" in query_text
    assert "batch" in params
    assert params["batch"][0]["node_id"] == "n1"
    prop_dict = json.loads(params["batch"][0]["properties_json"])
    assert prop_dict == {"docstring": "Core engine"}


@pytest.mark.asyncio
async def test_factory_singleton():
    reset_graph_store_instance()
    store1 = get_graph_store()
    store2 = get_graph_store()
    assert store1 is store2
    reset_graph_store_instance()


# ==============================================================================
# Integration Tests (Live Docker Neo4j instance at bolt://localhost:7687)
# ==============================================================================


async def is_live_neo4j_reachable() -> bool:
    try:
        adapter = Neo4jGraphStoreAdapter()
        health = await adapter.health_check()
        await adapter.close()
        return health.get("status") == "healthy"
    except Exception:
        return False


@pytest.fixture
async def live_graph_store():
    if not await is_live_neo4j_reachable():
        pytest.skip("Live Neo4j instance not reachable at bolt://localhost:7687")

    adapter = Neo4jGraphStoreAdapter()
    await adapter.ensure_schema()
    yield adapter
    await adapter.close()


@pytest.mark.asyncio
async def test_live_schema_and_health(live_graph_store):
    health = await live_graph_store.health_check()
    assert health["status"] == "healthy"
    assert health["database"] == "neo4j"
    assert "version" in health


@pytest.mark.asyncio
async def test_live_node_crud_and_isolation(live_graph_store):
    repo_a = f"repo-{uuid.uuid4()}"
    repo_b = f"repo-{uuid.uuid4()}"
    commit_1 = "commit-1111"
    commit_2 = "commit-2222"

    node_a1 = GraphNode(
        node_id=f"{repo_a}:{commit_1}:file:app.py",
        repository_id=repo_a,
        commit_sha=commit_1,
        node_type="File",
        name="app.py",
        qualified_name="app",
        file_path="app.py",
        properties={"lines": 120},
    )
    node_a2 = GraphNode(
        node_id=f"{repo_a}:{commit_1}:func:init_app",
        repository_id=repo_a,
        commit_sha=commit_1,
        node_type="Function",
        name="init_app",
        qualified_name="app.init_app",
        file_path="app.py",
        start_line=10,
        end_line=30,
    )
    node_b = GraphNode(
        node_id=f"{repo_b}:{commit_1}:file:secret.py",
        repository_id=repo_b,
        commit_sha=commit_1,
        node_type="File",
        name="secret.py",
        qualified_name="secret",
        file_path="secret.py",
    )

    try:
        # 1. Upsert nodes
        count = await live_graph_store.upsert_nodes([node_a1, node_a2, node_b])
        assert count >= 3

        # 2. Retrieve node with exact matching scope
        retrieved = await live_graph_store.get_node(
            node_id=node_a1.node_id,
            repository_id=repo_a,
            commit_sha=commit_1,
        )
        assert retrieved is not None
        assert retrieved.name == "app.py"
        assert retrieved.properties.get("lines") == 120

        # 3. Isolation: query same node_id with wrong repo -> returns None
        wrong_repo = await live_graph_store.get_node(
            node_id=node_a1.node_id,
            repository_id=repo_b,
            commit_sha=commit_1,
        )
        assert wrong_repo is None

        # 4. Isolation: query with wrong commit -> returns None
        wrong_commit = await live_graph_store.get_node(
            node_id=node_a1.node_id,
            repository_id=repo_a,
            commit_sha=commit_2,
        )
        assert wrong_commit is None

        # 5. Upsert relationship
        rel = GraphRelationship(
            source_id=node_a1.node_id,
            target_id=node_a2.node_id,
            type="DEFINES",
            repository_id=repo_a,
            commit_sha=commit_1,
            properties={"scope": "module"},
        )
        rel_count = await live_graph_store.upsert_relationships([rel])
        assert rel_count == 1

        # 6. Neighborhood traversal
        neighborhood = await live_graph_store.get_neighbors(
            node_id=node_a1.node_id,
            repository_id=repo_a,
            commit_sha=commit_1,
            direction="OUTGOING",
        )
        assert neighborhood.center_node is not None
        assert len(neighborhood.nodes) == 1
        assert neighborhood.nodes[0].node_id == node_a2.node_id
        assert len(neighborhood.relationships) == 1
        assert neighborhood.relationships[0].type == "DEFINES"
        assert neighborhood.relationships[0].properties.get("scope") == "module"

        # 7. Neighborhood isolation across repos
        cross_neighborhood = await live_graph_store.get_neighbors(
            node_id=node_a1.node_id,
            repository_id=repo_b,
            commit_sha=commit_1,
        )
        assert cross_neighborhood.center_node is None
        assert len(cross_neighborhood.nodes) == 0

    finally:
        # Clean up created test data
        await live_graph_store.delete_by_repository(repo_a)
        await live_graph_store.delete_by_repository(repo_b)

        # Verify deletion cleaned up all repo_a nodes
        post_del = await live_graph_store.get_node(node_a1.node_id, repo_a)
        assert post_del is None
