import logging
from celery import shared_task
from sqlalchemy.exc import OperationalError
from redis.exceptions import ConnectionError as RedisConnectionError

from app.database import SessionLocal
from .orchestrator import LocationIngestionOrchestrator
from .core.redis_lock import location_redis_mutex, redis_client

from .core.google_places_client import RateLimitExceeded, ProviderTimeout

logger = logging.getLogger(__name__)

TRANSIENT_INFRA_ERRORS = (
    OperationalError,        
    RedisConnectionError,    
    RateLimitExceeded,
    ProviderTimeout
)

TELEMETRY_KEY = "telemetry:active_location_tasks"

SAFE_DECR_SCRIPT = """
local v = redis.call('GET', KEYS[1])
if v and tonumber(v) > 0 then
  return redis.call('DECR', KEYS[1])
end
return 0
"""

@shared_task(
    name="ingestion.location_pipeline.tasks.ingest_college_location_task",
    bind=True,
    max_retries=3,
    autoretry_for=TRANSIENT_INFRA_ERRORS, 
    retry_backoff=True,         
    retry_backoff_max=300,      
    retry_jitter=True,
    rate_limit="2/s",  
    acks_late=True,             
    reject_on_worker_lost=True, 
    queue="ingestion_queue"
)
def ingest_college_location_task(self, college_id: str, canonical_name: str, state_code: str):
    """
    Asynchronous executor for Location Pipeline.
    Protected by strict distributed locks and telemetry counters.
    """
    # [AUDIT FIX] Extended lock TTL to 900 seconds
    with location_redis_mutex(college_id, expire_seconds=900) as acquired:
        if not acquired:
            logger.debug(f"[{college_id}] Location lock held by another worker. Skipping.")
            return "SKIPPED_LOCKED"
            
        with redis_client.pipeline() as pipe:
            pipe.incr(TELEMETRY_KEY)
            pipe.expire(TELEMETRY_KEY, 1800)
            pipe.execute()
        
        try:
            logger.info(f"[{college_id}] ▶️ Starting Location Orchestrator.")
            orchestrator = LocationIngestionOrchestrator(SessionLocal)
            
            success = orchestrator.ingest_location(
                college_id=college_id, 
                canonical_name=canonical_name, 
                state_code=state_code
            )
            
            if success:
                return "SUCCESS_INGESTED"
            return "EXHAUSTED_CANDIDATES"
            
        except Exception as e:
            logger.exception(f"[{college_id}] ❌ Task Execution Failure: {type(e).__name__}")
            raise
        finally:
            with redis_client.pipeline() as pipe:
                pipe.eval(SAFE_DECR_SCRIPT, 1, TELEMETRY_KEY)
                pipe.expire(TELEMETRY_KEY, 1800)
                pipe.execute()