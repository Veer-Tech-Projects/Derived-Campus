from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import StudentAccountStatus, StudentUser
from app.domains.student_auth.services.student_token_service import (
    student_token_service,
)


student_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/student-auth/refresh",
    auto_error=False,
)


async def get_db():
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()


async def get_current_student(
    token: str | None = Depends(student_oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> StudentUser:
    """
    Student-auth-only dependency.

    Design rules:
    - fully isolated from admin auth dependency
    - accepts only valid student access tokens
    - loads platform-owned StudentUser
    - rejects inactive/suspended/disabled accounts
    """

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = student_token_service.decode_access_token(token=token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    student_user_id_raw = payload.get("sub")
    if not student_user_id_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token missing student identity.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        student_user_id = UUID(str(student_user_id_raw))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token contains invalid student identity.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    result = await db.execute(
        select(StudentUser).where(StudentUser.id == student_user_id)
    )
    student = result.scalars().first()

    if not student:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Student account not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if student.account_status != StudentAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student account is not active.",
        )

    return student