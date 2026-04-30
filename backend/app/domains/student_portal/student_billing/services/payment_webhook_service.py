from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    BillingGatewayProvider,
    PaymentOrder,
    PaymentOrderStatus,
    PaymentTransaction,
    PaymentTransactionStatus,
    PaymentWebhookEvent,
    PaymentWebhookProcessingStatus,
)
from app.domains.student_portal.student_billing.constants import (
    BILLING_CREATED_BY_WEBHOOK,
)
from app.domains.student_portal.student_billing.exceptions import (
    DuplicateLedgerGrantError,
    PaymentOrderAmountMismatchError,
    PaymentOrderCurrencyMismatchError,
    PaymentOrderNotFoundError,
    StudentBillingError,
)
from app.domains.student_portal.student_billing.schemas.student_billing_schemas import (
    RazorpayWebhookAckResponse,
)
from app.domains.student_portal.student_billing.services.credit_ledger_service import (
    credit_ledger_service,
)
from app.domains.student_portal.student_billing.services.razorpay_gateway_service import (
    razorpay_gateway_service,
)


class PaymentWebhookService:
    """
    Verified webhook settlement orchestration.

    Important:
    - this service assumes signature verification already happened in memory
    - verified webhook persistence happens before settlement processing
    - settlement is idempotent across repeated webhook deliveries
    """

    async def process_verified_razorpay_webhook(
        self,
        *,
        db: AsyncSession,
        payload: dict[str, Any],
    ) -> RazorpayWebhookAckResponse:
        event_type = razorpay_gateway_service.extract_event_type(payload)
        if not event_type:
            raise StudentBillingError("Webhook payload did not contain an event type.")

        dedup_key = razorpay_gateway_service.build_webhook_dedup_key(payload)
        gateway_event_id = razorpay_gateway_service.extract_gateway_event_id(payload)

        await self._persist_verified_webhook_event(
            db=db,
            payload=payload,
            dedup_key=dedup_key,
            gateway_event_id=gateway_event_id,
            event_type=event_type,
        )

        try:
            webhook_event = await self._lock_webhook_event_for_processing(
                db=db,
                dedup_key=dedup_key,
            )

            if webhook_event.processing_status == PaymentWebhookProcessingStatus.PROCESSED:
                return RazorpayWebhookAckResponse(
                    success=True,
                    message="Webhook already processed.",
                )

            webhook_event.processing_attempts = webhook_event.processing_attempts + 1
            webhook_event.last_error = None

            if not razorpay_gateway_service.is_order_paid_event(payload):
                webhook_event.processing_status = PaymentWebhookProcessingStatus.PROCESSED
                webhook_event.processed_at = datetime.now(timezone.utc)
                await db.commit()
                return RazorpayWebhookAckResponse(
                    success=True,
                    message="Verified webhook ignored because event is not order.paid.",
                )

            gateway_order_id = razorpay_gateway_service.extract_gateway_order_id(payload)
            gateway_payment_id = razorpay_gateway_service.extract_gateway_payment_id(payload)
            amount_minor = razorpay_gateway_service.extract_amount_minor(payload)
            currency_code = razorpay_gateway_service.extract_currency_code(payload)

            if not gateway_order_id:
                raise StudentBillingError(
                    "Verified webhook payload did not contain a gateway order id."
                )
            if not gateway_payment_id:
                raise StudentBillingError(
                    "Verified webhook payload did not contain a gateway payment id."
                )
            if amount_minor is None:
                raise StudentBillingError(
                    "Verified webhook payload did not contain a valid amount."
                )
            if not currency_code:
                raise StudentBillingError(
                    "Verified webhook payload did not contain a valid currency."
                )

            payment_order = await self._resolve_internal_order_by_gateway_order_id(
                db=db,
                gateway_order_id=gateway_order_id,
            )

            self._validate_settlement_payload_against_order(
                payment_order=payment_order,
                amount_minor=amount_minor,
                currency_code=currency_code,
            )

            payment_transaction = await self._upsert_payment_transaction(
                db=db,
                payment_order=payment_order,
                gateway_payment_id=gateway_payment_id,
                gateway_event_type=event_type,
                amount_minor=amount_minor,
                currency_code=currency_code,
                raw_gateway_payload=payload,
            )

            if payment_order.status == PaymentOrderStatus.SETTLED:
                payment_transaction.status = PaymentTransactionStatus.PROCESSED
                payment_transaction.processed_at = datetime.now(timezone.utc)
                webhook_event.processing_status = PaymentWebhookProcessingStatus.PROCESSED
                webhook_event.processed_at = datetime.now(timezone.utc)
                await db.commit()
                return RazorpayWebhookAckResponse(
                    success=True,
                    message="Webhook processed idempotently for already-settled order.",
                )

            grant_idempotency_key = self._build_payment_grant_idempotency_key(
                payment_order_id=str(payment_order.id),
                gateway_payment_id=gateway_payment_id,
            )

            try:
                await credit_ledger_service.grant_purchase_credits(
                    db=db,
                    student_user_id=payment_order.student_user_id,
                    payment_order_id=payment_order.id,
                    credit_amount=payment_order.credit_package.credit_amount,
                    idempotency_key=grant_idempotency_key,
                    metadata_json={
                        "gateway_provider": BillingGatewayProvider.RAZORPAY.value,
                        "gateway_order_id": gateway_order_id,
                        "gateway_payment_id": gateway_payment_id,
                        "event_type": event_type,
                    },
                    created_by=BILLING_CREATED_BY_WEBHOOK,
                )
            except DuplicateLedgerGrantError:
                # Treat duplicate grant as idempotent success.
                pass

            payment_order.status = PaymentOrderStatus.SETTLED
            payment_transaction.status = PaymentTransactionStatus.PROCESSED
            payment_transaction.processed_at = datetime.now(timezone.utc)

            webhook_event.processing_status = PaymentWebhookProcessingStatus.PROCESSED
            webhook_event.processed_at = datetime.now(timezone.utc)

            await db.commit()

            return RazorpayWebhookAckResponse(
                success=True,
                message="Verified webhook processed successfully.",
            )

        except Exception as exc:
            await db.rollback()
            await self._mark_webhook_failed(
                db=db,
                dedup_key=dedup_key,
                error_message=str(exc),
            )
            raise

    async def _persist_verified_webhook_event(
        self,
        *,
        db: AsyncSession,
        payload: dict[str, Any],
        dedup_key: str,
        gateway_event_id: str | None,
        event_type: str,
    ) -> None:
        stmt = (
            insert(PaymentWebhookEvent)
            .values(
                gateway_provider=BillingGatewayProvider.RAZORPAY,
                gateway_event_id=gateway_event_id,
                event_type=event_type,
                signature_verified=True,
                payload_json=payload,
                dedup_key=dedup_key,
                processing_status=PaymentWebhookProcessingStatus.PENDING,
            )
            .on_conflict_do_nothing(index_elements=["dedup_key"])
        )
        await db.execute(stmt)
        await db.commit()

    async def _lock_webhook_event_for_processing(
        self,
        *,
        db: AsyncSession,
        dedup_key: str,
    ) -> PaymentWebhookEvent:
        result = await db.execute(
            select(PaymentWebhookEvent)
            .where(PaymentWebhookEvent.dedup_key == dedup_key)
            .with_for_update()
        )
        webhook_event = result.scalar_one_or_none()

        if webhook_event is None:
            raise StudentBillingError(
                "Verified webhook event could not be reloaded for processing."
            )

        return webhook_event

    async def _resolve_internal_order_by_gateway_order_id(
        self,
        *,
        db: AsyncSession,
        gateway_order_id: str,
    ) -> PaymentOrder:
        result = await db.execute(
            select(PaymentOrder)
            .options(selectinload(PaymentOrder.credit_package))
            .where(PaymentOrder.gateway_order_id == gateway_order_id)
            .with_for_update()
        )
        payment_order = result.scalar_one_or_none()

        if payment_order is None:
            raise PaymentOrderNotFoundError(
                "No internal payment order exists for the supplied gateway order id."
            )

        return payment_order

    @staticmethod
    def _validate_settlement_payload_against_order(
        *,
        payment_order: PaymentOrder,
        amount_minor: int,
        currency_code: str,
    ) -> None:
        if payment_order.amount_minor != amount_minor:
            raise PaymentOrderAmountMismatchError(
                "Verified webhook amount does not match internal order amount."
            )

        if payment_order.currency_code.upper() != currency_code.upper():
            raise PaymentOrderCurrencyMismatchError(
                "Verified webhook currency does not match internal order currency."
            )

    async def _upsert_payment_transaction(
        self,
        *,
        db: AsyncSession,
        payment_order: PaymentOrder,
        gateway_payment_id: str,
        gateway_event_type: str,
        amount_minor: int,
        currency_code: str,
        raw_gateway_payload: dict[str, Any],
    ) -> PaymentTransaction:
        stmt = (
            insert(PaymentTransaction)
            .values(
                payment_order_id=payment_order.id,
                gateway_payment_id=gateway_payment_id,
                gateway_event_type=gateway_event_type,
                amount_minor=amount_minor,
                currency_code=currency_code,
                status=PaymentTransactionStatus.RECEIVED,
                raw_gateway_payload=raw_gateway_payload,
            )
            .on_conflict_do_nothing(index_elements=["gateway_payment_id"])
        )
        await db.execute(stmt)

        result = await db.execute(
            select(PaymentTransaction)
            .where(PaymentTransaction.gateway_payment_id == gateway_payment_id)
            .with_for_update()
        )
        payment_transaction = result.scalar_one()

        if payment_transaction.payment_order_id != payment_order.id:
            raise StudentBillingError(
                "Gateway payment id is already associated with a different payment order."
            )

        payment_transaction.gateway_event_type = gateway_event_type
        payment_transaction.amount_minor = amount_minor
        payment_transaction.currency_code = currency_code
        payment_transaction.raw_gateway_payload = raw_gateway_payload

        return payment_transaction

    async def _mark_webhook_failed(
        self,
        *,
        db: AsyncSession,
        dedup_key: str,
        error_message: str,
    ) -> None:
        result = await db.execute(
            select(PaymentWebhookEvent)
            .where(PaymentWebhookEvent.dedup_key == dedup_key)
            .with_for_update()
        )
        webhook_event = result.scalar_one_or_none()
        if webhook_event is None:
            return

        webhook_event.processing_status = PaymentWebhookProcessingStatus.FAILED
        webhook_event.processing_attempts = webhook_event.processing_attempts + 1
        webhook_event.last_error = error_message[:2000] if error_message else "Unknown webhook processing error."

        await db.commit()

    @staticmethod
    def _build_payment_grant_idempotency_key(
        *,
        payment_order_id: str,
        gateway_payment_id: str,
    ) -> str:
        return f"PURCHASE_GRANT:{payment_order_id}:{gateway_payment_id}"


payment_webhook_service = PaymentWebhookService()