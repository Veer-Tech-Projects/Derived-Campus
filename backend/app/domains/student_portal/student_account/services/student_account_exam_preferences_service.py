from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    StudentExamPreference,
    StudentExternalIdentity,
    StudentUser,
)
from app.domains.student_auth.services.student_exam_preference_service import (
    student_exam_preference_service,
)
from app.domains.student_portal.student_account.schemas.student_account_schemas import (
    StudentAccountExamPreferencesStateResponse,
)


class StudentAccountExamPreferencesService:
    """
    Student account exam preferences service.

    Design rules:
    - account editing is isolated from onboarding completion semantics
    - catalog source of truth remains student_exam_preference_catalog
    - updates use wipe-and-replace semantics
    - at least one exam preference must remain selected
    """

    async def get_exam_preferences_state(
        self,
        *,
        db: AsyncSession,
        student: StudentUser,
    ) -> StudentAccountExamPreferencesStateResponse:
        catalog_response = await student_exam_preference_service.list_active_catalog(db=db)

        result = await db.execute(
            select(StudentExamPreference).where(
                StudentExamPreference.student_user_id == student.id
            )
        )
        selected_rows = result.scalars().all()

        selected_ids = [row.exam_preference_catalog_id for row in selected_rows]

        return StudentAccountExamPreferencesStateResponse(
            available_exam_preferences=catalog_response.items,
            selected_exam_preference_catalog_ids=selected_ids,
        )

    async def update_exam_preferences(
        self,
        *,
        db: AsyncSession,
        student: StudentUser,
        selected_ids: list[UUID],
    ) -> list[UUID]:
        result = await db.execute(
            select(StudentUser).where(StudentUser.id == student.id)
        )
        persistent_student = result.scalars().first()

        if not persistent_student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student account not found.",
            )

        validated_catalog_rows = (
            await student_exam_preference_service.validate_selected_catalog_ids(
                db=db,
                selected_ids=selected_ids,
                require_at_least_one=True,
            )
        )

        await db.execute(
            delete(StudentExamPreference).where(
                StudentExamPreference.student_user_id == persistent_student.id
            )
        )

        for catalog_row in validated_catalog_rows:
            db.add(
                StudentExamPreference(
                    student_user_id=persistent_student.id,
                    exam_preference_catalog_id=catalog_row.id,
                )
            )

        try:
            await db.commit()
        except Exception as exc:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update student account exam preferences.",
            ) from exc

        return [row.id for row in validated_catalog_rows]

    async def resolve_provider_avatar_url(
        self,
        *,
        db: AsyncSession,
        student: StudentUser,
    ) -> str | None:
        result = await db.execute(
            select(StudentExternalIdentity)
            .where(StudentExternalIdentity.student_user_id == student.id)
            .order_by(StudentExternalIdentity.created_at.asc())
        )
        provider_row = result.scalars().first()

        if not provider_row:
            return None

        return provider_row.provider_avatar_url


student_account_exam_preferences_service = StudentAccountExamPreferencesService()