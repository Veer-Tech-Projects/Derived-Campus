from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, outerjoin, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    CreditLedgerEntryType,
    PaymentOrder,
    PaymentOrderStatus,
    PaymentTransaction,
    PaymentTransactionStatus,
    PaymentWebhookEvent,
    PaymentWebhookProcessingStatus,
    StudentCreditLedger,
)
from app.domains.student_portal.student_billing.constants import (
    BILLING_CREATED_BY_RECONCILIATION,
    BILLING_REFERENCE_TYPE_PAYMENT_ORDER,
)
from app.domains.student_portal.student_billing.exceptions import (
    DuplicateLedgerGrantError,
    StudentBillingError,
)
from app.domains.student_portal.student_billing.services.credit_ledger_service import (
    credit_ledger_service,
)
from app.domains.student_portal.student_billing.services.payment_webhook_service import (
    payment_webhook_service,
)
from app.domains.student_portal.student_billing.services.razorpay_gateway_service import (
    razorpay_gateway_service,
)

logger = logging.getLogger(__name__)

RECONCILIATION_GATEWAY_EVENT_TYPE = "reconciliation.order.paid"


class BillingReconciliationService:
    """
    Operational reconciliation service.

    Design rules:
    - reconciliation is a repair path, not a second source of truth
    - webhook-first settlement remains primary
    - all wallet mutation still flows through credit_ledger_service
    - each candidate is processed in isolation for safe rollback boundaries
    """

    async def find_stale_non_final_orders(
        self,
        *,
        db: AsyncSession,
        older_than_minutes: int = 30,
        limit: int = 100,
    ) -> list[PaymentOrder]:
        threshold = datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)

        result = await db.execute(
            select(PaymentOrder)
            .where(
                PaymentOrder.created_at <= threshold,
                PaymentOrder.status.in_(
                    [
                        PaymentOrderStatus.CREATED,
                        PaymentOrderStatus.GATEWAY_ORDER_CREATED,
                        PaymentOrderStatus.CHECKOUT_INITIATED,
                    ]
                ),
            )
            .order_by(PaymentOrder.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def find_failed_verified_webhook_events(
        self,
        *,
        db: AsyncSession,
        limit: int = 100,
    ) -> list[PaymentWebhookEvent]:
        result = await db.execute(
            select(PaymentWebhookEvent)
            .where(
                PaymentWebhookEvent.signature_verified.is_(True),
                PaymentWebhookEvent.processing_status == PaymentWebhookProcessingStatus.FAILED,
            )
            .order_by(PaymentWebhookEvent.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def find_settled_orders_missing_ledger_grant(
        self,
        *,
        db: AsyncSession,
        limit: int = 100,
    ) -> list[PaymentOrder]:
        ledger_join = outerjoin(
            PaymentOrder,
            StudentCreditLedger,
            and_(
                StudentCreditLedger.reference_type == BILLING_REFERENCE_TYPE_PAYMENT_ORDER,
                StudentCreditLedger.reference_id == PaymentOrder.id,
                StudentCreditLedger.entry_type == CreditLedgerEntryType.PURCHASE_CREDIT_GRANTED,
            ),
        )

        result = await db.execute(
            select(PaymentOrder)
            .select_from(ledger_join)
            .where(
                PaymentOrder.status == PaymentOrderStatus.SETTLED,
                StudentCreditLedger.id.is_(None),
            )
            .order_by(PaymentOrder.updated_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def run_reconciliation_sweep(
        self,
        *,
        db: AsyncSession,
        older_than_minutes: int = 30,
        limit: int = 100,
    ) -> dict[str, int]:
        stale_orders = await self.find_stale_non_final_orders(
            db=db,
            older_than_minutes=older_than_minutes,
            limit=limit,
        )
        failed_verified_webhooks = await self.find_failed_verified_webhook_events(
            db=db,
            limit=limit,
        )
        settled_missing_ledger = await self.find_settled_orders_missing_ledger_grant(
            db=db,
            limit=limit,
        )

        summary = {
            "stale_orders_seen": len(stale_orders),
            "failed_verified_webhooks_seen": len(failed_verified_webhooks),
            "missing_ledger_grants_seen": len(settled_missing_ledger),
            "stale_orders_repaired": 0,
            "failed_verified_webhooks_repaired": 0,
            "missing_ledger_grants_repaired": 0,
            "failures": 0,
        }

        for order in stale_orders:
            try:
                outcome = await self.reconcile_stale_non_final_order(
                    db=db,
                    payment_order_id=order.id,
                )
                if outcome.startswith("repaired") or outcome.startswith("settled") or outcome.startswith("marked_expired"):
                    summary["stale_orders_repaired"] += 1
            except Exception:
                summary["failures"] += 1
                logger.exception(
                    "Billing reconciliation failed for stale payment order %s.",
                    order.id,
                )
                await db.rollback()

        for webhook_event in failed_verified_webhooks:
            try:
                outcome = await self.retry_failed_verified_webhook_event(
                    db=db,
                    webhook_event_id=webhook_event.id,
                )
                if outcome == "repaired_failed_verified_webhook":
                    summary["failed_verified_webhooks_repaired"] += 1
            except Exception:
                summary["failures"] += 1
                logger.exception(
                    "Billing reconciliation failed for verified webhook event %s.",
                    webhook_event.id,
                )
                await db.rollback()

        for order in settled_missing_ledger:
            try:
                outcome = await self.repair_settled_order_missing_ledger_grant(
                    db=db,
                    payment_order_id=order.id,
                )
                if outcome.startswith("repaired") or outcome == "already_consistent":
                    summary["missing_ledger_grants_repaired"] += 1
            except Exception:
                summary["failures"] += 1
                logger.exception(
                    "Billing reconciliation failed for settled order missing ledger grant %s.",
                    order.id,
                )
                await db.rollback()

        return summary

    async def reconcile_stale_non_final_order(
        self,
        *,
        db: AsyncSession,
        payment_order_id: UUID,
    ) -> str:
        try:
            payment_order = await self._load_order_for_update(
                db=db,
                payment_order_id=payment_order_id,
            )

            if payment_order.status == PaymentOrderStatus.SETTLED:
                return "already_terminal_settled"

            if payment_order.status in {
                PaymentOrderStatus.FAILED,
                PaymentOrderStatus.CANCELLED,
                PaymentOrderStatus.EXPIRED,
            }:
                return "already_terminal_non_success"

            now = datetime.now(timezone.utc)

            if not payment_order.gateway_order_id:
                if payment_order.expires_at and payment_order.expires_at <= now:
                    payment_order.status = PaymentOrderStatus.EXPIRED
                    await db.commit()
                    return "marked_expired_without_gateway_order"

                return "still_unresolved_missing_gateway_order"

            snapshot = await razorpay_gateway_service.build_order_reconciliation_snapshot(
                gateway_order_id=payment_order.gateway_order_id,
            )
            gateway_order = snapshot["order"]
            paid_payment = snapshot["paid_payment"]
            gateway_payments = snapshot["payments"]

            if paid_payment is not None:
                await self._settle_order_from_gateway_payment(
                    db=db,
                    payment_order=payment_order,
                    gateway_order=gateway_order,
                    gateway_payment=paid_payment,
                    raw_gateway_payload={
                        "source": "reconciliation",
                        "gateway_order": gateway_order,
                        "gateway_payments": gateway_payments,
                    },
                )
                return "settled_from_gateway_truth"

            if payment_order.expires_at and payment_order.expires_at <= now:
                payment_order.status = PaymentOrderStatus.EXPIRED
                await db.commit()
                return "marked_expired_after_gateway_check"

            return "still_unresolved_after_gateway_check"

        except Exception:
            await db.rollback()
            raise

    async def retry_failed_verified_webhook_event(
        self,
        *,
        db: AsyncSession,
        webhook_event_id: UUID,
    ) -> str:
        result = await db.execute(
            select(PaymentWebhookEvent).where(PaymentWebhookEvent.id == webhook_event_id)
        )
        webhook_event = result.scalar_one_or_none()

        if webhook_event is None:
            return "missing_webhook_event"

        if not webhook_event.signature_verified:
            return "skipped_unverified_webhook"

        if webhook_event.processing_status != PaymentWebhookProcessingStatus.FAILED:
            return "already_not_failed"

        await payment_webhook_service.process_verified_razorpay_webhook(
            db=db,
            payload=webhook_event.payload_json,
        )
        return "repaired_failed_verified_webhook"

    async def repair_settled_order_missing_ledger_grant(
        self,
        *,
        db: AsyncSession,
        payment_order_id: UUID,
    ) -> str:
        try:
            payment_order = await self._load_order_for_update(
                db=db,
                payment_order_id=payment_order_id,
                include_transactions=True,
            )

            if payment_order.status != PaymentOrderStatus.SETTLED:
                return "skipped_order_not_settled"

            transaction = await self._resolve_reconciliation_transaction(
                db=db,
                payment_order=payment_order,
            )
            if transaction is None:
                return "skipped_no_payment_transaction"

            grant_idempotency_key = payment_webhook_service._build_payment_grant_idempotency_key(
                payment_order_id=str(payment_order.id),
                gateway_payment_id=transaction.gateway_payment_id,
            )

            try:
                await credit_ledger_service.grant_purchase_credits(
                    db=db,
                    student_user_id=payment_order.student_user_id,
                    payment_order_id=payment_order.id,
                    credit_amount=payment_order.credit_package.credit_amount,
                    idempotency_key=grant_idempotency_key,
                    metadata_json={
                        "gateway_provider": str(payment_order.gateway_provider.value if hasattr(payment_order.gateway_provider, "value") else payment_order.gateway_provider),
                        "gateway_order_id": payment_order.gateway_order_id,
                        "gateway_payment_id": transaction.gateway_payment_id,
                        "event_type": transaction.gateway_event_type,
                        "repair_source": "reconciliation_missing_ledger_grant",
                    },
                    created_by=BILLING_CREATED_BY_RECONCILIATION,
                )
            except DuplicateLedgerGrantError:
                pass

            transaction.status = PaymentTransactionStatus.PROCESSED
            if transaction.processed_at is None:
                transaction.processed_at = datetime.now(timezone.utc)

            await db.commit()
            return "repaired_missing_ledger_grant"

        except Exception:
            await db.rollback()
            raise

    async def _load_order_for_update(
        self,
        *,
        db: AsyncSession,
        payment_order_id: UUID,
        include_transactions: bool = False,
    ) -> PaymentOrder:
        options = [selectinload(PaymentOrder.credit_package)]
        if include_transactions:
            options.append(selectinload(PaymentOrder.payment_transactions))

        result = await db.execute(
            select(PaymentOrder)
            .options(*options)
            .where(PaymentOrder.id == payment_order_id)
            .with_for_update()
        )
        payment_order = result.scalar_one_or_none()
        if payment_order is None:
            raise StudentBillingError(
                "Payment order could not be reloaded for reconciliation."
            )

        return payment_order

    async def _resolve_reconciliation_transaction(
        self,
        *,
        db: AsyncSession,
        payment_order: PaymentOrder,
    ) -> PaymentTransaction | None:
        existing_transactions = list(payment_order.payment_transactions or [])
        if existing_transactions:
            existing_transactions.sort(
                key=lambda tx: (
                    tx.processed_at or datetime.min.replace(tzinfo=timezone.utc),
                    tx.created_at,
                ),
                reverse=True,
            )
            return existing_transactions[0]

        if not payment_order.gateway_order_id:
            return None

        snapshot = await razorpay_gateway_service.build_order_reconciliation_snapshot(
            gateway_order_id=payment_order.gateway_order_id,
        )
        gateway_order = snapshot["order"]
        paid_payment = snapshot["paid_payment"]
        gateway_payments = snapshot["payments"]

        if paid_payment is None:
            return None

        return await self._settle_order_from_gateway_payment(
            db=db,
            payment_order=payment_order,
            gateway_order=gateway_order,
            gateway_payment=paid_payment,
            raw_gateway_payload={
                "source": "reconciliation_missing_ledger_grant",
                "gateway_order": gateway_order,
                "gateway_payments": gateway_payments,
            },
            skip_commit=True,
            skip_ledger_grant=True,
        )

    async def _settle_order_from_gateway_payment(
        self,
        *,
        db: AsyncSession,
        payment_order: PaymentOrder,
        gateway_order: dict[str, Any],
        gateway_payment: dict[str, Any],
        raw_gateway_payload: dict[str, Any],
        skip_commit: bool = False,
        skip_ledger_grant: bool = False,
    ) -> PaymentTransaction:
        gateway_payment_id = str(gateway_payment.get("id") or "").strip()
        if not gateway_payment_id:
            raise StudentBillingError(
                "Gateway reconciliation payment payload did not include a payment id."
            )

        amount_minor = gateway_payment.get("amount")
        try:
            amount_minor_int = int(amount_minor)
        except (TypeError, ValueError) as exc:
            raise StudentBillingError(
                "Gateway reconciliation payment payload did not include a valid amount."
            ) from exc

        currency_code = str(gateway_payment.get("currency") or "").strip().upper()
        if not currency_code:
            raise StudentBillingError(
                "Gateway reconciliation payment payload did not include a valid currency."
            )

        payment_webhook_service._validate_settlement_payload_against_order(
            payment_order=payment_order,
            amount_minor=amount_minor_int,
            currency_code=currency_code,
        )

        payment_transaction = await payment_webhook_service._upsert_payment_transaction(
            db=db,
            payment_order=payment_order,
            gateway_payment_id=gateway_payment_id,
            gateway_event_type=RECONCILIATION_GATEWAY_EVENT_TYPE,
            amount_minor=amount_minor_int,
            currency_code=currency_code,
            raw_gateway_payload={
                **raw_gateway_payload,
                "gateway_payment": gateway_payment,
            },
        )

        if not skip_ledger_grant:
            grant_idempotency_key = payment_webhook_service._build_payment_grant_idempotency_key(
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
                        "gateway_provider": str(payment_order.gateway_provider.value if hasattr(payment_order.gateway_provider, "value") else payment_order.gateway_provider),
                        "gateway_order_id": payment_order.gateway_order_id,
                        "gateway_payment_id": gateway_payment_id,
                        "event_type": RECONCILIATION_GATEWAY_EVENT_TYPE,
                        "repair_source": "reconciliation_stale_order",
                    },
                    created_by=BILLING_CREATED_BY_RECONCILIATION,
                )
            except DuplicateLedgerGrantError:
                pass

        payment_order.status = PaymentOrderStatus.SETTLED
        payment_transaction.status = PaymentTransactionStatus.PROCESSED
        payment_transaction.processed_at = datetime.now(timezone.utc)

        if not skip_commit:
            await db.commit()

        return payment_transaction


billing_reconciliation_service = BillingReconciliationService()