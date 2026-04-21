from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StudentProfileImageUploadResponse(BaseModel):
    success: bool
    profile_image_storage_key: str
    profile_image_url: str

    model_config = ConfigDict(extra="forbid")