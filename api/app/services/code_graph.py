import logging
import os
import uuid
from typing import Any

from tree_sitter_languages import get_parser

from app.infrastructure.graph.interfaces import (
    BaseGraphStore,
    GraphNeighborhood,
    GraphNode,
    GraphRelationship,
)

logger = logging.getLogger(__name__)


def make_node_id(
    repository_id: str,
    commit_sha: str,
    node_type: str,
    file_path: str,
    name: str,
) -> str:
    """Deterministic node ID generation."""
    return str(
        uuid.uuid5(
            uuid.NAMESPACE_DNS,
            f"{repository_id}:{commit_sha}:{node_type}:{file_path}:{name}",
        )
    )


class CodeGraphExtractor:
    """Syntax-directed extraction of code symbols, files, imports, and relationships."""

    def extract_from_source(
        self,
        repository_id: str,
        commit_sha: str,
        file_path: str,
        content: str,
    ) -> tuple[list[GraphNode], list[GraphRelationship]]:
        """Extract File, Class, Function, and Import nodes and relationships."""
        ext = os.path.splitext(file_path)[1].lower()
        if ext != ".py":
            # For non-Python files, record the File node
            file_node_id = make_node_id(
                repository_id, commit_sha, "File", file_path, file_path
            )
            file_node = GraphNode(
                node_id=file_node_id,
                repository_id=repository_id,
                commit_sha=commit_sha,
                node_type="File",
                name=os.path.basename(file_path),
                qualified_name=file_path,
                file_path=file_path,
                start_line=1,
                end_line=len(content.splitlines()) or 1,
                properties={"language": ext.lstrip(".") or "text"},
            )
            return [file_node], []

        parser = get_parser("python")
        source_bytes = content.encode("utf-8")
        tree = parser.parse(source_bytes)

        nodes: list[GraphNode] = []
        relationships: list[GraphRelationship] = []

        # 1. File node
        file_node_id = make_node_id(
            repository_id, commit_sha, "File", file_path, file_path
        )
        file_node = GraphNode(
            node_id=file_node_id,
            repository_id=repository_id,
            commit_sha=commit_sha,
            node_type="File",
            name=os.path.basename(file_path),
            qualified_name=file_path,
            file_path=file_path,
            start_line=1,
            end_line=len(content.splitlines()) or 1,
            properties={"language": "python"},
        )
        nodes.append(file_node)

        # 2. Traverse AST for classes, functions, and imports
        def visit(node: Any, parent_symbol_id: str | None = None) -> None:
            nonlocal nodes, relationships

            if node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    class_name = name_node.text.decode("utf-8")
                    class_node_id = make_node_id(
                        repository_id, commit_sha, "Class", file_path, class_name
                    )
                    c_node = GraphNode(
                        node_id=class_node_id,
                        repository_id=repository_id,
                        commit_sha=commit_sha,
                        node_type="Class",
                        name=class_name,
                        qualified_name=f"{file_path}:{class_name}",
                        file_path=file_path,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        properties={"verified": True},
                    )
                    nodes.append(c_node)

                    # File DEFINES Class
                    relationships.append(
                        GraphRelationship(
                            source_id=file_node_id,
                            target_id=class_node_id,
                            type="DEFINES",
                            repository_id=repository_id,
                            commit_sha=commit_sha,
                            properties={"verified": True},
                        )
                    )

                    # Recurse for class methods
                    for child in node.children:
                        visit(child, parent_symbol_id=class_node_id)
                    return

            elif node.type in ("function_definition", "async_function_definition"):
                name_node = node.child_by_field_name("name")
                if name_node:
                    fn_name = name_node.text.decode("utf-8")
                    fn_type = "Method" if parent_symbol_id else "Function"
                    fn_node_id = make_node_id(
                        repository_id, commit_sha, fn_type, file_path, fn_name
                    )
                    f_node = GraphNode(
                        node_id=fn_node_id,
                        repository_id=repository_id,
                        commit_sha=commit_sha,
                        node_type=fn_type,
                        name=fn_name,
                        qualified_name=f"{file_path}:{fn_name}",
                        file_path=file_path,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        properties={"verified": True},
                    )
                    nodes.append(f_node)

                    source_id = parent_symbol_id or file_node_id
                    relationships.append(
                        GraphRelationship(
                            source_id=source_id,
                            target_id=fn_node_id,
                            type="DEFINES",
                            repository_id=repository_id,
                            commit_sha=commit_sha,
                            properties={"verified": True},
                        )
                    )

            elif node.type in ("import_statement", "import_from_statement"):
                # Extract imported module or symbol name
                text = node.text.decode("utf-8").strip()
                import_name = text.split()[1] if len(text.split()) > 1 else text
                import_node_id = make_node_id(
                    repository_id, commit_sha, "Import", file_path, import_name
                )
                imp_node = GraphNode(
                    node_id=import_node_id,
                    repository_id=repository_id,
                    commit_sha=commit_sha,
                    node_type="Import",
                    name=import_name,
                    qualified_name=f"import:{import_name}",
                    file_path=file_path,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    properties={"verified": True, "raw_import": text},
                )
                nodes.append(imp_node)

                relationships.append(
                    GraphRelationship(
                        source_id=file_node_id,
                        target_id=import_node_id,
                        type="IMPORTS",
                        repository_id=repository_id,
                        commit_sha=commit_sha,
                        properties={"verified": True},
                    )
                )

            for child in node.children:
                visit(child, parent_symbol_id=parent_symbol_id)

        visit(tree.root_node)
        return nodes, relationships


class CodeGraphService:
    """Service to coordinate AST extraction and persistence to Neo4j graph store."""

    def __init__(self, graph_store: BaseGraphStore) -> None:
        self.graph_store = graph_store
        self.extractor = CodeGraphExtractor()

    async def index_file(
        self,
        repository_id: str,
        commit_sha: str,
        file_path: str,
        content: str,
    ) -> int:
        """Extract and index nodes and relationships for a file."""
        nodes, relationships = self.extractor.extract_from_source(
            repository_id=repository_id,
            commit_sha=commit_sha,
            file_path=file_path,
            content=content,
        )

        await self.graph_store.upsert_nodes(nodes)
        await self.graph_store.upsert_relationships(relationships)
        return len(nodes) + len(relationships)

    async def get_symbol_context(
        self,
        repository_id: str,
        commit_sha: str | None,
        symbol_name: str,
        file_path: str,
    ) -> GraphNeighborhood | None:
        """Retrieve symbol neighborhood to enhance RAG answers."""
        node_id = make_node_id(
            repository_id,
            commit_sha or "latest",
            "Function",
            file_path,
            symbol_name,
        )
        neighborhood = await self.graph_store.get_neighbors(
            node_id=node_id,
            repository_id=repository_id,
            commit_sha=commit_sha,
            direction="BOTH",
            depth=1,
            limit=20,
        )
        return neighborhood
