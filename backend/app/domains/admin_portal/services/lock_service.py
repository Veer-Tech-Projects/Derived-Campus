from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
import hashlib

logger = logging.getLogger(__name__)

class LockService:
    """
    Manages Distributed Locks using PostgreSQL Advisory Locks.
    Domain: Admin Portal
    """

    @staticmethod
    def _generate_lock_id(key: str) -> int:
        hash_digest = hashlib.sha256(key.encode()).hexdigest()
        return int(hash_digest[:8], 16) % 2147483647

    @staticmethod
    def acquire_lock(db: Session, lock_key: str) -> bool:
        lock_id = LockService._generate_lock_id(lock_key)
        try:
            result = db.execute(
                text("SELECT pg_try_advisory_lock(:id)"), 
                {"id": lock_id}
            ).scalar()
            if result:
                logger.info(f"🔐 Locked: {lock_key} (ID: {lock_id})")
            else:
                logger.warning(f"🔒 Failed to Lock: {lock_key} (ID: {lock_id}) - Busy")
            return result is True
        except Exception as e:
            logger.error(f"Lock acquisition error for {lock_key}: {e}")
            return False

    @staticmethod
    def release_lock(db: Session, lock_key: str):
        lock_id = LockService._generate_lock_id(lock_key)
        try:
            db.execute(
                text("SELECT pg_advisory_unlock(:id)"), 
                {"id": lock_id}
            )
            logger.info(f"🔓 Released: {lock_key} (ID: {lock_id})")
        except Exception as e:
            logger.error(f"Lock release error for {lock_key}: {e}")