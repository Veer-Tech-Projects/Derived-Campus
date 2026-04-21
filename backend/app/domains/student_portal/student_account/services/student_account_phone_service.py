from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StudentExternalIdentity, StudentUser
from app.domains.student_auth.services.student_phone_service import (
    student_phone_service,
)
from app.domains.student_portal.student_account.schemas.student_account_schemas import (
    StudentAccountPhoneUpdateRequest,
)


class StudentAccountPhoneService:
    """
    Student account phone mutation service.

    Design rules:
    - account editing is isolated from onboarding completion semantics
    - frontend sends exactly 10 India mobile digits
    - backend remains source of truth for normalization
    - phone_is_verified remains false until a real verification system exists
    """

    async def update_phone(
        self,
        *,
        db: AsyncSession,
        student: StudentUser,
        payload: StudentAccountPhoneUpdateRequest,
    ) -> StudentUser:
        raw_phone_number = payload.phone_number.strip()

        if not raw_phone_number.isdigit():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Phone number must contain only digits.",
            )

        if len(raw_phone_number) != 10:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Phone number must contain exactly 10 digits.",
            )

        normalized_phone_e164, phone_country_code = (
            student_phone_service.normalize_indian_phone(
                raw_phone_number=raw_phone_number,
            )
        )

        student.phone_number_e164 = normalized_phone_e164
        student.phone_country_code = phone_country_code
        student.phone_is_verified = False

        try:
            await db.commit()
            await db.refresh(student)
        except Exception as exc:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update student account phone number.",
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


student_account_phone_service = StudentAccountPhoneService()