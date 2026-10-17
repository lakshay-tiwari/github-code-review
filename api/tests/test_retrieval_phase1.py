"""
Phase 1 RAG retrieval tests.

Coverage:
- Question classifier: all 4 intent levels + edge cases
- Repository-wide retrieval: expansion triggered when initial results are sparse
- File-specific retrieval: file_path_prefix applied; scoped results
- Empty result set: insufficient-evidence path taken
- Insufficient evidence for broad questions (< 2 distinct files)
- Multi-file retrieval: workflow / repo-wide questions accepted with ≥ 2 files

No paid LLM API or live external services are required. All vector store and
embedding calls are replaced with AsyncMock / synchronous stubs.
"""

from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.infrastructure.llm.interfaces import BaseChatModel, ChatMessage, ChatResponse
from app.infrastructure.vector.interfaces import ChunkPayload, VectorSearchResult
from app.services.classifier import RETRIEVAL_PRESETS, classify_question
from app.services.graph import (
    CodebaseQAService,
    CodebaseQAState,
    retrieve_context_node,
    validate_evidence_node,
)
from app.services.retrieval import SemanticRetrievalService

# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------


class MockLLM(BaseChatModel):
    def __init__(self, text: str = "Mock answer."):
        self._text = text

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-model"

    async def agenerate(self, messages: list[ChatMessage], **kwargs: Any) -> ChatResponse:
        return ChatResponse(content=self._text, model="mock-model", usage={})

    async def astream(self, messages: list[ChatMessage], **kwargs: Any):
        yield self._text


def make_chunk(
    file_path: str = "src/service.py",
    start_line: int = 1,
    end_line: int = 10,
    symbol_name: str | None = "do_thing",
    score: float = 0.85,
    repo_id: str = "repo-test",
    commit: str = "sha-abc",
) -> VectorSearchResult:
    chunk_id = f"{repo_id}:{file_path}:{start_line}"
    return VectorSearchResult(
        chunk_id=chunk_id,
        score=score,
        payload=ChunkPayload(
            chunk_id=chunk_id,
            repository_id=repo_id,
            commit_sha=commit,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            symbol_name=symbol_name,
            content_hash="hash-" + chunk_id.replace(":", "_"),
            content=f"# content of {file_path}:{start_line}\ndef {symbol_name}(): pass",
        ),
    )


# ---------------------------------------------------------------------------
# 1. Question classifier tests
# ---------------------------------------------------------------------------


class TestClassifier:
    def test_file_specific_extension(self):
        assert classify_question("explain src/auth.py") == "file_specific"

    def test_file_specific_with_path(self):
        assert classify_question("What is in app/services/indexer.py?") == "file_specific"

    def test_symbol_specific_function_call(self):
        assert classify_question("What does process_data() return?") == "symbol_specific"

    def test_symbol_specific_class_keyword(self):
        assert classify_question("Explain class UserService") == "symbol_specific"

    def test_symbol_specific_def_keyword(self):
        assert classify_question("How does def authenticate work?") == "symbol_specific"

    def test_workflow_intent(self):
        q = "Walk me through the request lifecycle end-to-end"
        assert classify_question(q) == "workflow"

    def test_workflow_pipeline(self):
        assert classify_question("Describe the indexing pipeline") == "workflow"

    def test_repository_wide_architecture(self):
        assert classify_question("What is the overall architecture?") == "repository_wide"

    def test_repository_wide_codebase(self):
        assert classify_question("How is this codebase structured?") == "repository_wide"

    def test_repository_wide_list_all(self):
        assert classify_question("List all endpoints") == "repository_wide"

    def test_presets_exist_for_all_intents(self):
        for intent in ("file_specific", "symbol_specific", "workflow", "repository_wide"):
            assert intent in RETRIEVAL_PRESETS
            preset = RETRIEVAL_PRESETS[intent]
            assert "limit" in preset
            assert "score_threshold" in preset
            assert "expansion_limit" in preset
            assert "required_distinct_files" in preset

    def test_repository_wide_requires_multi_file(self):
        assert RETRIEVAL_PRESETS["repository_wide"]["required_distinct_files"] >= 2

    def test_workflow_requires_multi_file(self):
        assert RETRIEVAL_PRESETS["workflow"]["required_distinct_files"] >= 2

    def test_file_specific_requires_single_file(self):
        assert RETRIEVAL_PRESETS["file_specific"]["required_distinct_files"] == 1


# ---------------------------------------------------------------------------
# 2. retrieve_context_node tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retrieve_context_symbol_specific():
    """Symbol-specific question uses standard limit and returns chunks correctly."""
    mock_service = AsyncMock(spec=SemanticRetrievalService)
    chunk = make_chunk(file_path="src/calc.py", symbol_name="add")
    mock_service.search.return_value = [chunk]

    state: CodebaseQAState = {
        "question": "What does add() return?",
        "repository_id": "repo-1",
        "commit_sha": "sha-1",
        "history": [],
        "question_intent": "",
        "retrieved_chunks": [],
        "context_str": "",
        "has_sufficient_evidence": False,
        "citations": [],
        "answer": "",
    }

    result = await retrieve_context_node(state, retrieval_service=mock_service)

    assert result["question_intent"] == "symbol_specific"
    assert len(result["retrieved_chunks"]) == 1
    assert result["retrieved_chunks"][0]["file_path"] == "src/calc.py"
    assert "src/calc.py" in result["context_str"]


@pytest.mark.asyncio
async def test_retrieve_context_file_specific_applies_prefix():
    """File-specific question passes file_path_prefix to the vector store."""
    mock_service = AsyncMock(spec=SemanticRetrievalService)
    chunk = make_chunk(file_path="src/auth.py", symbol_name="login")
    mock_service.search.return_value = [chunk]

    state: CodebaseQAState = {
        "question": "Explain src/auth.py authentication flow",
        "repository_id": "repo-1",
        "commit_sha": "sha-1",
        "history": [],
        "question_intent": "",
        "retrieved_chunks": [],
        "context_str": "",
        "has_sufficient_evidence": False,
        "citations": [],
        "answer": "",
    }

    result = await retrieve_context_node(state, retrieval_service=mock_service)

    assert result["question_intent"] == "file_specific"
    # Verify the search was called with a file_path_prefix
    call_kwargs = mock_service.search.call_args_list[0].kwargs
    assert call_kwargs.get("file_path_prefix") is not None


@pytest.mark.asyncio
async def test_retrieve_context_expansion_triggered_for_repo_wide():
    """Repo-wide question with sparse initial results triggers expansion search."""
    mock_service = AsyncMock(spec=SemanticRetrievalService)

    # First call (initial): returns only 1 chunk — below min_chunks_for_expansion=4
    initial_chunk = make_chunk(file_path="src/main.py", score=0.5)
    # Second call (expansion): returns 3 more unique chunks from different files
    expansion_chunks = [
        make_chunk(file_path="src/auth.py", score=0.45, symbol_name="login"),
        make_chunk(file_path="src/db.py", score=0.42, symbol_name="connect"),
        make_chunk(file_path="src/config.py", score=0.40, symbol_name="Settings"),
    ]
    mock_service.search.side_effect = [
        [initial_chunk],   # initial pass
        expansion_chunks,  # expansion pass
    ]
    mock_service.get_indexed_files.return_value = [
        "src/auth.py", "src/config.py", "src/db.py", "src/main.py"
    ]

    state: CodebaseQAState = {
        "question": "What is the overall architecture of this codebase?",
        "repository_id": "repo-1",
        "commit_sha": "sha-1",
        "history": [],
        "question_intent": "",
        "retrieved_chunks": [],
        "context_str": "",
        "has_sufficient_evidence": False,
        "citations": [],
        "answer": "",
    }

    result = await retrieve_context_node(state, retrieval_service=mock_service)

    assert result["question_intent"] == "repository_wide"
    # Both passes should have been called
    assert mock_service.search.call_count == 2
    # Merged: 1 initial + 3 expansion = 4 total unique chunks
    assert len(result["retrieved_chunks"]) == 4


@pytest.mark.asyncio
async def test_retrieve_context_no_expansion_when_enough_chunks():
    """No expansion search when initial results meet the minimum threshold."""
    mock_service = AsyncMock(spec=SemanticRetrievalService)

    # symbol_specific requires min 2 chunks for expansion; provide 3
    chunks = [
        make_chunk(file_path="src/calc.py", symbol_name="add", start_line=1),
        make_chunk(file_path="src/calc.py", symbol_name="subtract", start_line=10),
        make_chunk(file_path="src/calc.py", symbol_name="multiply", start_line=20),
    ]
    mock_service.search.return_value = chunks

    state: CodebaseQAState = {
        "question": "What does add() do?",
        "repository_id": "repo-1",
        "commit_sha": "sha-1",
        "history": [],
        "question_intent": "",
        "retrieved_chunks": [],
        "context_str": "",
        "has_sufficient_evidence": False,
        "citations": [],
        "answer": "",
    }

    result = await retrieve_context_node(state, retrieval_service=mock_service)

    # Only one search call — no expansion needed
    assert mock_service.search.call_count == 1
    assert len(result["retrieved_chunks"]) == 3


# ---------------------------------------------------------------------------
# 3. validate_evidence_node tests
# ---------------------------------------------------------------------------


def test_validate_evidence_empty_chunks():
    """Empty chunks → insufficient evidence with explanatory message."""
    state: CodebaseQAState = {
        "question": "Where is Redis configured?",
        "repository_id": "repo-1",
        "commit_sha": None,
        "history": [],
        "question_intent": "symbol_specific",
        "retrieved_chunks": [],
        "context_str": "",
        "has_sufficient_evidence": False,
        "citations": [],
        "answer": "",
    }

    result = validate_evidence_node(state)

    assert result["has_sufficient_evidence"] is False
    assert result["citations"] == []
    assert "could not find" in result["answer"]


def test_validate_evidence_single_file_symbol_question():
    """Symbol-specific question passes with a single file chunk."""
    chunk = {
        "file_path": "src/calc.py",
        "start_line": 1,
        "end_line": 10,
        "commit_sha": "sha-1",
        "symbol_name": "add",
        "content": "def add(a, b): return a + b",
        "score": 0.9,
    }
    state: CodebaseQAState = {
        "question": "What does add() do?",
        "repository_id": "repo-1",
        "commit_sha": "sha-1",
        "history": [],
        "question_intent": "symbol_specific",
        "retrieved_chunks": [chunk],
        "context_str": "--- File: src/calc.py ---\ndef add(a, b): return a + b",
        "has_sufficient_evidence": False,
        "citations": [],
        "answer": "",
    }

    result = validate_evidence_node(state)

    assert result["has_sufficient_evidence"] is True
    assert len(result["citations"]) == 1
    assert result["citations"][0]["file_path"] == "src/calc.py"
    assert result["citations"][0]["symbol_name"] == "add"


def test_validate_evidence_repository_wide_insufficient_single_file():
    """Repository-wide question with only 1 distinct file → insufficient evidence."""
    chunks = [
        {
            "file_path": "src/auth.py",
            "start_line": i * 10,
            "end_line": i * 10 + 9,
            "commit_sha": "sha-1",
            "symbol_name": f"fn_{i}",
            "content": f"def fn_{i}(): pass",
            "score": 0.7,
        }
        for i in range(3)
    ]
    state: CodebaseQAState = {
        "question": "How is the whole repository structured?",
        "repository_id": "repo-1",
        "commit_sha": "sha-1",
        "history": [],
        "question_intent": "repository_wide",
        "retrieved_chunks": chunks,
        "context_str": "some content",
        "has_sufficient_evidence": False,
        "citations": [],
        "answer": "",
    }

    result = validate_evidence_node(state)

    assert result["has_sufficient_evidence"] is False
    assert "1 file" in result["answer"] or "scope" in result["answer"]


def test_validate_evidence_repository_wide_multi_file_passes():
    """Repository-wide question with ≥ 2 distinct files → sufficient evidence."""
    chunks = [
        {
            "file_path": "src/auth.py",
            "start_line": 1,
            "end_line": 10,
            "commit_sha": "sha-1",
            "symbol_name": "login",
            "content": "def login(): pass",
            "score": 0.8,
        },
        {
            "file_path": "src/db.py",
            "start_line": 5,
            "end_line": 20,
            "commit_sha": "sha-1",
            "symbol_name": "connect",
            "content": "def connect(): pass",
            "score": 0.75,
        },
        {
            "file_path": "src/config.py",
            "start_line": 1,
            "end_line": 8,
            "commit_sha": "sha-1",
            "symbol_name": "Settings",
            "content": "class Settings: pass",
            "score": 0.7,
        },
    ]
    state: CodebaseQAState = {
        "question": "Describe the overall architecture of the codebase.",
        "repository_id": "repo-1",
        "commit_sha": "sha-1",
        "history": [],
        "question_intent": "repository_wide",
        "retrieved_chunks": chunks,
        "context_str": "some multi-file context",
        "has_sufficient_evidence": False,
        "citations": [],
        "answer": "",
    }

    result = validate_evidence_node(state)

    assert result["has_sufficient_evidence"] is True
    assert len(result["citations"]) == 3
    file_paths = {c["file_path"] for c in result["citations"]}
    assert "src/auth.py" in file_paths
    assert "src/db.py" in file_paths


def test_validate_evidence_workflow_requires_two_files():
    """Workflow question fails with only 1 distinct file."""
    chunk = {
        "file_path": "src/pipeline.py",
        "start_line": 1,
        "end_line": 30,
        "commit_sha": "sha-1",
        "symbol_name": "run_pipeline",
        "content": "def run_pipeline(): pass",
        "score": 0.8,
    }
    state: CodebaseQAState = {
        "question": "Walk me through the request lifecycle",
        "repository_id": "repo-1",
        "commit_sha": "sha-1",
        "history": [],
        "question_intent": "workflow",
        "retrieved_chunks": [chunk],
        "context_str": "some context",
        "has_sufficient_evidence": False,
        "citations": [],
        "answer": "",
    }

    result = validate_evidence_node(state)

    assert result["has_sufficient_evidence"] is False


# ---------------------------------------------------------------------------
# 4. End-to-end: CodebaseQAService with intent-driven retrieval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_codebase_qa_service_file_specific_e2e():
    """File-specific question: service retrieves, validates, generates answer."""
    mock_retrieval = AsyncMock(spec=SemanticRetrievalService)
    chunk = make_chunk(file_path="src/auth.py", symbol_name="login")
    mock_retrieval.search.return_value = [chunk]

    mock_llm = MockLLM("The login function handles authentication.")

    service = CodebaseQAService(llm=mock_llm, retrieval_service=mock_retrieval)
    result = await service.run(
        question="What does src/auth.py do?",
        repository_id="repo-test",
        commit_sha="sha-abc",
        conversation_id="conv-file-1",
        use_in_memory=True,
    )

    assert result["has_sufficient_evidence"] is True
    assert result["question_intent"] == "file_specific"
    assert len(result["citations"]) == 1
    assert result["citations"][0]["file_path"] == "src/auth.py"
    assert "login" in result["answer"].lower() or "authentication" in result["answer"].lower()


@pytest.mark.asyncio
async def test_codebase_qa_service_repo_wide_multi_file_e2e():
    """Repository-wide question with multi-file evidence succeeds end-to-end."""
    mock_retrieval = AsyncMock(spec=SemanticRetrievalService)

    # Provide enough chunks from 3 different files on first call
    chunks = [
        make_chunk(file_path="src/auth.py", symbol_name="login", start_line=1),
        make_chunk(file_path="src/db.py", symbol_name="connect", start_line=5),
        make_chunk(file_path="src/config.py", symbol_name="Settings", start_line=1),
        make_chunk(file_path="src/main.py", symbol_name="app", start_line=1),
    ]
    mock_retrieval.search.return_value = chunks
    mock_retrieval.get_indexed_files.return_value = [
        "src/auth.py", "src/config.py", "src/db.py", "src/main.py"
    ]

    mock_llm = MockLLM("The repository uses FastAPI with Postgres and Qdrant.")

    service = CodebaseQAService(llm=mock_llm, retrieval_service=mock_retrieval)
    result = await service.run(
        question="What is the overall architecture of this codebase?",
        repository_id="repo-test",
        commit_sha="sha-abc",
        conversation_id="conv-repo-1",
        use_in_memory=True,
    )

    assert result["has_sufficient_evidence"] is True
    assert result["question_intent"] == "repository_wide"
    # Should have citations from multiple files
    cited_files = {c["file_path"] for c in result["citations"]}
    assert len(cited_files) >= 2


@pytest.mark.asyncio
async def test_codebase_qa_service_empty_results_e2e():
    """Empty vector results produce a truthful insufficient-evidence answer."""
    mock_retrieval = AsyncMock(spec=SemanticRetrievalService)
    mock_retrieval.search.return_value = []
    mock_retrieval.get_indexed_files.return_value = []

    mock_llm = MockLLM("Fabricated answer.")  # should NOT be called

    service = CodebaseQAService(llm=mock_llm, retrieval_service=mock_retrieval)
    result = await service.run(
        question="Where is Kubernetes configured?",
        repository_id="repo-test",
        commit_sha="sha-abc",
        conversation_id="conv-empty-1",
        use_in_memory=True,
    )

    assert result["has_sufficient_evidence"] is False
    assert result["citations"] == []
    assert "could not find" in result["answer"]
    # LLM fabricated text should not appear
    assert "Fabricated" not in result["answer"]


@pytest.mark.asyncio
async def test_codebase_qa_service_symbol_specific_e2e():
    """Symbol-specific question resolves with a single function chunk."""
    mock_retrieval = AsyncMock(spec=SemanticRetrievalService)
    chunk = make_chunk(file_path="src/calc.py", symbol_name="add", start_line=1)
    mock_retrieval.search.return_value = [chunk]

    mock_llm = MockLLM("The add function returns the sum of two numbers.")

    service = CodebaseQAService(llm=mock_llm, retrieval_service=mock_retrieval)
    result = await service.run(
        question="What does add() return?",
        repository_id="repo-test",
        commit_sha="sha-abc",
        conversation_id="conv-sym-1",
        use_in_memory=True,
    )

    assert result["has_sufficient_evidence"] is True
    assert result["question_intent"] == "symbol_specific"
    assert result["citations"][0]["symbol_name"] == "add"
    assert "sum" in result["answer"].lower()
