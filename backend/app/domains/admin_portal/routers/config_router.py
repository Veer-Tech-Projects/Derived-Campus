from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Literal

from app.database import SessionLocal 
from app.models import ExamConfiguration, DiscoveredArtifact, CollegeCandidate, College, SeatPolicyQuarantine, AdminRole
# [UPDATE] Import Enforcer
from app.domains.admin_auth.services.auth_dependency import get_current_admin, require_role

router = APIRouter(prefix="/config", tags=["Admin Portal: Configuration"], dependencies=[Depends(get_current_admin)])

def get_sync_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ModeUpdateRequest(BaseModel):
    ingestion_mode: Literal["BOOTSTRAP", "CONTINUOUS"]

@router.get("/dashboard-stats")
def get_stats(db: Session = Depends(get_sync_db)):
    airlock_count = db.query(func.count(DiscoveredArtifact.id)).filter(DiscoveredArtifact.status == 'PENDING').scalar() or 0
    triage_count = db.query(func.count(CollegeCandidate.candidate_id)).filter(CollegeCandidate.status == 'pending').scalar() or 0
    registry_count = db.query(func.count(College.college_id)).scalar() or 0
    seat_policy_count = db.query(func.count(SeatPolicyQuarantine.id)).filter(SeatPolicyQuarantine.status == 'OPEN').scalar() or 0

    return {
        "airlock_pending": airlock_count,
        "triage_pending": triage_count,
        "registry_total": registry_count,
        "seat_policy_pending": seat_policy_count
    }

@router.get("/exams")
def list_exams(db: Session = Depends(get_sync_db)):
    exams = db.execute(select(ExamConfiguration).order_by(ExamConfiguration.exam_code)).scalars().all()
    return [{"exam_code": e.exam_code, "is_active": e.is_active, "ingestion_mode": e.ingestion_mode, "last_updated": e.updated_at} for e in exams]

# [SECURE] Critical Write Action -> Requires SUPERADMIN
@router.patch("/exams/{exam_code}/mode")
def update_exam_mode(
    exam_code: str, 
    req: ModeUpdateRequest, 
    db: Session = Depends(get_sync_db),
    _ = Depends(require_role(AdminRole.SUPERADMIN)) # <--- Guard (God Mode)
):
    exam = db.query(ExamConfiguration).filter(ExamConfiguration.exam_code == exam_code).first()
    if not exam:
        exam = ExamConfiguration(exam_code=exam_code, ingestion_mode=req.ingestion_mode)
        db.add(exam)
    else:
        exam.ingestion_mode = req.ingestion_mode
    db.commit()
    return {"status": "updated", "new_mode": req.ingestion_mode}