import os
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from app.core.config import settings
from app.infrastructure.embeddings.factory import (
    get_embedding_provider,
    reset_embedding_provider_instances,
)
from app.infrastructure.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddingProvider,
)
from app.infrastructure.llm.factory import (
    get_chat_model,
    reset_chat_model_instances,
)
from app.infrastructure.llm.groq_provider import GroqChatProvider
from app.infrastructure.llm.interfaces import ChatMessage, ChatResponse


@pytest.fixture(autouse=True)
def cleanup_factories():
    """Reset provider factory singletons before and after each test."""
    reset_chat_model_instances()
    reset_embedding_provider_instances()
    yield
    reset_chat_model_instances()
    reset_embedding_provider_instances()


# ==============================================================================
# LLM Provider & Groq Tests
# ==============================================================================


def test_chat_message_and_response_models():
    """Verify serialization and validation of domain LLM messages and responses."""
    msg = ChatMessage(role="user", content="Hello Cortex")
    assert msg.role == "user"
    assert msg.content == "Hello Cortex"

    resp = ChatResponse(
        content="Response text",
        model="llama-3.3-70b-versatile",
        usage={"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
        finish_reason="stop",
    )
    assert resp.content == "Response text"
    assert resp.usage["total_tokens"] == 20
    assert resp.finish_reason == "stop"


def test_groq_init_validation():
    """Verify that GroqChatProvider requires a non-empty API key."""
    with pytest.raises(ValueError, match="GROQ_API_KEY must be provided"):
        GroqChatProvider(api_key="")

    with pytest.raises(ValueError, match="GROQ_API_KEY must be provided"):
        GroqChatProvider(api_key="   ")

    provider = GroqChatProvider(api_key="gsk_test_key_placeholder")
    assert provider.provider_name == "groq"
    assert provider.model_name == "openai/gpt-oss-120b"


@pytest.mark.asyncio
async def test_groq_agenerate_mocked():
    """Verify that GroqChatProvider.agenerate converts messages and metadata."""
    provider = GroqChatProvider(
        api_key="gsk_test_mocked",
        model="llama-3.3-70b-versatile",
    )

    mock_response = MagicMock()
    mock_response.content = "Synthesized answer from codebase."
    mock_response.usage_metadata = {
        "input_tokens": 25,
        "output_tokens": 15,
        "total_tokens": 40,
    }
    mock_response.response_metadata = {"finish_reason": "stop"}

    mock_client = MagicMock()
    mock_client.ainvoke = AsyncMock(return_value=mock_response)
    provider._client = mock_client

    messages = [
        ChatMessage(role="system", content="You are Cortex assistant."),
        ChatMessage(role="user", content="Explain repo architecture."),
    ]
    result = await provider.agenerate(messages, temperature=0.1)

    assert isinstance(result, ChatResponse)
    assert result.content == "Synthesized answer from codebase."
    assert result.model == "llama-3.3-70b-versatile"
    assert result.usage["total_tokens"] == 40
    assert result.finish_reason == "stop"
    mock_client.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_groq_astream_mocked():
    """Verify that GroqChatProvider.astream yields chunks asynchronously."""
    provider = GroqChatProvider(api_key="gsk_test_mocked")

    async def mock_stream_generator(*args, **kwargs) -> AsyncIterator[MagicMock]:
        for chunk_text in ["Chunk 1 ", "Chunk 2 ", "Chunk 3"]:
            chunk = MagicMock()
            chunk.content = chunk_text
            yield chunk

    mock_client = MagicMock()
    mock_client.astream = mock_stream_generator
    provider._client = mock_client

    messages = [ChatMessage(role="user", content="Stream me a response")]
    collected: list[str] = []
    async for token in provider.astream(messages):
        collected.append(token)

    assert "".join(collected) == "Chunk 1 Chunk 2 Chunk 3"



def test_llm_factory_missing_api_key(monkeypatch):
    """Verify LLM factory rejects initialization when GROQ_API_KEY is not configured."""
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
    with pytest.raises(ValueError, match="GROQ_API_KEY is not configured"):
        get_chat_model("groq", force_new=True)


def test_llm_factory_unsupported_provider():
    """Verify LLM factory rejects unknown provider names."""
    with pytest.raises(ValueError, match="Unsupported LLM provider 'anthropic'"):
        get_chat_model("anthropic")


def test_llm_factory_singleton_caching(monkeypatch):
    """Verify LLM factory caches instances to avoid redundant initialization."""
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_singleton")
    instance1 = get_chat_model("groq")
    instance2 = get_chat_model("groq")
    assert instance1 is instance2


# ==============================================================================
# Embedding Provider & SentenceTransformer Tests
# ==============================================================================


def test_embedding_provider_metadata():
    """Verify embedding provider reports correct metadata and dimension."""
    provider = SentenceTransformerEmbeddingProvider(
        model_name="all-MiniLM-L6-v2",
        dimension=384,
        lazy_load=True,
    )
    assert provider.provider_name == "sentence-transformers"
    assert provider.model_name == "all-MiniLM-L6-v2"
    assert provider.dimension == 384
    # Lazy loading check: model is NOT loaded on instantiation
    assert provider._model is None
    provider.close()


@pytest.mark.asyncio
async def test_embedding_mocked_vector_shape_and_dimension():
    """Verify embedding provider computes 384-dimensional vectors without network."""
    provider = SentenceTransformerEmbeddingProvider(
        model_name="all-MiniLM-L6-v2",
        dimension=384,
        lazy_load=True,
    )

    # Mock the internal sentence-transformer model
    mock_model = MagicMock()
    # Mock encode returning 2 normalized vectors of dimension 384
    mock_vectors = np.ones((2, 384), dtype=np.float32) / np.sqrt(384)
    mock_model.encode.return_value = mock_vectors
    provider._model = mock_model

    documents = ["First code chunk", "Second code chunk"]
    results = await provider.embed_documents(documents)

    assert len(results) == 2
    assert len(results[0]) == 384
    assert len(results[1]) == 384
    assert all(isinstance(val, float) for val in results[0])

    # Test single query embedding
    mock_model.encode.return_value = np.ones((1, 384), dtype=np.float32)
    query_vec = await provider.embed_query("Find authentication logic")
    assert len(query_vec) == 384

    provider.close()


@pytest.mark.asyncio
async def test_embedding_empty_batch():
    """Verify embed_documents returns empty list on empty input."""
    provider = SentenceTransformerEmbeddingProvider(lazy_load=True)
    results = await provider.embed_documents([])
    assert results == []
    provider.close()


def test_embedding_factory_unsupported_provider():
    """Verify embedding factory rejects unsupported providers."""
    with pytest.raises(ValueError, match="Unsupported embedding provider 'openai'"):
        get_embedding_provider("openai")


def test_embedding_factory_singleton_caching():
    """Verify embedding factory caches provider instance."""
    inst1 = get_embedding_provider("sentence-transformers")
    inst2 = get_embedding_provider("sentence-transformers")
    assert inst1 is inst2


def test_llm_and_embedding_independence(monkeypatch):
    """Verify changing LLM provider/model does not impact the embedding provider."""
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_independent")
    monkeypatch.setattr(settings, "GROQ_MODEL", "llama-3.1-8b-instant")

    llm = get_chat_model("groq")
    embedder = get_embedding_provider("sentence-transformers")

    assert llm.model_name == "llama-3.1-8b-instant"
    assert embedder.dimension == 384
    assert embedder.provider_name == "sentence-transformers"


# ==============================================================================
# Opt-In / Conditional Live Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_live_sentence_transformer_inference():
    """Verify real SentenceTransformer produces 384-dimensional normalized vectors.

    Skips gracefully if local environment cannot reach HuggingFace to download weights.
    """
    try:
        provider = SentenceTransformerEmbeddingProvider(
            model_name="all-MiniLM-L6-v2",
            dimension=384,
            device="cpu",
            lazy_load=False,
        )
    except Exception as err:
        pytest.skip(f"SentenceTransformer local model download skipped: {err}")

    vec = await provider.embed_query("Testing Cortex semantic embedding")
    assert len(vec) == 384
    # Verify vector is unit normalized (norm close to 1.0)
    norm = sum(x * x for x in vec) ** 0.5
    assert abs(norm - 1.0) < 1e-3
    provider.close()


@pytest.mark.asyncio
async def test_live_groq_smoke_opt_in():
    """Opt-in live smoke test for Groq API.

    Only executes when RUN_LIVE_GROQ_TESTS=true and GROQ_API_KEY is configured.
    """
    if os.environ.get("RUN_LIVE_GROQ_TESTS") != "true" or not os.environ.get(
        "GROQ_API_KEY"
    ):
        pytest.skip(
            "Opt-in live Groq smoke test skipped. Set RUN_LIVE_GROQ_TESTS=true to run."
        )

    provider = GroqChatProvider(api_key=os.environ["GROQ_API_KEY"])
    response = await provider.agenerate(
        [ChatMessage(role="user", content="Reply with one word: 'READY'")]
    )
    assert len(response.content) > 0
    assert response.usage.get("total_tokens", 0) > 0
