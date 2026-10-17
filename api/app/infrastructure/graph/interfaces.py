from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """Normalized code knowledge graph node representation."""

    node_id: str = Field(
        description="Deterministic unique node ID (e.g., repo:commit:type:qual_name)"
    )
    repository_id: str = Field(description="Repository UUID string for isolation")
    commit_sha: str = Field(description="Immutable Git commit SHA")
    node_type: str = Field(
        description="Type of code entity (e.g., 'File', 'Function', 'Class', 'Module')"
    )
    name: str = Field(description="Identifier or file name")
    qualified_name: str = Field(
        description="Fully qualified symbol path within project"
    )
    file_path: str = Field(description="Relative file path within repository")
    start_line: int | None = Field(default=None, description="1-indexed starting line")
    end_line: int | None = Field(default=None, description="1-indexed ending line")
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Safe metadata properties (no secrets or raw source code)",
    )


class GraphRelationship(BaseModel):
    """Normalized relationship connecting two code entities in the graph."""

    source_id: str = Field(description="node_id of the source node")
    target_id: str = Field(description="node_id of the target node")
    type: str = Field(
        description="Relationship type (e.g., 'CALLS', 'IMPORTS', 'DEFINES')"
    )
    repository_id: str = Field(description="Repository UUID string for isolation")
    commit_sha: str = Field(description="Immutable Git commit SHA")
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Safe relationship metadata (e.g., call site line number)",
    )


class GraphNeighborhood(BaseModel):
    """Bounded subgraph returned by neighborhood and dependency queries."""

    center_node: GraphNode | None = Field(
        default=None, description="Center node queried"
    )
    nodes: list[GraphNode] = Field(
        default_factory=list, description="Connected neighbor nodes"
    )
    relationships: list[GraphRelationship] = Field(
        default_factory=list, description="Edges connecting the neighborhood"
    )


class BaseGraphStore(ABC):
    """Abstract interface hiding graph database operations from application code."""

    @abstractmethod
    async def ensure_schema(self) -> None:
        """Create uniqueness constraints and composite indexes for code nodes."""
        ...

    @abstractmethod
    async def upsert_nodes(self, nodes: list[GraphNode]) -> int:
        """Upsert a batch of code graph nodes using parameterized Cypher."""
        ...

    @abstractmethod
    async def upsert_relationships(
        self, relationships: list[GraphRelationship]
    ) -> int:
        """Upsert a batch of code graph relationships using parameterized Cypher."""
        ...

    @abstractmethod
    async def get_node(
        self,
        node_id: str,
        repository_id: str,
        commit_sha: str | None = None,
    ) -> GraphNode | None:
        """Retrieve a single node scoped strictly by repository and commit."""
        ...

    @abstractmethod
    async def get_neighbors(
        self,
        node_id: str,
        repository_id: str,
        commit_sha: str | None = None,
        direction: str = "BOTH",
        depth: int = 1,
        limit: int = 50,
    ) -> GraphNeighborhood:
        """Query bounded neighborhood of a node, scoped by repo and commit."""
        ...

    @abstractmethod
    async def delete_by_repository(
        self,
        repository_id: str,
        commit_sha: str | None = None,
    ) -> int:
        """Delete all code nodes and relationships for a repository and commit."""
        ...

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Verify connectivity and retrieve server status."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close driver connection pools."""
        ...
