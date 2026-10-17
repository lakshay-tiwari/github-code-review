import json
import logging
import re
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase
from neo4j.exceptions import Neo4jError

from app.core.config import settings
from app.infrastructure.graph.interfaces import (
    BaseGraphStore,
    GraphNeighborhood,
    GraphNode,
    GraphRelationship,
)

logger = logging.getLogger(__name__)

# Strict identifier validation for relationship types to prevent Cypher injection
RELATIONSHIP_TYPE_REGEX = re.compile(r"^[A-Za-z0-9_]+$")


class Neo4jGraphStoreAdapter(BaseGraphStore):
    """Neo4j graph store adapter supporting repository-scoped operations.

    Ensures complete isolation between repositories and commit SHAs,
    as well as logical label separation (:CodeNode) to prevent collision
    with future Mem0 memory entities.
    """

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
        max_connection_pool_size: int | None = None,
        driver: AsyncDriver | None = None,
    ) -> None:
        self.uri = uri or settings.NEO4J_URI
        self.user = user or settings.NEO4J_USER
        self.password = password or settings.NEO4J_PASSWORD
        self.database = database or settings.NEO4J_DATABASE
        self.max_pool_size = (
            max_connection_pool_size or settings.NEO4J_MAX_CONNECTION_POOL_SIZE
        )

        if driver is not None:
            self._driver = driver
            self._owns_driver = False
        else:
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_pool_size=self.max_pool_size,
            )
            self._owns_driver = True

    async def ensure_schema(self) -> None:
        """Create uniqueness constraints and indexes for :CodeNode entities."""
        statements = [
            # Uniqueness constraint on node_id for CodeNode
            "CREATE CONSTRAINT code_node_id_unique IF NOT EXISTS FOR "
            "(n:CodeNode) REQUIRE n.node_id IS UNIQUE",
            # Composite index on repository_id and commit_sha for fast scoped filtering
            "CREATE INDEX code_node_repo_commit IF NOT EXISTS FOR "
            "(n:CodeNode) ON (n.repository_id, n.commit_sha)",
            # Index on symbol qualified name
            "CREATE INDEX code_node_qual_name IF NOT EXISTS FOR "
            "(n:CodeNode) ON (n.qualified_name)",
            # Index on relative file path
            "CREATE INDEX code_node_file_path IF NOT EXISTS FOR "
            "(n:CodeNode) ON (n.file_path)",
        ]

        async with self._driver.session(database=self.database) as session:
            for stmt in statements:
                try:
                    await session.run(stmt)
                except Neo4jError as exc:
                    logger.error(
                        "Failed to execute schema statement: %s, error: %s", stmt, exc
                    )
                    raise

    async def upsert_nodes(self, nodes: list[GraphNode]) -> int:
        """Upsert a batch of code graph nodes using parameterized Cypher.

        Serializes metadata dictionary to JSON string to adhere to Neo4j's
        primitive property value constraints.
        """
        if not nodes:
            return 0

        query = """
        UNWIND $batch AS item
        MERGE (n:CodeNode {node_id: item.node_id})
        SET n.repository_id = item.repository_id,
            n.commit_sha = item.commit_sha,
            n.node_type = item.node_type,
            n.name = item.name,
            n.qualified_name = item.qualified_name,
            n.file_path = item.file_path,
            n.start_line = item.start_line,
            n.end_line = item.end_line,
            n.properties_json = item.properties_json
        RETURN count(n) AS upserted_count
        """

        batch_data = [
            {
                "node_id": node.node_id,
                "repository_id": node.repository_id,
                "commit_sha": node.commit_sha,
                "node_type": node.node_type,
                "name": node.name,
                "qualified_name": node.qualified_name,
                "file_path": node.file_path,
                "start_line": node.start_line,
                "end_line": node.end_line,
                "properties_json": json.dumps(node.properties),
            }
            for node in nodes
        ]

        async with self._driver.session(database=self.database) as session:
            result = await session.run(query, {"batch": batch_data})
            record = await result.single()
            return record["upserted_count"] if record else len(nodes)

    async def upsert_relationships(
        self, relationships: list[GraphRelationship]
    ) -> int:
        """Upsert relationships grouped by sanitized relationship type.

        Uses strict validation for relationship types to ensure safe Cypher queries.
        """
        if not relationships:
            return 0

        # Group by relationship type
        by_type: dict[str, list[dict[str, Any]]] = {}
        for rel in relationships:
            rel_type = rel.type.strip()
            if not RELATIONSHIP_TYPE_REGEX.match(rel_type):
                raise ValueError(
                    f"Invalid relationship type '{rel.type}'. "
                    f"Must match regex {RELATIONSHIP_TYPE_REGEX.pattern}"
                )

            data = {
                "source_id": rel.source_id,
                "target_id": rel.target_id,
                "repository_id": rel.repository_id,
                "commit_sha": rel.commit_sha,
                "properties_json": json.dumps(rel.properties),
            }
            by_type.setdefault(rel_type, []).append(data)

        total_upserted = 0
        async with self._driver.session(database=self.database) as session:
            for rel_type, batch in by_type.items():
                query = f"""
                UNWIND $batch AS rel
                MATCH (src:CodeNode {{
                    node_id: rel.source_id,
                    repository_id: rel.repository_id,
                    commit_sha: rel.commit_sha
                }})
                MATCH (dst:CodeNode {{
                    node_id: rel.target_id,
                    repository_id: rel.repository_id,
                    commit_sha: rel.commit_sha
                }})
                MERGE (src)-[r:{rel_type}]->(dst)
                SET r.repository_id = rel.repository_id,
                    r.commit_sha = rel.commit_sha,
                    r.properties_json = rel.properties_json
                RETURN count(r) AS rel_count
                """
                result = await session.run(query, {"batch": batch})
                record = await result.single()
                if record:
                    total_upserted += record["rel_count"]

        return total_upserted

    async def get_node(
        self,
        node_id: str,
        repository_id: str,
        commit_sha: str | None = None,
    ) -> GraphNode | None:
        """Retrieve a single code node strictly scoped by repository and commit."""
        where_clauses = [
            "n.node_id = $node_id",
            "n.repository_id = $repository_id",
        ]
        params: dict[str, Any] = {
            "node_id": node_id,
            "repository_id": repository_id,
        }

        if commit_sha:
            where_clauses.append("n.commit_sha = $commit_sha")
            params["commit_sha"] = commit_sha

        query = f"""
        MATCH (n:CodeNode)
        WHERE {' AND '.join(where_clauses)}
        RETURN properties(n) AS props
        LIMIT 1
        """

        async with self._driver.session(database=self.database) as session:
            result = await session.run(query, params)
            record = await result.single()
            if not record:
                return None
            return self._node_from_record(record["props"])

    async def get_neighbors(
        self,
        node_id: str,
        repository_id: str,
        commit_sha: str | None = None,
        direction: str = "BOTH",
        depth: int = 1,
        limit: int = 50,
    ) -> GraphNeighborhood:
        """Query bounded neighborhood of a node, scoped by repo and commit.

        direction: 'OUTGOING', 'INCOMING', or 'BOTH'.
        depth: 1 to 3 hops (bounded for safety).
        """
        center = await self.get_node(node_id, repository_id, commit_sha)
        if not center:
            return GraphNeighborhood(center_node=None, nodes=[], relationships=[])

        # Bound depth and limit to prevent runaway graph traversals
        safe_depth = max(1, min(depth, 3))
        safe_limit = max(1, min(limit, 200))

        dir_pattern = "-[r*1..{depth}]-"
        if direction.upper() == "OUTGOING":
            dir_pattern = "-[r*1..{depth}]->"
        elif direction.upper() == "INCOMING":
            dir_pattern = "<-[r*1..{depth}]-"

        pattern = dir_pattern.format(depth=safe_depth)

        where_commit = "AND m.commit_sha = $commit_sha" if commit_sha else ""
        params: dict[str, Any] = {
            "node_id": node_id,
            "repository_id": repository_id,
            "limit": safe_limit,
        }
        if commit_sha:
            params["commit_sha"] = commit_sha

        query = f"""
        MATCH (n:CodeNode {{node_id: $node_id, repository_id: $repository_id}})
        MATCH (n){pattern}(m:CodeNode)
        WHERE m.repository_id = $repository_id {where_commit}
          AND m.node_id <> n.node_id
        WITH DISTINCT m
        LIMIT $limit
        RETURN properties(m) AS props
        """

        nodes_map: dict[str, GraphNode] = {}
        async with self._driver.session(database=self.database) as session:
            result = await session.run(query, params)
            records = await result.data()
            for rec in records:
                node = self._node_from_record(rec["props"])
                nodes_map[node.node_id] = node

        # If neighbors were found, retrieve direct edges between all nodes
        neighbor_ids = list(nodes_map.keys())
        relationships: list[GraphRelationship] = []

        if neighbor_ids:
            all_ids = [node_id] + neighbor_ids
            rel_query = """
            MATCH (a:CodeNode)-[r]->(b:CodeNode)
            WHERE a.node_id IN $all_ids
              AND b.node_id IN $all_ids
              AND a.repository_id = $repository_id
              AND b.repository_id = $repository_id
            RETURN a.node_id AS src, b.node_id AS dst,
                   type(r) AS rel_type, properties(r) AS rel_props
            """
            async with self._driver.session(database=self.database) as session:
                rel_res = await session.run(
                    rel_query,
                    {"all_ids": all_ids, "repository_id": repository_id},
                )
                rel_records = await rel_res.data()
                for rec in rel_records:
                    r_props = rec.get("rel_props") or {}
                    props_json = r_props.get("properties_json", "{}")
                    try:
                        props = (
                            json.loads(props_json)
                            if isinstance(props_json, str)
                            else {}
                        )
                    except json.JSONDecodeError:
                        props = {}

                    relationships.append(
                        GraphRelationship(
                            source_id=rec["src"],
                            target_id=rec["dst"],
                            type=rec["rel_type"],
                            repository_id=r_props.get(
                                "repository_id", repository_id
                            ),
                            commit_sha=r_props.get("commit_sha", ""),
                            properties=props,
                        )
                    )

        return GraphNeighborhood(
            center_node=center,
            nodes=list(nodes_map.values()),
            relationships=relationships,
        )

    async def delete_by_repository(
        self,
        repository_id: str,
        commit_sha: str | None = None,
    ) -> int:
        """Delete all code nodes and relationships for a repository and commit."""
        where_clauses = ["n.repository_id = $repository_id"]
        params: dict[str, Any] = {"repository_id": repository_id}

        if commit_sha:
            where_clauses.append("n.commit_sha = $commit_sha")
            params["commit_sha"] = commit_sha

        query = f"""
        MATCH (n:CodeNode)
        WHERE {' AND '.join(where_clauses)}
        DETACH DELETE n
        RETURN count(n) AS deleted_count
        """

        async with self._driver.session(database=self.database) as session:
            result = await session.run(query, params)
            record = await result.single()
            return record["deleted_count"] if record else 0

    async def health_check(self) -> dict[str, Any]:
        """Verify driver connectivity and retrieve Neo4j kernel details."""
        try:
            await self._driver.verify_connectivity()
            async with self._driver.session(database=self.database) as session:
                res = await session.run(
                    "CALL dbms.components() YIELD name, versions, edition "
                    "RETURN name, versions, edition"
                )
                rec = await res.single()
                info = dict(rec) if rec else {}
                return {
                    "status": "healthy",
                    "database": self.database,
                    "component": info.get("name", "Neo4j Kernel"),
                    "version": info.get("versions", ["unknown"])[0]
                    if info.get("versions")
                    else "unknown",
                    "edition": info.get("edition", "community"),
                }
        except Exception as exc:
            logger.error("Neo4j health check failed: %s", exc)
            return {
                "status": "unhealthy",
                "database": self.database,
                "error": str(exc),
            }

    async def close(self) -> None:
        """Close driver connection pools if owned."""
        if self._owns_driver and self._driver:
            await self._driver.close()

    def _node_from_record(self, record_node: Any) -> GraphNode:
        """Convert a Neo4j node properties map into a normalized GraphNode."""
        props_json = record_node.get("properties_json")
        props: dict[str, Any] = {}
        if props_json and isinstance(props_json, str):
            try:
                props = json.loads(props_json)
            except json.JSONDecodeError:
                props = {}

        return GraphNode(
            node_id=record_node["node_id"],
            repository_id=record_node["repository_id"],
            commit_sha=record_node["commit_sha"],
            node_type=record_node.get("node_type", "CodeNode"),
            name=record_node.get("name", ""),
            qualified_name=record_node.get("qualified_name", ""),
            file_path=record_node.get("file_path", ""),
            start_line=record_node.get("start_line"),
            end_line=record_node.get("end_line"),
            properties=props,
        )
