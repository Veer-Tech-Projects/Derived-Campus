from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime

from app.database import SessionLocal
from app.models import AdminAuditTrail, AdminUser, AdminRole
from app.domains.admin_auth.services.auth_dependency import require_role
from app.domains.admin_auth.schemas.auth_schemas import AuditLogResponse

router = APIRouter(
    prefix="/admin/audit", 
    tags=["Admin Audit Logs"],
    dependencies=[Depends(require_role(AdminRole.SUPERADMIN))]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[AuditLogResponse])
def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    action: Optional[str] = None,
    username: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Fetch system audit logs with optional filtering.
    """
    query = db.query(AdminAuditTrail).options(joinedload(AdminAuditTrail.admin))

    if action:
        query = query.filter(AdminAuditTrail.action == action)
    
    if username:
        query = query.join(AdminUser).filter(AdminUser.username.ilike(f"%{username}%"))

    # Default sort: Newest first
    logs = query.order_by(AdminAuditTrail.created_at.desc()).offset(skip).limit(limit).all()

    # Transform for schema (flatten username)
    return [
        {
            "id": log.id,
            "admin_username": log.admin.username if log.admin else "System/Deleted",
            "action": log.action,
            "target_resource": log.target_resource,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at
        }
        for log in logs
    ]