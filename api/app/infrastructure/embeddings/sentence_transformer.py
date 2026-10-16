import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.infrastructure.embeddings.interfaces import BaseEmbeddingProvider

logger = logging.getLogger("cortex.embeddings.sentence_transformer")


class SentenceTransformerEmbeddingProvider(BaseEmbeddingProvider):
    """Local embedding provider using SentenceTransformers (e.g., all-MiniLM-L6-v2).

    Key features:
    - Lazy loading: Weights are loaded only on first inference request.
    - Singleton reuse: Model is kept in memory to avoid reload overhead.
    - Non-blocking: Inference is dispatched to a background thread pool executor.
    - Verified dimension: Validates runtime embedding dimension matches configuration.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        dimension: int = 384,
        device: str | None = None,
        lazy_load: bool = True,
    ) -> None:
        self._model_name = model_name
        self._dimension = dimension
        self._device = device or "cpu"
        self._model: Any = None
        self._lock = asyncio.Lock()
        self._executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="embedder"
        )

        if not lazy_load:
            self._load_model()

    @property
    def provider_name(self) -> str:
        return "sentence-transformers"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def _load_model(self) -> None:
        """Synchronously load model weights and verify dimension."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info(
                    "Loading SentenceTransformer '%s' on %s...",
                    self._model_name,
                    self._device,
                )
                model = SentenceTransformer(self._model_name, device=self._device)
                if hasattr(model, "get_embedding_dimension"):
                    actual_dim = model.get_embedding_dimension()
                else:
                    actual_dim = model.get_sentence_embedding_dimension()

                if actual_dim and actual_dim != self._dimension:
                    logger.warning(
                        "Configured dimension (%d) != actual model dimension (%d). "
                        "Updating to %d.",
                        self._dimension,
                        actual_dim,
                        actual_dim,
                    )
                    self._dimension = actual_dim
                self._model = model
            except Exception as err:
                logger.error(
                    "Failed to load SentenceTransformer '%s': %s",
                    self._model_name,
                    err,
                )
                raise RuntimeError(
                    f"Failed to load embedding model '{self._model_name}': {err}"
                ) from err

    async def _ensure_model_loaded(self) -> Any:
        """Asynchronously ensure model is loaded using double-checked locking."""
        if self._model is not None:
            return self._model

        async with self._lock:
            if self._model is None:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(self._executor, self._load_model)
            return self._model

    async def embed_query(self, text: str) -> list[float]:
        """Compute an embedding vector for a single search query."""
        results = await self.embed_documents([text])
        if not results:
            return [0.0] * self._dimension
        return results[0]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Compute normalized embedding vectors for a batch of texts."""
        if not texts:
            return []

        model = await self._ensure_model_loaded()

        def _encode_batch() -> list[list[float]]:
            embeddings = model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return [vec.tolist() for vec in embeddings]

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, _encode_batch)

    def close(self) -> None:
        """Shut down background thread pool executor."""
        self._executor.shutdown(wait=False)
