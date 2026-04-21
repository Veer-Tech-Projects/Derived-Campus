from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    StudentAuthSession,
    StudentSessionStatus,
    StudentUser,
)
from app.domains.student_auth.schemas.student_auth_schemas import StudentAuthProviderEnum
from app.domains.student_auth.services.student_auth_audit_service import (
    student_auth_audit_service,
)
from app.domains.student_auth.services.student_token_service import (
    student_token_service,
)
from app.domains.student_auth.config.student_auth_config import student_auth_settings


class StudentSessionService:
    """
    Student session lifecycle service.

    Design rules:
    - refresh token plaintext is never stored in DB
    - DB stores only fingerprint/hash
    - session lifecycle is DB-backed and revocable
    - audit events are written for major session actions
    """

    async def create_authenticated_session(
        self,
        *,
        db: AsyncSession,
        student_user: StudentUser,
        provider: StudentAuthProviderEnum,
        ip_address: str | None,
        user_agent: str | None,
    ) -> tuple[StudentAuthSession, str, str]:
        session = StudentAuthSession(
            student_user_id=student_user.id,
            refresh_token_fingerprint="PENDING_TOKEN_FINGERPRINT",
            status=StudentSessionStatus.ACTIVE,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=student_auth_settings.STUDENT_REFRESH_TOKEN_EXPIRE_DAYS),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(session)
        await db.flush()

        access_token = student_token_service.create_access_token(
            student_user_id=student_user.id,
            session_id=session.id,
            onboarding_status=student_user.onboarding_status.value,
        )

        refresh_token = student_token_service.create_refresh_token(
            student_user_id=student_user.id,
            session_id=session.id,
        )

        session.refresh_token_fingerprint = student_token_service.fingerprint_refresh_token(
            refresh_token=refresh_token
        )
        session.last_seen_at = datetime.now(timezone.utc)

        student_user.last_login_at = datetime.now(timezone.utc)

        await student_auth_audit_service.log_login_success(
            db=db,
            student_user_id=student_user.id,
            provider=provider,
            session_id=session.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await db.commit()
        await db.refresh(session)
        await db.refresh(student_user)

        return session, access_token, refresh_token

    async def validate_refresh_token_and_get_session(
        self,
        *,
        db: AsyncSession,
        refresh_token: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> tuple[StudentAuthSession, StudentUser, dict]:
        try:
            payload = student_token_service.decode_refresh_token(token=refresh_token)
        except JWTError as exc:
            await student_auth_audit_service.log_refresh_failure(
                db=db,
                reason="INVALID_REFRESH_TOKEN",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"error": str(exc)},
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
            ) from exc

        session_id_raw = payload.get("sid")
        student_user_id_raw = payload.get("sub")

        if not session_id_raw or not student_user_id_raw:
            await student_auth_audit_service.log_refresh_failure(
                db=db,
                reason="MALFORMED_REFRESH_TOKEN",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed refresh token.",
            )

        try:
            session_id = UUID(str(session_id_raw))
            student_user_id = UUID(str(student_user_id_raw))
        except ValueError as exc:
            await student_auth_audit_service.log_refresh_failure(
                db=db,
                reason="INVALID_REFRESH_TOKEN_UUIDS",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"error": str(exc)},
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token identifiers.",
            ) from exc

        session_result = await db.execute(
            select(StudentAuthSession).where(
                StudentAuthSession.id == session_id,
                StudentAuthSession.student_user_id == student_user_id,
            )
        )
        session = session_result.scalars().first()

        if not session:
            await student_auth_audit_service.log_refresh_failure(
                db=db,
                reason="SESSION_NOT_FOUND",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"session_id": str(session_id)},
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session not found.",
            )

        if session.status != StudentSessionStatus.ACTIVE:
            await student_auth_audit_service.log_refresh_failure(
                db=db,
                reason="SESSION_NOT_ACTIVE",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"session_id": str(session.id), "status": session.status.value},
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session is not active.",
            )

        if session.expires_at <= datetime.now(timezone.utc):
            session.status = StudentSessionStatus.EXPIRED
            await student_auth_audit_service.log_refresh_failure(
                db=db,
                reason="SESSION_EXPIRED",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"session_id": str(session.id)},
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired.",
            )

        presented_fingerprint = student_token_service.fingerprint_refresh_token(
            refresh_token=refresh_token
        )
        if presented_fingerprint != session.refresh_token_fingerprint:
            await student_auth_audit_service.log_refresh_failure(
                db=db,
                reason="REFRESH_TOKEN_FINGERPRINT_MISMATCH",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"session_id": str(session.id)},
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token mismatch.",
            )

        student_result = await db.execute(
            select(StudentUser).where(StudentUser.id == student_user_id)
        )
        student_user = student_result.scalars().first()

        if not student_user:
            await student_auth_audit_service.log_refresh_failure(
                db=db,
                reason="STUDENT_USER_NOT_FOUND",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"student_user_id": str(student_user_id)},
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Student account not found.",
            )

        return session, student_user, payload

    async def rotate_refresh_session(
        self,
        *,
        db: AsyncSession,
        session: StudentAuthSession,
        student_user: StudentUser,
        ip_address: str | None,
        user_agent: str | None,
    ) -> tuple[str, str]:
        access_token = student_token_service.create_access_token(
            student_user_id=student_user.id,
            session_id=session.id,
            onboarding_status=student_user.onboarding_status.value,
        )

        refresh_token = student_token_service.create_refresh_token(
            student_user_id=student_user.id,
            session_id=session.id,
        )

        session.refresh_token_fingerprint = student_token_service.fingerprint_refresh_token(
            refresh_token=refresh_token
        )
        session.last_seen_at = datetime.now(timezone.utc)
        session.expires_at = datetime.now(timezone.utc) + timedelta(
            days=student_auth_settings.STUDENT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        session.ip_address = ip_address
        session.user_agent = user_agent

        await student_auth_audit_service.log_refresh_success(
            db=db,
            student_user_id=student_user.id,
            session_id=session.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await db.commit()
        await db.refresh(session)

        return access_token, refresh_token

    async def revoke_session(
        self,
        *,
        db: AsyncSession,
        session: StudentAuthSession,
        student_user_id: UUID,
        reason: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        session.status = StudentSessionStatus.REVOKED
        session.revoked_at = datetime.now(timezone.utc)
        session.last_seen_at = datetime.now(timezone.utc)

        await student_auth_audit_service.log_session_revoked(
            db=db,
            student_user_id=student_user_id,
            session_id=session.id,
            reason=reason,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await db.commit()

    async def revoke_session_by_id(
        self,
        *,
        db: AsyncSession,
        session_id: UUID,
        student_user_id: UUID,
        reason: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        session_result = await db.execute(
            select(StudentAuthSession).where(
                StudentAuthSession.id == session_id,
                StudentAuthSession.student_user_id == student_user_id,
            )
        )
        session = session_result.scalars().first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found.",
            )

        await self.revoke_session(
            db=db,
            session=session,
            student_user_id=student_user_id,
            reason=reason,
            ip_address=ip_address,
            user_agent=user_agent,
        )


student_session_service = StudentSessionService()