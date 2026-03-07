import os
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import case, func, exists

from app.models import CollegeMedia, MediaTypeEnum, MediaStatusEnum, MediaIngestionTracker
from .core.constants import LOGO_MAX_BYTES, CAMPUS_MAX_BYTES
from .core.google_search_client import GoogleImageSearchClient
from .core.downloader import (
    SecureMediaDownloader, 
    SecurityViolationError, 
    DownloadError, 
    FileTooLargeError, 
    MalformedHeaderError, 
    InvalidMimeTypeError
)
from .core.storage_client import MinioStorageClient, StorageUploadError

logger = logging.getLogger(__name__)

class MediaIngestionOrchestrator:
    """
    The Master State Machine.
    Coordinates Discovery, Air-Lock IO, Vault Storage, and Database Integrity.
    Strictly isolates Network IO from Database Transactions.
    """
    def __init__(self, db_session_factory: sessionmaker):
        self.SessionLocal = db_session_factory
        self.search_client = GoogleImageSearchClient()
        self.downloader = SecureMediaDownloader()
        self.storage_client = MinioStorageClient()

    def _get_max_bytes(self, media_type: MediaTypeEnum) -> int:
        return LOGO_MAX_BYTES if media_type == MediaTypeEnum.LOGO else CAMPUS_MAX_BYTES

    def ingest_media(self, college_id: str, canonical_name: str, city: str, media_type: MediaTypeEnum) -> bool:
        """
        Executes the Stop-on-First-Success ingestion pipeline.
        Returns True if a candidate was successfully secured and committed.
        """
        # ==========================================
        # 0. HARD EXHAUSTION GATE (CIRCUIT BREAKER)
        # ==========================================
        with self.SessionLocal() as session:
            is_exhausted = session.query(
                exists().where(
                    MediaIngestionTracker.college_id == college_id,
                    MediaIngestionTracker.media_type == media_type.value,
                    MediaIngestionTracker.is_exhausted == True
                )
            ).scalar()

            if is_exhausted:
                logger.info(f"[{college_id}] 🛑 Exhaustion gate active for {media_type.name}. Skipping ingestion to prevent API burn.")
                return False

        # ==========================================
        # 1. THE STATE MACHINE OPTIMIZATION (SOFT LOCK)
        # ==========================================
        with self.SessionLocal() as session:
            existing = session.query(CollegeMedia).filter(
                CollegeMedia.college_id == college_id,
                CollegeMedia.media_type == media_type,
                CollegeMedia.status.in_([MediaStatusEnum.PENDING, MediaStatusEnum.ACCEPTED])
            ).first()
            
            if existing:
                logger.info(f"[{college_id}] Ingestion halted: Active pipeline record for {media_type.name} already exists.")
                return True 

        # ==========================================
        # 2. NETWORK IO: GOOGLE DISCOVERY
        # ==========================================
        if media_type == MediaTypeEnum.LOGO:
            search_result = self.search_client.search_logo(canonical_name, city)
        else:
            search_result = self.search_client.search_campus_hero(canonical_name, city)

        if not search_result.candidates:
            logger.warning(f"[{college_id}] No viable candidates found for {media_type.name}.")
            self._increment_semantic_exhaustion(college_id, media_type)
            return False

        max_bytes = self._get_max_bytes(media_type)

        # ==========================================
        # 3. THE STOP-ON-FIRST-SUCCESS LOOP
        # ==========================================
        for candidate in search_result.candidates:
            downloaded_media = None
            try:
                # --- PHASE A: THE AIR-LOCK ---
                try:
                    downloaded_media = self.downloader.download_and_validate(candidate.image_url, max_bytes)
                except SecurityViolationError as e:
                    logger.warning(f"[{college_id}] Security Violation on {candidate.source_domain}: {str(e)}")
                    continue 
                except (DownloadError, FileTooLargeError, MalformedHeaderError, InvalidMimeTypeError) as e:
                    logger.debug(f"[{college_id}] Air-Lock rejected candidate: {str(e)}")
                    continue 

                # --- PHASE A.1: CRYPTOGRAPHIC TOMBSTONE SKIP ---
                with self.SessionLocal() as skip_session:
                    tombstone_check = skip_session.query(CollegeMedia).filter(
                        CollegeMedia.college_id == college_id,
                        CollegeMedia.content_hash == downloaded_media.content_hash
                    ).first()
                    
                    if tombstone_check:
                        logger.info(f"[{college_id}] Tombstone Skip: Hash {downloaded_media.content_hash} already known (Status: {tombstone_check.status.value}). Dropping candidate.")
                        if os.path.exists(downloaded_media.temp_file_path):
                            os.remove(downloaded_media.temp_file_path)
                        continue

                # --- PHASE B: THE VAULT ADAPTER ---
                try:
                    storage_key = self.storage_client.upload_media(
                        file_path=downloaded_media.temp_file_path,
                        college_id=college_id,
                        media_type=media_type.value,
                        content_hash=downloaded_media.content_hash,
                        extension=downloaded_media.extension,
                        mime_type=downloaded_media.mime_type
                    )
                except StorageUploadError as e:
                    logger.error(f"[{college_id}] Fatal Storage Failure: {str(e)}")
                    raise 

                # --- PHASE C: THE TRANSACTIONAL COMMIT ---
                commit_success = self._attempt_db_commit(
                    college_id=college_id,
                    media_type=media_type,
                    candidate=candidate,
                    downloaded_media=downloaded_media,
                    storage_key=storage_key
                )

                if commit_success:
                    logger.info(f"[{college_id}] Successfully ingested {media_type.name}. Halting loop.")
                    return True

            finally:
                # Memory & Disk Immunity: Guarantee /tmp filesystem stays clean
                if downloaded_media and os.path.exists(downloaded_media.temp_file_path):
                    os.remove(downloaded_media.temp_file_path)

        # Loop exhausted all candidates without returning True.
        self._increment_semantic_exhaustion(college_id, media_type)
        return False

    def _attempt_db_commit(self, college_id, media_type, candidate, downloaded_media, storage_key) -> bool:
        """
        Executes the ephemeral DB commit and the highly surgical exception routing matrix.
        """
        with self.SessionLocal() as session:
            new_media = CollegeMedia(
                college_id=college_id,
                media_type=media_type,
                status=MediaStatusEnum.PENDING,
                source_url=candidate.image_url,
                storage_key=storage_key,
                content_hash=downloaded_media.content_hash,
                file_size_bytes=downloaded_media.byte_size,
                width=candidate.width,
                height=candidate.height
            )
            session.add(new_media)

            try:
                session.commit()
                return True
                
            except IntegrityError:
                session.rollback()
                logger.info(f"[{college_id}] IntegrityError: Concurrent ingestion collision. Preserving shared S3 object.")
                return False 
                
            except OperationalError as e:
                session.rollback()
                
                pgcode = getattr(e.orig, "pgcode", None) if hasattr(e, "orig") else None
                is_connection_drop = pgcode is None or pgcode.startswith("08")
                is_transaction_kill = pgcode in ("40P01", "40001")
                
                if is_transaction_kill:
                    logger.warning(f"[{college_id}] DB Transaction Killed (pgcode: {pgcode}). Preserving S3 for Celery retry.")
                    return False
                    
                if not is_connection_drop:
                    logger.error(f"[{college_id}] Fatal DB Rejection (pgcode: {pgcode}). Proceeding with S3 Orphan Cleanup.")
                    self._safe_s3_cleanup(storage_key, college_id)
                    return False

                logger.error(f"[{college_id}] Connection dropped during commit. Verifying if DB is alive for ACK-Loss check.")
                
                try:
                    with self.SessionLocal() as check_session:
                        exists = check_session.query(CollegeMedia).filter(
                            CollegeMedia.college_id == college_id,
                            CollegeMedia.content_hash == downloaded_media.content_hash
                        ).first()
                        
                        if exists:
                            logger.info(f"[{college_id}] ACK-Loss mitigated: Row exists. Preserving S3 object.")
                            return True 
                        
                        logger.info(f"[{college_id}] DB is alive but row missing. Proceeding with S3 Orphan Cleanup.")
                        self._safe_s3_cleanup(storage_key, college_id)
                        return False
                        
                except OperationalError as double_check_error:
                    logger.critical(f"[{college_id}] SYSTEMIC DB FAILURE detected during double-check. Preserving S3 and aborting.")
                    raise double_check_error

    def _increment_semantic_exhaustion(self, college_id: str, media_type: MediaTypeEnum):
        """
        Safely increments the ingestion failure count.
        Uses PostgreSQL Atomic UPSERT with strict SQLAlchemy case() compilation.
        """
        with self.SessionLocal() as session:
            try:
                stmt = insert(MediaIngestionTracker).values(
                    college_id=college_id,
                    media_type=media_type.value,
                    attempt_count=1,
                    is_exhausted=False
                )
                
                # Atomic ON CONFLICT DO UPDATE
                stmt = stmt.on_conflict_do_update(
                    index_elements=['college_id', 'media_type'],
                    set_={
                        'attempt_count': MediaIngestionTracker.attempt_count + 1,
                        'is_exhausted': case(
                            (MediaIngestionTracker.attempt_count + 1 >= 3, True),
                            else_=MediaIngestionTracker.is_exhausted
                        ),
                        'last_attempted_at': func.now()
                    }
                )
                
                session.execute(stmt)
                session.commit()
                
            except Exception as e:
                session.rollback()
                logger.error(f"[{college_id}] Failed to increment semantic exhaustion tracker: {str(e)}")

    def _safe_s3_cleanup(self, storage_key: str, college_id: str):
        """Best-effort S3 orphan mitigation. Never crashes the worker."""
        try:
            self.storage_client.s3_client.delete_object(
                Bucket=self.storage_client.bucket_name,
                Key=storage_key
            )
        except Exception as cleanup_error:
            logger.error(f"[{college_id}] Failed to clean up orphan {storage_key}: {str(cleanup_error)}")