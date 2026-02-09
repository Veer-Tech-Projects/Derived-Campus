from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.registry_service import RegistryService
from app.models import CollegeCandidate, DiscoveredArtifact, RegistryAuditLog
from sqlalchemy import update
from typing import List
from pydantic import BaseModel
import uuid
from sqlalchemy import select, desc

router = APIRouter(prefix="/identity", tags=["Admin Portal: Identity"])

def get_sync_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class LinkRequest(BaseModel):
    candidate_ids: List[int]
    target_registry_uuid: uuid.UUID
    user_email: str = "admin@derivedcampus.com"

class PromoteRequest(BaseModel):
    candidate_ids: List[int]
    official_name: str
    user_email: str = "admin@derivedcampus.com"
    # state_code REMOVED completely.

@router.post("/link")
def link_candidate(req: LinkRequest, db: Session = Depends(get_sync_db)):
    service = RegistryService()
    candidates = db.query(CollegeCandidate).filter(CollegeCandidate.candidate_id.in_(req.candidate_ids)).all()
    if not candidates: raise HTTPException(404, "No candidates found")

    for cand in candidates:
        service.link_alias(db, req.target_registry_uuid, service.normalize_name(cand.raw_name), "manual_triage")
        
        db.add(RegistryAuditLog(
            entity_type="ALIAS", entity_id=req.target_registry_uuid,
            action="LINKED", performed_by=req.user_email,
            reason=f"Linked candidate {cand.raw_name}"
        ))

        db.execute(
            update(DiscoveredArtifact)
            .where(DiscoveredArtifact.id == uuid.UUID(cand.source_document))
            .values(requires_reprocessing=True)
        )
        db.delete(cand)
    
    db.commit()
    return {"status": "linked", "count": len(candidates)}

@router.post("/promote-new")
def promote_new_college(req: PromoteRequest, db: Session = Depends(get_sync_db)):
    service = RegistryService()
    candidates = db.query(CollegeCandidate).filter(CollegeCandidate.candidate_id.in_(req.candidate_ids)).all()
    if not candidates: raise HTTPException(404, "No candidates found")

    normalized = service.normalize_name(req.official_name)
    
    # CALL SERVICE WITHOUT STATE CODE
    new_id = service.promote_candidate(
        db, 
        req.official_name, 
        normalized, 
        "manual_promotion"
    )
    
    db.add(RegistryAuditLog(
        entity_type="REGISTRY", entity_id=new_id,
        action="CREATED", performed_by=req.user_email,
        reason=f"Promoted: {req.official_name}"
    ))

    for cand in candidates:
        norm_cand = service.normalize_name(cand.raw_name)
        if norm_cand != normalized:
            service.link_alias(db, new_id, norm_cand, "manual_triage")
            
        db.execute(
            update(DiscoveredArtifact)
            .where(DiscoveredArtifact.id == uuid.UUID(cand.source_document))
            .values(requires_reprocessing=True)
        )
        db.delete(cand)

    db.commit()
    return {"status": "promoted", "new_college_id": new_id}

@router.get("/candidates")
def list_candidates(db: Session = Depends(get_sync_db)):
    candidates = db.execute(
        select(CollegeCandidate)
        .where(CollegeCandidate.status == 'pending')
        .order_by(desc(CollegeCandidate.created_at))
    ).scalars().all()

    return [
        {
            "candidate_id": c.candidate_id,
            "raw_name": c.raw_name,
            "source_document": str(c.source_document),
            "reason_flagged": c.reason_flagged,
            "status": c.status,
            "ingestion_run_id": str(c.ingestion_run_id)
        }
        for c in candidates
    ]