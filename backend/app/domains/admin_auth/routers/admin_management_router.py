from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.database import SessionLocal
from app.models import AdminUser, AdminRole, AdminAuditTrail
from app.domains.admin_auth.services.auth_dependency import get_current_admin, require_role
from app.domains.admin_auth.services.security_service import SecurityService
from app.domains.admin_auth.schemas.auth_schemas import AdminCreateRequest, AdminResponse, AdminUpdateRequest

router = APIRouter(
    prefix="/admin/users", 
    tags=["Admin Management (Super Admin Only)"],
    dependencies=[Depends(require_role(AdminRole.SUPERADMIN))] # <--- THE FORTRESS LOCK
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- HELPER: ENSURE SURVIVAL ---
def ensure_superadmin_survival(db: Session, target_user: AdminUser):
    """
    Blocks action if target is the LAST remaining Super Admin.
    """
    if target_user.role == AdminRole.SUPERADMIN:
        count = db.query(AdminUser).filter(AdminUser.role == AdminRole.SUPERADMIN).count()
        if count <= 1:
            raise HTTPException(
                status_code=400, 
                detail="Operation denied. You cannot remove/demote the last Super Admin."
            )

@router.get("/", response_model=List[AdminResponse])
def list_admins(db: Session = Depends(get_db)):
    """List all admin users."""
    return db.query(AdminUser).order_by(AdminUser.created_at.desc()).all()

@router.post("/", response_model=AdminResponse)
def create_admin(
    req: AdminCreateRequest, 
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """Create a new admin user."""
    # 1. Check Uniqueness
    if db.query(AdminUser).filter((AdminUser.username == req.username) | (AdminUser.email == req.email)).first():
        raise HTTPException(status_code=400, detail="Username or Email already exists")

    # 2. Hash Password
    hashed = SecurityService.get_password_hash(req.password)

    # 3. Create User
    new_admin = AdminUser(
        username=req.username,
        email=req.email,
        hashed_password=hashed,
        role=req.role,
        is_active=True
    )
    db.add(new_admin)
    
    # 4. Audit Log
    db.add(AdminAuditTrail(
        admin_id=current_admin.id,
        action="CREATE_ADMIN",
        details={"target_user": req.username, "role": req.role}
    ))
    
    db.commit()
    db.refresh(new_admin)
    return new_admin

@router.patch("/{admin_id}", response_model=AdminResponse)
def update_admin(
    admin_id: uuid.UUID,
    req: AdminUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """Update role, status, or reset password."""
    target = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Admin not found")

    # [HARDENING 1] Prevent Self-Sabotage
    if target.id == current_admin.id:
        if req.is_active is False:
            raise HTTPException(status_code=400, detail="You cannot disable your own account")
        if req.role and req.role != AdminRole.SUPERADMIN:
            raise HTTPException(status_code=400, detail="You cannot demote your own account.")

    # [HARDENING 2] Prevent Demoting Last Super Admin
    if req.role and req.role != AdminRole.SUPERADMIN:
        ensure_superadmin_survival(db, target)
        
    # [HARDENING 3] Prevent Disabling Last Super Admin
    if req.is_active is False:
        ensure_superadmin_survival(db, target)

    updates = []
    if req.role:
        target.role = req.role
        updates.append(f"role={req.role}")
    
    if req.is_active is not None:
        target.is_active = req.is_active
        updates.append(f"active={req.is_active}")

    if req.password:
        target.hashed_password = SecurityService.get_password_hash(req.password)
        updates.append("password_reset")

    if updates:
        db.add(AdminAuditTrail(
            admin_id=current_admin.id,
            action="UPDATE_ADMIN",
            target_resource=target.username,
            details={"changes": updates}
        ))
        db.commit()
        db.refresh(target)

    return target

@router.delete("/{admin_id}")
def delete_admin(
    admin_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin)
):
    """Permanently delete an admin."""
    target = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Admin not found")
        
    # [HARDENING 1] Prevent Self-Deletion
    if target.id == current_admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete yourself")

    # [HARDENING 2] Prevent Deleting Last Super Admin
    ensure_superadmin_survival(db, target)

    username = target.username
    db.delete(target)
    
    db.add(AdminAuditTrail(
        admin_id=current_admin.id,
        action="DELETE_ADMIN",
        target_resource=username
    ))
    db.commit()
    
    return {"message": f"Admin {username} deleted successfully"}