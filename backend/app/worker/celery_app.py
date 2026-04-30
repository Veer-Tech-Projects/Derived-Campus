from celery import Celery
from celery.schedules import crontab
from app.config import settings
from app.domains.student_portal.student_billing.constants import (
    BILLING_RECONCILIATION_BEAT_MINUTES,
    BILLING_RECONCILIATION_QUEUE,
    BILLING_RECONCILIATION_SWEEP_TASK,
)
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
        
        # Billing operational jobs -> isolated billing lane
        BILLING_RECONCILIATION_SWEEP_TASK: {"queue": BILLING_RECONCILIATION_QUEUE},

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
    "run-billing-reconciliation-every-10-minutes": {
        "task": BILLING_RECONCILIATION_SWEEP_TASK,
        "schedule": crontab(minute=f"*/{BILLING_RECONCILIATION_BEAT_MINUTES}"),
    },
}

celery_app.autodiscover_tasks([
    "ingestion", 
    "ingestion.media_ingestion",
    "ingestion.location_pipeline",
    "app.domains.student_portal.college_filter_tool",
    "app.domains.student_portal.student_billing.tasks",
])

logger = logging.getLogger(__name__)