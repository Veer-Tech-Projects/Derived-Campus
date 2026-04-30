from __future__ import annotations

from datetime import datetime, timezone, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StudentSearchEntitlement
from app.domains.student_portal.student_billing.constants import (
    COLLEGE_FILTER_SEARCH_ENTITLEMENT_HOURS,
)


class CollegeFilterSearchEntitlementService:
    """
    DB-backed entitlement service for College Filter search reuse.

    Design rules:
    - same fingerprint for same student is reusable only within TTL
    - DB is source of truth for entitlement state
    - pagination/refresh/reopen should reuse the same entitlement
    - entitlement storage is separate from Redis snapshot cache
    """

    async def get_active_entitlement(
        self,
        *,
        db: AsyncSession,
        student_user_id: UUID,
        fingerprint: str,
    ) -> StudentSearchEntitlement | None:
        now = datetime.now(timezone.utc)

        result = await db.execute(
            select(StudentSearchEntitlement).where(
                StudentSearchEntitlement.student_user_id == student_user_id,
                StudentSearchEntitlement.search_fingerprint == fingerprint,
                StudentSearchEntitlement.entitlement_expires_at > now,
            )
        )
        return result.scalar_one_or_none()

    async def create_or_replace_entitlement(
        self,
        *,
        db: AsyncSession,
        student_user_id: UUID,
        path_id: UUID,
        fingerprint: str,
        request_snapshot_json: dict,
        consumption_ledger_id: UUID | None,
    ) -> StudentSearchEntitlement:
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=COLLEGE_FILTER_SEARCH_ENTITLEMENT_HOURS
        )

        stmt = (
            insert(StudentSearchEntitlement)
            .values(
                student_user_id=student_user_id,
                path_id=path_id,
                search_fingerprint=fingerprint,
                request_snapshot_json=request_snapshot_json,
                entitlement_expires_at=expires_at,
                last_accessed_at=datetime.now(timezone.utc),
                consumption_ledger_id=consumption_ledger_id,
            )
            .on_conflict_do_update(
                index_elements=["student_user_id", "search_fingerprint"],
                set_={
                    "path_id": path_id,
                    "request_snapshot_json": request_snapshot_json,
                    "entitlement_expires_at": expires_at,
                    "last_accessed_at": datetime.now(timezone.utc),
                    "consumption_ledger_id": consumption_ledger_id,
                },
            )
        )
        await db.execute(stmt)

        result = await db.execute(
            select(StudentSearchEntitlement).where(
                StudentSearchEntitlement.student_user_id == student_user_id,
                StudentSearchEntitlement.search_fingerprint == fingerprint,
            )
        )
        return result.scalar_one()

    async def mark_entitlement_accessed(
        self,
        *,
        db: AsyncSession,
        entitlement_id: UUID,
    ) -> None:
        result = await db.execute(
            select(StudentSearchEntitlement)
            .where(StudentSearchEntitlement.id == entitlement_id)
            .with_for_update()
        )
        entitlement = result.scalar_one_or_none()
        if entitlement is None:
            return

        entitlement.last_accessed_at = datetime.now(timezone.utc)
        await db.flush()


college_filter_search_entitlement_service = CollegeFilterSearchEntitlementService()