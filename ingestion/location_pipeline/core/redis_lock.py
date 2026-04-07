import uuid
import logging
from contextlib import contextmanager
import redis
from app.config import settings

logger = logging.getLogger(__name__)

redis_client = redis.from_url(
    settings.REDIS_URL, 
    decode_responses=True,
    socket_timeout=5.0,
    retry_on_timeout=True,
    health_check_interval=30
)

RELEASE_LUA_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

@contextmanager
def location_redis_mutex(college_id: str, expire_seconds: int = 900): # [AUDIT FIX] Extended to 15 mins
    """
    Non-blocking Redis Distributed Mutex.
    Isolated purely to the location domain.
    """
    lock_key = f"mutex:location_ingest:{college_id}"
    lock_token = str(uuid.uuid4())
    
    acquired = redis_client.set(lock_key, lock_token, nx=True, ex=expire_seconds)
    
    try:
        yield acquired
    finally:
        if acquired:
            redis_client.eval(RELEASE_LUA_SCRIPT, 1, lock_key, lock_token)