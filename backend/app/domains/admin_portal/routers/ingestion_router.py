from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, Body
from sqlalchemy import text, select, desc, update
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.database import SessionLocal 
from app.models import DiscoveredArtifact, IngestionRun, AdminRole 
from app.domains.admin_portal.services.lock_service import LockService
from ingestion.common.process_artifacts import ArtifactProcessor
# [UPDATE] Import Enforcer
from app.domains.admin_auth.services.auth_dependency import get_current_admin, require_role 

router = APIRouter(prefix="/ingestion", tags=["Admin Portal: Ingestion"], dependencies=[Depends(get_current_admin)])

def get_sync_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/status")
def get_ingestion_status(db: Session = Depends(get_sync_db)):
    running_count = db.query(IngestionRun).filter(IngestionRun.status == "RUNNING").count()
    return {"is_ingesting": running_count > 0}

@router.get("/artifacts")
def list_artifacts(db: Session = Depends(get_sync_db)):
    artifacts = db.execute(
        select(DiscoveredArtifact)
        .order_by(desc(DiscoveredArtifact.created_at))
    ).scalars().all()

    return [
        {
            "id": str(a.id),
            "pdf_path": a.pdf_path,
            "exam_code": a.exam_code,
            "year": a.year,
            "round_name": a.round_name,
            "round_number": a.round_number,
            "status": a.status,
            "requires_reprocessing": a.requires_reprocessing,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "review_notes": a.review_notes,
        }
        for a in artifacts
    ]

def run_ingestion_task(exam_code: str = "GLOBAL"):
    db = SessionLocal()
    lock_key = f"INGESTION:{exam_code}"
    locked = False 
    try:
        if LockService.acquire_lock(db, lock_key):
            locked = True
            processor = ArtifactProcessor(db)
            target_exam = exam_code if exam_code != "GLOBAL" else None
            processor.process_approved_artifacts(specific_exam=target_exam)
        else:
            print(f"🔒 Ingestion Locked for {exam_code}. Skipping run.")
            return
    finally:
        if locked:
            LockService.release_lock(db, lock_key)
        db.close()

# [SECURE] Write Action -> Requires EDITOR
@router.post("/approve-batch")
def approve_batch_artifacts(
    background_tasks: BackgroundTasks, 
    artifact_ids: List[uuid.UUID] = Body(..., embed=True),
    db: Session = Depends(get_sync_db),
    _ = Depends(require_role(AdminRole.EDITOR)) # <--- Guard
):
    if not artifact_ids:
        raise HTTPException(status_code=400, detail="No artifacts selected")

    try:
        stmt = (
            update(DiscoveredArtifact)
            .where(DiscoveredArtifact.id.in_(artifact_ids))
            .values(status='APPROVED', requires_reprocessing=True)
        )
        result = db.execute(stmt)
        db.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="No matching artifacts found to update.")
            
        count = result.rowcount
        
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    background_tasks.add_task(run_ingestion_task, "GLOBAL")
    return {"status": "success", "message": f"Queued {count} artifacts for immediate ingestion."}

# [SECURE] Write Action -> Requires EDITOR
@router.post("/apply-dirty")
def trigger_dirty_update(
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_sync_db),
    _ = Depends(require_role(AdminRole.EDITOR)) # <--- Guard
):
    try:
        db.execute(
            text("UPDATE discovered_artifacts SET status = 'APPROVED' WHERE requires_reprocessing = true AND status = 'INGESTED'")
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    background_tasks.add_task(run_ingestion_task, "GLOBAL")
    return {"status": "Job Queued", "message": "Ingestion triggered for dirty artifacts."}