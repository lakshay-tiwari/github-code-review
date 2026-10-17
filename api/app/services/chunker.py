import hashlib
import logging
import os
import uuid
from typing import Any

from tree_sitter_languages import get_parser

from app.core.config import settings
from app.infrastructure.vector.interfaces import ChunkPayload

logger = logging.getLogger(__name__)

# Map file extensions to Tree-sitter language identifiers
EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cs": "c_sharp",
    ".rb": "ruby",
    ".php": "php",
    ".html": "html",
    ".md": "markdown",
}

# Tree-sitter node types representing top-level or scoped semantic code units
DEFINITION_NODE_TYPES = {
    "python": {
        "function_definition": "function",
        "async_function_definition": "function",
        "class_definition": "class",
    },
    "javascript": {
        "function_declaration": "function",
        "class_declaration": "class",
        "method_definition": "method",
        "generator_function_declaration": "function",
    },
    "typescript": {
        "function_declaration": "function",
        "class_declaration": "class",
        "method_definition": "method",
        "interface_declaration": "interface",
        "type_alias_declaration": "type",
    },
    "tsx": {
        "function_declaration": "function",
        "class_declaration": "class",
        "method_definition": "method",
        "interface_declaration": "interface",
    },
    "go": {
        "function_declaration": "function",
        "method_declaration": "method",
        "type_declaration": "type",
    },
    "rust": {
        "function_item": "function",
        "impl_item": "impl",
        "struct_item": "struct",
        "enum_item": "enum",
        "trait_item": "trait",
    },
    "java": {
        "method_declaration": "method",
        "class_declaration": "class",
        "interface_declaration": "interface",
        "constructor_declaration": "constructor",
    },
    "c": {
        "function_definition": "function",
        "struct_specifier": "struct",
    },
    "cpp": {
        "function_definition": "function",
        "class_specifier": "class",
        "struct_specifier": "struct",
    },
}

# UUID namespace for deterministic chunk IDs
CHUNK_NAMESPACE = uuid.NAMESPACE_DNS


def estimate_tokens(text: str) -> int:
    """Approximate token count (roughly 3.8 to 4 chars per token for code)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def make_chunk_id(
    repository_id: str,
    commit_sha: str,
    file_path: str,
    start_line: int,
    end_line: int,
    content_hash: str,
) -> str:
    """Generate a deterministic UUIDv5 identifier for a chunk."""
    seed = (
        f"{repository_id}:{commit_sha}:{file_path}:"
        f"{start_line}:{end_line}:{content_hash[:16]}"
    )
    return str(uuid.uuid5(CHUNK_NAMESPACE, seed))


class CodeChunker:
    """Syntax-aware code chunker with fallback sliding-window splitting."""

    def __init__(
        self,
        target_tokens: int = 500,
        max_tokens: int = 800,
        overlap_tokens: int = 50,
        min_tokens: int = 20,
    ) -> None:
        self.target_tokens = target_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.min_tokens = min_tokens

    def chunk_file(
        self,
        file_path: str,
        content: str,
        repository_id: str,
        commit_sha: str,
    ) -> list[ChunkPayload]:
        """Parse and chunk source file, falling back to sliding-window."""
        if not content.strip():
            return []

        lines = content.splitlines(keepends=True)
        total_lines = len(lines)
        if total_lines == 0:
            return []

        _, ext = os.path.splitext(file_path.lower())
        language = EXTENSION_TO_LANGUAGE.get(ext)

        # Attempt syntax-aware Tree-sitter chunking if language is supported
        if language and language in DEFINITION_NODE_TYPES:
            try:
                chunks = self._chunk_with_tree_sitter(
                    file_path=file_path,
                    content=content,
                    lines=lines,
                    language=language,
                    repository_id=repository_id,
                    commit_sha=commit_sha,
                )
                if chunks:
                    return chunks
            except Exception as exc:
                logger.debug(
                    "Tree-sitter parse failed for %s (%s). Falling back: %s",
                    file_path,
                    language,
                    exc,
                )

        # Fallback to line-based token-aware sliding window
        return self._chunk_with_lines(
            file_path=file_path,
            lines=lines,
            language=language or "text",
            repository_id=repository_id,
            commit_sha=commit_sha,
        )

    def _chunk_with_tree_sitter(
        self,
        file_path: str,
        content: str,
        lines: list[str],
        language: str,
        repository_id: str,
        commit_sha: str,
    ) -> list[ChunkPayload]:
        """Extract syntax definitions using Tree-sitter AST nodes."""
        parser = get_parser(language)
        content_bytes = content.encode("utf-8")
        tree = parser.parse(content_bytes)

        target_types = DEFINITION_NODE_TYPES.get(language, {})
        chunks: list[ChunkPayload] = []
        covered_lines: set[int] = set()

        def visit_node(node: Any) -> None:
            if node.type in target_types:
                symbol_type = target_types[node.type]
                name_node = node.child_by_field_name("name")
                symbol_name = (
                    name_node.text.decode("utf-8") if name_node else None
                )

                # 1-indexed line numbers
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1

                # Extract exact node slice from file lines
                node_lines = lines[start_line - 1 : end_line]
                node_text = "".join(node_lines)
                token_count = estimate_tokens(node_text)

                if token_count <= self.max_tokens:
                    # Semantic node fits in a single chunk
                    if token_count >= self.min_tokens:
                        content_hash = hashlib.sha256(
                            node_text.encode("utf-8")
                        ).hexdigest()
                        chunk_id = make_chunk_id(
                            repository_id=repository_id,
                            commit_sha=commit_sha,
                            file_path=file_path,
                            start_line=start_line,
                            end_line=end_line,
                            content_hash=content_hash,
                        )
                        chunks.append(
                            ChunkPayload(
                                chunk_id=chunk_id,
                                repository_id=repository_id,
                                commit_sha=commit_sha,
                                file_path=file_path,
                                start_line=start_line,
                                end_line=end_line,
                                language=language,
                                symbol_name=symbol_name,
                                symbol_type=symbol_type,
                                content_hash=content_hash,
                                content=node_text,
                                embedding_model=settings.EMBEDDING_MODEL,
                                embedding_version="v1",
                            )
                        )
                        covered_lines.update(range(start_line, end_line + 1))
                else:
                    # Oversized definition: split with sliding window
                    sub_chunks = self._chunk_with_lines(
                        file_path=file_path,
                        lines=node_lines,
                        language=language,
                        repository_id=repository_id,
                        commit_sha=commit_sha,
                        base_line_offset=start_line - 1,
                        symbol_name=symbol_name,
                        symbol_type=symbol_type,
                    )
                    chunks.extend(sub_chunks)
                    covered_lines.update(range(start_line, end_line + 1))
            else:
                for child in node.children:
                    visit_node(child)

        visit_node(tree.root_node)

        # Chunk any uncovered module-level header or leftover code
        uncovered = [
            i for i in range(1, len(lines) + 1) if i not in covered_lines
        ]
        if uncovered:
            # Group consecutive uncovered line blocks
            block_start = uncovered[0]
            prev_line = uncovered[0]

            for line_no in uncovered[1:]:
                if line_no == prev_line + 1:
                    prev_line = line_no
                else:
                    block_lines = lines[block_start - 1 : prev_line]
                    if estimate_tokens("".join(block_lines)) >= self.min_tokens:
                        chunks.extend(
                            self._chunk_with_lines(
                                file_path=file_path,
                                lines=block_lines,
                                language=language,
                                repository_id=repository_id,
                                commit_sha=commit_sha,
                                base_line_offset=block_start - 1,
                            )
                        )
                    block_start = line_no
                    prev_line = line_no

            block_lines = lines[block_start - 1 : prev_line]
            if estimate_tokens("".join(block_lines)) >= self.min_tokens:
                chunks.extend(
                    self._chunk_with_lines(
                        file_path=file_path,
                        lines=block_lines,
                        language=language,
                        repository_id=repository_id,
                        commit_sha=commit_sha,
                        base_line_offset=block_start - 1,
                    )
                )

        # Sort chunks by starting line
        chunks.sort(key=lambda c: (c.start_line, c.end_line))
        return chunks

    def _chunk_with_lines(
        self,
        file_path: str,
        lines: list[str],
        language: str,
        repository_id: str,
        commit_sha: str,
        base_line_offset: int = 0,
        symbol_name: str | None = None,
        symbol_type: str | None = None,
    ) -> list[ChunkPayload]:
        """Sliding-window line chunker with token bounds and line preservation."""
        chunks: list[ChunkPayload] = []
        total_lines = len(lines)
        if total_lines == 0:
            return chunks

        line_tokens = [estimate_tokens(line) for line in lines]
        idx = 0

        while idx < total_lines:
            chunk_tokens = 0
            end_idx = idx

            # Accumulate lines until target_tokens is reached or exceeded
            while end_idx < total_lines and chunk_tokens < self.target_tokens:
                chunk_tokens += line_tokens[end_idx]
                end_idx += 1

            # Ensure at least 1 line is included
            if end_idx == idx:
                end_idx = idx + 1

            chunk_lines = lines[idx:end_idx]
            chunk_text = "".join(chunk_lines)

            # 1-indexed line numbers
            start_line = base_line_offset + idx + 1
            end_line = base_line_offset + end_idx

            content_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
            chunk_id = make_chunk_id(
                repository_id=repository_id,
                commit_sha=commit_sha,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                content_hash=content_hash,
            )

            chunks.append(
                ChunkPayload(
                    chunk_id=chunk_id,
                    repository_id=repository_id,
                    commit_sha=commit_sha,
                    file_path=file_path,
                    start_line=start_line,
                    end_line=end_line,
                    language=language,
                    symbol_name=symbol_name,
                    symbol_type=symbol_type,
                    content_hash=content_hash,
                    content=chunk_text,
                    embedding_model=settings.EMBEDDING_MODEL,
                    embedding_version="v1",
                )
            )

            # Advance index with overlap
            if end_idx >= total_lines:
                break

            # Calculate line overlap backwards
            overlap_acc = 0
            back_idx = end_idx
            while back_idx > idx and overlap_acc < self.overlap_tokens:
                back_idx -= 1
                overlap_acc += line_tokens[back_idx]

            # Prevent zero progression
            idx = max(idx + 1, back_idx)

        return chunks
