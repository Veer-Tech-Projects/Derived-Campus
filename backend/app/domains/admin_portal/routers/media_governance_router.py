from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional, List
from enum import Enum
import logging

from app.database import SessionLocal
from app.models import AdminUser, AdminRole, MediaTypeEnum
from app.domains.admin_auth.services.auth_dependency import get_current_admin, require_role
from app.domains.admin_portal.services.media_governance_service import media_governance_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/media-governance",
    tags=["Media Governance Control Plane"],
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

class DispatchRequest(BaseModel):
    college_id: UUID
    media_type: MediaTypeEnum
    force: bool = False

class TriageRequest(BaseModel):
    media_id: UUID
    action: TriageAction 

class BulkDispatchRequest(BaseModel):
    college_ids: List[UUID] = Field(
        ..., 
        max_length=200, 
        description="Max 200 items per batch to prevent Celery queue saturation and DB transaction locks."
    )
    force: bool = False

@router.get("/colleges")
def get_governance_colleges(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    return media_governance_service.get_paginated_colleges(
        db=db, skip=skip, limit=limit, search_query=search
    )

@router.post("/dispatch")
def dispatch_media_ingestion(
    req: DispatchRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    return media_governance_service.dispatch_ingestion(
        db=db,
        college_id=req.college_id,
        media_type=req.media_type,
        admin_id=current_admin.id,
        admin_username=current_admin.username,
        force=req.force
    )

@router.post("/triage/{college_id}")
def triage_media_candidate(
    college_id: UUID,
    req: TriageRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    return media_governance_service.triage_media(
        db=db,
        college_id=college_id,
        media_id=req.media_id,
        action=req.action.value,
        admin_id=current_admin.id
    )

@router.post("/dispatch-batch")
def dispatch_bulk_media_ingestion(
    req: BulkDispatchRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    return media_governance_service.dispatch_bulk_ingestion(
        db=db,
        college_ids=req.college_ids,
        admin_id=current_admin.id,
        admin_username=current_admin.username,
        force=req.force
    )

@router.get("/status")
def get_ingestion_status():
    try:
        from ingestion.media_ingestion.core.redis_lock import redis_client
        val = redis_client.get("telemetry:active_media_tasks")
        active_count = max(0, int(val)) if val else 0
        return {"is_ingesting": active_count > 0, "active_tasks": active_count}
    except Exception as e:
        logger.error(f"[Telemetry] Failed to fetch ingestion status from Redis: {str(e)}")
        return {"is_ingesting": False, "active_tasks": 0}