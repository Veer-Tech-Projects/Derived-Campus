import os
import logging
from uuid import UUID
from typing import List
from urllib.parse import urlparse, urljoin

from sqlalchemy.orm import Session, aliased
from sqlalchemy import select, func, text
from sqlalchemy.sql import true
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import OperationalError
from fastapi import HTTPException

from app.models import (
    College, CollegeMedia, MediaTypeEnum, MediaStatusEnum, 
    MediaDispatchLock, MediaIngestionTracker, AdminAuditTrail
)
from ingestion.media_ingestion.tasks import ingest_college_media_task
from ingestion.media_ingestion.core.storage_client import MinioStorageClient
from app.domains.student_portal.college_filter_tool.services.college_filter_rebuild_dispatcher import (
    CollegeFilterRebuildMode,
    CollegeFilterRebuildRequest,
    college_filter_rebuild_dispatcher,
)

logger = logging.getLogger(__name__)

def _validate_and_get_cdn_base() -> str:
    cdn_base = os.environ.get("CDN_PUBLIC_BASE")
    if not cdn_base:
        raise RuntimeError("CRITICAL: CDN_PUBLIC_BASE environment variable is missing.")

    parsed = urlparse(cdn_base)
    env = os.environ.get("ENVIRONMENT", "development").lower()
    
    if env == "production" and parsed.scheme != "https":
        raise RuntimeError("CRITICAL: CDN_PUBLIC_BASE must use HTTPS in production environments.")
    elif parsed.scheme not in ("http", "https"):
        raise RuntimeError(f"CRITICAL: CDN_PUBLIC_BASE must use HTTP or HTTPS.")
    if not parsed.netloc:
        raise RuntimeError("CRITICAL: CDN_PUBLIC_BASE missing host/netloc.")
    if parsed.username or parsed.password:
        raise RuntimeError("CRITICAL: CDN_PUBLIC_BASE must not contain credentials.")
        
    return cdn_base.rstrip("/") + "/"

CDN_BASE_URL = _validate_and_get_cdn_base()

class MediaGovernanceService:
    def __init__(self):
        self.storage_client = MinioStorageClient()
        self.cdn_base_url = CDN_BASE_URL

    def dispatch_ingestion(self, db: Session, college_id: UUID, media_type: MediaTypeEnum, admin_id: UUID, admin_username: str, force: bool = False):
        try:
            college = db.query(College).filter(College.college_id == college_id).first()
            if not college:
                raise HTTPException(status_code=404, detail="College not found")

            # --- FIX 1: DYNAMIC LOCK OVERRIDE ---
            base_insert = insert(MediaDispatchLock).values(
                college_id=college_id,
                media_type=media_type.value,
                locked_by=f"admin:{admin_username}",
                expires_at=func.now() + text("interval '15 minutes'")
            )
            
            update_dict = {
                'locked_by': f"admin:{admin_username}",
                'expires_at': func.now() + text("interval '15 minutes'")
            }

            if force:
                # If 'Force' is clicked, we bypass the 15-minute check and violently seize the lock
                lock_stmt = base_insert.on_conflict_do_update(
                    index_elements=['college_id', 'media_type'],
                    set_=update_dict
                )
            else:
                # Normal dispatch strictly enforces the 15-minute API cooldown
                lock_stmt = base_insert.on_conflict_do_update(
                    index_elements=['college_id', 'media_type'],
                    set_=update_dict,
                    where=(MediaDispatchLock.expires_at < func.now())
                )

            if db.execute(lock_stmt).rowcount == 0:
                db.rollback()
                raise HTTPException(status_code=409, detail=f"Ingestion for {media_type.name} is running.")

            tracker = db.query(MediaIngestionTracker).filter_by(college_id=college_id, media_type=media_type.value).first()

            if force:
                if tracker:
                    tracker.attempt_count = 0
                    tracker.is_exhausted = False
                else:
                    db.add(MediaIngestionTracker(college_id=college_id, media_type=media_type.value, attempt_count=0, is_exhausted=False))
            else:
                if tracker and tracker.is_exhausted:
                    db.rollback() 
                    raise HTTPException(status_code=400, detail=f"Ingestion for {media_type.name} EXHAUSTED.")

            db.add(AdminAuditTrail(
                admin_id=admin_id, action="FORCE_DISPATCH_INGESTION" if force else "DISPATCH_INGESTION",
                target_resource=str(college_id), details={"media_type": media_type.value, "force": force}
            ))
            db.commit()

        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"[{college_id}] Fatal DB Transaction failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Database transaction failed.")

        ingest_college_media_task.delay(
            college_id=str(college_id), canonical_name=college.canonical_name,
            city=college.city or "India", media_type_str=media_type.value
        )
        return {"message": "Ingestion Dispatched", "media_type": media_type.value}

    def dispatch_bulk_ingestion(self, db: Session, college_ids: List[UUID], admin_id: UUID, admin_username: str, force: bool = False):
        summary = {"queued": 0, "skipped_locked": 0, "skipped_exhausted": 0, "errors": 0}
        for cid in college_ids:
            for m_type in [MediaTypeEnum.LOGO, MediaTypeEnum.CAMPUS_HERO]:
                try:
                    self.dispatch_ingestion(db, cid, m_type, admin_id, admin_username, force)
                    summary["queued"] += 1
                except HTTPException as he:
                    if he.status_code == 409: summary["skipped_locked"] += 1
                    elif he.status_code == 400: summary["skipped_exhausted"] += 1
                    else: summary["errors"] += 1
                except Exception as e:
                    logger.error(f"Bulk dispatch error on {m_type.name} for {cid}: {e}")
                    summary["errors"] += 1

        if summary["queued"] == 0 and sum(summary.values()) > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"No tasks queued. Locked: {summary['skipped_locked']}, Exhausted: {summary['skipped_exhausted']}, Errors: {summary['errors']}."
            )
        return summary

    def triage_media(self, db: Session, college_id: UUID, media_id: UUID, action: str, admin_id: UUID):
        action = action.upper()
        s3_keys_to_delete: List[str] = []

        try:
            if action not in ("ACCEPT", "REJECT", "DELETE"):
                raise HTTPException(status_code=400, detail="Invalid action.")

            target_stub = db.query(CollegeMedia).filter(
                CollegeMedia.id == media_id,
                CollegeMedia.college_id == college_id
            ).first()
            if not target_stub:
                raise HTTPException(status_code=404, detail="Media candidate not found.")

            slot_rows = db.query(CollegeMedia).filter(
                CollegeMedia.college_id == college_id,
                CollegeMedia.media_type == target_stub.media_type
            ).order_by(CollegeMedia.id).with_for_update(nowait=True).all()

            target_media = {row.id: row for row in slot_rows}.get(media_id)
            if not target_media:
                raise HTTPException(status_code=404, detail="Media candidate not found.")

            if action == "ACCEPT":
                if target_media.status != MediaStatusEnum.PENDING:
                    raise HTTPException(status_code=400, detail="Can only accept PENDING media.")
                for row in slot_rows:
                    if row.id != target_media.id and row.status == MediaStatusEnum.ACCEPTED:
                        if row.storage_key and row.storage_key != "DELETED_ORPHAN":
                            s3_keys_to_delete.append(row.storage_key)
                        db.delete(row)
                target_media.status = MediaStatusEnum.ACCEPTED

                tracker = db.query(MediaIngestionTracker).filter_by(
                    college_id=college_id,
                    media_type=target_media.media_type.value
                ).first()
                if tracker:
                    tracker.attempt_count = 0
                    tracker.is_exhausted = False
                else:
                    db.add(
                        MediaIngestionTracker(
                            college_id=college_id,
                            media_type=target_media.media_type.value,
                            attempt_count=0,
                            is_exhausted=False,
                        )
                    )

            elif action == "REJECT":
                if target_media.status != MediaStatusEnum.PENDING:
                    raise HTTPException(status_code=400, detail="Only PENDING media can be rejected.")
                target_media.status = MediaStatusEnum.REJECTED
                if target_media.storage_key and target_media.storage_key != "DELETED_ORPHAN":
                    s3_keys_to_delete.append(target_media.storage_key)
                target_media.storage_key = "DELETED_ORPHAN"

            elif action == "DELETE":
                if target_media.status != MediaStatusEnum.ACCEPTED:
                    raise HTTPException(status_code=400, detail="Only ACCEPTED media can be deleted.")
                if target_media.storage_key and target_media.storage_key != "DELETED_ORPHAN":
                    s3_keys_to_delete.append(target_media.storage_key)
                db.delete(target_media)

            db.query(MediaDispatchLock).filter(
                MediaDispatchLock.college_id == college_id,
                MediaDispatchLock.media_type == target_media.media_type.value
            ).delete()

            db.add(
                AdminAuditTrail(
                    admin_id=admin_id,
                    action=f"TRIAGE_{action}",
                    target_resource=str(college_id),
                    details={"media_id": str(media_id)},
                )
            )
            db.commit()

        except OperationalError as e:
            db.rollback()
            if "could not obtain lock" in str(e).lower():
                raise HTTPException(status_code=409, detail="This media is currently being modified.")
            raise HTTPException(status_code=500, detail="Database transaction failed.")
        except HTTPException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            raise HTTPException(status_code=500, detail="Internal server error.")

        try:
            college_filter_rebuild_dispatcher.dispatch(
                CollegeFilterRebuildRequest(
                    reason=f"MEDIA_{action}",
                    rebuild_mode=CollegeFilterRebuildMode.READ_MODEL_ONLY,
                    trigger_exam_code=None,
                    created_by=f"admin:{admin_id}",
                )
            )
        except Exception:
            logger.exception(
                "Failed to dispatch college-filter read-model rebuild after media triage "
                "college_id=%s media_id=%s action=%s",
                college_id,
                media_id,
                action,
            )

        for s3_key in s3_keys_to_delete:
            try:
                self.storage_client.s3_client.delete_object(
                    Bucket=self.storage_client.bucket_name,
                    Key=s3_key
                )
            except Exception:
                pass

        return {"message": f"Successfully marked as {action}", "media_id": str(media_id)}

    def get_paginated_colleges(self, db: Session, skip: int = 0, limit: int = 50, search_query: str = None):
        count_query = db.query(func.count(College.college_id))
        if search_query:
            count_query = count_query.filter(College.canonical_name.ilike(f"%{search_query}%"))
        total_count = count_query.scalar() or 0

        base_query = db.query(College)
        if search_query:
            base_query = base_query.filter(College.canonical_name.ilike(f"%{search_query}%"))

        paginated_subq = base_query.order_by(College.canonical_name.asc(), College.college_id.asc()).offset(skip).limit(limit).subquery("paginated_colleges")
        PaginatedCollege = aliased(College, paginated_subq)

        logo_subq = select(CollegeMedia.status.label("status"), CollegeMedia.id.label("media_id"), CollegeMedia.storage_key.label("storage_key")).where(
            CollegeMedia.college_id == PaginatedCollege.college_id, CollegeMedia.media_type == MediaTypeEnum.LOGO,
            CollegeMedia.storage_key.isnot(None), CollegeMedia.storage_key != "DELETED_ORPHAN"
        ).order_by(CollegeMedia.ingested_at.desc()).limit(1).correlate(PaginatedCollege).lateral().alias("latest_logo")

        hero_subq = select(CollegeMedia.status.label("status"), CollegeMedia.id.label("media_id"), CollegeMedia.storage_key.label("storage_key")).where(
            CollegeMedia.college_id == PaginatedCollege.college_id, CollegeMedia.media_type == MediaTypeEnum.CAMPUS_HERO,
            CollegeMedia.storage_key.isnot(None), CollegeMedia.storage_key != "DELETED_ORPHAN"
        ).order_by(CollegeMedia.ingested_at.desc()).limit(1).correlate(PaginatedCollege).lateral().alias("latest_hero")

        logo_tracker = aliased(MediaIngestionTracker)
        hero_tracker = aliased(MediaIngestionTracker)

        final_query = db.query(
            PaginatedCollege, logo_subq.c.status.label("logo_status"), logo_subq.c.media_id.label("logo_media_id"), logo_subq.c.storage_key.label("logo_storage_key"),
            hero_subq.c.status.label("hero_status"), hero_subq.c.media_id.label("hero_media_id"), hero_subq.c.storage_key.label("hero_storage_key"),
            func.coalesce(logo_tracker.is_exhausted, False).label("logo_exhausted"), func.coalesce(hero_tracker.is_exhausted, False).label("hero_exhausted")
        ).select_from(PaginatedCollege).outerjoin(logo_subq, true()).outerjoin(hero_subq, true())\
        .outerjoin(logo_tracker, (logo_tracker.college_id == PaginatedCollege.college_id) & (logo_tracker.media_type == MediaTypeEnum.LOGO.value))\
        .outerjoin(hero_tracker, (hero_tracker.college_id == PaginatedCollege.college_id) & (hero_tracker.media_type == MediaTypeEnum.CAMPUS_HERO.value))\
        .order_by(PaginatedCollege.canonical_name.asc(), PaginatedCollege.college_id.asc())

        results = []
        for row in final_query.all():
            college = row[0] 
            derived_state = "EMPTY"
            if row.logo_status == MediaStatusEnum.PENDING or row.hero_status == MediaStatusEnum.PENDING: derived_state = "PENDING"
            elif row.logo_status == MediaStatusEnum.ACCEPTED or row.hero_status == MediaStatusEnum.ACCEPTED: derived_state = "ACCEPTED"
            elif row.logo_exhausted or row.hero_exhausted: derived_state = "EXHAUSTED"
            elif row.logo_status == MediaStatusEnum.REJECTED or row.hero_status == MediaStatusEnum.REJECTED: derived_state = "GRAVEYARD"

            results.append({
                "college_id": str(college.college_id), "canonical_name": college.canonical_name, "city": college.city, "derived_state": derived_state,
                "media_details": {
                    "LOGO": { "media_id": str(row.logo_media_id) if row.logo_media_id else None, "status": row.logo_status.value if row.logo_status else None, "exhausted": row.logo_exhausted, "source_url": urljoin(self.cdn_base_url, row.logo_storage_key.lstrip("/")) if row.logo_storage_key else None },
                    "CAMPUS_HERO": { "media_id": str(row.hero_media_id) if row.hero_media_id else None, "status": row.hero_status.value if row.hero_status else None, "exhausted": row.hero_exhausted, "source_url": urljoin(self.cdn_base_url, row.hero_storage_key.lstrip("/")) if row.hero_storage_key else None }
                }
            })
        return { "total_count": total_count, "data": results }

media_governance_service = MediaGovernanceService()