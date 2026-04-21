from __future__ import annotations

import io

import boto3
from botocore.client import Config
from fastapi import HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from PIL import Image, ImageOps
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StudentUser
from app.domains.student_auth.config.student_auth_config import student_auth_settings


class StudentProfileImageService:
    """
    Student profile image storage service.

    Design rules:
    - fully isolated from college media pipeline business logic
    - only one uploaded image object per student
    - final stored format is always webp
    - provider avatar is never copied automatically
    - uploaded image becomes canonical once present

    Cache invalidation rule:
    - canonical object key remains stable
    - profile_image_version increments on every successful upload
    - returned public URL uses ?v=<profile_image_version>
    """

    CANONICAL_OBJECT_NAME = "avatar.webp"

    def __init__(self) -> None:
        self._s3_client = boto3.client(
            "s3",
            endpoint_url=student_auth_settings.S3_ENDPOINT_URL,
            aws_access_key_id=student_auth_settings.S3_ACCESS_KEY,
            aws_secret_access_key=student_auth_settings.S3_SECRET_KEY,
            config=Config(signature_version="s3v4"),
        )

    def build_storage_key(
        self,
        *,
        student_user_id: str,
    ) -> str:
        return f"users/{student_user_id}/profile/{self.CANONICAL_OBJECT_NAME}"

    def build_public_url(
        self,
        *,
        storage_key: str,
        cache_buster: str | None = None,
    ) -> str:
        base_url = f"{student_auth_settings.cdn_public_base_normalized}{storage_key}"
        if cache_buster:
            return f"{base_url}?v={cache_buster}"
        return base_url

    async def upload_profile_image(
        self,
        *,
        db: AsyncSession,
        student: StudentUser,
        upload_file: UploadFile,
    ) -> tuple[str, str]:
        if upload_file.content_type is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file content type is missing.",
            )

        normalized_content_type = upload_file.content_type.strip().lower()
        if (
            normalized_content_type
            not in student_auth_settings.student_profile_image_allowed_mime_type_values
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported profile image type. Allowed types: jpeg, png, webp.",
            )

        raw_bytes = await upload_file.read()
        if not raw_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded profile image is empty.",
            )

        if len(raw_bytes) > student_auth_settings.STUDENT_PROFILE_IMAGE_MAX_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profile image exceeds maximum allowed size of 5 MB.",
            )

        final_webp_bytes = await run_in_threadpool(
            self._normalize_to_webp,
            raw_bytes=raw_bytes,
        )

        storage_key = self.build_storage_key(student_user_id=str(student.id))

        try:
            await run_in_threadpool(
                self._put_object,
                storage_key=storage_key,
                body=final_webp_bytes,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to upload profile image to object storage.",
            ) from exc

        student.profile_image_storage_key = storage_key
        student.profile_image_version = (student.profile_image_version or 0) + 1

        try:
            await db.commit()
            await db.refresh(student)
        except Exception as exc:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to persist uploaded profile image metadata.",
            ) from exc

        return storage_key, self.build_public_url(
            storage_key=storage_key,
            cache_buster=str(student.profile_image_version),
        )

    def _put_object(
        self,
        *,
        storage_key: str,
        body: bytes,
    ) -> None:
        self._s3_client.put_object(
            Bucket=student_auth_settings.S3_BUCKET_NAME,
            Key=storage_key,
            Body=body,
            ContentType="image/webp",
            CacheControl="no-cache",
        )

    def resolve_active_profile_image_url(
        self,
        *,
        student: StudentUser,
        provider_avatar_url: str | None,
    ) -> str | None:
        if student.profile_image_storage_key:
            return self.build_public_url(
                storage_key=student.profile_image_storage_key,
                cache_buster=str(student.profile_image_version or 0),
            )

        if provider_avatar_url:
            return provider_avatar_url

        return None

    def _normalize_to_webp(
        self,
        *,
        raw_bytes: bytes,
    ) -> bytes:
        try:
            with Image.open(io.BytesIO(raw_bytes)) as image:
                normalized = ImageOps.exif_transpose(image)

                if normalized.mode not in ("RGB", "RGBA"):
                    normalized = normalized.convert("RGBA")

                if normalized.mode == "RGBA":
                    background = Image.new("RGBA", normalized.size, (255, 255, 255, 255))
                    background.alpha_composite(normalized)
                    normalized = background.convert("RGB")
                else:
                    normalized = normalized.convert("RGB")

                output = io.BytesIO()
                normalized.save(
                    output,
                    format="WEBP",
                    quality=90,
                    method=6,
                )
                return output.getvalue()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is not a valid supported image.",
            ) from exc


student_profile_image_service = StudentProfileImageService()