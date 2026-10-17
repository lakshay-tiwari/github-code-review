import logging
from typing import Any

from celery import Task

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
