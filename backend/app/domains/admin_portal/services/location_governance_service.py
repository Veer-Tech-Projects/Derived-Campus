import logging
from uuid import UUID
from typing import List, Optional

from sqlalchemy.orm import Session, aliased
from sqlalchemy import select, func, text
from sqlalchemy.sql import true
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import OperationalError
from fastapi import HTTPException

from app.models import (
    College, CollegeLocation, CollegeLocationCandidate, 
    LocationStatusEnum, LocationDispatchLock, LocationIngestionTracker, AdminAuditTrail
)
from ingestion.location_pipeline.tasks import ingest_college_location_task
from app.domains.student_portal.college_filter_tool.services.college_filter_rebuild_dispatcher import (
    CollegeFilterRebuildMode,
    CollegeFilterRebuildRequest,
    college_filter_rebuild_dispatcher,
)

logger = logging.getLogger(__name__)

class LocationGovernanceService:
    
    def dispatch_ingestion(self, db: Session, college_id: UUID, admin_id: UUID, admin_username: str, force: bool = False):
        try:
            college = db.query(College).filter(College.college_id == college_id).first()
            if not college:
                raise HTTPException(status_code=404, detail="College not found")

            base_insert = insert(LocationDispatchLock).values(
                college_id=college_id,
                locked_by=f"admin:{admin_username}",
                expires_at=func.now() + text("interval '15 minutes'")
            )
            
            update_dict = {
                'locked_by': f"admin:{admin_username}",
                'expires_at': func.now() + text("interval '15 minutes'")
            }

            if force:
                lock_stmt = base_insert.on_conflict_do_update(
                    index_elements=['college_id'], set_=update_dict
                )
            else:
                lock_stmt = base_insert.on_conflict_do_update(
                    index_elements=['college_id'], set_=update_dict,
                    where=(LocationDispatchLock.expires_at < func.now())
                )

            if db.execute(lock_stmt).rowcount == 0:
                db.rollback()
                raise HTTPException(status_code=409, detail="Ingestion for Location is currently running.")

            tracker = db.query(LocationIngestionTracker).filter_by(college_id=college_id).first()
            if force:
                if tracker:
                    tracker.attempt_count = 0
                    tracker.is_exhausted = False
                else:
                    db.add(LocationIngestionTracker(college_id=college_id, attempt_count=0, is_exhausted=False))
            else:
                if tracker and tracker.is_exhausted:
                    db.rollback() 
                    raise HTTPException(status_code=400, detail="Ingestion for Location EXHAUSTED.")

            db.add(AdminAuditTrail(
                admin_id=admin_id, action="FORCE_DISPATCH_LOCATION" if force else "DISPATCH_LOCATION",
                target_resource=str(college_id), details={"force": force}
            ))
            db.commit()

        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"[{college_id}] Fatal DB Transaction failed: {str(e)}")
            raise HTTPException(status_code=500, detail="Database transaction failed.")

        ingest_college_location_task.delay(
            college_id=str(college_id), 
            canonical_name=college.canonical_name,
            state_code=college.state_code or ""
        )
        return {"message": "Location Ingestion Dispatched"}

    def dispatch_bulk_ingestion(self, db: Session, college_ids: List[UUID], admin_id: UUID, admin_username: str, force: bool = False):
        summary = {"queued": 0, "skipped_locked": 0, "skipped_exhausted": 0, "errors": 0}
        for cid in college_ids:
            try:
                self.dispatch_ingestion(db, cid, admin_id, admin_username, force)
                summary["queued"] += 1
            except HTTPException as he:
                if he.status_code == 409: summary["skipped_locked"] += 1
                elif he.status_code == 400: summary["skipped_exhausted"] += 1
                else: summary["errors"] += 1
            except Exception as e:
                logger.error(f"Bulk dispatch error on location for {cid}: {e}")
                summary["errors"] += 1

        if summary["queued"] == 0 and sum(summary.values()) > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"No tasks queued. Locked: {summary['skipped_locked']}, Exhausted: {summary['skipped_exhausted']}, Errors: {summary['errors']}."
            )
        return summary

    def triage_location(self, db: Session, college_id: UUID, candidate_id: UUID, action: str, admin_id: UUID, overrides: dict = None):
        action = action.upper()
        try:
            if action not in ("ACCEPT", "REJECT", "DELETE"):
                raise HTTPException(status_code=400, detail="Invalid action.")

            # Explicit SELECT FOR UPDATE NOWAIT ensures Concurrent_Triage(college_id) <= 1
            master_lock = db.execute(
                select(College.college_id)
                .where(College.college_id == college_id)
                .with_for_update(nowait=True)
            ).scalar_one_or_none()

            if not master_lock:
                raise HTTPException(status_code=404, detail="College not found.")

            audit_details = {
                "candidate_id": str(candidate_id) if candidate_id else None,
                "overrides": overrides
            }

            if action == "DELETE":
                canonical = db.query(CollegeLocation).filter(CollegeLocation.college_id == college_id).first()
                if not canonical:
                    raise HTTPException(status_code=400, detail="No canonical location to delete.")
                db.delete(canonical)

                db.query(CollegeLocationCandidate).filter(
                    CollegeLocationCandidate.college_id == college_id,
                    CollegeLocationCandidate.status == LocationStatusEnum.PENDING
                ).update({"status": LocationStatusEnum.REJECTED})

            else:
                candidate = db.query(CollegeLocationCandidate).filter(
                    CollegeLocationCandidate.id == candidate_id,
                    CollegeLocationCandidate.college_id == college_id
                ).one_or_none()

                if not candidate:
                    raise HTTPException(status_code=404, detail="Candidate not found.")
                if candidate.status != LocationStatusEnum.PENDING:
                    raise HTTPException(status_code=400, detail="Can only triage PENDING candidates.")

                if action == "ACCEPT":
                    candidate.status = LocationStatusEnum.ACCEPTED

                    final_city = overrides["city"] if overrides and overrides.get("city") is not None else candidate.city
                    final_district = overrides["district"] if overrides and overrides.get("district") is not None else candidate.district
                    final_state = overrides["state_code"] if overrides and overrides.get("state_code") is not None else candidate.state_code
                    final_pincode = overrides["pincode"] if overrides and overrides.get("pincode") is not None else candidate.pincode

                    stmt = insert(CollegeLocation).values(
                        college_id=college_id,
                        address_line=candidate.address_line,
                        city=final_city,
                        district=final_district,
                        state_code=final_state,
                        pincode=final_pincode,
                        latitude=candidate.latitude,
                        longitude=candidate.longitude
                    ).on_conflict_do_update(
                        index_elements=['college_id'],
                        set_={
                            'address_line': candidate.address_line,
                            'city': final_city,
                            'district': final_district,
                            'state_code': final_state,
                            'pincode': final_pincode,
                            'latitude': candidate.latitude,
                            'longitude': candidate.longitude
                        }
                    )
                    db.execute(stmt)

                    tracker = db.query(LocationIngestionTracker).filter_by(college_id=college_id).first()
                    if tracker:
                        tracker.attempt_count = 0
                        tracker.is_exhausted = False
                    else:
                        db.add(LocationIngestionTracker(college_id=college_id, attempt_count=0, is_exhausted=False))

                elif action == "REJECT":
                    candidate.status = LocationStatusEnum.REJECTED

            db.query(LocationDispatchLock).filter(LocationDispatchLock.college_id == college_id).delete()

            db.add(AdminAuditTrail(
                admin_id=admin_id,
                action=f"TRIAGE_LOCATION_{action}",
                target_resource=str(college_id),
                details=audit_details
            ))
            db.commit()

        except OperationalError as e:
            db.rollback()
            if "could not obtain lock" in str(e).lower():
                raise HTTPException(status_code=409, detail="This location is currently being modified by another admin.")
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
                    reason=f"LOCATION_{action}",
                    rebuild_mode=CollegeFilterRebuildMode.READ_MODEL_ONLY,
                    trigger_exam_code=None,
                    created_by=f"admin:{admin_id}",
                )
            )
        except Exception:
            logger.exception(
                "Failed to dispatch college-filter read-model rebuild after location triage "
                "college_id=%s action=%s",
                college_id,
                action,
            )

        return {"message": f"Successfully marked as {action}"}

    def get_paginated_colleges(self, db: Session, skip: int = 0, limit: int = 50, search_query: str = None, status_filter: str = None):
        base_query = db.query(College)
        
        if search_query:
            base_query = base_query.filter(College.canonical_name.ilike(f"%{search_query}%"))

        # [NEW] Highly optimized Database-Level State Machine Filtering
        if status_filter:
            status_filter = status_filter.upper()
            if status_filter == "ACCEPTED":
                base_query = base_query.filter(
                    db.query(CollegeLocation).filter(CollegeLocation.college_id == College.college_id).exists()
                )
            elif status_filter == "PENDING":
                base_query = base_query.filter(
                    db.query(CollegeLocationCandidate).filter(
                        CollegeLocationCandidate.college_id == College.college_id,
                        CollegeLocationCandidate.status == LocationStatusEnum.PENDING
                    ).exists()
                )
            elif status_filter == "EXHAUSTED":
                base_query = base_query.filter(
                    db.query(LocationIngestionTracker).filter(
                        LocationIngestionTracker.college_id == College.college_id,
                        LocationIngestionTracker.is_exhausted == True
                    ).exists(),
                    ~db.query(CollegeLocation).filter(CollegeLocation.college_id == College.college_id).exists(),
                    ~db.query(CollegeLocationCandidate).filter(
                        CollegeLocationCandidate.college_id == College.college_id,
                        CollegeLocationCandidate.status == LocationStatusEnum.PENDING
                    ).exists()
                )
            elif status_filter == "EMPTY":
                base_query = base_query.filter(
                    ~db.query(CollegeLocation).filter(CollegeLocation.college_id == College.college_id).exists(),
                    ~db.query(CollegeLocationCandidate).filter(
                        CollegeLocationCandidate.college_id == College.college_id,
                        CollegeLocationCandidate.status == LocationStatusEnum.PENDING
                    ).exists(),
                    ~db.query(LocationIngestionTracker).filter(
                        LocationIngestionTracker.college_id == College.college_id,
                        LocationIngestionTracker.is_exhausted == True
                    ).exists()
                )

        count_query = base_query.statement.with_only_columns(func.count(College.college_id)).order_by(None)
        total_count = db.execute(count_query).scalar() or 0

        paginated_subq = base_query.order_by(College.canonical_name.asc(), College.college_id.asc()).offset(skip).limit(limit).subquery("paginated_colleges")
        PaginatedCollege = aliased(College, paginated_subq)

        tracker = aliased(LocationIngestionTracker)
        canonical = aliased(CollegeLocation)
        
        pending_candidate = select(
            CollegeLocationCandidate.id.label("candidate_id"),
            CollegeLocationCandidate.status.label("candidate_status"),
            CollegeLocationCandidate.address_line,
            CollegeLocationCandidate.latitude,
            CollegeLocationCandidate.longitude,
            CollegeLocationCandidate.pincode,
            CollegeLocationCandidate.city,
            CollegeLocationCandidate.district,
            CollegeLocationCandidate.state_code
        ).where(
            CollegeLocationCandidate.college_id == PaginatedCollege.college_id,
            CollegeLocationCandidate.status == LocationStatusEnum.PENDING
        ).limit(1).lateral().alias("pending_cand")

        final_query = db.query(
            PaginatedCollege,
            canonical.address_line.label("canonical_address"),
            pending_candidate.c.candidate_id,
            pending_candidate.c.candidate_status,
            pending_candidate.c.address_line.label("cand_address"),
            pending_candidate.c.latitude,
            pending_candidate.c.longitude,
            pending_candidate.c.pincode,
            pending_candidate.c.city.label("cand_city"),
            pending_candidate.c.district.label("cand_district"),
            pending_candidate.c.state_code.label("cand_state"),
            func.coalesce(tracker.is_exhausted, False).label("is_exhausted")
        ).select_from(PaginatedCollege)\
         .outerjoin(canonical, canonical.college_id == PaginatedCollege.college_id)\
         .outerjoin(pending_candidate, true())\
         .outerjoin(tracker, tracker.college_id == PaginatedCollege.college_id)\
         .order_by(PaginatedCollege.canonical_name.asc())

        results = []
        for row in final_query.all():
            college = row[0]
            
            derived_state = "EMPTY"
            if row.candidate_status == LocationStatusEnum.PENDING: derived_state = "PENDING"
            elif row.canonical_address is not None: derived_state = "ACCEPTED"
            elif row.is_exhausted: derived_state = "EXHAUSTED"

            candidate_payload = None
            if row.candidate_id:
                candidate_payload = {
                    "candidate_id": str(row.candidate_id),
                    "raw_address": row.cand_address,
                    "latitude": float(row.latitude) if row.latitude else None,
                    "longitude": float(row.longitude) if row.longitude else None,
                    "pincode": row.pincode,
                    "parsed_city": row.cand_city,
                    "parsed_district": row.cand_district,
                    "parsed_state_code": row.cand_state
                }

            results.append({
                "college_id": str(college.college_id), 
                "canonical_name": college.canonical_name, 
                "registry_city": college.city, 
                "registry_state_code": college.state_code,
                "derived_state": derived_state,
                "canonical_address": row.canonical_address,
                "candidate_details": candidate_payload
            })
            
        return { "total_count": total_count, "data": results }

location_governance_service = LocationGovernanceService()