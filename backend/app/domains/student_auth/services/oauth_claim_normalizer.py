from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.domains.student_auth.schemas.student_auth_schemas import (
    NormalizedOAuthClaimsDTO,
    StudentAuthProviderEnum,
)


class OAuthClaimNormalizer:
    """
    Provider-specific claim normalization into one platform-owned DTO.

    Design rules:
    - backend services must not depend on raw provider payload shape
    - normalization must be strict and explicit
    - missing optional claims remain nullable
    - provider user id is mandatory
    """

    def normalize_google_claims(
        self,
        *,
        id_token_claims: dict[str, Any] | None,
        userinfo_claims: dict[str, Any] | None = None,
    ) -> NormalizedOAuthClaimsDTO:
        merged: dict[str, Any] = {}
        if id_token_claims:
            merged.update(id_token_claims)
        if userinfo_claims:
            merged.update(userinfo_claims)

        provider_user_id = self._extract_google_subject(merged)
        given_name = self._optional_clean_string(merged.get("given_name"))
        family_name = self._optional_clean_string(merged.get("family_name"))
        name = self._optional_clean_string(merged.get("name"))
        email = self._optional_clean_string(merged.get("email"))
        picture = self._optional_clean_string(merged.get("picture"))
        email_verified_raw = merged.get("email_verified")

        return NormalizedOAuthClaimsDTO(
            provider=StudentAuthProviderEnum.GOOGLE,
            provider_user_id=provider_user_id,
            provider_email=email,
            provider_email_verified=self._normalize_optional_bool(email_verified_raw),
            first_name=given_name,
            last_name=family_name,
            display_name=name,
            avatar_url=picture,
            raw_claims=merged,
        )

    def normalize_facebook_claims(
        self,
        *,
        userinfo_claims: dict[str, Any] | None,
    ) -> NormalizedOAuthClaimsDTO:
        merged: dict[str, Any] = {}
        if userinfo_claims:
            merged.update(userinfo_claims)

        provider_user_id = self._extract_facebook_subject(merged)
        first_name = self._optional_clean_string(merged.get("first_name"))
        last_name = self._optional_clean_string(merged.get("last_name"))
        name = self._optional_clean_string(merged.get("name"))
        email = self._optional_clean_string(merged.get("email"))
        email_verified_raw = merged.get("is_verified")

        picture_url: str | None = None
        picture_payload = merged.get("picture")
        if isinstance(picture_payload, dict):
            data_payload = picture_payload.get("data")
            if isinstance(data_payload, dict):
                picture_url = self._optional_clean_string(data_payload.get("url"))

        return NormalizedOAuthClaimsDTO(
            provider=StudentAuthProviderEnum.FACEBOOK,
            provider_user_id=provider_user_id,
            provider_email=email,
            provider_email_verified=self._normalize_optional_bool(email_verified_raw),
            first_name=first_name,
            last_name=last_name,
            display_name=name,
            avatar_url=picture_url,
            raw_claims=merged,
        )

    def _extract_google_subject(
        self,
        claims: dict[str, Any],
    ) -> str:
        subject = self._optional_clean_string(claims.get("sub"))
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google identity response is missing subject claim.",
            )
        return subject


    def _extract_facebook_subject(
        self,
        claims: dict[str, Any],
    ) -> str:
        subject = self._optional_clean_string(claims.get("id"))
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Facebook identity response is missing user id.",
            )
        return subject


    @staticmethod
    def _optional_clean_string(value: Any) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned if cleaned else None

    @staticmethod
    def _normalize_optional_bool(value: Any) -> bool | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes"}:
                return True
            if normalized in {"false", "0", "no"}:
                return False
        if isinstance(value, int):
            if value == 1:
                return True
            if value == 0:
                return False
        return None


oauth_claim_normalizer = OAuthClaimNormalizer()