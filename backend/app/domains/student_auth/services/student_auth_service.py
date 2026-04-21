from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    StudentExternalIdentity,
    StudentOnboardingStatus,
    StudentUser,
)
from app.domains.student_auth.schemas.student_auth_schemas import (
    NormalizedOAuthClaimsDTO,
)


class StudentAuthService:
    """
    Student auth identity orchestration service.

    Design rules:
    - provider identity is resolved only by (provider, provider_user_id)
    - no cross-provider linking
    - no email-based merging
    - callback replay must be idempotent and race-safe
    """

    async def resolve_or_create_student_from_oauth_claims(
        self,
        *,
        db: AsyncSession,
        claims: NormalizedOAuthClaimsDTO,
    ) -> StudentUser:
        existing_identity_result = await db.execute(
            select(StudentExternalIdentity).where(
                StudentExternalIdentity.provider == claims.provider.value,
                StudentExternalIdentity.provider_user_id == claims.provider_user_id,
            )
        )
        existing_identity = existing_identity_result.scalars().first()

        if existing_identity:
            student_result = await db.execute(
                select(StudentUser).where(
                    StudentUser.id == existing_identity.student_user_id
                )
            )
            student = student_result.scalars().first()

            if not student:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Linked student account not found.",
                )

            existing_identity.provider_email = claims.provider_email
            existing_identity.provider_email_verified = claims.provider_email_verified
            existing_identity.provider_avatar_url = (
                str(claims.avatar_url) if claims.avatar_url else None
            )
            existing_identity.raw_claims = claims.raw_claims

            await db.commit()
            await db.refresh(student)
            return student

        try:
            student = StudentUser(
                first_name=claims.first_name,
                last_name=claims.last_name,
                display_name=claims.display_name,
                onboarding_status=StudentOnboardingStatus.PENDING,
            )
            db.add(student)
            await db.flush()

            identity = StudentExternalIdentity(
                student_user_id=student.id,
                provider=claims.provider.value,
                provider_user_id=claims.provider_user_id,
                provider_email=claims.provider_email,
                provider_email_verified=claims.provider_email_verified,
                provider_avatar_url=str(claims.avatar_url) if claims.avatar_url else None,
                raw_claims=claims.raw_claims,
            )
            db.add(identity)

            await db.commit()
            await db.refresh(student)
            return student

        except IntegrityError:
            await db.rollback()

            race_identity_result = await db.execute(
                select(StudentExternalIdentity).where(
                    StudentExternalIdentity.provider == claims.provider.value,
                    StudentExternalIdentity.provider_user_id == claims.provider_user_id,
                )
            )
            race_identity = race_identity_result.scalars().first()

            if not race_identity:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to resolve student identity after callback race recovery.",
                )

            student_result = await db.execute(
                select(StudentUser).where(
                    StudentUser.id == race_identity.student_user_id
                )
            )
            student = student_result.scalars().first()

            if not student:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Recovered student identity has no matching student account.",
                )

            race_identity.provider_email = claims.provider_email
            race_identity.provider_email_verified = claims.provider_email_verified
            race_identity.provider_avatar_url = (
                str(claims.avatar_url) if claims.avatar_url else None
            )
            race_identity.raw_claims = claims.raw_claims

            await db.commit()
            await db.refresh(student)
            return student


student_auth_service = StudentAuthService()