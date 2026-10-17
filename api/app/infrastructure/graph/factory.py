from app.infrastructure.graph.interfaces import BaseGraphStore
from app.infrastructure.graph.neo4j_adapter import Neo4jGraphStoreAdapter

_graph_store_instance: BaseGraphStore | None = None


def get_graph_store(force_new: bool = False) -> BaseGraphStore:
    """Return a singleton or new instance of BaseGraphStore."""
    global _graph_store_instance
    if _graph_store_instance is None or force_new:
        _graph_store_instance = Neo4jGraphStoreAdapter()
    return _graph_store_instance


def reset_graph_store_instance() -> None:
    """Reset cached singleton instance (useful in tests)."""
    global _graph_store_instance
    _graph_store_instance = None
