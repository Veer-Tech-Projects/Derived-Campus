import uuid
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import select

# [FIX] Import SessionLocal to create a synchronous connection
from app.database import SessionLocal

from app.domains.admin_auth.services.auth_dependency import get_current_admin, require_role
from app.models import ExamCourseTypeCandidate, ExamBranchCandidate, AdminUser, AdminRole, ExamBranchRegistry, ExamCourseType

from app.domains.admin_portal.services.course_triage_service import (
    CourseTypeTriageService, 
    BranchTriageService,
    TriageConcurrencyEngine,
)
from app.domains.student_portal.college_filter_tool.services.college_filter_rebuild_dispatcher import (
    CollegeFilterRebuildMode,
    CollegeFilterRebuildRequest,
    college_filter_rebuild_dispatcher,
)

logger = logging.getLogger(__name__)

# [FIX] Synchronous DB Generator matching identity_router.py
def get_sync_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter(
    prefix="/triage/courses",
    tags=["Admin Course Taxonomy Triage"],
    dependencies=[Depends(get_current_admin)]
)

# ==========================================
# STRICT PYDANTIC PAYLOAD SCHEMAS
# ==========================================

class CourseTypePromoteRequest(BaseModel):
    canonical_name: str

class CourseTypeLinkRequest(BaseModel):
    target_course_type_id: uuid.UUID

class BranchPromoteRequest(BaseModel):
    discipline: str
    variant: Optional[str] = None

class BranchLinkRequest(BaseModel):
    target_branch_id: uuid.UUID

class CandidateQueueResponse(BaseModel):
    id: uuid.UUID
    exam_code: str
    raw_name: str
    normalized_name: str
    status: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class TaxonomyAliasPromotionRequest(BaseModel):
    registry_id: uuid.UUID
    alias_text: str


# ==========================================
# DOMAIN A: COURSE TYPE TRIAGE ENDPOINTS
# ==========================================

@router.get("/course-types/queue", response_model=List[CandidateQueueResponse])
def get_course_type_queue(
    exam_code: str = Query(..., description="The exam code namespace"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_sync_db), # [FIX] Inject Sync DB
    admin: AdminUser = Depends(require_role(AdminRole.EDITOR))
):
    try:
        candidates = db.scalars(
            select(ExamCourseTypeCandidate)
            .where(
                ExamCourseTypeCandidate.exam_code == exam_code,
                ExamCourseTypeCandidate.status == "PENDING"
            )
            .order_by(ExamCourseTypeCandidate.created_at.asc())
            .offset(offset)
            .limit(limit)
        ).all()
        return candidates
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/course-types/candidates/{candidate_id}/promote")
def promote_course_type(
    candidate_id: uuid.UUID,
    payload: CourseTypePromoteRequest,
    db: Session = Depends(get_sync_db),
    admin: AdminUser = Depends(require_role(AdminRole.EDITOR))
):
    try:
        registry_entity = CourseTypeTriageService.promote_candidate(
            db, str(candidate_id), payload.canonical_name
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    try:
        college_filter_rebuild_dispatcher.dispatch(
            CollegeFilterRebuildRequest(
                reason="COURSE_TAXONOMY_PROMOTED",
                rebuild_mode=CollegeFilterRebuildMode.SERVING_AND_READ_MODEL,
                trigger_exam_code=registry_entity.exam_code,
                created_by=f"admin:{admin.username}",
            )
        )
    except Exception:
        logger.exception(
            "Failed to dispatch college-filter rebuild after course promote "
            "candidate_id=%s exam_code=%s",
            candidate_id,
            registry_entity.exam_code,
        )

    return {
        "status": "success",
        "message": "Candidate promoted",
        "registry_id": registry_entity.id,
    }

@router.post("/course-types/candidates/{candidate_id}/link")
def link_course_type(
    candidate_id: uuid.UUID,
    payload: CourseTypeLinkRequest,
    db: Session = Depends(get_sync_db),
    admin: AdminUser = Depends(require_role(AdminRole.EDITOR))
):
    candidate = db.scalar(
        select(ExamCourseTypeCandidate).where(ExamCourseTypeCandidate.id == candidate_id)
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    exam_code = candidate.exam_code

    try:
        CourseTypeTriageService.link_candidate(
            db, str(candidate_id), str(payload.target_course_type_id)
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    try:
        college_filter_rebuild_dispatcher.dispatch(
            CollegeFilterRebuildRequest(
                reason="COURSE_TAXONOMY_LINKED",
                rebuild_mode=CollegeFilterRebuildMode.SERVING_AND_READ_MODEL,
                trigger_exam_code=exam_code,
                created_by=f"admin:{admin.username}",
            )
        )
    except Exception:
        logger.exception(
            "Failed to dispatch college-filter rebuild after course link "
            "candidate_id=%s exam_code=%s",
            candidate_id,
            exam_code,
        )

    return {"status": "success", "message": "Candidate linked successfully."}

@router.post("/course-types/candidates/{candidate_id}/reject")
def reject_course_type(
    candidate_id: uuid.UUID,
    db: Session = Depends(get_sync_db), # [FIX] Inject Sync DB
    admin: AdminUser = Depends(require_role(AdminRole.EDITOR))
):
    try:
        CourseTypeTriageService.reject_candidate(db, str(candidate_id))
        db.commit()
        return {"status": "success", "message": "Candidate rejected and suppressed."}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/course-types/registry")
def list_course_type_registry(
    exam_code: str = Query(..., description="The exam code namespace"),
    db: Session = Depends(get_sync_db), # [FIX] Inject Sync DB
    admin: AdminUser = Depends(require_role(AdminRole.EDITOR))
):
    registry = db.scalars(
        select(ExamCourseType)
        .where(ExamCourseType.exam_code == exam_code)
        .order_by(ExamCourseType.normalized_name.asc())
        .limit(1000)
    ).all()
    return [{"id": str(r.id), "name": r.normalized_name} for r in registry]


@router.post("/course-types/promote-alias")
def promote_course_type_alias(
    req: TaxonomyAliasPromotionRequest,
    db: Session = Depends(get_sync_db),
    admin: AdminUser = Depends(require_role(AdminRole.EDITOR))
):
    try:
        registry_entity = db.query(ExamCourseType).filter(ExamCourseType.id == req.registry_id).first()
        if not registry_entity:
            raise HTTPException(status_code=404, detail="Course Type not found.")

        registry_entity.canonical_name = req.alias_text
        registry_entity.normalized_name = TriageConcurrencyEngine.normalize_string(req.alias_text)

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    try:
        college_filter_rebuild_dispatcher.dispatch(
            CollegeFilterRebuildRequest(
                reason="COURSE_ALIAS_PROMOTED_TO_CANONICAL",
                rebuild_mode=CollegeFilterRebuildMode.READ_MODEL_ONLY,
                trigger_exam_code=registry_entity.exam_code,
                created_by=f"admin:{admin.username}",
            )
        )
    except Exception:
        logger.exception(
            "Failed to dispatch read-model rebuild after course alias promote "
            "registry_id=%s exam_code=%s",
            req.registry_id,
            registry_entity.exam_code,
        )

    return {"status": "success", "new_name": req.alias_text}


# ==========================================
# DOMAIN B: BRANCH TRIAGE ENDPOINTS
# ==========================================

@router.get("/branches/queue", response_model=List[CandidateQueueResponse])
def get_branch_queue(
    exam_code: str = Query(..., description="The exam code namespace"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_sync_db), # [FIX] Inject Sync DB
    admin: AdminUser = Depends(require_role(AdminRole.EDITOR))
):
    try:
        candidates = db.scalars(
            select(ExamBranchCandidate)
            .where(
                ExamBranchCandidate.exam_code == exam_code,
                ExamBranchCandidate.status == "PENDING"
            )
            .order_by(ExamBranchCandidate.created_at.asc())
            .offset(offset)
            .limit(limit)
        ).all()
        return candidates
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/branches/candidates/{candidate_id}/promote")
def promote_branch(
    candidate_id: uuid.UUID,
    payload: BranchPromoteRequest,
    db: Session = Depends(get_sync_db),
    admin: AdminUser = Depends(require_role(AdminRole.EDITOR))
):
    try:
        registry_entity = BranchTriageService.promote_candidate(
            db, str(candidate_id), payload.discipline, payload.variant
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    try:
        college_filter_rebuild_dispatcher.dispatch(
            CollegeFilterRebuildRequest(
                reason="BRANCH_TAXONOMY_PROMOTED",
                rebuild_mode=CollegeFilterRebuildMode.SERVING_AND_READ_MODEL,
                trigger_exam_code=registry_entity.exam_code,
                created_by=f"admin:{admin.username}",
            )
        )
    except Exception:
        logger.exception(
            "Failed to dispatch college-filter rebuild after branch promote "
            "candidate_id=%s exam_code=%s",
            candidate_id,
            registry_entity.exam_code,
        )

    return {
        "status": "success",
        "message": "Branch promoted",
        "registry_id": registry_entity.id,
    }

@router.post("/branches/candidates/{candidate_id}/link")
def link_branch(
    candidate_id: uuid.UUID,
    payload: BranchLinkRequest,
    db: Session = Depends(get_sync_db),
    admin: AdminUser = Depends(require_role(AdminRole.EDITOR))
):
    candidate = db.scalar(
        select(ExamBranchCandidate).where(ExamBranchCandidate.id == candidate_id)
    )
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    exam_code = candidate.exam_code

    try:
        BranchTriageService.link_candidate(
            db, str(candidate_id), str(payload.target_branch_id)
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    try:
        college_filter_rebuild_dispatcher.dispatch(
            CollegeFilterRebuildRequest(
                reason="BRANCH_TAXONOMY_LINKED",
                rebuild_mode=CollegeFilterRebuildMode.SERVING_AND_READ_MODEL,
                trigger_exam_code=exam_code,
                created_by=f"admin:{admin.username}",
            )
        )
    except Exception:
        logger.exception(
            "Failed to dispatch college-filter rebuild after branch link "
            "candidate_id=%s exam_code=%s",
            candidate_id,
            exam_code,
        )

    return {"status": "success", "message": "Branch linked successfully."}

@router.post("/branches/candidates/{candidate_id}/reject")
def reject_branch(
    candidate_id: uuid.UUID,
    db: Session = Depends(get_sync_db), # [FIX] Inject Sync DB
    admin: AdminUser = Depends(require_role(AdminRole.EDITOR))
):
    try:
        BranchTriageService.reject_candidate(db, str(candidate_id))
        db.commit()
        return {"status": "success", "message": "Branch rejected and suppressed."}
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/branches/registry")
def list_branch_registry(
    exam_code: str = Query(..., description="The exam code namespace"),
    db: Session = Depends(get_sync_db), # [FIX] Inject Sync DB
    admin: AdminUser = Depends(require_role(AdminRole.EDITOR))
):
    registry = db.scalars(
        select(ExamBranchRegistry)
        .where(ExamBranchRegistry.exam_code == exam_code)
        .order_by(ExamBranchRegistry.normalized_name.asc())
        .limit(1000)
    ).all()
    return [{"id": str(r.id), "name": r.normalized_name} for r in registry]


@router.post("/branches/promote-alias")
def promote_branch_alias(
    req: TaxonomyAliasPromotionRequest,
    db: Session = Depends(get_sync_db),
    admin: AdminUser = Depends(require_role(AdminRole.EDITOR))
):
    try:
        registry_entity = db.query(ExamBranchRegistry).filter(ExamBranchRegistry.id == req.registry_id).first()
        if not registry_entity:
            raise HTTPException(status_code=404, detail="Branch not found.")

        registry_entity.discipline = req.alias_text
        registry_entity.variant = None
        registry_entity.normalized_name = BranchTriageService._generate_branch_normalized_name(
            req.alias_text,
            None,
        )

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    try:
        college_filter_rebuild_dispatcher.dispatch(
            CollegeFilterRebuildRequest(
                reason="BRANCH_ALIAS_PROMOTED_TO_CANONICAL",
                rebuild_mode=CollegeFilterRebuildMode.READ_MODEL_ONLY,
                trigger_exam_code=registry_entity.exam_code,
                created_by=f"admin:{admin.username}",
            )
        )
    except Exception:
        logger.exception(
            "Failed to dispatch read-model rebuild after branch alias promote "
            "registry_id=%s exam_code=%s",
            req.registry_id,
            registry_entity.exam_code,
        )

    return {"status": "success", "new_name": req.alias_text}