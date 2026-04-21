from __future__ import annotations

import phonenumbers
from fastapi import HTTPException, status

from app.domains.student_auth.config.student_auth_config import student_auth_settings


class StudentPhoneService:
    """
    India-only phone normalization service.

    Design rules:
    - validate at API boundary
    - canonicalize to E.164
    - do not persist raw uncontrolled formatting
    - v1 is India-only by product decision
    """

    def normalize_indian_phone(
        self,
        *,
        raw_phone_number: str,
    ) -> tuple[str, str]:
        cleaned = (raw_phone_number or "").strip()
        if not cleaned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is required.",
            )

        try:
            parsed = phonenumbers.parse(
                cleaned,
                student_auth_settings.STUDENT_PHONE_REGION,
            )
        except phonenumbers.NumberParseException as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid phone number format.",
            ) from exc

        if parsed.country_code != 91:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only Indian phone numbers are supported.",
            )

        if not phonenumbers.is_possible_number(parsed):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is not possible.",
            )

        if not phonenumbers.is_valid_number(parsed):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is not valid.",
            )

        e164 = phonenumbers.format_number(
            parsed,
            phonenumbers.PhoneNumberFormat.E164,
        )

        return e164, student_auth_settings.STUDENT_PHONE_COUNTRY_CODE


student_phone_service = StudentPhoneService()