from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StudentExamPreferenceCatalog
from app.domains.student_auth.schemas.student_auth_schemas import (
    StudentExamPreferenceCatalogItemDTO,
    StudentExamPreferenceCatalogResponse,
)


class StudentExamPreferenceService:
    """
    Presentation-layer exam preference catalog service.

    Design rules:
    - onboarding exam options come only from student_exam_preference_catalog
    - do not depend on exam_configuration or exam_path_catalog
    - only active items are exposed to frontend
    - selections must be validated against active catalog entries
    """

    async def list_active_catalog(
        self,
        *,
        db: AsyncSession,
    ) -> StudentExamPreferenceCatalogResponse:
        result = await db.execute(
            select(StudentExamPreferenceCatalog)
            .where(StudentExamPreferenceCatalog.active.is_(True))
            .order_by(
                StudentExamPreferenceCatalog.display_order.asc(),
                StudentExamPreferenceCatalog.visible_label.asc(),
                StudentExamPreferenceCatalog.exam_key.asc(),
            )
        )
        rows = result.scalars().all()

        items = [
            StudentExamPreferenceCatalogItemDTO(
                id=row.id,
                exam_key=row.exam_key,
                visible_label=row.visible_label,
                description=row.description,
                active=bool(row.active),
                display_order=int(row.display_order),
            )
            for row in rows
        ]

        return StudentExamPreferenceCatalogResponse(
            items=items,
            generated_at=datetime.now(timezone.utc),
        )

    async def validate_selected_catalog_ids(
        self,
        *,
        db: AsyncSession,
        selected_ids: list[UUID],
        require_at_least_one: bool = True,
    ) -> list[StudentExamPreferenceCatalog]:
        """
        Validates submitted onboarding selections against active catalog rows.

        Returns the resolved active catalog rows in DB form for later persistence.
        """
        normalized_ids = self._normalize_uuid_list(selected_ids)

        if require_at_least_one and not normalized_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one exam preference must be selected.",
            )

        if not normalized_ids:
            return []

        result = await db.execute(
            select(StudentExamPreferenceCatalog).where(
                StudentExamPreferenceCatalog.id.in_(normalized_ids),
                StudentExamPreferenceCatalog.active.is_(True),
            )
        )
        rows = result.scalars().all()

        found_ids = {row.id for row in rows}
        missing_ids = [
            str(item_id)
            for item_id in normalized_ids
            if item_id not in found_ids
        ]

        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "One or more selected exam preferences are invalid or inactive.",
                    "invalid_exam_preference_catalog_ids": missing_ids,
                },
            )

        return rows

    @staticmethod
    def _normalize_uuid_list(values: list[UUID]) -> list[UUID]:
        """
        Deduplicates while preserving incoming order.
        """
        seen: set[UUID] = set()
        normalized: list[UUID] = []

        for value in values:
            if value in seen:
                continue
            seen.add(value)
            normalized.append(value)

        return normalized


student_exam_preference_service = StudentExamPreferenceService()