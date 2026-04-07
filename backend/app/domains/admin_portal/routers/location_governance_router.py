import logging
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional, List
from enum import Enum

from app.database import SessionLocal
from app.models import AdminUser, AdminRole
from app.domains.admin_auth.services.auth_dependency import get_current_admin, require_role
from app.domains.admin_portal.services.location_governance_service import location_governance_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/location-governance",
    tags=["Location Governance Control Plane"],
    dependencies=[Depends(require_role(AdminRole.EDITOR))]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class TriageAction(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    DELETE = "DELETE"

class LocationDispatchRequest(BaseModel):
    college_id: UUID
    force: bool = False

class LocationTriageRequest(BaseModel):
    candidate_id: Optional[UUID] = None 
    action: TriageAction 
    city: Optional[str] = None
    district: Optional[str] = None
    state_code: Optional[str] = None
    pincode: Optional[str] = None

class LocationBulkDispatchRequest(BaseModel):
    college_ids: List[UUID] = Field(
        ..., 
        max_length=200, 
        description="Max 200 items per batch to prevent Celery queue saturation."
    )
    force: bool = False

@router.get("/colleges")
def get_location_colleges(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None), # [NEW] Added status query param
    db: Session = Depends(get_db)
):
    return location_governance_service.get_paginated_colleges(
        db=db, skip=skip, limit=limit, search_query=search, status_filter=status
    )

@router.post("/dispatch")
def dispatch_location_ingestion(
    req: LocationDispatchRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    return location_governance_service.dispatch_ingestion(
        db=db,
        college_id=req.college_id,
        admin_id=current_admin.id,
        admin_username=current_admin.username,
        force=req.force
    )

@router.post("/triage/{college_id}")
def triage_location_candidate(
    college_id: UUID,
    req: LocationTriageRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    # Strict API Contract Validation
    if req.action in (TriageAction.ACCEPT, TriageAction.REJECT) and not req.candidate_id:
        raise HTTPException(status_code=400, detail="candidate_id is strictly required for ACCEPT and REJECT actions.")

    overrides = {
        "city": req.city,
        "district": req.district,
        "state_code": req.state_code,
        "pincode": req.pincode
    }
    
    return location_governance_service.triage_location(
        db=db,
        college_id=college_id,
        candidate_id=req.candidate_id,
        action=req.action.value,
        admin_id=current_admin.id,
        overrides=overrides
    )

@router.post("/dispatch-batch")
def dispatch_bulk_location_ingestion(
    req: LocationBulkDispatchRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    return location_governance_service.dispatch_bulk_ingestion(
        db=db,
        college_ids=req.college_ids,
        admin_id=current_admin.id,
        admin_username=current_admin.username,
        force=req.force
    )

@router.get("/status")
def get_ingestion_status():
    try:
        from ingestion.location_pipeline.core.redis_lock import redis_client
        val = redis_client.get("telemetry:active_location_tasks")
        active_count = max(0, int(val)) if val else 0
        return {"is_ingesting": active_count > 0, "active_tasks": active_count}
    except Exception as e:
        logger.error(f"[Telemetry] Failed to fetch location ingestion status from Redis: {str(e)}")
        return {"is_ingesting": False, "active_tasks": 0}