"""
Celery Workers for Background Jobs
Retry-safe async task processing for AI analysis.
"""
from celery import Celery
from app.config import settings

# Initialize Celery app
celery_app = Celery(
    "workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

# Celery configuration for production
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    # Concurrency
    worker_prefetch_multiplier=1,
    # Rate limiting
    task_default_rate_limit="10/m",
)
