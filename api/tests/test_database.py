import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.domain.models import Conversation, IngestionJob, Message, Repository


@pytest.fixture
async def db_session():
    """Provides an isolated transactional AsyncSession with NullPool for tests."""
    test_engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
    )
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_database_engine_connection(db_session: AsyncSession):
    """Verify that the async PostgreSQL engine connects and executes basic queries."""
    result = await db_session.execute(select(1))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_repository_crud(db_session: AsyncSession):
    """Test full CRUD lifecycle for Repository model."""
    uid = uuid.uuid4().hex[:8]
    repo = Repository(
        owner_id=f"user_clerk_{uid}",
        github_url=f"https://github.com/fastapi/fastapi-{uid}",
        owner="fastapi",
        name=f"fastapi-{uid}",
        default_branch="master",
        status="pending",
    )
    db_session.add(repo)
    await db_session.commit()
    await db_session.refresh(repo)

    repo_id = repo.id
    assert repo.id is not None
    assert repo.created_at is not None
    assert repo.updated_at is not None
    assert repo.status == "pending"

    # Query back
    queried = await db_session.get(Repository, repo_id)
    assert queried is not None
    assert queried.owner == "fastapi"

    # Update
    queried.status = "ready"
    queried.latest_commit_sha = "abcdef1234567890abcdef1234567890abcdef12"
    await db_session.commit()

    # Verify update
    updated = await db_session.get(Repository, repo_id)
    assert updated is not None
    assert updated.status == "ready"
    assert updated.latest_commit_sha == "abcdef1234567890abcdef1234567890abcdef12"

    # Clean up
    await db_session.delete(updated)
    await db_session.commit()


@pytest.mark.asyncio
async def test_repository_uniqueness_constraint(db_session: AsyncSession):
    """Verify unique constraint on (owner_id, github_url)."""
    uid = uuid.uuid4().hex[:8]
    owner_id = f"user_clerk_unique_{uid}"
    github_url = f"https://github.com/test-org/unique-repo-{uid}"

    repo1 = Repository(
        owner_id=owner_id,
        github_url=github_url,
        owner="test-org",
        name="unique-repo",
    )
    db_session.add(repo1)
    await db_session.commit()
    await db_session.refresh(repo1)
    repo1_id = repo1.id

    # Attempt duplicate
    repo2 = Repository(
        owner_id=owner_id,
        github_url=github_url,
        owner="test-org",
        name="unique-repo",
    )
    db_session.add(repo2)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()

    # Cleanup
    existing = await db_session.get(Repository, repo1_id)
    if existing:
        await db_session.delete(existing)
        await db_session.commit()


@pytest.mark.asyncio
async def test_ingestion_job_tracking(db_session: AsyncSession):
    """Verify ingestion job creation, step progress, and repository linking."""
    uid = uuid.uuid4().hex[:8]
    repo = Repository(
        owner_id=f"user_clerk_job_{uid}",
        github_url=f"https://github.com/psf/requests-{uid}",
        owner="psf",
        name="requests",
        status="indexing",
    )
    db_session.add(repo)
    await db_session.commit()

    job = IngestionJob(
        repository_id=repo.id,
        status="in_progress",
        progress=45,
        current_step="tree_sitter_parsing",
        commit_sha="1234567890abcdef1234567890abcdef12345678",
        attempts=1,
        max_attempts=3,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    assert job.id is not None
    assert job.repository_id == repo.id
    assert job.progress == 45
    assert job.current_step == "tree_sitter_parsing"

    # Cleanup
    await db_session.delete(repo)
    await db_session.commit()


@pytest.mark.asyncio
async def test_conversation_and_messages_with_citations(db_session: AsyncSession):
    """Verify conversation message thread and JSONB citations."""
    uid = uuid.uuid4().hex[:8]
    owner_id = f"user_clerk_chat_{uid}"
    repo = Repository(
        owner_id=owner_id,
        github_url=f"https://github.com/pallets/flask-{uid}",
        owner="pallets",
        name="flask",
    )
    db_session.add(repo)
    await db_session.commit()

    conv = Conversation(
        repository_id=repo.id,
        owner_id=owner_id,
        title="Flask Routing Question",
    )
    db_session.add(conv)
    await db_session.commit()

    # User message
    msg1 = Message(
        conversation_id=conv.id,
        role="user",
        content="How does url_for work in Flask?",
        status="completed",
    )
    db_session.add(msg1)

    # Assistant message with citations
    citations_data = [
        {
            "file_path": "src/flask/helpers.py",
            "start_line": 210,
            "end_line": 255,
            "commit_sha": "abc1234567890",
        }
    ]
    msg2 = Message(
        conversation_id=conv.id,
        role="assistant",
        content="url_for generates URLs by looking up the endpoint in the url_map.",
        status="completed",
        citations=citations_data,
    )
    db_session.add(msg2)
    await db_session.commit()

    # Query messages
    stmt = (
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
    )
    result = await db_session.execute(stmt)
    messages = result.scalars().all()

    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert messages[1].citations is not None
    assert len(messages[1].citations) == 1
    assert messages[1].citations[0]["file_path"] == "src/flask/helpers.py"

    # Cleanup
    await db_session.delete(repo)
    await db_session.commit()


@pytest.mark.asyncio
async def test_cascade_delete(db_session: AsyncSession):
    """Verify deleting a repo cascades to jobs, conversations, and messages."""
    uid = uuid.uuid4().hex[:8]
    repo = Repository(
        owner_id=f"user_clerk_cascade_{uid}",
        github_url=f"https://github.com/django/django-{uid}",
        owner="django",
        name="django",
    )
    db_session.add(repo)
    await db_session.commit()

    job = IngestionJob(
        repository_id=repo.id,
        status="completed",
        progress=100,
    )
    db_session.add(job)

    conv = Conversation(
        repository_id=repo.id,
        owner_id=f"user_clerk_cascade_{uid}",
        title="Django ORM Queries",
    )
    db_session.add(conv)
    await db_session.commit()

    msg = Message(
        conversation_id=conv.id,
        role="user",
        content="What is select_related?",
    )
    db_session.add(msg)
    await db_session.commit()

    job_id = job.id
    conv_id = conv.id
    msg_id = msg.id

    # Delete repository
    await db_session.delete(repo)
    await db_session.commit()

    # Verify all children were cascaded
    assert await db_session.get(IngestionJob, job_id) is None
    assert await db_session.get(Conversation, conv_id) is None
    assert await db_session.get(Message, msg_id) is None


@pytest.mark.asyncio
async def test_session_rollback_on_error(db_session: AsyncSession):
    """Verify uncommitted transactions roll back cleanly without dirty state."""
    fake_id = uuid.uuid4()
    # Inserting an invalid IngestionJob referencing non-existent repository
    invalid_job = IngestionJob(
        repository_id=fake_id,
        status="queued",
    )
    db_session.add(invalid_job)
    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()

    # Session should be clean and reusable
    result = await db_session.execute(select(1))
    assert result.scalar() == 1
