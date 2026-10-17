import logging
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from app.core.config import settings

logger = logging.getLogger(__name__)

_postgres_pool: AsyncConnectionPool | None = None
_postgres_checkpointer: AsyncPostgresSaver | None = None
_in_memory_checkpointer: InMemorySaver | None = None


def get_postgres_connection_string() -> str:
    """Format connection string for psycopg3 connection pool."""
    user = settings.POSTGRES_USER
    pwd = settings.POSTGRES_PASSWORD
    host = settings.POSTGRES_HOST
    port = settings.POSTGRES_PORT
    dbname = settings.POSTGRES_DB
    return f"postgresql://{user}:{pwd}@{host}:{port}/{dbname}"


async def init_postgres_checkpointer() -> AsyncPostgresSaver:
    """Initialize and run migrations for AsyncPostgresSaver."""
    global _postgres_pool, _postgres_checkpointer

    if _postgres_checkpointer is not None:
        return _postgres_checkpointer

    conn_str = get_postgres_connection_string()
    logger.info(
        "Initializing AsyncPostgresSaver connection pool on %s:%s",
        settings.POSTGRES_HOST,
        settings.POSTGRES_PORT,
    )

    pool = AsyncConnectionPool(
        conn_str,
        min_size=1,
        max_size=10,
        kwargs={"autocommit": True},
        open=False,
    )
    await pool.open()
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()

    _postgres_pool = pool
    _postgres_checkpointer = checkpointer
    logger.info("AsyncPostgresSaver initialized and setup successfully.")
    return _postgres_checkpointer


async def get_checkpointer(use_in_memory: bool = False) -> BaseCheckpointSaver[Any]:
    """Provide the active checkpointer.

    Uses AsyncPostgresSaver by default, or InMemorySaver if specified
    (e.g. for unit testing).
    """
    global _in_memory_checkpointer
    if use_in_memory:
        if _in_memory_checkpointer is None:
            _in_memory_checkpointer = InMemorySaver()
        return _in_memory_checkpointer

    try:
        return await init_postgres_checkpointer()
    except Exception as exc:
        logger.warning(
            "Failed to initialize AsyncPostgresSaver (%s). "
            "Falling back to InMemorySaver.",
            exc,
        )
        if _in_memory_checkpointer is None:
            _in_memory_checkpointer = InMemorySaver()
        return _in_memory_checkpointer


async def close_checkpointer_pool() -> None:
    """Close connection pool cleanly during application shutdown."""
    global _postgres_pool, _postgres_checkpointer
    if _postgres_pool is not None:
        await _postgres_pool.close()
        _postgres_pool = None
        _postgres_checkpointer = None
        logger.info("Closed AsyncPostgresSaver connection pool.")
