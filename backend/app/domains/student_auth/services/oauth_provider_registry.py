from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from authlib.jose import JsonWebKey, jwt as authlib_jwt
from fastapi import HTTPException, status

from app.domains.student_auth.config.student_auth_config import student_auth_settings
from app.domains.student_auth.schemas.student_auth_schemas import (
    StudentAuthProviderDTO,
    StudentAuthProviderEnum,
)


class OAuthProviderAdapter(Protocol):
    provider: StudentAuthProviderEnum
    display_label: str

    def is_enabled(self) -> bool: ...
    def build_authorization_url(self, *, state: str, nonce: str) -> str: ...
    async def exchange_code_for_tokens(self, *, code: str) -> dict[str, Any]: ...
    async def fetch_userinfo(self, *, access_token: str) -> dict[str, Any]: ...
    async def decode_and_validate_id_token(self, *, id_token: str, expected_nonce: str) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ProviderDefinition:
    provider: StudentAuthProviderEnum
    display_label: str
    enabled: bool


class GoogleOAuthProvider:
    provider = StudentAuthProviderEnum.GOOGLE
    display_label = "Google"

    def is_enabled(self) -> bool:
        return student_auth_settings.google_provider_enabled

    def build_authorization_url(
        self,
        *,
        state: str,
        nonce: str,
    ) -> str:
        if not self.is_enabled():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google login is not enabled.",
            )

        params = {
            "client_id": student_auth_settings.GOOGLE_CLIENT_ID,
            "redirect_uri": student_auth_settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": student_auth_settings.GOOGLE_SCOPE,
            "access_type": "offline",
            "include_granted_scopes": "true",
            "prompt": "consent",
            "state": state,
            "nonce": nonce,
        }

        return f"{student_auth_settings.GOOGLE_AUTHORIZATION_ENDPOINT}?{httpx.QueryParams(params)}"

    async def exchange_code_for_tokens(
        self,
        *,
        code: str,
    ) -> dict[str, Any]:
        if not self.is_enabled():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google login is not enabled.",
            )

        payload = {
            "code": code,
            "client_id": student_auth_settings.GOOGLE_CLIENT_ID,
            "client_secret": student_auth_settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": student_auth_settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    student_auth_settings.GOOGLE_TOKEN_ENDPOINT,
                    data=payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Google token exchange failed.",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Google token endpoint is unreachable.",
            ) from exc

    async def fetch_userinfo(
        self,
        *,
        access_token: str,
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    student_auth_settings.GOOGLE_USERINFO_ENDPOINT,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Google userinfo fetch failed.",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Google userinfo endpoint is unreachable.",
            ) from exc

    async def decode_and_validate_id_token(
        self,
        *,
        id_token: str,
        expected_nonce: str,
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(student_auth_settings.GOOGLE_JWKS_URI)
                response.raise_for_status()
                jwks = response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Google JWKS fetch failed.",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Google JWKS endpoint is unreachable.",
            ) from exc

        key_set = JsonWebKey.import_key_set(jwks)

        try:
            claims = authlib_jwt.decode(
                id_token,
                key_set,
                claims_options={
                    "iss": {
                        "essential": True,
                        "values": student_auth_settings.google_expected_issuer_values,
                    },
                    "aud": {
                        "essential": True,
                        "values": [student_auth_settings.GOOGLE_CLIENT_ID],
                    },
                    "nonce": {"essential": True, "value": expected_nonce},
                    "sub": {"essential": True},
                    "exp": {"essential": True},
                    "iat": {"essential": True},
                },
            )
            claims.validate(leeway=120)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Google ID token validation failed: {type(exc).__name__}: {str(exc)}",
            ) from exc

        return dict(claims)


class FacebookOAuthProvider:
    provider = StudentAuthProviderEnum.FACEBOOK
    display_label = "Facebook"

    def is_enabled(self) -> bool:
        return student_auth_settings.facebook_provider_enabled

    def build_authorization_url(
        self,
        *,
        state: str,
        nonce: str,
    ) -> str:
        if not self.is_enabled():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Facebook login is not enabled.",
            )

        params = {
            "client_id": student_auth_settings.FACEBOOK_CLIENT_ID,
            "redirect_uri": student_auth_settings.FACEBOOK_REDIRECT_URI,
            "response_type": "code",
            "scope": student_auth_settings.FACEBOOK_SCOPE,
            "state": state,
        }

        return f"{student_auth_settings.FACEBOOK_AUTHORIZATION_ENDPOINT}?{httpx.QueryParams(params)}"

    async def exchange_code_for_tokens(
        self,
        *,
        code: str,
    ) -> dict[str, Any]:
        if not self.is_enabled():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Facebook login is not enabled.",
            )

        payload = {
            "client_id": student_auth_settings.FACEBOOK_CLIENT_ID,
            "client_secret": student_auth_settings.FACEBOOK_CLIENT_SECRET,
            "redirect_uri": student_auth_settings.FACEBOOK_REDIRECT_URI,
            "code": code,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    student_auth_settings.FACEBOOK_TOKEN_ENDPOINT,
                    data=payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Facebook token exchange failed.",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Facebook token endpoint is unreachable.",
            ) from exc

    async def fetch_userinfo(
        self,
        *,
        access_token: str,
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    student_auth_settings.FACEBOOK_USERINFO_ENDPOINT,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Facebook userinfo fetch failed.",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Facebook userinfo endpoint is unreachable.",
            ) from exc

    async def decode_and_validate_id_token(
        self,
        *,
        id_token: str,
        expected_nonce: str,
    ) -> dict[str, Any]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Facebook ID token validation is not used in this auth flow.",
        )


class OAuthProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[StudentAuthProviderEnum, OAuthProviderAdapter] = {
            StudentAuthProviderEnum.GOOGLE: GoogleOAuthProvider(),
            StudentAuthProviderEnum.FACEBOOK: FacebookOAuthProvider(),
        }

    def get_provider(
        self,
        *,
        provider: StudentAuthProviderEnum,
    ) -> OAuthProviderAdapter:
        adapter = self._providers.get(provider)
        if adapter is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unsupported auth provider: {provider.value}",
            )
        return adapter

    def list_provider_definitions(self) -> list[ProviderDefinition]:
        return [
            ProviderDefinition(
                provider=StudentAuthProviderEnum.GOOGLE,
                display_label="Google",
                enabled=self._providers[StudentAuthProviderEnum.GOOGLE].is_enabled(),
            ),
            ProviderDefinition(
                provider=StudentAuthProviderEnum.APPLE,
                display_label="Apple",
                enabled=False,
            ),
            ProviderDefinition(
                provider=StudentAuthProviderEnum.FACEBOOK,
                display_label="Facebook",
                enabled=self._providers[StudentAuthProviderEnum.FACEBOOK].is_enabled(),
            ),
            ProviderDefinition(
                provider=StudentAuthProviderEnum.X,
                display_label="X",
                enabled=False,
            ),
        ]

    def list_provider_dtos(self) -> list[StudentAuthProviderDTO]:
        return [
            StudentAuthProviderDTO(
                provider=item.provider,
                display_label=item.display_label,
                enabled=item.enabled,
            )
            for item in self.list_provider_definitions()
        ]


oauth_provider_registry = OAuthProviderRegistry()