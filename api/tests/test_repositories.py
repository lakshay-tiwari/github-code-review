import time
import uuid
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.deps import get_db, get_token_verifier
from app.core.config import settings
from app.core.security import ClerkTokenVerifier
from app.domain.models import IngestionJob, Repository
from app.infrastructure.db.session import get_db as app_get_db
from app.main import app
from app.services.github import (
    GitHubRateLimitError,
    GitHubService,
    InvalidRepositoryURLError,
    RepositoryNotFoundError,
    RepositoryPrivateError,
    RepositoryTooLargeError,
)
from app.workers.tasks import index_repository_task

# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture(scope="session")
def rsa_key_pair():
    """Generates a trusted RSA 2048-bit key pair for unit testing."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    kid = "cortex-repo-test-kid-1"
    return {
        "private_key": private_key,
        "public_key": public_key,
        "kid": kid,
    }


@pytest.fixture
def test_verifier(rsa_key_pair):
    """Provides a ClerkTokenVerifier preloaded with the test RSA public key."""
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
    """Factory fixture to create signed JWTs with customizable claims."""

    def _create_token(
        sub: str = "user_clerk_alice",
        iss: str = "https://stunning-bobcat-41.clerk.accounts.dev",
        exp_delta: int = 3600,
    ) -> str:
        now = int(time.time())
        payload = {
            "sub": sub,
            "iss": iss,
            "iat": now,
            "exp": now + exp_delta,
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
    """Provides an isolated database session with automatic rollback."""
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
    """AsyncClient fixture overriding auth verifier and db session."""
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
# Unit Tests — URL Validation and GitHubService
# ==============================================================================


def test_parse_github_url_valid():
    valid_cases = [
        ("https://github.com/psf/requests", "psf", "requests"),
        ("https://github.com/fastapi/fastapi/", "fastapi", "fastapi"),
        ("http://github.com/torvalds/linux.git", "torvalds", "linux"),
        ("https://www.github.com/owner_1/repo-2", "owner_1", "repo-2"),
    ]
    for url, exp_owner, exp_repo in valid_cases:
        owner, repo, canonical = GitHubService.parse_github_url(url)
        assert owner == exp_owner
        assert repo == exp_repo
        assert canonical == f"https://github.com/{exp_owner}/{exp_repo}"


def test_parse_github_url_invalid():
    invalid_cases = [
        "https://gitlab.com/psf/requests",
        "https://github.com/fastapi",
        "https://github.com/settings/profile",
        "ftp://github.com/owner/repo",
        "not_a_url",
        "",
    ]
    for url in invalid_cases:
        with pytest.raises(InvalidRepositoryURLError):
            GitHubService.parse_github_url(url)


@pytest.mark.asyncio
async def test_github_service_private_repo_rejected():
    mock_client = AsyncMock()
    mock_client.get.return_value = Response(
        status_code=200,
        json={"private": True, "size": 100},
    )
    service = GitHubService(client=mock_client)
    with pytest.raises(RepositoryPrivateError):
        await service.get_repository_details("owner", "private-repo")


@pytest.mark.asyncio
async def test_github_service_size_limit_rejected():
    mock_client = AsyncMock()
    # 300 MB in KB = 307200 KB
    mock_client.get.return_value = Response(
        status_code=200,
        json={"private": False, "size": 307200, "default_branch": "main"},
    )
    service = GitHubService(max_size_mb=200, client=mock_client)
    with pytest.raises(RepositoryTooLargeError):
        await service.get_repository_details("owner", "huge-repo")


@pytest.mark.asyncio
async def test_github_service_not_found():
    mock_client = AsyncMock()
    mock_client.get.return_value = Response(status_code=404, text="Not Found")
    service = GitHubService(client=mock_client)
    with pytest.raises(RepositoryNotFoundError):
        await service.get_repository_details("owner", "nonexistent")


@pytest.mark.asyncio
async def test_github_service_rate_limited():
    mock_client = AsyncMock()
    mock_client.get.return_value = Response(
        status_code=403, text="API rate limit exceeded"
    )
    service = GitHubService(client=mock_client)
    with pytest.raises(GitHubRateLimitError):
        await service.get_repository_details("owner", "repo")


# ==============================================================================
# Endpoint Integration Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_submit_repository_unauthorized(client):
    res = await client.post(
        "/api/v1/repositories",
        json={"github_url": "https://github.com/fastapi/fastapi"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_submit_repository_invalid_url(client, make_token):
    token = make_token(sub="user_alice")
    res = await client.post(
        "/api/v1/repositories",
        json={"github_url": "https://gitlab.com/fastapi/fastapi"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    assert "Invalid GitHub URL" in res.json()["detail"]


@pytest.mark.asyncio
async def test_submit_repository_success(client, make_token, db_session):
    user_id = f"user_test_{uuid.uuid4().hex[:8]}"
    token = make_token(sub=user_id)
    repo_name = f"cortex-test-repo-{uuid.uuid4().hex[:6]}"
    github_url = f"https://github.com/cortex-org/{repo_name}"

    mock_details = {
        "owner": "cortex-org",
        "name": repo_name,
        "default_branch": "main",
        "size_kb": 1024,
    }
    mock_sha = "a1b2c3d4e5f6789012345678901234567890abcd"

    with (
        patch.object(
            GitHubService, "get_repository_details", return_value=mock_details
        ),
        patch.object(
            GitHubService, "get_latest_commit_sha", return_value=mock_sha
        ),
        patch(
            "app.api.v1.endpoints.repositories.enqueue_index_repository"
        ) as mock_enqueue,
    ):
        mock_enqueue.return_value = "celery-job-1"

        res = await client.post(
            "/api/v1/repositories",
            json={"github_url": github_url},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["owner"] == "cortex-org"
        assert data["name"] == repo_name
        assert data["status"] == "pending"
        assert data["latest_commit_sha"] == mock_sha
        assert data["latest_job"] is not None
        assert data["latest_job"]["status"] == "queued"
        mock_enqueue.assert_called_once()

        repo_id = uuid.UUID(data["id"])

        # Verify database record exists
        repo_res = await db_session.execute(
            select(Repository).where(Repository.id == repo_id)
        )
        saved_repo = repo_res.scalar_one_or_none()
        assert saved_repo is not None
        assert saved_repo.owner_id == user_id

        # Clean up
        await db_session.delete(saved_repo)
        await db_session.commit()


@pytest.mark.asyncio
async def test_repository_list_and_cross_user_isolation(client, make_token, db_session):
    user_alice = f"user_alice_{uuid.uuid4().hex[:8]}"
    user_bob = f"user_bob_{uuid.uuid4().hex[:8]}"

    token_alice = make_token(sub=user_alice)
    token_bob = make_token(sub=user_bob)

    repo_alice = Repository(
        owner_id=user_alice,
        github_url=f"https://github.com/alice/repo-{uuid.uuid4().hex[:6]}",
        owner="alice",
        name="alice-repo",
        default_branch="main",
        status="ready",
    )
    repo_bob = Repository(
        owner_id=user_bob,
        github_url=f"https://github.com/bob/repo-{uuid.uuid4().hex[:6]}",
        owner="bob",
        name="bob-repo",
        default_branch="main",
        status="ready",
    )
    db_session.add_all([repo_alice, repo_bob])
    await db_session.commit()

    try:
        # 1. Alice lists her repositories
        res_alice = await client.get(
            "/api/v1/repositories",
            headers={"Authorization": f"Bearer {token_alice}"},
        )
        assert res_alice.status_code == 200
        alice_repos = res_alice.json()["repositories"]
        assert len(alice_repos) == 1
        assert alice_repos[0]["owner_id"] == user_alice
        assert alice_repos[0]["name"] == "alice-repo"

        # 2. Bob lists his repositories
        res_bob = await client.get(
            "/api/v1/repositories",
            headers={"Authorization": f"Bearer {token_bob}"},
        )
        assert res_bob.status_code == 200
        bob_repos = res_bob.json()["repositories"]
        assert len(bob_repos) == 1
        assert bob_repos[0]["owner_id"] == user_bob
        assert bob_repos[0]["name"] == "bob-repo"

        # 3. Bob attempts to access Alice's repository directly -> 403 Forbidden
        res_forbidden = await client.get(
            f"/api/v1/repositories/{repo_alice.id}",
            headers={"Authorization": f"Bearer {token_bob}"},
        )
        assert res_forbidden.status_code == 403

    finally:
        await db_session.delete(repo_alice)
        await db_session.delete(repo_bob)
        await db_session.commit()


@pytest.mark.asyncio
async def test_job_status_ownership_enforcement(client, make_token, db_session):
    user_alice = f"user_alice_{uuid.uuid4().hex[:8]}"
    user_bob = f"user_bob_{uuid.uuid4().hex[:8]}"

    token_alice = make_token(sub=user_alice)
    token_bob = make_token(sub=user_bob)

    repo_alice = Repository(
        owner_id=user_alice,
        github_url=f"https://github.com/alice/repo-{uuid.uuid4().hex[:6]}",
        owner="alice",
        name="alice-repo",
        default_branch="main",
        status="indexing",
    )
    db_session.add(repo_alice)
    await db_session.flush()

    job_alice = IngestionJob(
        repository_id=repo_alice.id,
        status="in_progress",
        progress=45,
        current_step="cloning",
    )
    db_session.add(job_alice)
    await db_session.commit()

    try:
        # Alice can check status of her own job
        res_alice = await client.get(
            f"/api/v1/jobs/{job_alice.id}",
            headers={"Authorization": f"Bearer {token_alice}"},
        )
        assert res_alice.status_code == 200
        assert res_alice.json()["progress"] == 45
        assert res_alice.json()["current_step"] == "cloning"

        # Bob cannot check status of Alice's job -> 403 Forbidden
        res_bob = await client.get(
            f"/api/v1/jobs/{job_alice.id}",
            headers={"Authorization": f"Bearer {token_bob}"},
        )
        assert res_bob.status_code == 403

    finally:
        await db_session.delete(repo_alice)
        await db_session.commit()


# ==============================================================================
# Worker Task Execution Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_index_repository_task_eager(db_session):
    user_id = f"user_worker_test_{uuid.uuid4().hex[:8]}"
    repo = Repository(
        owner_id=user_id,
        github_url=f"https://github.com/org/repo-{uuid.uuid4().hex[:6]}",
        owner="org",
        name="repo-worker",
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

    mock_details = {
        "owner": "org",
        "name": "repo-worker",
        "default_branch": "main",
        "size_kb": 2048,
    }
    mock_sha = "fedcba9876543210fedcba9876543210fedcba98"

    with (
        patch.object(
            GitHubService, "get_repository_details", return_value=mock_details
        ),
        patch.object(
            GitHubService, "get_latest_commit_sha", return_value=mock_sha
        ),
        patch(
            "app.services.cloner.RepositoryCloner.download_and_extract_tarball"
        ) as mock_clone,
        patch(
            "app.services.indexer.RepositoryIndexer.index_directory"
        ) as mock_index_dir,
    ):
        mock_clone.return_value = "/tmp/dummy_extracted_path"
        mock_index_dir.return_value = {
            "total_files": 1,
            "indexed_files": 1,
            "total_chunks": 2,
            "upserted_vectors": 2,
        }

        # Run Celery task synchronously via .apply()
        task_res = index_repository_task.apply(kwargs={"job_id": str(job.id)})
        assert task_res.successful()
        result_data = task_res.result
        assert result_data["status"] == "success"
        assert result_data["commit_sha"] == mock_sha

        # Verify job and repository state updated in PostgreSQL
        await db_session.refresh(job)
        await db_session.refresh(repo)

        assert job.status == "completed"
        assert job.progress == 100
        assert job.current_step == "completed"
        assert job.commit_sha == mock_sha
        assert repo.status == "ready"
        assert repo.latest_commit_sha == mock_sha

    # Clean up
    await db_session.delete(repo)
    await db_session.commit()
