from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.domains.admin_portal.services.lock_service import LockService
from ingestion.common.services.governance import IngestionGovernanceController
from ingestion.common.services.plugin_factory import PluginFactory
from ingestion.cutoff_ingestion.core.orchestrator import UniversalNotificationOrchestrator

logger = get_task_logger(__name__)

# --- CONFIGURATION ---
ACTIVE_YEARS = [2026] 
ACTIVE_EXAMS = ["kcet", "neet_ka"]

@shared_task(name="ingestion.tasks.trigger_scheduled_scans")
def trigger_scheduled_scans():
    """
    THE BEAT: Wakes up every 6 hours.
    """
    logger.info(f"⏰ Scheduler Woke Up. Targets: {ACTIVE_EXAMS} for Years: {ACTIVE_YEARS}")
    
    for exam in ACTIVE_EXAMS:
        for year in ACTIVE_YEARS:
            perform_exam_scan.delay(exam, year)
            logger.info(f"🚀 Dispatched: {exam.upper()} - {year}")

@shared_task(
    name="ingestion.tasks.perform_exam_scan",
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,), 
    retry_backoff=True,         
    retry_backoff_max=60,       
    retry_jitter=True           
)
def perform_exam_scan(self, exam_slug: str, year: int):
    """
    THE WORKER: Uses Two-Session Strategy for Lock Safety.
    """
    lock_key = f"scan_{exam_slug}_{year}"
    
    # Session A: The Guard (Holds the Lock)
    lock_db: Session = SessionLocal()
    
    try:
        # [HARDENING] Explicitly start the transaction boundary.
        lock_db.begin()
        
        # 1. Acquire Lock on Session A
        with LockService.locked(lock_db, lock_key) as acquired:
            if not acquired:
                logger.warning(f"🔒 Skipped {lock_key}: Scan already in progress.")
                return "SKIPPED_LOCKED"

            # 2. Session B: The Worker (Does the IO/Commits)
            work_db: Session = SessionLocal()
            try:
                logger.info(f"▶️ Starting Scan: {exam_slug.upper()} ({year})")
                
                governance = IngestionGovernanceController()
                orchestrator = UniversalNotificationOrchestrator(governance)
                plugin = PluginFactory.get_plugin(exam_slug)

                # Execute Scan (Commits happen here on work_db)
                new_count = orchestrator.scan(work_db, plugin, year)
                
                logger.info(f"✅ Scan Complete: {exam_slug.upper()} ({year}) | New Artifacts: {new_count}")
                return f"SUCCESS_NEW_{new_count}"
            
            finally:
                work_db.close() # Clean up Worker Session

    except Exception as e:
        logger.error(f"❌ Critical Failure for {exam_slug}-{year}: {e}")
        # Re-raise so Celery handles the retry logic
        raise 
    
    finally:
        # [HYGIENE] Explicitly rollback to signal "No writes intended here"
        lock_db.rollback()
        lock_db.close()