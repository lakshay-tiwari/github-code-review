import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any

from app.infrastructure.embeddings.factory import get_embedding_provider
from app.infrastructure.graph.factory import get_graph_store
from app.infrastructure.vector.factory import get_vector_store
from app.infrastructure.vector.interfaces import ChunkPayload
from app.services.chunker import CodeChunker
from app.services.code_graph import CodeGraphService
from app.services.file_filter import is_binary_content, should_index_file

logger = logging.getLogger(__name__)


class RepositoryIndexer:
    """Orchestrates file discovery, chunking, embedding, vector upsert, and graph."""

    def __init__(
        self,
        batch_size: int = 64,
        chunker: CodeChunker | None = None,
        graph_service: CodeGraphService | None = None,
    ) -> None:
        self.batch_size = batch_size
        self.chunker = chunker or CodeChunker()
        self.graph_service = graph_service or CodeGraphService(get_graph_store())

    async def index_directory(
        self,
        repository_id: str,
        commit_sha: str,
        root_dir: str,
        progress_callback: Callable[[int, str], Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
        """Index all valid files in root_dir into Qdrant."""
        embedding_provider = get_embedding_provider()
        vector_store = get_vector_store()

        # Ensure collection exists with exact matching dimension
        await vector_store.ensure_collection(dimension=embedding_provider.dimension)

        if progress_callback:
            await progress_callback(55, "discovering_files")

        # 1. Discover and filter files
        eligible_files: list[tuple[str, str]] = []  # (abs_path, rel_path)
        for root, dirs, files in os.walk(root_dir):
            # Prune excluded directories in-place for fast traversal
            dirs[:] = [
                d
                for d in dirs
                if should_index_file(os.path.join(d, "file.txt"))
            ]

            for file_name in files:
                abs_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(abs_path, root_dir).replace("\\", "/")

                try:
                    file_size = os.path.getsize(abs_path)
                except OSError:
                    continue

                if should_index_file(rel_path, file_size_bytes=file_size):
                    eligible_files.append((abs_path, rel_path))

        logger.info(
            "Found %d candidate files to index for repo %s",
            len(eligible_files),
            repository_id,
        )

        if progress_callback:
            await progress_callback(65, "chunking_code")

        # 2. Syntax-aware chunking
        all_chunks: list[ChunkPayload] = []
        files_indexed_count = 0

        for abs_path, rel_path in eligible_files:
            try:
                with open(abs_path, "rb") as f:
                    raw_bytes = f.read()

                # Skip binary files
                if is_binary_content(raw_bytes):
                    continue

                try:
                    content = raw_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    content = raw_bytes.decode("latin-1", errors="replace")

                chunks = self.chunker.chunk_file(
                    file_path=rel_path,
                    content=content,
                    repository_id=repository_id,
                    commit_sha=commit_sha,
                )
                if chunks:
                    all_chunks.extend(chunks)
                    files_indexed_count += 1

                # Extract and persist code graph entities (functions, classes, imports)
                try:
                    await self.graph_service.index_file(
                        repository_id=repository_id,
                        commit_sha=commit_sha,
                        file_path=rel_path,
                        content=content,
                    )
                except Exception as graph_err:
                    logger.debug(
                        "Graph extraction skipped for %s: %s", rel_path, graph_err
                    )

            except Exception as exc:
                logger.warning("Failed to chunk file %s: %s", rel_path, exc)

        logger.info(
            "Generated %d code chunks from %d files for repo %s",
            len(all_chunks),
            files_indexed_count,
            repository_id,
        )

        if not all_chunks:
            return {
                "files_indexed": files_indexed_count,
                "chunks_created": 0,
                "vectors_upserted": 0,
                "embedding_model": embedding_provider.model_name,
                "dimension": embedding_provider.dimension,
            }

        if progress_callback:
            await progress_callback(75, "generating_embeddings")

        # 3. Generate embeddings in batches and upsert to Qdrant
        total_upserted = 0
        total_chunks = len(all_chunks)

        for i in range(0, total_chunks, self.batch_size):
            batch = all_chunks[i : i + self.batch_size]
            texts = [chunk.content for chunk in batch]

            vectors = await embedding_provider.embed_documents(texts)
            pairs = list(zip(batch, vectors, strict=True))

            upserted = await vector_store.upsert_chunks(pairs)
            total_upserted += upserted

            if progress_callback:
                progress_pct = 75 + int((i + len(batch)) / total_chunks * 20)
                await progress_callback(
                    min(95, progress_pct), "upserting_vectors"
                )

        if progress_callback:
            await progress_callback(100, "indexing_completed")

        return {
            "files_indexed": files_indexed_count,
            "chunks_created": total_chunks,
            "vectors_upserted": total_upserted,
            "embedding_model": embedding_provider.model_name,
            "dimension": embedding_provider.dimension,
        }
