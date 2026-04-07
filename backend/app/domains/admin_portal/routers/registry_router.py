from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from app.database import SessionLocal
from pydantic import BaseModel
import uuid
from app.models import College, CollegeAlias, AdminRole
from sqlalchemy import select
# [UPDATE] Import Enforcer
from app.domains.admin_auth.services.auth_dependency import get_current_admin, require_role
import logging
from app.domains.student_portal.college_filter_tool.services.college_filter_rebuild_dispatcher import (
    CollegeFilterRebuildMode,
    CollegeFilterRebuildRequest,
    college_filter_rebuild_dispatcher,
)

logger = logging.getLogger(__name__)

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
    admin = Depends(require_role(AdminRole.EDITOR))
):
    college = db.query(College).filter(College.college_id == req.college_id).first()
    if not college:
        raise HTTPException(404, "College not found")

    try:
        college.canonical_name = req.alias_text
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    try:
        college_filter_rebuild_dispatcher.dispatch(
            CollegeFilterRebuildRequest(
                reason="REGISTRY_ALIAS_PROMOTED_TO_CANONICAL",
                rebuild_mode=CollegeFilterRebuildMode.READ_MODEL_ONLY,
                trigger_exam_code=None,
                created_by=f"admin:{getattr(admin, 'username', 'unknown')}",
            )
        )
    except Exception:
        logger.exception(
            "Failed to dispatch college-filter read-model rebuild after registry promote-alias "
            "college_id=%s",
            req.college_id,
        )

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