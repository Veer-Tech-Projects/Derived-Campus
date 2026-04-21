from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StudentExternalIdentity, StudentUser
from app.domains.student_portal.student_account.schemas.student_account_schemas import (
    StudentAccountProfileUpdateRequest,
)


class StudentAccountProfileService:
    """
    Student account profile mutation service.

    Design rules:
    - account editing is isolated from onboarding completion semantics
    - schema boundary handles trimming and length validation
    - service handles domain mutation + persistence
    - no phone mutation, no exam preference mutation, no onboarding mutation
    """

    async def update_profile(
        self,
        *,
        db: AsyncSession,
        student: StudentUser,
        payload: StudentAccountProfileUpdateRequest,
    ) -> StudentUser:
        normalized_display_name = payload.display_name if payload.display_name else None

        student.first_name = payload.first_name
        student.last_name = payload.last_name
        student.display_name = normalized_display_name

        try:
            await db.commit()
            await db.refresh(student)
        except Exception as exc:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update student account profile.",
            ) from exc

        return student

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


student_account_profile_service = StudentAccountProfileService()