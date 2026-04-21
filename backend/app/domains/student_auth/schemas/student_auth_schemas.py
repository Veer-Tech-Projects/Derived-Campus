from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


# ============================================================
# ENUMS
# ============================================================

class StudentAuthProviderEnum(str, Enum):
    GOOGLE = "GOOGLE"
    APPLE = "APPLE"
    FACEBOOK = "FACEBOOK"
    X = "X"


class StudentAccountStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DISABLED = "DISABLED"


class StudentOnboardingStatusEnum(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"


class StudentSessionStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


# ============================================================
# PROVIDER / OAUTH DTOs
# ============================================================

class StudentAuthProviderDTO(BaseModel):
    provider: StudentAuthProviderEnum
    display_label: str
    enabled: bool

    model_config = ConfigDict(extra="forbid")


class NormalizedOAuthClaimsDTO(BaseModel):
    provider: StudentAuthProviderEnum
    provider_user_id: str = Field(..., min_length=1, max_length=255)

    provider_email: str | None = None
    provider_email_verified: bool | None = None
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    avatar_url: HttpUrl | None = None

    raw_claims: dict[str, Any]

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ============================================================
# EXAM PREFERENCE DTOs
# ============================================================

class StudentExamPreferenceCatalogItemDTO(BaseModel):
    id: UUID
    exam_key: str
    visible_label: str
    description: str | None = None
    active: bool
    display_order: int

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class StudentExamPreferenceCatalogResponse(BaseModel):
    items: list[StudentExamPreferenceCatalogItemDTO]
    generated_at: datetime

    model_config = ConfigDict(extra="forbid")


# ============================================================
# STUDENT PROFILE / SESSION DTOs
# ============================================================

class StudentProfileDTO(BaseModel):
    id: UUID
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None

    phone_number_e164: str | None = None
    phone_country_code: str
    phone_is_verified: bool

    account_status: StudentAccountStatusEnum
    onboarding_status: StudentOnboardingStatusEnum
    onboarding_last_completed_step: int | None = None

    profile_image_storage_key: str | None = None
    profile_image_url: str | None = None

    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class StudentSessionTokenResponse(BaseModel):
    access_token: str
    token_type: str

    model_config = ConfigDict(extra="forbid")


class StudentAuthMeResponse(BaseModel):
    authenticated: bool
    profile: StudentProfileDTO
    provider_links: list[StudentAuthProviderEnum]

    model_config = ConfigDict(extra="forbid")


class StudentLogoutResponse(BaseModel):
    success: bool
    message: str

    model_config = ConfigDict(extra="forbid")


# ============================================================
# ONBOARDING DTOs
# ============================================================

class StudentOnboardingBootstrapDTO(BaseModel):
    provider: StudentAuthProviderEnum
    provider_email: str | None = None
    provider_email_verified: bool | None = None

    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None

    provider_avatar_url: HttpUrl | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class StudentOnboardingStateResponse(BaseModel):
    onboarding_required: bool
    onboarding_status: StudentOnboardingStatusEnum
    last_completed_step: int | None = None

    profile: StudentProfileDTO
    bootstrap: StudentOnboardingBootstrapDTO
    available_exam_preferences: list[StudentExamPreferenceCatalogItemDTO]

    model_config = ConfigDict(extra="forbid")


class StudentOnboardingCompleteRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    display_name: str | None = Field(default=None, max_length=200)

    phone_number: str = Field(..., min_length=1, max_length=32)

    exam_preference_catalog_ids: list[UUID]

    use_provider_avatar: bool

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class StudentOnboardingCompleteResponse(BaseModel):
    success: bool
    onboarding_status: StudentOnboardingStatusEnum
    profile: StudentProfileDTO

    model_config = ConfigDict(extra="forbid")

    
# ============================================================
# AUDIT / INTERNAL HELPER DTOs
# ============================================================

class StudentAuthAuditEventDTO(BaseModel):
    student_user_id: UUID | None = None
    provider: StudentAuthProviderEnum | None = None
    event_type: str = Field(..., min_length=1, max_length=64)
    status: str = Field(..., min_length=1, max_length=32)
    details: dict[str, Any]
    ip_address: str | None = None
    user_agent: str | None = None

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    

class StudentPhoneValidationRequest(BaseModel):
    phone_number: str = Field(..., min_length=1, max_length=32)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class StudentPhoneValidationResponse(BaseModel):
    success: bool
    normalized_phone_e164: str
    phone_country_code: str

    model_config = ConfigDict(extra="forbid")