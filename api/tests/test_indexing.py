import time
import uuid
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.api.deps import get_db, get_token_verifier
from app.core.config import settings
from app.core.security import ClerkTokenVerifier
from app.domain.models import IngestionJob, Repository
from app.infrastructure.db.session import get_db as app_get_db
from app.infrastructure.vector.interfaces import ChunkPayload, VectorSearchResult
from app.main import app
from app.services.chunker import CodeChunker
from app.services.file_filter import is_binary_content, should_index_file
from app.services.retrieval import SemanticRetrievalService
from app.workers.tasks import index_repository_task

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
        "kid": "cortex-index-test-kid-1",
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
        sub: str = "user_clerk_alice",
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


# ==============================================================================
# 1. File Filter & Secret Exclusion Tests
# ==============================================================================


def test_file_filter_excluded_directories():
    assert not should_index_file("node_modules/express/index.js")
    assert not should_index_file(".git/config")
    assert not should_index_file(".venv/lib/site.py")
    assert not should_index_file("dist/bundle.js")
    assert not should_index_file("build/main.o")
    assert not should_index_file("__pycache__/app.cpython-312.pyc")
    assert should_index_file("src/components/button.tsx")
    assert should_index_file("app/main.py")


def test_file_filter_excluded_extensions_and_lockfiles():
    assert not should_index_file("assets/logo.png")
    assert not should_index_file("bin/server.exe")
    assert not should_index_file("lib/utils.pyc")
    assert not should_index_file("package-lock.json")
    assert not should_index_file("pnpm-lock.yaml")
    assert not should_index_file("poetry.lock")
    assert not should_index_file("static/bundle.min.js")
    assert should_index_file("package.json")
    assert should_index_file("pyproject.toml")


def test_file_filter_secrets():
    assert not should_index_file(".env")
    assert not should_index_file(".env.local")
    assert not should_index_file(".env.production")
    assert not should_index_file("certs/server.pem")
    assert not should_index_file("keys/private.key")
    assert not should_index_file("id_rsa")
    assert not should_index_file("id_ed25519")
    assert not should_index_file("config/google-credentials.json")
    assert should_index_file("config/settings.json")


def test_is_binary_content():
    text_sample = b"def hello():\n    return 'world'\n"
    binary_sample = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00"

    assert not is_binary_content(text_sample)
    assert is_binary_content(binary_sample)


# ==============================================================================
# 2. Syntax-Aware Tree-Sitter & Line Chunker Tests
# ==============================================================================


def test_tree_sitter_python_chunking():
    chunker = CodeChunker(target_tokens=200, max_tokens=400)
    code = """# Module header
import math

def calculate_hypotenuse(a: float, b: float) -> float:
    \"\"\"Calculate hypotenuse length.\"\"\"
    return math.sqrt(a ** 2 + b ** 2)

class Vector3D:
    \"\"\"Represents a 3D vector.\"\"\"
    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z

    def length(self) -> float:
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)
"""
    chunks = chunker.chunk_file(
        file_path="math_utils.py",
        content=code,
        repository_id="repo-1",
        commit_sha="sha-111",
    )
    assert len(chunks) >= 2

    symbols = [c.symbol_name for c in chunks if c.symbol_name]
    assert "calculate_hypotenuse" in symbols
    assert "Vector3D" in symbols

    for c in chunks:
        assert c.start_line <= c.end_line
        assert c.language == "python"
        assert c.commit_sha == "sha-111"
        assert len(c.content_hash) == 64


def test_tree_sitter_typescript_chunking():
    chunker = CodeChunker(target_tokens=200, max_tokens=400)
    code = """export interface UserProps {
    id: string;
    email: string;
}

export class UserService {
    private users: Map<string, UserProps> = new Map();

    public getUser(id: string): UserProps | undefined {
        return this.users.get(id);
    }
}
"""
    chunks = chunker.chunk_file(
        file_path="src/user.ts",
        content=code,
        repository_id="repo-1",
        commit_sha="sha-111",
    )
    assert len(chunks) >= 1
    symbols = [c.symbol_name for c in chunks if c.symbol_name]
    assert "UserService" in symbols or "UserProps" in symbols


def test_chunker_deterministic_ids_and_deduplication():
    chunker = CodeChunker()
    code = "def sample():\n    return 42\n"

    chunks_run1 = chunker.chunk_file(
        file_path="app.py",
        content=code,
        repository_id="repo-1",
        commit_sha="sha-1",
    )
    chunks_run2 = chunker.chunk_file(
        file_path="app.py",
        content=code,
        repository_id="repo-1",
        commit_sha="sha-1",
    )

    assert len(chunks_run1) == len(chunks_run2)
    assert chunks_run1[0].chunk_id == chunks_run2[0].chunk_id
    assert chunks_run1[0].content_hash == chunks_run2[0].content_hash


def test_chunker_fallback_for_unsupported_language():
    chunker = CodeChunker(target_tokens=50, max_tokens=100)
    lines = [f"Line {i} content text information" for i in range(1, 30)]
    content = "\n".join(lines)

    chunks = chunker.chunk_file(
        file_path="notes.txt",
        content=content,
        repository_id="repo-1",
        commit_sha="sha-1",
    )
    assert len(chunks) > 1
    for c in chunks:
        assert c.language == "text"
        assert c.start_line <= c.end_line


# ==============================================================================
# 3. Semantic Retrieval Service Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_semantic_retrieval_service_mocked():
    retrieval_service = SemanticRetrievalService()

    mock_search_result = VectorSearchResult(
        chunk_id="chunk-123",
        score=0.88,
        payload=ChunkPayload(
            chunk_id="chunk-123",
            repository_id="repo-abc",
            commit_sha="commit-xyz",
            file_path="src/main.py",
            start_line=1,
            end_line=10,
            language="python",
            symbol_name="main",
            symbol_type="function",
            content_hash="hash-123",
            content="def main(): pass",
            embedding_model="all-MiniLM-L6-v2",
        ),
    )

    with (
        patch("app.services.retrieval.get_embedding_provider") as mock_get_embed,
        patch("app.services.retrieval.get_vector_store") as mock_get_store,
    ):
        mock_embed = AsyncMock()
        mock_embed.embed_query.return_value = [0.1] * 384
        mock_get_embed.return_value = mock_embed

        mock_store = AsyncMock()
        mock_store.search.return_value = [mock_search_result]
        mock_get_store.return_value = mock_store

        results = await retrieval_service.search(
            query="find main function",
            repository_id="repo-abc",
            commit_sha="commit-xyz",
            limit=5,
        )

        assert len(results) == 1
        assert results[0].score == 0.88
        assert results[0].payload.file_path == "src/main.py"
        assert results[0].payload.symbol_name == "main"
        mock_store.search.assert_called_once()


# ==============================================================================
# 4. Search API Endpoint Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_search_repository_unauthorized(client):
    fake_id = uuid.uuid4()
    res = await client.post(
        f"/api/v1/repositories/{fake_id}/search",
        json={"query": "how does auth work"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_search_repository_cross_user_forbidden(
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
        # Bob tries to search Alice's repo -> 403 Forbidden
        res = await client.post(
            f"/api/v1/repositories/{repo_alice.id}/search",
            json={"query": "secret code"},
            headers={"Authorization": f"Bearer {token_bob}"},
        )
        assert res.status_code == 403
    finally:
        await db_session.delete(repo_alice)
        await db_session.commit()


@pytest.mark.asyncio
async def test_search_repository_success(client, make_token, db_session):
    user_alice = f"user_alice_{uuid.uuid4().hex[:8]}"
    token_alice = make_token(sub=user_alice)

    repo_alice = Repository(
        owner_id=user_alice,
        github_url=f"https://github.com/alice/repo-{uuid.uuid4().hex[:6]}",
        owner="alice",
        name="alice-repo",
        default_branch="main",
        latest_commit_sha="commit-alice-sha",
        status="ready",
    )
    db_session.add(repo_alice)
    await db_session.commit()

    mock_search_item = VectorSearchResult(
        chunk_id="chunk-456",
        score=0.92,
        payload=ChunkPayload(
            chunk_id="chunk-456",
            repository_id=str(repo_alice.id),
            commit_sha="commit-alice-sha",
            file_path="src/auth.py",
            start_line=15,
            end_line=30,
            language="python",
            symbol_name="login",
            symbol_type="function",
            content_hash="hash-456",
            content="def login(): pass",
            embedding_model="all-MiniLM-L6-v2",
        ),
    )

    with patch(
        "app.services.retrieval.SemanticRetrievalService.search"
    ) as mock_search:
        mock_search.return_value = [mock_search_item]

        res = await client.post(
            f"/api/v1/repositories/{repo_alice.id}/search",
            json={"query": "user login", "limit": 10},
            headers={"Authorization": f"Bearer {token_alice}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["query"] == "user login"
        assert data["total"] == 1
        assert data["results"][0]["file_path"] == "src/auth.py"
        assert data["results"][0]["start_line"] == 15
        assert data["results"][0]["symbol_name"] == "login"

    await db_session.delete(repo_alice)
    await db_session.commit()


# ==============================================================================
# 5. Full Ingestion Celery Task Integration Test
# ==============================================================================


@pytest.mark.asyncio
async def test_full_index_repository_task(db_session, tmp_path):
    user_id = f"user_e2e_{uuid.uuid4().hex[:8]}"
    repo = Repository(
        owner_id=user_id,
        github_url=f"https://github.com/org/e2e-{uuid.uuid4().hex[:6]}",
        owner="org",
        name="e2e-repo",
        default_branch="main",
        status="pending",
    )
    db_session.add(repo)
    await db_session.flush()

    job = IngestionJob(
        repository_id=repo.id,
        status="queued",
        progress=0,
        current_step="queued",
    )
    db_session.add(job)
    await db_session.commit()

    # Create dummy source code in a temp directory
    sample_repo_dir = tmp_path / "sample_code"
    sample_repo_dir.mkdir()
    (sample_repo_dir / "calc.py").write_text(
        "def multiply(a: int, b: int) -> int:\n    return a * b\n"
    )
    (sample_repo_dir / "notes.txt").write_text("General repository documentation.")

    commit_sha = "abc1234567890abcdef1234567890abcdef1234"

    mock_meta = {
        "owner": "org",
        "name": "e2e-repo",
        "default_branch": "main",
        "size_kb": 100,
    }

    with (
        patch(
            "app.services.github.GitHubService.get_repository_details",
            return_value=mock_meta,
        ),
        patch(
            "app.services.github.GitHubService.get_latest_commit_sha",
            return_value=commit_sha,
        ),
        patch(
            "app.services.cloner.RepositoryCloner.download_and_extract_tarball",
            return_value=str(sample_repo_dir),
        ),
    ):
        task_res = index_repository_task.apply(kwargs={"job_id": str(job.id)})
        assert task_res.successful()
        result_data = task_res.result
        assert result_data["status"] == "success"

        # Check job status and repository state in PostgreSQL
        await db_session.refresh(job)
        await db_session.refresh(repo)

        assert job.status == "completed"
        assert job.progress == 100
        assert job.current_step == "completed"
        assert repo.status == "ready"
        assert repo.latest_commit_sha == commit_sha

    # Clean up
    await db_session.delete(repo)
    await db_session.commit()
