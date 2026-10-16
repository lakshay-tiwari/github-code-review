import time
import uuid
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.deps import get_db, get_token_verifier
from app.core.config import settings
from app.core.security import ClerkTokenVerifier
from app.domain.models import Conversation, IngestionJob, Message, Repository
from app.infrastructure.db.session import get_db as app_get_db
from app.main import app


@pytest.fixture(scope="session")
def rsa_key_pair():
    """Generates a trusted RSA 2048-bit key pair for unit testing."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    kid = "cortex-test-kid-1"
    return {
        "private_key": private_key,
        "public_key": public_key,
        "kid": kid,
    }


@pytest.fixture(scope="session")
def untrusted_rsa_key_pair():
    """Generates an untrusted RSA key pair to verify signature rejection."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    kid = "untrusted-kid-forgery"
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
    # Preload the in-memory cache with the test public key
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
        nbf_delta: int = -10,
        azp: str | None = None,
        sid: str | None = "sess_test_123",
        private_key: Any = None,
        kid: str | None = None,
    ) -> str:
        now = int(time.time())
        payload = {
            "sub": sub,
            "iss": iss,
            "iat": now,
            "exp": now + exp_delta,
            "nbf": now + nbf_delta,
        }
        if sid:
            payload["sid"] = sid
        if azp:
            payload["azp"] = azp

        signing_key = private_key or rsa_key_pair["private_key"]
        key_id = kid if kid is not None else rsa_key_pair["kid"]
        headers = {"kid": key_id} if key_id else {}

        pem_bytes = signing_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return jwt.encode(payload, pem_bytes, algorithm="RS256", headers=headers)

    return _create_token


@pytest.fixture
async def db_session():
    """Provides an isolated database session with NullPool for tests."""
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def client(test_verifier, db_session: AsyncSession):
    """Provides an authenticated HTTPX test client with overridden dependencies."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_token_verifier] = lambda: test_verifier
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[app_get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ==============================================================================
# Token Verification Unit Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_auth_missing_header(client: httpx.AsyncClient):
    """Reject requests with no Authorization header with 401."""
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert "Authorization header is required" in res.json()["detail"]


@pytest.mark.asyncio
async def test_auth_malformed_scheme(client: httpx.AsyncClient):
    """Reject requests with non-Bearer or malformed authorization schemes with 401."""
    res_basic = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Basic dXNlcjpwYXNz"}
    )
    assert res_basic.status_code == 401
    assert "Invalid authorization scheme" in res_basic.json()["detail"]

    res_empty = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer "}
    )
    assert res_empty.status_code == 401

    res_parts = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer foo bar baz"}
    )
    assert res_parts.status_code == 401


@pytest.mark.asyncio
async def test_auth_garbage_token(client: httpx.AsyncClient):
    """Reject garbage token strings with 401."""
    res = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-valid-jwt"}
    )
    assert res.status_code == 401
    assert "Malformed token header" in res.json()["detail"]


@pytest.mark.asyncio
async def test_auth_expired_token(client: httpx.AsyncClient, make_token):
    """Reject expired tokens with 401."""
    token = make_token(exp_delta=-60)
    res = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 401
    assert "Token has expired" in res.json()["detail"]


@pytest.mark.asyncio
async def test_auth_immature_token(client: httpx.AsyncClient, make_token):
    """Reject tokens where nbf is in the future with 401."""
    token = make_token(nbf_delta=3600)
    res = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 401
    assert "Token is not yet active" in res.json()["detail"]


@pytest.mark.asyncio
async def test_auth_invalid_signature(
    client: httpx.AsyncClient, make_token, untrusted_rsa_key_pair
):
    """Reject tokens signed with untrusted keys with 401."""
    # Sign with untrusted key, but specify trusted kid to test signature check
    token = make_token(
        private_key=untrusted_rsa_key_pair["private_key"],
        kid="cortex-test-kid-1",
    )
    res = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 401
    assert "Invalid token signature" in res.json()["detail"]


@pytest.mark.asyncio
async def test_auth_invalid_issuer(client: httpx.AsyncClient, make_token):
    """Reject tokens from untrusted issuers with 401."""
    token = make_token(iss="https://malicious-issuer.example.com")
    res = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 401
    assert "Invalid token issuer" in res.json()["detail"]


@pytest.mark.asyncio
async def test_auth_invalid_authorized_party(
    client: httpx.AsyncClient, test_verifier, make_token
):
    """Reject tokens with mismatched authorized party when configured."""
    test_verifier.expected_azp = "http://localhost:3000"
    token = make_token(azp="http://attacker-site.com")
    res = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 401
    assert "Invalid authorized party" in res.json()["detail"]
    test_verifier.expected_azp = None  # Reset


@pytest.mark.asyncio
async def test_auth_valid_token_me(client: httpx.AsyncClient, make_token):
    """Verify that a valid token correctly extracts trusted identity claims."""
    token = make_token(sub="user_clerk_verified_123", sid="sess_active_987")
    res = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == "user_clerk_verified_123"
    assert data["session_id"] == "sess_active_987"
    assert "claims" in data
    assert data["claims"]["sub"] == "user_clerk_verified_123"


# ==============================================================================
# Resource Ownership Enforcement Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_repository_ownership_enforcement(
    client: httpx.AsyncClient, db_session: AsyncSession, make_token
):
    """Verify that only the repository owner can access protected endpoints."""
    alice_id = f"user_alice_{uuid.uuid4().hex[:6]}"
    bob_id = f"user_bob_{uuid.uuid4().hex[:6]}"

    repo = Repository(
        owner_id=alice_id,
        github_url=f"https://github.com/alice/test-repo-{uuid.uuid4().hex[:6]}",
        owner="alice",
        name="test-repo",
    )
    db_session.add(repo)
    await db_session.commit()
    await db_session.refresh(repo)

    alice_token = make_token(sub=alice_id)
    bob_token = make_token(sub=bob_id)

    # 1. Owner (Alice) accesses -> 200 OK
    res_alice = await client.get(
        f"/api/v1/auth/test/repositories/{repo.id}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_alice.status_code == 200
    assert res_alice.json()["id"] == str(repo.id)
    assert res_alice.json()["owner_id"] == alice_id

    # 2. Non-owner (Bob) accesses -> 403 Forbidden
    res_bob = await client.get(
        f"/api/v1/auth/test/repositories/{repo.id}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert res_bob.status_code == 403
    assert "Forbidden" in res_bob.json()["detail"]

    # 3. Non-existent repository -> 404 Not Found
    res_404 = await client.get(
        f"/api/v1/auth/test/repositories/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_job_ownership_enforcement(
    client: httpx.AsyncClient, db_session: AsyncSession, make_token
):
    """Verify that only the owner of the parent repository can access job endpoints."""
    alice_id = f"user_alice_{uuid.uuid4().hex[:6]}"
    bob_id = f"user_bob_{uuid.uuid4().hex[:6]}"

    repo = Repository(
        owner_id=alice_id,
        github_url=f"https://github.com/alice/job-repo-{uuid.uuid4().hex[:6]}",
        owner="alice",
        name="job-repo",
    )
    db_session.add(repo)
    await db_session.flush()

    job = IngestionJob(
        repository_id=repo.id,
        status="queued",
        progress=0,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    alice_token = make_token(sub=alice_id)
    bob_token = make_token(sub=bob_id)

    # Alice accesses -> 200 OK
    res_alice = await client.get(
        f"/api/v1/auth/test/jobs/{job.id}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_alice.status_code == 200
    assert res_alice.json()["id"] == str(job.id)

    # Bob accesses -> 403 Forbidden
    res_bob = await client.get(
        f"/api/v1/auth/test/jobs/{job.id}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert res_bob.status_code == 403


@pytest.mark.asyncio
async def test_conversation_and_message_ownership(
    client: httpx.AsyncClient, db_session: AsyncSession, make_token
):
    """Verify that conversation and message ownership is enforced per user."""
    alice_id = f"user_alice_{uuid.uuid4().hex[:6]}"
    bob_id = f"user_bob_{uuid.uuid4().hex[:6]}"

    repo = Repository(
        owner_id=alice_id,
        github_url=f"https://github.com/alice/chat-repo-{uuid.uuid4().hex[:6]}",
        owner="alice",
        name="chat-repo",
    )
    db_session.add(repo)
    await db_session.flush()

    conv = Conversation(
        repository_id=repo.id,
        owner_id=alice_id,
        title="Test Conversation",
    )
    db_session.add(conv)
    await db_session.flush()

    msg = Message(
        conversation_id=conv.id,
        role="user",
        content="Hello Cortex",
    )
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(conv)
    await db_session.refresh(msg)

    alice_token = make_token(sub=alice_id)
    bob_token = make_token(sub=bob_id)

    # Conversation checks
    res_conv_alice = await client.get(
        f"/api/v1/auth/test/conversations/{conv.id}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_conv_alice.status_code == 200

    res_conv_bob = await client.get(
        f"/api/v1/auth/test/conversations/{conv.id}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert res_conv_bob.status_code == 403

    # Message checks
    res_msg_alice = await client.get(
        f"/api/v1/auth/test/messages/{msg.id}",
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert res_msg_alice.status_code == 200

    res_msg_bob = await client.get(
        f"/api/v1/auth/test/messages/{msg.id}",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert res_msg_bob.status_code == 403


# ==============================================================================
# Live Clerk JWKS Connectivity Test
# ==============================================================================


@pytest.mark.asyncio
async def test_live_clerk_jwks_connectivity():
    """Verify live Clerk JWKS endpoint connectivity and key parsing.

    Distinguished integration test verifying that the live Clerk domain configured in
    settings.clerk_effective_jwks_url serves valid, parseable RSA public keys.
    """
    jwks_url = settings.clerk_effective_jwks_url
    assert jwks_url, "Clerk JWKS URL must be configured"

    verifier = ClerkTokenVerifier(jwks_url=jwks_url)
    keys = await verifier._fetch_jwks_keys()
    assert len(keys) >= 1
    for kid, pub_key in keys.items():
        assert kid.startswith("ins_") or len(kid) > 5
        assert isinstance(pub_key, rsa.RSAPublicKey)
