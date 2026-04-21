from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt

from app.domains.student_auth.config.student_auth_config import student_auth_settings


class StudentTokenService:
    """
    Student-auth-only token service.

    Design rules:
    - fully isolated from admin token service
    - access and refresh tokens are distinct
    - refresh tokens are never stored in plaintext in DB
    - DB stores only cryptographic fingerprint/hash
    """

    ACCESS_TOKEN_TYPE = "access"
    REFRESH_TOKEN_TYPE = "refresh"

    def create_access_token(
        self,
        *,
        student_user_id: UUID,
        session_id: UUID,
        onboarding_status: str,
        expires_delta: timedelta | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        expire_at = now + (
            expires_delta
            if expires_delta is not None
            else timedelta(minutes=student_auth_settings.STUDENT_ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        payload = {
            "sub": str(student_user_id),
            "sid": str(session_id),
            "type": self.ACCESS_TOKEN_TYPE,
            "onboarding_status": onboarding_status,
            "iat": int(now.timestamp()),
            "exp": int(expire_at.timestamp()),
        }

        return jwt.encode(
            payload,
            student_auth_settings.STUDENT_AUTH_SECRET_KEY,
            algorithm=student_auth_settings.STUDENT_AUTH_ALGORITHM,
        )

    def create_refresh_token(
        self,
        *,
        student_user_id: UUID,
        session_id: UUID,
        expires_delta: timedelta | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        expire_at = now + (
            expires_delta
            if expires_delta is not None
            else timedelta(days=student_auth_settings.STUDENT_REFRESH_TOKEN_EXPIRE_DAYS)
        )

        # High-entropy random secret embedded inside signed refresh JWT.
        jti = secrets.token_urlsafe(32)

        payload = {
            "sub": str(student_user_id),
            "sid": str(session_id),
            "jti": jti,
            "type": self.REFRESH_TOKEN_TYPE,
            "iat": int(now.timestamp()),
            "exp": int(expire_at.timestamp()),
        }

        return jwt.encode(
            payload,
            student_auth_settings.STUDENT_AUTH_SECRET_KEY,
            algorithm=student_auth_settings.STUDENT_AUTH_ALGORITHM,
        )

    def decode_token(
        self,
        *,
        token: str,
    ) -> dict[str, Any]:
        return jwt.decode(
            token,
            student_auth_settings.STUDENT_AUTH_SECRET_KEY,
            algorithms=[student_auth_settings.STUDENT_AUTH_ALGORITHM],
        )

    def decode_access_token(
        self,
        *,
        token: str,
    ) -> dict[str, Any]:
        payload = self.decode_token(token=token)
        if payload.get("type") != self.ACCESS_TOKEN_TYPE:
            raise JWTError("Invalid token type for access token")
        return payload

    def decode_refresh_token(
        self,
        *,
        token: str,
    ) -> dict[str, Any]:
        payload = self.decode_token(token=token)
        if payload.get("type") != self.REFRESH_TOKEN_TYPE:
            raise JWTError("Invalid token type for refresh token")
        return payload

    def fingerprint_refresh_token(
        self,
        *,
        refresh_token: str,
    ) -> str:
        """
        Store only a deterministic cryptographic fingerprint in DB.
        Never persist the plaintext refresh token.
        """
        return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()


student_token_service = StudentTokenService()