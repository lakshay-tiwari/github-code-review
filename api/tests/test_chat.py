import time
import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.api.deps import get_db, get_token_verifier
from app.core.config import settings
from app.core.security import ClerkTokenVerifier
from app.domain.models import Conversation, Message, Repository
from app.infrastructure.checkpoint import get_checkpointer
from app.infrastructure.db.session import get_db as app_get_db
from app.infrastructure.llm.interfaces import BaseChatModel, ChatMessage, ChatResponse
from app.infrastructure.vector.interfaces import ChunkPayload, VectorSearchResult
from app.main import app
from app.services.graph import CodebaseQAService, build_codebase_qa_graph

# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture(scope="session")
def rsa_key_pair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return {
        "private_key": private_key,
        "public_key": public_key,
        "kid": "cortex-chat-test-kid-1",
    }


@pytest.fixture
def test_verifier(rsa_key_pair):
    verifier = ClerkTokenVerifier(
        jwks_url="https://stunning-bobcat-41.clerk.accounts.dev/.well-known/jwks.json",
        expected_issuer="https://stunning-bobcat-41.clerk.accounts.dev",
        cache_ttl_seconds=3600,
    )
    verifier._keys_cache[rsa_key_pair["kid"]] = rsa_key_pair["public_key"]
    verifier._cache_expires_at = time.time() + 3600
    return verifier


@pytest.fixture
def make_token(rsa_key_pair):
    def _create_token(
        sub: str = "user_chat_test",
        iss: str = "https://stunning-bobcat-41.clerk.accounts.dev",
    ) -> str:
        now = int(time.time())
        payload = {
            "sub": sub,
            "iss": iss,
            "iat": now,
            "exp": now + 3600,
            "nbf": now - 10,
        }
        headers = {"kid": rsa_key_pair["kid"], "alg": "RS256"}
        return jwt.encode(
            payload,
            rsa_key_pair["private_key"],
            algorithm="RS256",
            headers=headers,
        )

    return _create_token


@pytest.fixture
async def db_session():
    test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    await test_engine.dispose()


@pytest.fixture
async def client(test_verifier, db_session):
    app.dependency_overrides[get_token_verifier] = lambda: test_verifier
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[app_get_db] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()


class MockLLM(BaseChatModel):
    def __init__(self, response_text: str = "This is a mock answer."):
        self.response_text = response_text

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-model"

    async def agenerate(
        self, messages: list[ChatMessage], **kwargs: Any
    ) -> ChatResponse:
        return ChatResponse(
            content=self.response_text,
            model="mock-model",
            usage={"total_tokens": 50},
        )

    async def astream(self, messages: list[ChatMessage], **kwargs: Any):
        for word in self.response_text.split(" "):
            yield word + " "


# ==============================================================================
# 1. LangGraph State Machine, Scoping, & Evidence Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_langgraph_rag_workflow_with_evidence():
    """Verify LangGraph flow retrieves evidence and generates answer."""
    mock_retrieval = AsyncMock()
    mock_chunk = VectorSearchResult(
        chunk_id="chunk-1",
        score=0.92,
        payload=ChunkPayload(
            chunk_id="chunk-1",
            repository_id="repo-123",
            commit_sha="commit-abc",
            file_path="src/service.py",
            start_line=10,
            end_line=25,
            symbol_name="process_data",
            content_hash="hash1",
            content="def process_data(): return 42",
        ),
    )
    mock_retrieval.search.return_value = [mock_chunk]
    mock_llm = MockLLM("The `process_data` function returns 42.")

    service = CodebaseQAService(llm=mock_llm, retrieval_service=mock_retrieval)
    result = await service.run(
        question="What does process_data return?",
        repository_id="repo-123",
        commit_sha="commit-abc",
        conversation_id="test-conv-1",
        use_in_memory=True,
    )

    assert result["has_sufficient_evidence"] is True
    assert len(result["citations"]) == 1
    assert result["citations"][0]["file_path"] == "src/service.py"
    assert result["citations"][0]["start_line"] == 10
    assert result["citations"][0]["end_line"] == 25
    assert result["citations"][0]["symbol_name"] == "process_data"
    assert "42" in result["answer"]


@pytest.mark.asyncio
async def test_langgraph_rag_insufficient_evidence():
    """Verify LangGraph reports insufficient evidence truthfully."""
    mock_retrieval = AsyncMock()
    mock_retrieval.search.return_value = []  # No chunks retrieved
    mock_llm = MockLLM("Fabricated answer.")

    service = CodebaseQAService(llm=mock_llm, retrieval_service=mock_retrieval)
    result = await service.run(
        question="Where is Kubernetes configured?",
        repository_id="repo-123",
        commit_sha="commit-abc",
        conversation_id="test-conv-insufficient",
        use_in_memory=True,
    )

    assert result["has_sufficient_evidence"] is False
    assert len(result["citations"]) == 0
    assert "could not find any code or documentation" in result["answer"]


# ==============================================================================
# 2. Checkpointer Save/Load & Recovery Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_checkpointer_in_memory_save_and_resume():
    """Verify LangGraph checkpoint state can be recovered using thread_id."""
    checkpointer = await get_checkpointer(use_in_memory=True)
    mock_retrieval = AsyncMock()
    mock_chunk = VectorSearchResult(
        chunk_id="chk-1",
        score=0.88,
        payload=ChunkPayload(
            chunk_id="chk-1",
            repository_id="repo-chk",
            commit_sha="sha-1",
            file_path="main.py",
            start_line=1,
            end_line=5,
            content_hash="h1",
            content="print('cortex')",
        ),
    )
    mock_retrieval.search.return_value = [mock_chunk]
    mock_llm = MockLLM("Grounded print statement.")

    app_graph = build_codebase_qa_graph(
        checkpointer=checkpointer,
        llm=mock_llm,
        retrieval_service=mock_retrieval,
    )

    thread_id = f"thread-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    # Initial invoke
    state_1 = await app_graph.ainvoke(
        {
            "question": "What does main do?",
            "repository_id": "repo-chk",
            "commit_sha": "sha-1",
            "history": [],
            "retrieved_chunks": [],
            "context_str": "",
            "has_sufficient_evidence": False,
            "citations": [],
            "answer": "",
        },
        config=config,
    )
    assert state_1["has_sufficient_evidence"] is True

    # Verify state was persisted and can be reloaded
    saved_state = await app_graph.aget_state(config)
    assert saved_state is not None
    assert saved_state.values["question"] == "What does main do?"
    assert saved_state.values["answer"] == "Grounded print statement."


@pytest.mark.asyncio
async def test_postgres_checkpointer_live_save_and_load():
    """Verify PostgreSQL checkpointer persists state to live Postgres container."""
    try:
        checkpointer = await get_checkpointer(use_in_memory=False)
    except Exception:
        pytest.skip("PostgreSQL checkpointer not available in current environment")

    thread_id = f"pg-test-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    mock_llm = MockLLM("Postgres checkpointer response.")
    mock_retrieval = AsyncMock()
    mock_retrieval.search.return_value = [
        VectorSearchResult(
            chunk_id="pg-c1",
            score=0.9,
            payload=ChunkPayload(
                chunk_id="pg-c1",
                repository_id="repo-pg",
                commit_sha="sha-pg",
                file_path="pg.py",
                start_line=1,
                end_line=2,
                content_hash="hp",
                content="val = 1",
            ),
        )
    ]

    app_graph = build_codebase_qa_graph(
        checkpointer=checkpointer,
        llm=mock_llm,
        retrieval_service=mock_retrieval,
    )

    await app_graph.ainvoke(
        {
            "question": "PG question?",
            "repository_id": "repo-pg",
            "commit_sha": "sha-pg",
            "history": [],
            "retrieved_chunks": [],
            "context_str": "",
            "has_sufficient_evidence": False,
            "citations": [],
            "answer": "",
        },
        config=config,
    )

    # Read back state from postgres checkpointer
    loaded_state = await app_graph.aget_state(config)
    assert loaded_state is not None
    assert loaded_state.values["question"] == "PG question?"
    assert loaded_state.values["has_sufficient_evidence"] is True


# ==============================================================================
# 3. Conversations & Messages API Authorization Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_create_conversation_unauthorized(client):
    res = await client.post(
        "/api/v1/conversations",
        json={"repository_id": str(uuid.uuid4()), "title": "Test"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_create_conversation_cross_user_forbidden(
    client, make_token, db_session
):
    user_alice = f"user_alice_{uuid.uuid4().hex[:8]}"
    user_bob = f"user_bob_{uuid.uuid4().hex[:8]}"
    token_bob = make_token(sub=user_bob)

    repo_alice = Repository(
        owner_id=user_alice,
        github_url=f"https://github.com/alice/repo-{uuid.uuid4().hex[:6]}",
        owner="alice",
        name="alice-repo",
        default_branch="main",
        status="ready",
    )
    db_session.add(repo_alice)
    await db_session.commit()

    try:
        # Bob tries to start a conversation on Alice's repository
        res = await client.post(
            "/api/v1/conversations",
            json={"repository_id": str(repo_alice.id), "title": "Bob's Chat"},
            headers={"Authorization": f"Bearer {token_bob}"},
        )
        assert res.status_code == 403
    finally:
        await db_session.delete(repo_alice)
        await db_session.commit()


@pytest.mark.asyncio
async def test_conversation_lifecycle_and_isolation(
    client, make_token, db_session
):
    user_alice = f"user_alice_{uuid.uuid4().hex[:8]}"
    user_bob = f"user_bob_{uuid.uuid4().hex[:8]}"
    token_alice = make_token(sub=user_alice)
    token_bob = make_token(sub=user_bob)

    repo = Repository(
        owner_id=user_alice,
        github_url=f"https://github.com/alice/repo-{uuid.uuid4().hex[:6]}",
        owner="alice",
        name="repo-chat",
        default_branch="main",
        status="ready",
    )
    db_session.add(repo)
    await db_session.commit()

    try:
        # 1. Alice creates conversation
        create_res = await client.post(
            "/api/v1/conversations",
            json={"repository_id": str(repo.id), "title": "Architecture Chat"},
            headers={"Authorization": f"Bearer {token_alice}"},
        )
        assert create_res.status_code == 201
        conv_data = create_res.json()
        conv_id = conv_data["id"]
        assert conv_data["title"] == "Architecture Chat"

        # 2. Bob cannot view Alice's conversation (403 Forbidden)
        bob_get = await client.get(
            f"/api/v1/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {token_bob}"},
        )
        assert bob_get.status_code == 403

        # 3. Alice can view her conversation
        alice_get = await client.get(
            f"/api/v1/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {token_alice}"},
        )
        assert alice_get.status_code == 200

        # 4. List conversations filtered by repository
        list_res = await client.get(
            f"/api/v1/conversations?repository_id={repo.id}",
            headers={"Authorization": f"Bearer {token_alice}"},
        )
        assert list_res.status_code == 200
        assert list_res.json()["total"] == 1

        # 5. Bob's list shows 0 conversations
        bob_list = await client.get(
            "/api/v1/conversations",
            headers={"Authorization": f"Bearer {token_bob}"},
        )
        assert bob_list.status_code == 200
        assert bob_list.json()["total"] == 0

        # 6. Delete conversation
        del_res = await client.delete(
            f"/api/v1/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {token_alice}"},
        )
        assert del_res.status_code == 204

    finally:
        await db_session.delete(repo)
        await db_session.commit()


# ==============================================================================
# 4. SSE Streaming & Message Persistence Integration Test
# ==============================================================================


@pytest.mark.asyncio
async def test_send_message_streaming_and_persistence(
    client, make_token, db_session
):
    user_id = f"user_stream_{uuid.uuid4().hex[:8]}"
    token = make_token(sub=user_id)

    repo = Repository(
        owner_id=user_id,
        github_url=f"https://github.com/org/repo-{uuid.uuid4().hex[:6]}",
        owner="org",
        name="stream-repo",
        default_branch="main",
        latest_commit_sha="abc1234567890abcdef1234567890abcdef1234",
        status="ready",
    )
    db_session.add(repo)
    await db_session.flush()

    conv = Conversation(
        repository_id=repo.id,
        owner_id=user_id,
        title="Streaming Test",
    )
    db_session.add(conv)
    await db_session.commit()

    mock_chunk = VectorSearchResult(
        chunk_id="chunk-stream-1",
        score=0.95,
        payload=ChunkPayload(
            chunk_id="chunk-stream-1",
            repository_id=str(repo.id),
            commit_sha=repo.latest_commit_sha,
            file_path="src/calc.py",
            start_line=1,
            end_line=10,
            symbol_name="add",
            content_hash="hcalc",
            content="def add(a, b): return a + b",
        ),
    )

    mock_llm = MockLLM("The `add` function computes a + b.")

    try:
        with (
            patch(
                "app.services.chat_stream.SemanticRetrievalService.search",
                return_value=[mock_chunk],
            ),
            patch("app.services.chat_stream.get_chat_model", return_value=mock_llm),
            patch(
                "app.services.chat_stream.get_checkpointer",
                return_value=await get_checkpointer(use_in_memory=True),
            ),
        ):
            res = await client.post(
                f"/api/v1/conversations/{conv.id}/messages",
                json={"content": "What does add do?"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 200
            assert "text/event-stream" in res.headers["content-type"]

            # Parse SSE events from body
            sse_content = res.text
            assert "event: start" in sse_content
            assert "event: citations" in sse_content
            assert "src/calc.py" in sse_content
            assert "event: chunk" in sse_content
            assert "event: done" in sse_content

            # Verify PostgreSQL persistence: user and assistant messages stored
            messages_res = await db_session.execute(
                select(Message)
                .where(Message.conversation_id == conv.id)
                .order_by(Message.created_at.asc())
            )
            saved_messages = messages_res.scalars().all()
            assert len(saved_messages) == 2

            user_msg = saved_messages[0]
            assert user_msg.role == "user"
            assert user_msg.content == "What does add do?"
            assert user_msg.status == "completed"

            assistant_msg = saved_messages[1]
            assert assistant_msg.role == "assistant"
            assert "The `add` function computes a + b." in assistant_msg.content
            assert assistant_msg.status == "completed"
            assert assistant_msg.citations is not None
            assert len(assistant_msg.citations) == 1
            assert assistant_msg.citations[0]["file_path"] == "src/calc.py"
            assert assistant_msg.citations[0]["start_line"] == 1
            assert assistant_msg.citations[0]["end_line"] == 10

    finally:
        await db_session.delete(repo)
        await db_session.commit()
