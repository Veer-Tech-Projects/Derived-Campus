from celery import Celery
from app.config import settings
import logging

# Initialize Celery
# The 'broker' is the inbox (Redis), 'backend' is the results storage (Redis)
celery_app = Celery(
    "derived_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Enterprise Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # ISOLATION: Routes allow us to dedicate workers to specific high-priority exams later
    task_routes={
        "app.worker.run_kcet_pipeline": "cutoff_queue", 
        "app.worker.run_jee_pipeline": "cutoff_queue",
        "app.worker.run_placement_pipeline": "placement_queue"
    },
    
    # GUARANTEES: Ack only after task is done (prevents data loss on crash)
    task_acks_late=True,
    worker_prefetch_multiplier=1
)

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def test_celery_task(self, word: str):
    """Simple connectivity test"""
    return f"Celery is connected: {word}"

# --- EXECUTION ENTRY POINTS (The Engine Starters) ---
# Note: These tasks do NOT contain business logic. 
# They strictly import and run the pipeline classes defined in /ingestion.

@celery_app.task
def run_kcet_pipeline(run_id: str, mode: str = "continuous"):
    logger.info(f"Triggering KCET Pipeline | RunID: {run_id} | Mode: {mode}")
    # Future Phase 5 Code:
    # pipeline = KcetIngestionPipeline(run_id, mode)
    # asyncio.run(pipeline.run())
    return {"status": "triggered", "exam": "KCET", "mode": mode}
