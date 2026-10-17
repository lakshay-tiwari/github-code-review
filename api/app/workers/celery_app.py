import logging

from celery import Celery

from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize the Celery application bound to the shared app package
celery_app = Celery(
    "cortex",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

# Apply production-ready queue settings
celery_app.conf.update(
    # Serialization: enforce pure JSON (no unsafe pickle)
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone & UTC
    timezone="UTC",
    enable_utc=True,
    # Worker execution & acknowledgement
    task_track_started=True,
    task_acks_late=True,  # Acknowledge after completion
    worker_prefetch_multiplier=1,  # Fair dispatch for long-running ingestion jobs
    worker_max_tasks_per_child=50,  # Prevent memory leaks across worker lifetimes
    # Default Queue
    task_default_queue=settings.CELERY_TASK_DEFAULT_QUEUE,
    # Time limits: 30m hard limit, 25m soft limit for heavy background workloads
    task_time_limit=1800,
    task_soft_time_limit=1500,
    # Task event reporting
    worker_send_task_events=True,
)
