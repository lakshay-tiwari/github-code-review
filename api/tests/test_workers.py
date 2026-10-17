from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.workers.celery_app import celery_app
from app.workers.tasks import LoggingTask, enqueue_smoke_ping, ping_task


def test_celery_app_configuration():
    """Verify production queue configuration parameters."""
    conf = celery_app.conf
    assert conf.task_serializer == "json"
    assert conf.result_serializer == "json"
    assert conf.accept_content == ["json"]
    assert conf.timezone == "UTC"
    assert conf.enable_utc is True
    assert conf.task_acks_late is True
    assert conf.worker_prefetch_multiplier == 1
    assert conf.task_time_limit == 1800
    assert conf.task_soft_time_limit == 1500
    assert conf.task_default_queue == settings.CELERY_TASK_DEFAULT_QUEUE


def test_task_registration():
    """Verify smoke task is registered and importable by worker."""
    assert "app.workers.tasks.ping_task" in celery_app.tasks
    task = celery_app.tasks["app.workers.tasks.ping_task"]
    assert task.name == "app.workers.tasks.ping_task"
    assert issubclass(task.__class__, LoggingTask)


def test_ping_task_direct_execution():
    """Test in-process synchronous invocation of the smoke task."""
    result = ping_task.apply(args=(), kwargs={"message": "sync_test"})
    assert result.successful()
    data = result.result
    assert data["status"] == "success"
    assert data["echo"] == "sync_test"
    assert "task_id" in data


def test_enqueue_smoke_ping_boundary():
    """Test queue submission boundary helper returns string task ID."""
    with patch.object(ping_task, "delay") as mock_delay:
        mock_result = MagicMock()
        mock_result.id = "mocked-task-id-1234"
        mock_delay.return_value = mock_result

        task_id = enqueue_smoke_ping(message="hello_boundary")
        assert task_id == "mocked-task-id-1234"
        mock_delay.assert_called_once_with(message="hello_boundary")


def test_logging_task_on_failure():
    """Test that custom LoggingTask.on_failure logs exception details."""
    task = LoggingTask()
    with patch("app.workers.tasks.logger.error") as mock_log_error:
        exc = RuntimeError("Simulated task failure")
        task.on_failure(
            exc=exc,
            task_id="fail-task-id",
            args=("arg1",),
            kwargs={"k": "v"},
            einfo=None,
        )
        assert mock_log_error.called
        log_msg = mock_log_error.call_args[0][0]
        assert "fail-task-id" in log_msg or "%s" in log_msg


def test_eager_mode_execution():
    """Test task execution in Celery eager mode."""
    celery_app.conf.task_always_eager = True
    try:
        res = ping_task.delay(message="eager_test")
        assert res.successful()
        assert res.result["echo"] == "eager_test"
        assert res.result["status"] == "success"
    finally:
        celery_app.conf.task_always_eager = False
