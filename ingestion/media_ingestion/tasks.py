import logging
from celery import shared_task
from sqlalchemy.exc import OperationalError
from redis.exceptions import ConnectionError as RedisConnectionError

from app.database import SessionLocal
from app.models import MediaTypeEnum

from .orchestrator import MediaIngestionOrchestrator
from .core.storage_client import StorageUploadError
from .core.redis_lock import redis_mutex, redis_client

logger = logging.getLogger(__name__)

TRANSIENT_INFRA_ERRORS = (
    OperationalError,        
    RedisConnectionError,    
    StorageUploadError       
)

# Guarantees the counter never drops below 0 even during zombie worker recovery
SAFE_DECR_SCRIPT = """
local v = redis.call('GET', KEYS[1])
if v and tonumber(v) > 0 then
  return redis.call('DECR', KEYS[1])
end
return 0
"""

TELEMETRY_KEY = "telemetry:active_media_tasks"

@shared_task(
    name="ingestion.media_ingestion.tasks.ingest_college_media_task",
    bind=True,
    max_retries=3,
    autoretry_for=TRANSIENT_INFRA_ERRORS, 
    retry_backoff=True,         
    retry_backoff_max=300,      
    retry_jitter=True,
    queue="ingestion_queue"
)
def ingest_college_media_task(self, college_id: str, canonical_name: str, city: str, media_type_str: str):
    try:
        media_type = MediaTypeEnum[media_type_str]
    except KeyError:
        logger.error(f"[{college_id}] Invalid Media Type '{media_type_str}'. Aborting task.")
        return "ABORTED_INVALID_TYPE"

    lock_name = f"{college_id}_{media_type.name}"
    
    with redis_mutex(lock_name, expire_seconds=900) as acquired:
        if not acquired:
            return "SKIPPED_LOCKED"
            
        # --- AUDITOR FIX: REDIS PIPELINING (Halves TCP Overhead) ---
        with redis_client.pipeline() as pipe:
            pipe.incr(TELEMETRY_KEY)
            pipe.expire(TELEMETRY_KEY, 1800)
            pipe.execute()
        
        try:
            logger.info(f"[{college_id}] ▶️ Starting Orchestrator for {media_type.name}.")
            orchestrator = MediaIngestionOrchestrator(SessionLocal)
            success = orchestrator.ingest_media(
                college_id=college_id, 
                canonical_name=canonical_name, 
                city=city, 
                media_type=media_type
            )
            
            if success:
                return f"SUCCESS_INGESTED_{media_type.name}"
            return f"EXHAUSTED_CANDIDATES_{media_type.name}"
            
        except Exception as e:
            # --- AUDITOR FIX: FORENSIC STACK TRACE LOGGING ---
            logger.exception(f"[{college_id}] ❌ Task Execution Failure: {type(e).__name__}")
            raise
        finally:
            # Safe Decrement and renew TTL via Pipeline
            with redis_client.pipeline() as pipe:
                pipe.eval(SAFE_DECR_SCRIPT, 1, TELEMETRY_KEY)
                pipe.expire(TELEMETRY_KEY, 1800)
                pipe.execute()