from celery import Celery

from core.config import settings

celery_app = Celery("comply_core", broker=settings.resolved_redis_url, backend=settings.resolved_redis_url)
celery_app.conf.task_always_eager = settings.celery_task_always_eager
celery_app.conf.task_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.result_serializer = "json"
celery_app.conf.timezone = "UTC"
celery_app.conf.beat_schedule = {}

if settings.auto_ingest_enabled:
    celery_app.conf.beat_schedule["poll-connector-alerts"] = {
        "task": "poll_connector_alerts",
        "schedule": max(settings.auto_ingest_interval_seconds, 5),
    }

celery_app.autodiscover_tasks(["core"])
