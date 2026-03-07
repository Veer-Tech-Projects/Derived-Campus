import uuid
import logging
from contextlib import contextmanager
import redis
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize a global, connection-pooled Redis client with Socket-Level Resilience
redis_client = redis.from_url(
    settings.REDIS_URL, 
    decode_responses=True,
    socket_timeout=5.0,
    retry_on_timeout=True
)

# Atomic Lua Script: Mathematically guarantees ownership before deletion
RELEASE_LUA_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

@contextmanager
def redis_mutex(lock_name: str, expire_seconds: int = 900):
    """
    Non-blocking Redis Distributed Mutex with strict ownership verification.
    TTL set to 900s (15m) to mathematically envelop worst-case IO degradation.
    """
    lock_key = f"mutex:media_ingest:{lock_name}"
    lock_token = str(uuid.uuid4())
    
    # nx=True: Set IF NOT Exists (Atomic acquisition)
    acquired = redis_client.set(lock_key, lock_token, nx=True, ex=expire_seconds)
    
    try:
        yield acquired
    finally:
        # Strict hygiene: Only the exact thread that acquired the lock may release it
        if acquired:
            redis_client.eval(RELEASE_LUA_SCRIPT, 1, lock_key, lock_token)