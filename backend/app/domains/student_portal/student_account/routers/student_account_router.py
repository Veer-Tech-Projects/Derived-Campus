from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StudentUser
from app.domains.student_auth.dependencies.student_auth_dependency import (
    get_current_student,
    get_db,
)
from app.domains.student_auth.schemas.student_auth_schemas import StudentProfileDTO
from app.domains.student_auth.services.student_profile_image_service import (
    student_profile_image_service,
)
from app.domains.student_portal.student_account.schemas.student_account_schemas import (
    StudentAccountExamPreferencesStateResponse,
    StudentAccountExamPreferencesUpdateRequest,
    StudentAccountExamPreferencesUpdateResponse,
    StudentAccountPhoneUpdateRequest,
    StudentAccountPhoneUpdateResponse,
    StudentAccountProfileUpdateRequest,
    StudentAccountProfileUpdateResponse,
)
from app.domains.student_portal.student_account.services.student_account_phone_service import (
    student_account_phone_service,
)
from app.domains.student_portal.student_account.services.student_account_profile_service import (
    student_account_profile_service,
)
from app.domains.student_portal.student_account.services.student_account_exam_preferences_service import (
    student_account_exam_preferences_service,
)

router = APIRouter(
    prefix="/student-account",
    tags=["Student Account"],
)


def _resolve_profile_image_url(
    *,
    student: StudentUser,
    provider_avatar_url: str | None,
) -> str | None:
    return student_profile_image_service.resolve_active_profile_image_url(
        student=student,
        provider_avatar_url=provider_avatar_url,
    )


def _build_student_profile_dto(
    *,
    student: StudentUser,
    provider_avatar_url: str | None,
) -> StudentProfileDTO:
    return StudentProfileDTO(
        id=student.id,
        first_name=student.first_name,
        last_name=student.last_name,
        display_name=student.display_name,
        phone_number_e164=student.phone_number_e164,
        phone_country_code=student.phone_country_code,
        phone_is_verified=student.phone_is_verified,
        account_status=student.account_status,
        onboarding_status=student.onboarding_status,
        onboarding_last_completed_step=student.onboarding_last_completed_step,
        profile_image_storage_key=student.profile_image_storage_key,
        profile_image_url=_resolve_profile_image_url(
            student=student,
            provider_avatar_url=provider_avatar_url,
        ),
        last_login_at=student.last_login_at,
        created_at=student.created_at,
        updated_at=student.updated_at,
    )


@router.patch(
    "/profile",
    response_model=StudentAccountProfileUpdateResponse,
)
async def update_student_account_profile(
    payload: StudentAccountProfileUpdateRequest,
    current_student: StudentUser = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    updated_student = await student_account_profile_service.update_profile(
        db=db,
        student=current_student,
        payload=payload,
    )

    provider_avatar_url = await student_account_profile_service.resolve_provider_avatar_url(
        db=db,
        student=updated_student,
    )

    return StudentAccountProfileUpdateResponse(
        success=True,
        profile=_build_student_profile_dto(
            student=updated_student,
            provider_avatar_url=provider_avatar_url,
        ),
    )


@router.patch(
    "/phone",
    response_model=StudentAccountPhoneUpdateResponse,
)
async def update_student_account_phone(
    payload: StudentAccountPhoneUpdateRequest,
    current_student: StudentUser = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    updated_student = await student_account_phone_service.update_phone(
        db=db,
        student=current_student,
        payload=payload,
    )

    provider_avatar_url = await student_account_phone_service.resolve_provider_avatar_url(
        db=db,
        student=updated_student,
    )

    return StudentAccountPhoneUpdateResponse(
        success=True,
        profile=_build_student_profile_dto(
            student=updated_student,
            provider_avatar_url=provider_avatar_url,
        ),
    )


@router.get(
    "/exam-preferences",
    response_model=StudentAccountExamPreferencesStateResponse,
)
async def get_student_account_exam_preferences(
    current_student: StudentUser = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    return await student_account_exam_preferences_service.get_exam_preferences_state(
        db=db,
        student=current_student,
    )


@router.patch(
    "/exam-preferences",
    response_model=StudentAccountExamPreferencesUpdateResponse,
)
async def update_student_account_exam_preferences(
    payload: StudentAccountExamPreferencesUpdateRequest,
    current_student: StudentUser = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    selected_ids = await student_account_exam_preferences_service.update_exam_preferences(
        db=db,
        student=current_student,
        selected_ids=payload.exam_preference_catalog_ids,
    )

    return StudentAccountExamPreferencesUpdateResponse(
        success=True,
        selected_exam_preference_catalog_ids=selected_ids,
    )