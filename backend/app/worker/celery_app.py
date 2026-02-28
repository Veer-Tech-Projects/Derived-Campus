from celery import Celery
from celery.schedules import crontab
from app.config import settings
import logging

# Initialize Celery
celery_app = Celery(
    "derived_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Enterprise Configuration
celery_app.conf.update(
    # 1. Serialization Security
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # 2. Queue Isolation
    task_default_queue="default",
    task_routes={
        # Daily Scheduled Scans -> Fast Lane
        "ingestion.tasks.perform_exam_scan": {"queue": "ingestion_queue"},
        "ingestion.tasks.trigger_scheduled_scans": {"queue": "ingestion_queue"},
        
        # --- INFRASTRUCTURE NOTE ---
        # The 'bootstrap_queue' is NOT listed here intentionally.
        # Historical bootstraps use Explicit Routing via .apply_async(queue='bootstrap_queue')
        # in the management CLI. Do NOT remove the queue configuration from Docker.
    },
    
    # 3. Safety Limits
    task_time_limit=1800,       # Hard Kill: 30 minutes
    task_soft_time_limit=1500,  # Warning: 25 minutes
    
    # 4. Resilience
    task_acks_late=True,             
    worker_max_tasks_per_child=500,  
)

# The Schedule
celery_app.conf.beat_schedule = {
    "scan-active-exams-every-6-hours": {
        "task": "ingestion.tasks.trigger_scheduled_scans",
        "schedule": crontab(minute=0, hour="*/6"),
    },
}

celery_app.autodiscover_tasks(["ingestion"])

logger = logging.getLogger(__name__)