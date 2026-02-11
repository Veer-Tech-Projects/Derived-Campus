from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.models import AdminRole
from app.domains.admin_portal.services.seat_triage_service import SeatTriageService
# [UPDATE] Import Enforcer
from app.domains.admin_auth.services.auth_dependency import get_current_admin, require_role

router = APIRouter(
    prefix="/admin/triage/seat-policy",
    tags=["Admin - Seat Policy Triage"],
    dependencies=[Depends(get_current_admin)]
)

triage_service = SeatTriageService()

@router.get("/pending")
async def get_pending_violations(
    skip: int = 0, 
    limit: int = 50, 
    db: AsyncSession = Depends(get_db)
):
    return await triage_service.get_pending_violations(db, skip, limit)

# [SECURE] Write Action -> Requires EDITOR
@router.post("/{violation_id}/promote")
async def promote_seat_bucket(
    violation_id: UUID, 
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_role(AdminRole.EDITOR)) # <--- Guard
):
    try:
        await triage_service.promote_bucket(db, violation_id)
        return {"status": "success", "message": "Bucket type promoted and reprocessing triggered."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"Promotion Error: {e}") 
        raise HTTPException(status_code=500, detail="Internal server error during promotion.")

# [SECURE] Write Action -> Requires EDITOR
@router.post("/{violation_id}/ignore")
async def ignore_seat_bucket(
    violation_id: UUID, 
    db: AsyncSession = Depends(get_db),
    _ = Depends(require_role(AdminRole.EDITOR)) # <--- Guard
):
    await triage_service.ignore_bucket(db, violation_id)
    return {"status": "success", "message": "Bucket type ignored."}