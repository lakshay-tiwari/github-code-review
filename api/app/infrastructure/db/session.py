from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Async engine for PostgreSQL with connection pooling and health checks
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# Thread-safe async session factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)



async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency providing a transactional AsyncSession.

    Automatically commits successful operations and rolls back on unhandled exceptions.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_task_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated, transient AsyncSession for Celery tasks or worker threads.

    Avoids event loop binding collisions across threads by using NullPool.
    """
    task_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        poolclass=NullPool,
    )
    factory = async_sessionmaker(
        bind=task_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()
            await task_engine.dispose()

