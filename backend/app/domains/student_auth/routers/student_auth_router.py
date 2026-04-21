from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from app.models import StudentExternalIdentity, StudentOnboardingStatus, StudentUser
from app.domains.student_auth.config.student_auth_config import student_auth_settings
from app.domains.student_auth.dependencies.student_auth_dependency import (
    get_current_student,
    get_db,
)
from app.domains.student_auth.schemas.student_auth_schemas import (
    StudentAuthMeResponse,
    StudentAuthProviderDTO,
    StudentAuthProviderEnum,
    StudentLogoutResponse,
    StudentOnboardingBootstrapDTO,
    StudentOnboardingCompleteRequest,
    StudentOnboardingCompleteResponse,
    StudentOnboardingStateResponse,
    StudentProfileDTO,
    StudentSessionTokenResponse,
    StudentPhoneValidationRequest,
    StudentPhoneValidationResponse,
)
from app.domains.student_auth.services.oauth_claim_normalizer import (
    oauth_claim_normalizer,
)
from app.domains.student_auth.services.oauth_provider_registry import (
    oauth_provider_registry,
)
from app.domains.student_auth.services.student_auth_audit_service import (
    student_auth_audit_service,
)
from app.domains.student_auth.services.student_auth_service import (
    student_auth_service,
)
from app.domains.student_auth.services.student_session_service import (
    student_session_service,
)
from app.domains.student_auth.services.student_exam_preference_service import (
    student_exam_preference_service,
)
from app.domains.student_auth.services.student_onboarding_service import (
    student_onboarding_service,
)
from app.domains.student_auth.schemas.student_profile_image_schemas import (
    StudentProfileImageUploadResponse,
)
from app.domains.student_auth.services.student_profile_image_service import (
    student_profile_image_service,
)
from app.domains.student_auth.services.student_phone_service import (
    student_phone_service,
)

router = APIRouter(
    prefix="/student-auth",
    tags=["Student Auth"],
)


def _resolve_profile_image_url(
    *,
    student: StudentUser,
    provider_avatar_url: str | None,
) -> str | None:
    return student_profile_image_service.resolve_active_profile_image_url(
        student=student,
        provider_avatar_url=provider_avatar_url,
    )


def _build_student_profile_dto(
    *,
    student: StudentUser,
    provider_avatar_url: str | None,
) -> StudentProfileDTO:
    return StudentProfileDTO(
        id=student.id,
        first_name=student.first_name,
        last_name=student.last_name,
        display_name=student.display_name,
        phone_number_e164=student.phone_number_e164,
        phone_country_code=student.phone_country_code,
        phone_is_verified=student.phone_is_verified,
        account_status=student.account_status,
        onboarding_status=student.onboarding_status,
        onboarding_last_completed_step=student.onboarding_last_completed_step,
        profile_image_storage_key=student.profile_image_storage_key,
        profile_image_url=_resolve_profile_image_url(
            student=student,
            provider_avatar_url=provider_avatar_url,
        ),
        last_login_at=student.last_login_at,
        created_at=student.created_at,
        updated_at=student.updated_at,
    )


def _build_onboarding_bootstrap_dto(
    *,
    provider_row: StudentExternalIdentity | None,
    student: StudentUser,
) -> StudentOnboardingBootstrapDTO:
    if provider_row is None:
        return StudentOnboardingBootstrapDTO(
            provider=StudentAuthProviderEnum.GOOGLE,
            provider_email=None,
            provider_email_verified=None,
            first_name=student.first_name,
            last_name=student.last_name,
            display_name=student.display_name,
            provider_avatar_url=None,
        )

    return StudentOnboardingBootstrapDTO(
        provider=provider_row.provider,
        provider_email=provider_row.provider_email,
        provider_email_verified=provider_row.provider_email_verified,
        first_name=student.first_name or None,
        last_name=student.last_name or None,
        display_name=student.display_name or None,
        provider_avatar_url=provider_row.provider_avatar_url,
    )


def _set_refresh_cookie(
    *,
    response: Response,
    refresh_token: str,
) -> None:
    response.set_cookie(
        key=student_auth_settings.STUDENT_REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=student_auth_settings.STUDENT_COOKIE_SECURE,
        samesite=student_auth_settings.STUDENT_COOKIE_SAMESITE,
        domain=student_auth_settings.STUDENT_COOKIE_DOMAIN,
        path=student_auth_settings.STUDENT_COOKIE_PATH,
        max_age=student_auth_settings.STUDENT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )


def _clear_refresh_cookie(
    *,
    response: Response,
) -> None:
    response.delete_cookie(
        key=student_auth_settings.STUDENT_REFRESH_COOKIE_NAME,
        domain=student_auth_settings.STUDENT_COOKIE_DOMAIN,
        path=student_auth_settings.STUDENT_COOKIE_PATH,
    )


def _set_oauth_start_cookies(
    *,
    response: Response,
    state: str,
    nonce: str,
) -> None:
    response.set_cookie(
        key=student_auth_settings.STUDENT_OAUTH_STATE_COOKIE_NAME,
        value=state,
        httponly=True,
        secure=student_auth_settings.STUDENT_COOKIE_SECURE,
        samesite=student_auth_settings.STUDENT_COOKIE_SAMESITE,
        domain=student_auth_settings.STUDENT_COOKIE_DOMAIN,
        path=student_auth_settings.STUDENT_COOKIE_PATH,
        max_age=student_auth_settings.STUDENT_OAUTH_COOKIE_MAX_AGE_SECONDS,
    )
    response.set_cookie(
        key=student_auth_settings.STUDENT_OAUTH_NONCE_COOKIE_NAME,
        value=nonce,
        httponly=True,
        secure=student_auth_settings.STUDENT_COOKIE_SECURE,
        samesite=student_auth_settings.STUDENT_COOKIE_SAMESITE,
        domain=student_auth_settings.STUDENT_COOKIE_DOMAIN,
        path=student_auth_settings.STUDENT_COOKIE_PATH,
        max_age=student_auth_settings.STUDENT_OAUTH_COOKIE_MAX_AGE_SECONDS,
    )


def _clear_oauth_start_cookies(
    *,
    response: Response,
) -> None:
    response.delete_cookie(
        key=student_auth_settings.STUDENT_OAUTH_STATE_COOKIE_NAME,
        domain=student_auth_settings.STUDENT_COOKIE_DOMAIN,
        path=student_auth_settings.STUDENT_COOKIE_PATH,
    )
    response.delete_cookie(
        key=student_auth_settings.STUDENT_OAUTH_NONCE_COOKIE_NAME,
        domain=student_auth_settings.STUDENT_COOKIE_DOMAIN,
        path=student_auth_settings.STUDENT_COOKIE_PATH,
    )


@router.get("/providers", response_model=list[StudentAuthProviderDTO])
def list_student_auth_providers():
    return oauth_provider_registry.list_provider_dtos()


@router.get("/oauth/start/google")
def start_google_oauth():
    provider = oauth_provider_registry.get_provider(
        provider=StudentAuthProviderEnum.GOOGLE,
    )

    if not provider.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google login is not enabled.",
        )

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)

    authorization_url = provider.build_authorization_url(
        state=state,
        nonce=nonce,
    )

    response = RedirectResponse(
        url=authorization_url,
        status_code=status.HTTP_302_FOUND,
    )

    _set_oauth_start_cookies(
        response=response,
        state=state,
        nonce=nonce,
    )

    return response


@router.get("/oauth/start/facebook")
def start_facebook_oauth():
    provider = oauth_provider_registry.get_provider(
        provider=StudentAuthProviderEnum.FACEBOOK,
    )

    if not provider.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Facebook login is not enabled.",
        )

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)

    authorization_url = provider.build_authorization_url(
        state=state,
        nonce=nonce,
    )

    response = RedirectResponse(
        url=authorization_url,
        status_code=status.HTTP_302_FOUND,
    )

    _set_oauth_start_cookies(
        response=response,
        state=state,
        nonce=nonce,
    )

    return response


@router.get("/oauth/callback/google")
async def google_oauth_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    provider = oauth_provider_registry.get_provider(
        provider=StudentAuthProviderEnum.GOOGLE,
    )

    error = request.query_params.get("error")
    code = request.query_params.get("code")
    returned_state = request.query_params.get("state")

    cookie_state = request.cookies.get(student_auth_settings.STUDENT_OAUTH_STATE_COOKIE_NAME)
    cookie_nonce = request.cookies.get(student_auth_settings.STUDENT_OAUTH_NONCE_COOKIE_NAME)

    if error:
        await student_auth_audit_service.log_login_failure(
            db=db,
            provider=StudentAuthProviderEnum.GOOGLE,
            reason="GOOGLE_CALLBACK_ERROR",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            details={"provider_error": error},
        )
        await db.commit()

        response = RedirectResponse(
            url=student_auth_settings.student_login_url,
            status_code=status.HTTP_302_FOUND,
        )
        _clear_oauth_start_cookies(response=response)
        return response

    if not code or not returned_state or not cookie_state or returned_state != cookie_state:
        await student_auth_audit_service.log_login_failure(
            db=db,
            provider=StudentAuthProviderEnum.GOOGLE,
            reason="INVALID_OAUTH_STATE",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        await db.commit()

        response = RedirectResponse(
            url=student_auth_settings.student_login_url,
            status_code=status.HTTP_302_FOUND,
        )
        _clear_oauth_start_cookies(response=response)
        return response

    if not cookie_nonce:
        await student_auth_audit_service.log_login_failure(
            db=db,
            provider=StudentAuthProviderEnum.GOOGLE,
            reason="MISSING_OAUTH_NONCE",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        await db.commit()

        response = RedirectResponse(
            url=student_auth_settings.student_login_url,
            status_code=status.HTTP_302_FOUND,
        )
        _clear_oauth_start_cookies(response=response)
        return response

    try:
        token_payload = await provider.exchange_code_for_tokens(code=code)

        access_token = token_payload.get("access_token")
        id_token = token_payload.get("id_token")

        if not access_token or not id_token:
            await student_auth_audit_service.log_login_failure(
                db=db,
                provider=StudentAuthProviderEnum.GOOGLE,
                reason="GOOGLE_TOKEN_RESPONSE_INCOMPLETE",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            await db.commit()

            response = RedirectResponse(
                url=student_auth_settings.student_login_url,
                status_code=status.HTTP_302_FOUND,
            )
            _clear_oauth_start_cookies(response=response)
            return response

        id_token_claims = await provider.decode_and_validate_id_token(
            id_token=id_token,
            expected_nonce=cookie_nonce,
        )
        userinfo_claims = await provider.fetch_userinfo(
            access_token=access_token,
        )

        normalized_claims = oauth_claim_normalizer.normalize_google_claims(
            id_token_claims=id_token_claims,
            userinfo_claims=userinfo_claims,
        )

        student_user = await student_auth_service.resolve_or_create_student_from_oauth_claims(
            db=db,
            claims=normalized_claims,
        )

        _session, _new_access_token, refresh_token = await student_session_service.create_authenticated_session(
            db=db,
            student_user=student_user,
            provider=StudentAuthProviderEnum.GOOGLE,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

    except HTTPException as exc:
        await student_auth_audit_service.log_login_failure(
            db=db,
            provider=StudentAuthProviderEnum.GOOGLE,
            reason="GOOGLE_CALLBACK_PROCESSING_FAILED",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            details={"error_detail": exc.detail},
        )
        await db.commit()

        response = RedirectResponse(
            url=student_auth_settings.student_login_url,
            status_code=status.HTTP_302_FOUND,
        )
        _clear_oauth_start_cookies(response=response)
        return response

    redirect_url = (
        student_auth_settings.student_onboarding_url
        if student_user.onboarding_status == StudentOnboardingStatus.PENDING
        else student_auth_settings.student_post_login_url
    )

    response = RedirectResponse(
        url=redirect_url,
        status_code=status.HTTP_302_FOUND,
    )
    _set_refresh_cookie(
        response=response,
        refresh_token=refresh_token,
    )
    _clear_oauth_start_cookies(response=response)

    return response


@router.get("/oauth/callback/facebook")
async def facebook_oauth_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    provider = oauth_provider_registry.get_provider(
        provider=StudentAuthProviderEnum.FACEBOOK,
    )

    error = request.query_params.get("error")
    code = request.query_params.get("code")
    returned_state = request.query_params.get("state")

    cookie_state = request.cookies.get(student_auth_settings.STUDENT_OAUTH_STATE_COOKIE_NAME)
    cookie_nonce = request.cookies.get(student_auth_settings.STUDENT_OAUTH_NONCE_COOKIE_NAME)

    if error:
        await student_auth_audit_service.log_login_failure(
            db=db,
            provider=StudentAuthProviderEnum.FACEBOOK,
            reason="FACEBOOK_CALLBACK_ERROR",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            details={"provider_error": error},
        )
        await db.commit()

        response = RedirectResponse(
            url=student_auth_settings.student_login_url,
            status_code=status.HTTP_302_FOUND,
        )
        _clear_oauth_start_cookies(response=response)
        return response

    if not code or not returned_state or not cookie_state or returned_state != cookie_state:
        await student_auth_audit_service.log_login_failure(
            db=db,
            provider=StudentAuthProviderEnum.FACEBOOK,
            reason="INVALID_OAUTH_STATE",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        await db.commit()

        response = RedirectResponse(
            url=student_auth_settings.student_login_url,
            status_code=status.HTTP_302_FOUND,
        )
        _clear_oauth_start_cookies(response=response)
        return response

    if not cookie_nonce:
        await student_auth_audit_service.log_login_failure(
            db=db,
            provider=StudentAuthProviderEnum.FACEBOOK,
            reason="MISSING_OAUTH_NONCE",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        await db.commit()

        response = RedirectResponse(
            url=student_auth_settings.student_login_url,
            status_code=status.HTTP_302_FOUND,
        )
        _clear_oauth_start_cookies(response=response)
        return response

    try:
        token_payload = await provider.exchange_code_for_tokens(code=code)

        access_token = token_payload.get("access_token")

        if not access_token:
            await student_auth_audit_service.log_login_failure(
                db=db,
                provider=StudentAuthProviderEnum.FACEBOOK,
                reason="FACEBOOK_TOKEN_RESPONSE_INCOMPLETE",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )
            await db.commit()

            response = RedirectResponse(
                url=student_auth_settings.student_login_url,
                status_code=status.HTTP_302_FOUND,
            )
            _clear_oauth_start_cookies(response=response)
            return response

        userinfo_claims = await provider.fetch_userinfo(
            access_token=access_token,
        )

        normalized_claims = oauth_claim_normalizer.normalize_facebook_claims(
            userinfo_claims=userinfo_claims,
        )

        student_user = await student_auth_service.resolve_or_create_student_from_oauth_claims(
            db=db,
            claims=normalized_claims,
        )

        _session, _new_access_token, refresh_token = await student_session_service.create_authenticated_session(
            db=db,
            student_user=student_user,
            provider=StudentAuthProviderEnum.FACEBOOK,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

    except HTTPException as exc:
        await student_auth_audit_service.log_login_failure(
            db=db,
            provider=StudentAuthProviderEnum.FACEBOOK,
            reason="FACEBOOK_CALLBACK_PROCESSING_FAILED",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            details={"error_detail": exc.detail},
        )
        await db.commit()

        response = RedirectResponse(
            url=student_auth_settings.student_login_url,
            status_code=status.HTTP_302_FOUND,
        )
        _clear_oauth_start_cookies(response=response)
        return response

    redirect_url = (
        student_auth_settings.student_onboarding_url
        if student_user.onboarding_status == StudentOnboardingStatus.PENDING
        else student_auth_settings.student_post_login_url
    )

    response = RedirectResponse(
        url=redirect_url,
        status_code=status.HTTP_302_FOUND,
    )
    _set_refresh_cookie(
        response=response,
        refresh_token=refresh_token,
    )
    _clear_oauth_start_cookies(response=response)

    return response


@router.get("/me", response_model=StudentAuthMeResponse)
async def get_student_auth_me(
    current_student: StudentUser = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(StudentExternalIdentity).where(
            StudentExternalIdentity.student_user_id == current_student.id
        )
    )
    provider_rows = result.scalars().all()

    provider_links: list[StudentAuthProviderEnum] = []
    provider_avatar_url: str | None = None

    for row in provider_rows:
        provider_links.append(StudentAuthProviderEnum(row.provider.value))
        if provider_avatar_url is None and row.provider_avatar_url:
            provider_avatar_url = row.provider_avatar_url

    return StudentAuthMeResponse(
        authenticated=True,
        profile=_build_student_profile_dto(
            student=current_student,
            provider_avatar_url=provider_avatar_url,
        ),
        provider_links=provider_links,
    )


@router.get("/onboarding-state", response_model=StudentOnboardingStateResponse)
async def get_student_onboarding_state(
    current_student: StudentUser = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(StudentExternalIdentity).where(
            StudentExternalIdentity.student_user_id == current_student.id
        )
    )
    provider_rows = result.scalars().all()

    primary_provider_row: StudentExternalIdentity | None = provider_rows[0] if provider_rows else None

    provider_avatar_url: str | None = None
    if primary_provider_row and primary_provider_row.provider_avatar_url:
        provider_avatar_url = primary_provider_row.provider_avatar_url

    exam_catalog_response = await student_exam_preference_service.list_active_catalog(db=db)

    return StudentOnboardingStateResponse(
        onboarding_required=current_student.onboarding_status == StudentOnboardingStatus.PENDING,
        onboarding_status=current_student.onboarding_status,
        last_completed_step=current_student.onboarding_last_completed_step,
        profile=_build_student_profile_dto(
            student=current_student,
            provider_avatar_url=provider_avatar_url,
        ),
        bootstrap=_build_onboarding_bootstrap_dto(
            provider_row=primary_provider_row,
            student=current_student,
        ),
        available_exam_preferences=exam_catalog_response.items,
    )


@router.post("/profile-image", response_model=StudentProfileImageUploadResponse)
async def upload_student_profile_image(
    file: UploadFile = File(...),
    current_student: StudentUser = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    storage_key, profile_image_url = await student_profile_image_service.upload_profile_image(
        db=db,
        student=current_student,
        upload_file=file,
    )

    return StudentProfileImageUploadResponse(
        success=True,
        profile_image_storage_key=storage_key,
        profile_image_url=profile_image_url,
    )


@router.post(
    "/onboarding/validate-phone",
    response_model=StudentPhoneValidationResponse,
)
def validate_student_phone_for_onboarding(
    payload: StudentPhoneValidationRequest,
    current_student: StudentUser = Depends(get_current_student),
):
    normalized_phone_e164, phone_country_code = (
        student_phone_service.normalize_indian_phone(
            raw_phone_number=payload.phone_number,
        )
    )

    return StudentPhoneValidationResponse(
        success=True,
        normalized_phone_e164=normalized_phone_e164,
        phone_country_code=phone_country_code,
    )


@router.post("/onboarding/complete", response_model=StudentOnboardingCompleteResponse)
async def complete_student_onboarding(
    payload: StudentOnboardingCompleteRequest,
    current_student: StudentUser = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    updated_student = await student_onboarding_service.complete_onboarding(
        db=db,
        student=current_student,
        payload=payload,
    )

    result = await db.execute(
        select(StudentExternalIdentity).where(
            StudentExternalIdentity.student_user_id == updated_student.id
        )
    )
    provider_rows = result.scalars().all()

    provider_avatar_url: str | None = None
    if provider_rows:
        primary_provider_row = provider_rows[0]
        if primary_provider_row.provider_avatar_url:
            provider_avatar_url = primary_provider_row.provider_avatar_url

    return StudentOnboardingCompleteResponse(
        success=True,
        onboarding_status=updated_student.onboarding_status,
        profile=_build_student_profile_dto(
            student=updated_student,
            provider_avatar_url=provider_avatar_url,
        ),
    )


@router.post("/refresh", response_model=StudentSessionTokenResponse)
async def refresh_student_session(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    refresh_token = request.cookies.get(student_auth_settings.STUDENT_REFRESH_COOKIE_NAME)
    if not refresh_token:
        await student_auth_audit_service.log_refresh_failure(
            db=db,
            reason="MISSING_REFRESH_COOKIE",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token cookie is missing.",
        )

    session, student_user, _payload = await student_session_service.validate_refresh_token_and_get_session(
        db=db,
        refresh_token=refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    access_token, new_refresh_token = await student_session_service.rotate_refresh_session(
        db=db,
        session=session,
        student_user=student_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    _set_refresh_cookie(
        response=response,
        refresh_token=new_refresh_token,
    )

    return StudentSessionTokenResponse(
        access_token=access_token,
        token_type="bearer",
    )


@router.post("/logout", response_model=StudentLogoutResponse)
async def logout_student(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    refresh_token = request.cookies.get(student_auth_settings.STUDENT_REFRESH_COOKIE_NAME)
    if not refresh_token:
        _clear_refresh_cookie(response=response)
        return StudentLogoutResponse(
            success=True,
            message="Logged out successfully.",
        )

    try:
        session, student_user, _payload = await student_session_service.validate_refresh_token_and_get_session(
            db=db,
            refresh_token=refresh_token,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except HTTPException:
        _clear_refresh_cookie(response=response)
        return StudentLogoutResponse(
            success=True,
            message="Logged out successfully.",
        )
    except JWTError:
        _clear_refresh_cookie(response=response)
        return StudentLogoutResponse(
            success=True,
            message="Logged out successfully.",
        )

    await student_session_service.revoke_session(
        db=db,
        session=session,
        student_user_id=student_user.id,
        reason="USER_LOGOUT",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    _clear_refresh_cookie(response=response)

    return StudentLogoutResponse(
        success=True,
        message="Logged out successfully.",
    )