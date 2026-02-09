from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from app.database import SessionLocal
from pydantic import BaseModel
import uuid
from app.models import College, CollegeAlias
from sqlalchemy import select

router = APIRouter(prefix="/registry", tags=["Admin Portal: Registry"])

def get_sync_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class AliasPromotionRequest(BaseModel):
    college_id: uuid.UUID
    alias_text: str

@router.post("/promote-alias")
def promote_alias(req: AliasPromotionRequest, db: Session = Depends(get_sync_db)):
    college = db.query(College).filter(College.college_id == req.college_id).first()
    if not college: raise HTTPException(404, "College not found")
        
    college.canonical_name = req.alias_text
    db.commit()
    return {"status": "updated", "new_name": req.alias_text}


@router.get("/colleges")
def list_colleges(db: Session = Depends(get_sync_db)):
    """
    Fetches the Master Registry Tree (Colleges + Aliases).
    """
    # We use selectinload to fetch the related aliases efficiently
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
            # Flatten aliases to a simple list of strings for the frontend
            "aliases": [a.alias_name for a in c.aliases]
        }
        for c in colleges
    ]