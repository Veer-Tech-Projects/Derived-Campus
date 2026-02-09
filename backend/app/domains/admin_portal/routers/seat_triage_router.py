from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.domains.admin_portal.services.seat_triage_service import SeatTriageService

router = APIRouter(
    prefix="/admin/triage/seat-policy",
    tags=["Admin - Seat Policy Triage"]
)

triage_service = SeatTriageService()

@router.get("/pending")
async def get_pending_violations(
    skip: int = 0, 
    limit: int = 50, 
    db: AsyncSession = Depends(get_db)
):
    """List unique seat buckets stuck in quarantine with counts."""
    return await triage_service.get_pending_violations(db, skip, limit)

@router.post("/{violation_id}/promote")
async def promote_seat_bucket(
    violation_id: UUID, 
    db: AsyncSession = Depends(get_db)
):
    """
    APPROVE TYPE: Moves the bucket type to Master Taxonomy and resolves all instances.
    """
    try:
        await triage_service.promote_bucket(db, violation_id)
        return {"status": "success", "message": "Bucket type promoted and reprocessing triggered."}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Log the actual error on the server side
        print(f"Promotion Error: {e}") 
        raise HTTPException(status_code=500, detail="Internal server error during promotion.")

@router.post("/{violation_id}/ignore")
async def ignore_seat_bucket(
    violation_id: UUID, 
    db: AsyncSession = Depends(get_db)
):
    """
    REJECT TYPE: Marks all instances of this bucket type as ignored.
    """
    await triage_service.ignore_bucket(db, violation_id)
    return {"status": "success", "message": "Bucket type ignored."}