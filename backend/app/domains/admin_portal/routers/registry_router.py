from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from app.database import SessionLocal
from pydantic import BaseModel
import uuid
from app.models import College, CollegeAlias, AdminRole
from sqlalchemy import select
# [UPDATE] Import Enforcer
from app.domains.admin_auth.services.auth_dependency import get_current_admin, require_role

router = APIRouter(prefix="/registry", tags=["Admin Portal: Registry"], dependencies=[Depends(get_current_admin)])

def get_sync_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class AliasPromotionRequest(BaseModel):
    college_id: uuid.UUID
    alias_text: str

# [SECURE] Write Action -> Requires EDITOR
@router.post("/promote-alias")
def promote_alias(
    req: AliasPromotionRequest, 
    db: Session = Depends(get_sync_db),
    _ = Depends(require_role(AdminRole.EDITOR)) # <--- Guard
):
    college = db.query(College).filter(College.college_id == req.college_id).first()
    if not college: raise HTTPException(404, "College not found")
        
    college.canonical_name = req.alias_text
    db.commit()
    return {"status": "updated", "new_name": req.alias_text}

@router.get("/colleges")
def list_colleges(db: Session = Depends(get_sync_db)):
    colleges = db.execute(
        select(College)
        .options(selectinload(College.aliases))
        .order_by(College.canonical_name)
    ).scalars().all()

    return [
        {
            "college_id": str(c.college_id),
            "canonical_name": c.canonical_name,
            "state_code": c.state_code,
            "aliases": [a.alias_name for a in c.aliases]
        }
        for c in colleges
    ]