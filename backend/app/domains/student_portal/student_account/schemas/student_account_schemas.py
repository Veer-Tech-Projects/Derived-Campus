from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domains.student_auth.schemas.student_auth_schemas import (
    StudentExamPreferenceCatalogItemDTO,
    StudentProfileDTO,
)


class StudentAccountProfileUpdateRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    display_name: str | None = Field(default=None, max_length=200)

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class StudentAccountProfileUpdateResponse(BaseModel):
    success: bool
    profile: StudentProfileDTO

    model_config = ConfigDict(extra="forbid")


class StudentAccountPhoneUpdateRequest(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=10)

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class StudentAccountPhoneUpdateResponse(BaseModel):
    success: bool
    profile: StudentProfileDTO

    model_config = ConfigDict(extra="forbid")


class StudentAccountExamPreferencesStateResponse(BaseModel):
    available_exam_preferences: list[StudentExamPreferenceCatalogItemDTO]
    selected_exam_preference_catalog_ids: list[UUID]

    model_config = ConfigDict(extra="forbid")


class StudentAccountExamPreferencesUpdateRequest(BaseModel):
    exam_preference_catalog_ids: list[UUID]

    model_config = ConfigDict(extra="forbid")


class StudentAccountExamPreferencesUpdateResponse(BaseModel):
    success: bool
    selected_exam_preference_catalog_ids: list[UUID]

    model_config = ConfigDict(extra="forbid")