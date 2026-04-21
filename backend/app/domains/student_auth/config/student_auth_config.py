from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class StudentAuthSettings(BaseSettings):
    """
    Student-auth-only configuration.

    Design rules:
    - zero hardcoded runtime values
    - environment-driven only
    - fully isolated from admin auth config
    - no development fallback secrets or URLs inside code
    """

    # ---------------------------------------------------------
    # Core token settings
    # ---------------------------------------------------------
    STUDENT_AUTH_SECRET_KEY: str = Field(..., min_length=32)
    STUDENT_AUTH_ALGORITHM: str = Field(..., min_length=1)
    STUDENT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(..., ge=5, le=60)
    STUDENT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(..., ge=1, le=30)

    # ---------------------------------------------------------
    # Cookie settings
    # ---------------------------------------------------------
    STUDENT_REFRESH_COOKIE_NAME: str = Field(..., min_length=1)
    STUDENT_COOKIE_SECURE: bool = Field(...)
    STUDENT_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = Field(...)
    STUDENT_COOKIE_DOMAIN: str | None = Field(default=None)
    STUDENT_COOKIE_PATH: str = Field(..., min_length=1)

    STUDENT_OAUTH_STATE_COOKIE_NAME: str = Field(..., min_length=1)
    STUDENT_OAUTH_NONCE_COOKIE_NAME: str = Field(..., min_length=1)
    STUDENT_OAUTH_COOKIE_MAX_AGE_SECONDS: int = Field(..., ge=60, le=1800)

    # ---------------------------------------------------------
    # Frontend / redirect settings
    # ---------------------------------------------------------
    FRONTEND_BASE_URL: str = Field(..., min_length=1)
    STUDENT_LOGIN_PATH: str = Field(..., min_length=1)
    STUDENT_ONBOARDING_PATH: str = Field(..., min_length=1)
    STUDENT_POST_LOGIN_PATH: str = Field(..., min_length=1)

    # ---------------------------------------------------------
    # Google OAuth
    # ---------------------------------------------------------
    GOOGLE_OAUTH_ENABLED: bool = Field(...)
    GOOGLE_CLIENT_ID: str | None = Field(default=None)
    GOOGLE_CLIENT_SECRET: str | None = Field(default=None)
    GOOGLE_REDIRECT_URI: str | None = Field(default=None)
    GOOGLE_SCOPE: str = Field(..., min_length=1)

    GOOGLE_AUTHORIZATION_ENDPOINT: str = Field(..., min_length=1)
    GOOGLE_TOKEN_ENDPOINT: str = Field(..., min_length=1)
    GOOGLE_USERINFO_ENDPOINT: str = Field(..., min_length=1)
    GOOGLE_JWKS_URI: str = Field(..., min_length=1)
    GOOGLE_EXPECTED_ISSUERS: str = Field(..., min_length=1)

    # ---------------------------------------------------------
    # Facebook OAuth
    # ---------------------------------------------------------
    FACEBOOK_OAUTH_ENABLED: bool = Field(...)
    FACEBOOK_CLIENT_ID: str | None = Field(default=None)
    FACEBOOK_CLIENT_SECRET: str | None = Field(default=None)
    FACEBOOK_REDIRECT_URI: str | None = Field(default=None)
    FACEBOOK_SCOPE: str | None = Field(default=None)

    FACEBOOK_AUTHORIZATION_ENDPOINT: str | None = Field(default=None)
    FACEBOOK_TOKEN_ENDPOINT: str | None = Field(default=None)
    FACEBOOK_USERINFO_ENDPOINT: str | None = Field(default=None)

    # ---------------------------------------------------------
    # Platform business constraints
    # ---------------------------------------------------------
    STUDENT_PHONE_REGION: str = Field(..., min_length=2, max_length=2)
    STUDENT_PHONE_COUNTRY_CODE: str = Field(..., min_length=2, max_length=2)

    # ---------------------------------------------------------
    # Student profile image storage / delivery
    # ---------------------------------------------------------
    S3_ENDPOINT_URL: str = Field(..., min_length=1)
    S3_ACCESS_KEY: str = Field(..., min_length=1)
    S3_SECRET_KEY: str = Field(..., min_length=1)
    S3_BUCKET_NAME: str = Field(..., min_length=1)
    CDN_PUBLIC_BASE: str = Field(..., min_length=1)

    STUDENT_PROFILE_IMAGE_MAX_BYTES: int = Field(..., gt=0)
    STUDENT_PROFILE_IMAGE_ALLOWED_MIME_TYPES: str = Field(..., min_length=1)

    @field_validator(
        "STUDENT_COOKIE_DOMAIN",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GOOGLE_REDIRECT_URI",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, value):
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=True,
    )

    @property
    def google_provider_enabled(self) -> bool:
        return bool(
            self.GOOGLE_OAUTH_ENABLED
            and self.GOOGLE_CLIENT_ID
            and self.GOOGLE_CLIENT_SECRET
            and self.GOOGLE_REDIRECT_URI
            and self.GOOGLE_SCOPE
            and self.GOOGLE_AUTHORIZATION_ENDPOINT
            and self.GOOGLE_TOKEN_ENDPOINT
            and self.GOOGLE_USERINFO_ENDPOINT
            and self.GOOGLE_JWKS_URI
            and self.GOOGLE_EXPECTED_ISSUERS
        )

    @property
    def facebook_provider_enabled(self) -> bool:
        return bool(
            self.FACEBOOK_OAUTH_ENABLED
            and self.FACEBOOK_CLIENT_ID
            and self.FACEBOOK_CLIENT_SECRET
            and self.FACEBOOK_REDIRECT_URI
            and self.FACEBOOK_SCOPE
            and self.FACEBOOK_AUTHORIZATION_ENDPOINT
            and self.FACEBOOK_TOKEN_ENDPOINT
            and self.FACEBOOK_USERINFO_ENDPOINT
        )

    @property
    def student_login_url(self) -> str:
        return f"{self.FRONTEND_BASE_URL.rstrip('/')}{self.STUDENT_LOGIN_PATH}"

    @property
    def student_onboarding_url(self) -> str:
        return f"{self.FRONTEND_BASE_URL.rstrip('/')}{self.STUDENT_ONBOARDING_PATH}"

    @property
    def student_post_login_url(self) -> str:
        return f"{self.FRONTEND_BASE_URL.rstrip('/')}{self.STUDENT_POST_LOGIN_PATH}"

    @property
    def google_expected_issuer_values(self) -> list[str]:
        return [
            item.strip()
            for item in self.GOOGLE_EXPECTED_ISSUERS.split(",")
            if item.strip()
        ]

    @property
    def student_profile_image_allowed_mime_type_values(self) -> set[str]:
        return {
            item.strip().lower()
            for item in self.STUDENT_PROFILE_IMAGE_ALLOWED_MIME_TYPES.split(",")
            if item.strip()
        }

    @property
    def cdn_public_base_normalized(self) -> str:
        return self.CDN_PUBLIC_BASE.rstrip("/") + "/"


student_auth_settings = StudentAuthSettings()