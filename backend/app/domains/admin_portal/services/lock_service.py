from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
import hashlib
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)

class LockService:
    """
    Manages Distributed Locks using PostgreSQL Advisory Locks.
    Domain: Admin Portal
    Updated for Phase A: Supports Transaction-Level Locks (Safety).
    """

    @staticmethod
    def _generate_lock_id(key: str) -> int:
        # Generate a deterministic 64-bit compatible integer
        hash_digest = hashlib.sha256(key.encode()).hexdigest()
        # Postgres BigInt is signed 64-bit. We mask to ensure it fits.
        val = int(hash_digest[:15], 16)
        return val if val < 9223372036854775807 else val % 9223372036854775807

    @staticmethod
    @contextmanager
    def locked(db: Session, lock_key: str) -> Generator[bool, None, None]:
        """
        [NEW] Safe Context Manager using Transaction-Level Locks.
        Automatically releases the lock when the transaction ends (commit/rollback).
        Prevents 'Zombie Locks' if a worker crashes.
        
        Usage:
            with LockService.locked(db, "kcet_2026"):
                if not acquired: return
                # do work
        """
        lock_id = LockService._generate_lock_id(lock_key)
        acquired = False
        try:
            # pg_try_advisory_xact_lock: Scoped to the transaction.
            result = db.execute(
                text("SELECT pg_try_advisory_xact_lock(:id)"), 
                {"id": lock_id}
            ).scalar()
            
            if result:
                logger.info(f"🔐 Locked (XACT): {lock_key} (ID: {lock_id})")
                acquired = True
                yield True
            else:
                logger.warning(f"🔒 Failed to Lock (XACT): {lock_key} (ID: {lock_id}) - Busy")
                yield False
        finally:
            if acquired:
                # Logging only. The DB releases it automatically at transaction end.
                logger.debug(f"🔓 Releasing (XACT): {lock_key} (ID: {lock_id})")

    # --- LEGACY SUPPORT (Session Locks) ---
    @staticmethod
    def acquire_lock(db: Session, lock_key: str) -> bool:
        """
        Acquires a Session-Level lock. Must be manually released.
        Use only for long-running processes spanning multiple commits.
        """
        lock_id = LockService._generate_lock_id(lock_key)
        try:
            result = db.execute(
                text("SELECT pg_try_advisory_lock(:id)"), 
                {"id": lock_id}
            ).scalar()
            if result:
                logger.info(f"🔐 Locked (Session): {lock_key} (ID: {lock_id})")
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
            logger.info(f"🔓 Released (Session): {lock_key}")
        except Exception as e:
            logger.error(f"Lock release error: {e}")