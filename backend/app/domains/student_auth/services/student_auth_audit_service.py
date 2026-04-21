from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StudentAuthAuditLog
from app.domains.student_auth.schemas.student_auth_schemas import (
    StudentAuthAuditEventDTO,
    StudentAuthProviderEnum,
)


class StudentAuthAuditService:
    """
    Centralized audit writer for student authentication events.

    Design rules:
    - services should not handcraft raw audit DB writes repeatedly
    - auth/session/provider failures must be auditable
    - this service must remain student-auth isolated
    """

    async def write_event(
        self,
        *,
        db: AsyncSession,
        event: StudentAuthAuditEventDTO,
        commit: bool = False,
    ) -> StudentAuthAuditLog:
        row = StudentAuthAuditLog(
            student_user_id=event.student_user_id,
            provider=event.provider.value if event.provider is not None else None,
            event_type=event.event_type,
            status=event.status,
            details=event.details,
            ip_address=event.ip_address,
            user_agent=event.user_agent,
        )
        db.add(row)

        if commit:
            await db.commit()
            await db.refresh(row)

        return row

    async def log_login_success(
        self,
        *,
        db: AsyncSession,
        student_user_id: UUID,
        provider: StudentAuthProviderEnum,
        session_id: UUID | None,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        await self.write_event(
            db=db,
            event=StudentAuthAuditEventDTO(
                student_user_id=student_user_id,
                provider=provider,
                event_type="LOGIN_SUCCESS",
                status="SUCCESS",
                details={"session_id": str(session_id) if session_id else None},
                ip_address=ip_address,
                user_agent=user_agent,
            ),
        )

    async def log_login_failure(
        self,
        *,
        db: AsyncSession,
        provider: StudentAuthProviderEnum | None,
        reason: str,
        ip_address: str | None,
        user_agent: str | None,
        details: dict[str, Any] | None = None,
    ) -> None:
        payload = {"reason": reason}
        if details:
            payload.update(details)

        await self.write_event(
            db=db,
            event=StudentAuthAuditEventDTO(
                student_user_id=None,
                provider=provider,
                event_type="LOGIN_FAILURE",
                status="FAILED",
                details=payload,
                ip_address=ip_address,
                user_agent=user_agent,
            ),
        )

    async def log_refresh_success(
        self,
        *,
        db: AsyncSession,
        student_user_id: UUID,
        session_id: UUID,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        await self.write_event(
            db=db,
            event=StudentAuthAuditEventDTO(
                student_user_id=student_user_id,
                provider=None,
                event_type="REFRESH_SUCCESS",
                status="SUCCESS",
                details={"session_id": str(session_id)},
                ip_address=ip_address,
                user_agent=user_agent,
            ),
        )

    async def log_refresh_failure(
        self,
        *,
        db: AsyncSession,
        reason: str,
        ip_address: str | None,
        user_agent: str | None,
        details: dict[str, Any] | None = None,
    ) -> None:
        payload = {"reason": reason}
        if details:
            payload.update(details)

        await self.write_event(
            db=db,
            event=StudentAuthAuditEventDTO(
                student_user_id=None,
                provider=None,
                event_type="REFRESH_FAILURE",
                status="FAILED",
                details=payload,
                ip_address=ip_address,
                user_agent=user_agent,
            ),
        )

    async def log_logout(
        self,
        *,
        db: AsyncSession,
        student_user_id: UUID,
        session_id: UUID | None,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        await self.write_event(
            db=db,
            event=StudentAuthAuditEventDTO(
                student_user_id=student_user_id,
                provider=None,
                event_type="LOGOUT",
                status="SUCCESS",
                details={"session_id": str(session_id) if session_id else None},
                ip_address=ip_address,
                user_agent=user_agent,
            ),
        )

    async def log_session_revoked(
        self,
        *,
        db: AsyncSession,
        student_user_id: UUID,
        session_id: UUID,
        reason: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        await self.write_event(
            db=db,
            event=StudentAuthAuditEventDTO(
                student_user_id=student_user_id,
                provider=None,
                event_type="SESSION_REVOKED",
                status="SUCCESS",
                details={"session_id": str(session_id), "reason": reason},
                ip_address=ip_address,
                user_agent=user_agent,
            ),
        )


student_auth_audit_service = StudentAuthAuditService()