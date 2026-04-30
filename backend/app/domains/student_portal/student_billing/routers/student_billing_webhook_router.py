from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domains.student_portal.student_billing.exceptions import (
    InvalidWebhookSignatureError,
    PaymentOrderAmountMismatchError,
    PaymentOrderCurrencyMismatchError,
    PaymentOrderNotFoundError,
    StudentBillingError,
)
from app.domains.student_portal.student_billing.schemas.student_billing_schemas import (
    RazorpayWebhookAckResponse,
)
from app.domains.student_portal.student_billing.services.payment_webhook_service import (
    payment_webhook_service,
)
from app.domains.student_portal.student_billing.services.razorpay_gateway_service import (
    razorpay_gateway_service,
)

router = APIRouter(
    prefix="/student-billing/webhooks",
    tags=["Student Billing Webhooks"],
)


@router.post(
    "/razorpay",
    response_model=RazorpayWebhookAckResponse,
    status_code=status.HTTP_200_OK,
)
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None, alias="x-razorpay-signature"),
    db: AsyncSession = Depends(get_db),
) -> RazorpayWebhookAckResponse:
    raw_body = await request.body()

    try:
        razorpay_gateway_service.verify_webhook_signature(
            raw_body=raw_body,
            signature_header=x_razorpay_signature,
        )
    except InvalidWebhookSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook payload is not valid JSON.",
        ) from exc

    try:
        return await payment_webhook_service.process_verified_razorpay_webhook(
            db=db,
            payload=payload,
        )
    except PaymentOrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (PaymentOrderAmountMismatchError, PaymentOrderCurrencyMismatchError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except StudentBillingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc