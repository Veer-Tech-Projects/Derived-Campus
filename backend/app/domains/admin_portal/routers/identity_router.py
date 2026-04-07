from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.registry_service import RegistryService
from app.models import CollegeCandidate, DiscoveredArtifact, RegistryAuditLog, AdminRole, AdminUser
from sqlalchemy import update, select, desc
from typing import List
from pydantic import BaseModel
import uuid
# [UPDATE] Import the new role enforcer
from app.domains.admin_auth.services.auth_dependency import get_current_admin, require_role

router = APIRouter(prefix="/identity", tags=["Admin Portal: Identity"], dependencies=[Depends(get_current_admin)])

def get_sync_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _get_candidate_origin_source_type(db: Session, candidate: CollegeCandidate) -> str:
    artifact = db.execute(
        select(DiscoveredArtifact).where(
            DiscoveredArtifact.id == uuid.UUID(candidate.source_document)
        )
    ).scalar_one_or_none()

    if not artifact:
        raise HTTPException(
            status_code=400,
            detail=f"Missing originating artifact for candidate {candidate.candidate_id}"
        )

    # Enterprise-safe semantic source resolution:
    # prefer exam family / exam slug over transport-layer detected_source.
    if getattr(artifact, "exam_code", None):
        return str(artifact.exam_code).strip().lower()

    raw_metadata = getattr(artifact, "raw_metadata", None) or {}
    exam_slug = raw_metadata.get("exam_slug")
    if exam_slug:
        return str(exam_slug).strip().lower()

    detected_source = getattr(artifact, "detected_source", None)
    if detected_source:
        return str(detected_source).strip().lower()

    raise HTTPException(
        status_code=400,
        detail=f"Missing semantic origin source for candidate {candidate.candidate_id}"
    )

class LinkRequest(BaseModel):
    candidate_ids: List[int]
    target_registry_uuid: uuid.UUID
    # [FIX] Removed user_email. It is now injected securely.

class PromoteRequest(BaseModel):
    candidate_ids: List[int]
    official_name: str
    # [FIX] Removed user_email.

# [SECURE] Write Action -> Requires EDITOR
@router.post("/link")
def link_candidate(
    req: LinkRequest, 
    db: Session = Depends(get_sync_db),
    admin: AdminUser = Depends(require_role(AdminRole.EDITOR)) # <--- Guard + User Info
):
    service = RegistryService()
    candidates = db.query(CollegeCandidate).filter(CollegeCandidate.candidate_id.in_(req.candidate_ids)).all()
    if not candidates: raise HTTPException(404, "No candidates found")

    for cand in candidates:
        cand_origin_source = _get_candidate_origin_source_type(db, cand)
        service.link_alias(
            db,
            req.target_registry_uuid,
            cand.raw_name,
            "manual_triage",
            origin_source_type=cand_origin_source,
        )
        
        # [FIX] Use actual admin email
        db.add(RegistryAuditLog(
            entity_type="ALIAS", entity_id=req.target_registry_uuid,
            action="LINKED", performed_by=admin.email, 
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

# [SECURE] Write Action -> Requires EDITOR
@router.post("/promote-new")
def promote_new_college(
    req: PromoteRequest, 
    db: Session = Depends(get_sync_db),
    admin: AdminUser = Depends(require_role(AdminRole.EDITOR)) # <--- Guard
):
    service = RegistryService()
    candidates = db.query(CollegeCandidate).filter(CollegeCandidate.candidate_id.in_(req.candidate_ids)).all()
    if not candidates: raise HTTPException(404, "No candidates found")

        # Use the originating candidate source for identity normalization.
    # If multiple candidates are selected, they must share the same source family.
    candidate_source_types = {_get_candidate_origin_source_type(db, c) for c in candidates}
    if len(candidate_source_types) != 1:
        raise HTTPException(
            status_code=400,
            detail=f"Selected candidates span multiple source types: {sorted(candidate_source_types)}"
        )

    origin_source_type = next(iter(candidate_source_types))
    normalized = service.normalize_name(req.official_name, source_type=origin_source_type)

    new_id = service.promote_candidate(
        db,
        req.official_name,
        normalized,
        "manual_promotion",
        origin_source_type=origin_source_type,
    )
    
    # [FIX] Use actual admin email
    db.add(RegistryAuditLog(
        entity_type="REGISTRY", entity_id=new_id,
        action="CREATED", performed_by=admin.email,
        reason=f"Promoted: {req.official_name}"
    ))

    for cand in candidates:
        cand_origin_source = _get_candidate_origin_source_type(db, cand)
        norm_cand = service.normalize_name(cand.raw_name, source_type=cand_origin_source)
        if norm_cand != normalized:
            service.link_alias(
                db,
                new_id,
                cand.raw_name,
                "manual_triage",
                origin_source_type=cand_origin_source,
            )
            
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