from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    StudentExamPreference,
    StudentOnboardingStatus,
    StudentUser,
)
from app.domains.student_auth.schemas.student_auth_schemas import (
    StudentOnboardingCompleteRequest,
)
from app.domains.student_auth.services.student_exam_preference_service import (
    student_exam_preference_service,
)
from app.domains.student_auth.services.student_phone_service import (
    student_phone_service,
)


class StudentOnboardingService:
    """
    Student onboarding mutation service.

    Design rules:
    - write-side logic must stay out of router
    - phone is normalized at API boundary
    - exam preferences use wipe-and-replace semantics
    - onboarding completion must be transactionally safe
    """

    async def complete_onboarding(
        self,
        *,
        db: AsyncSession,
        student: StudentUser,
        payload: StudentOnboardingCompleteRequest,
    ) -> StudentUser:
        result = await db.execute(
            select(StudentUser).where(StudentUser.id == student.id)
        )
        persistent_student = result.scalars().first()

        if not persistent_student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student account not found.",
            )

        if not payload.use_provider_avatar:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom profile image upload is not implemented yet. Submit use_provider_avatar=true for now.",
            )

        normalized_phone_e164, phone_country_code = (
            student_phone_service.normalize_indian_phone(
                raw_phone_number=payload.phone_number,
            )
        )

        validated_catalog_rows = (
            await student_exam_preference_service.validate_selected_catalog_ids(
                db=db,
                selected_ids=payload.exam_preference_catalog_ids,
                require_at_least_one=True,
            )
        )

        persistent_student.first_name = payload.first_name
        persistent_student.last_name = payload.last_name
        persistent_student.display_name = payload.display_name
        persistent_student.phone_number_e164 = normalized_phone_e164
        persistent_student.phone_country_code = phone_country_code
        persistent_student.phone_is_verified = False
        persistent_student.onboarding_status = StudentOnboardingStatus.COMPLETED
        persistent_student.onboarding_last_completed_step = None

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
            await db.refresh(persistent_student)
        except Exception as exc:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to finalize onboarding transaction.",
            ) from exc

        return persistent_student


student_onboarding_service = StudentOnboardingService()