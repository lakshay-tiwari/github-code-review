import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from celery import Task
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.domain.models import IngestionJob
from app.infrastructure.db.session import async_session_factory
from app.services.github import GitHubError, GitHubService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


class LoggingTask(Task):
    """Base Celery task providing structured lifecycle error logging."""

    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: Any,
    ) -> None:
        logger.error(
            "Task %s failed: %s (args=%s, kwargs=%s)",
            task_id,
            exc,
            args,
            kwargs,
            exc_info=einfo,
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)


@celery_app.task(
    bind=True,
    base=LoggingTask,
    name="app.workers.tasks.ping_task",
    max_retries=3,
    default_retry_delay=5,
)
def ping_task(self: Task, message: str = "pong") -> dict[str, Any]:
    """Harmless smoke test task that validates queue submission and execution.

    Does not process repositories or touch application database state.
    """
    task_id = self.request.id or "direct-call"
    logger.info("Executing smoke ping_task [%s] with message='%s'", task_id, message)
    return {
        "status": "success",
        "echo": message,
        "task_id": task_id,
    }


def enqueue_smoke_ping(message: str = "pong") -> str:
    """Queue submission boundary helper: enqueue smoke ping and return task_id."""
    result = ping_task.delay(message=message)
    return result.id


async def _execute_index_job(job_id: str) -> dict[str, Any]:
    """Execute repository metadata preparation and queue transition in PostgreSQL.

    In Phase 4, validates GitHub repository access, enforces size/resource limits,
    and transitions job state to 'ready_for_indexing' (deferring full chunking and
    vector/graph indexing to Phase 5).
    """
    job_uuid = uuid.UUID(job_id)
    github_service = GitHubService()

    async with async_session_factory() as session:
        # Load job with repository
        res = await session.execute(
            select(IngestionJob)
            .options(joinedload(IngestionJob.repository))
            .where(IngestionJob.id == job_uuid)
        )
        job = res.scalar_one_or_none()
        if not job:
            logger.error("Job %s not found in database", job_id)
            return {"status": "error", "error": f"Job {job_id} not found"}

        repo = job.repository
        if not repo:
            logger.error("Repository for job %s not found", job_id)
            return {"status": "error", "error": "Associated repository missing"}

        try:
            # Mark job started
            job.status = "in_progress"
            job.current_step = "validating"
            job.progress = 15
            job.started_at = datetime.now(UTC)
            job.attempts += 1
            repo.status = "indexing"
            await session.commit()

            # Verify and fetch latest commit
            meta = await github_service.get_repository_details(repo.owner, repo.name)
            default_branch = meta.get("default_branch") or repo.default_branch
            repo.default_branch = default_branch

            commit_sha = await github_service.get_latest_commit_sha(
                repo.owner, repo.name, default_branch
            )
            job.commit_sha = commit_sha
            repo.latest_commit_sha = commit_sha

            job.progress = 40
            job.current_step = "metadata_verified"
            await session.commit()

            # Phase 4 checkpoint: preparation verified.
            # Full chunking & embeddings in Phase 5
            job.progress = 50
            job.current_step = "ready_for_indexing"
            job.status = "in_progress"
            repo.status = "indexing"
            await session.commit()

            return {
                "status": "success",
                "job_id": str(job.id),
                "repository_id": str(repo.id),
                "commit_sha": commit_sha,
                "step": job.current_step,
            }

        except GitHubError as g_err:
            logger.warning("GitHub validation failed for job %s: %s", job_id, g_err)
            job.status = "failed"
            job.error_details = g_err.message
            job.completed_at = datetime.now(UTC)
            repo.status = "failed"
            repo.error_message = g_err.message
            await session.commit()
            return {"status": "failed", "error": g_err.message}

        except Exception as exc:
            logger.exception("Unexpected error executing job %s: %s", job_id, exc)
            job.status = "failed"
            job.error_details = (
                "An unexpected error occurred during repository ingestion"
            )
            job.completed_at = datetime.now(UTC)
            repo.status = "failed"
            repo.error_message = "Ingestion failed due to an internal error"
            await session.commit()
            raise


def _run_async(coro: Any) -> Any:
    """Execute coroutine safely whether invoked from sync worker or running loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


@celery_app.task(
    bind=True,
    base=LoggingTask,
    name="app.workers.tasks.index_repository_task",
    max_retries=2,
    default_retry_delay=10,
)
def index_repository_task(self: Task, job_id: str) -> dict[str, Any]:
    """Celery task entry point to process repository ingestion asynchronously."""
    logger.info("Starting index_repository_task for job_id=%s", job_id)
    return _run_async(_execute_index_job(job_id))


def enqueue_index_repository(job_id: str) -> str:
    """Queue submission boundary: enqueue repository indexing job."""
    result = index_repository_task.delay(job_id=job_id)
    return result.id
