from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CreditLedgerEntryType,
    StudentCreditLedger,
    StudentCreditWallet,
)
from app.domains.student_portal.student_billing.constants import (
    BILLING_REFERENCE_TYPE_PAYMENT_ORDER,
    BILLING_REFERENCE_TYPE_COLLEGE_FILTER_SEARCH,
)
from app.domains.student_portal.student_billing.exceptions import (
    DuplicateLedgerGrantError,
    InsufficientCreditsError,
    StudentBillingError,
)


class CreditLedgerService:
    """
    Immutable-ledger-backed wallet mutation service.

    Design rules:
    - all credit balance changes flow through ledger first
    - wallet is only an operational snapshot
    - caller manages the outer transaction boundary
    """

    async def get_or_create_wallet_for_update(
        self,
        *,
        db: AsyncSession,
        student_user_id: UUID,
        nowait: bool = False,
    ) -> StudentCreditWallet:
        """
        Concurrency-safe wallet acquisition.

        Uses PostgreSQL UPSERT semantics to avoid first-wallet race conditions.
        Then locks the row for update.

        nowait=False:
            default blocking lock behavior for non-interactive billing flows

        nowait=True:
            fail-fast lock behavior for interactive user-facing flows
        """
        stmt = (
            insert(StudentCreditWallet)
            .values(student_user_id=student_user_id)
            .on_conflict_do_nothing(index_elements=["student_user_id"])
        )
        await db.execute(stmt)

        wallet_result = await db.execute(
            select(StudentCreditWallet)
            .where(StudentCreditWallet.student_user_id == student_user_id)
            .with_for_update(nowait=nowait)
        )
        wallet = wallet_result.scalar_one()

        return wallet

    async def get_wallet_snapshot(
        self,
        *,
        db: AsyncSession,
        student_user_id: UUID,
    ) -> StudentCreditWallet | None:
        """
        Read-only wallet lookup.

        Design rules:
        - no row locking
        - no implicit wallet creation
        - safe for preflight checks in latency-sensitive flows
        """
        result = await db.execute(
            select(StudentCreditWallet).where(
                StudentCreditWallet.student_user_id == student_user_id
            )
        )
        return result.scalar_one_or_none()

    async def grant_purchase_credits(
        self,
        *,
        db: AsyncSession,
        student_user_id: UUID,
        payment_order_id: UUID,
        credit_amount: int,
        idempotency_key: str,
        metadata_json: dict[str, Any] | None = None,
        created_by: str,
    ) -> tuple[StudentCreditWallet, StudentCreditLedger]:
        """
        Grants purchase credits exactly once.

        Caller must ensure:
        - payment has already been validated
        - settlement trigger is trusted
        - outer transaction commit/rollback is handled by caller
        """
        existing_result = await db.execute(
            select(StudentCreditLedger).where(
                StudentCreditLedger.idempotency_key == idempotency_key
            )
        )
        existing_ledger_entry = existing_result.scalar_one_or_none()
        if existing_ledger_entry is not None:
            raise DuplicateLedgerGrantError(
                "A purchase credit grant already exists for this idempotency key."
            )

        wallet = await self.get_or_create_wallet_for_update(
            db=db,
            student_user_id=student_user_id,
        )

        new_balance = wallet.available_credits + credit_amount

        insert_stmt = (
            insert(StudentCreditLedger)
            .values(
                student_user_id=student_user_id,
                entry_type=CreditLedgerEntryType.PURCHASE_CREDIT_GRANTED,
                credit_delta=credit_amount,
                balance_after=new_balance,
                reference_type=BILLING_REFERENCE_TYPE_PAYMENT_ORDER,
                reference_id=payment_order_id,
                idempotency_key=idempotency_key,
                metadata_json=metadata_json or {},
                created_by=created_by,
            )
            .on_conflict_do_nothing(index_elements=["idempotency_key"])
        )

        result = await db.execute(insert_stmt)

        if result.rowcount == 0:
            raise DuplicateLedgerGrantError(
                "A purchase credit grant already exists for this idempotency key."
            )

        wallet.available_credits = new_balance
        wallet.lifetime_credits_purchased = (
            wallet.lifetime_credits_purchased + credit_amount
        )
        wallet.version = wallet.version + 1

        await db.flush()

        ledger_result = await db.execute(
            select(StudentCreditLedger).where(
                StudentCreditLedger.idempotency_key == idempotency_key
            )
        )
        ledger_entry = ledger_result.scalar_one()

        await db.refresh(wallet)

        return wallet, ledger_entry

    async def consume_search_credit(
        self,
        *,
        db: AsyncSession,
        student_user_id: UUID,
        entitlement_id: UUID,
        credit_cost: int,
        idempotency_key: str,
        metadata_json: dict[str, Any] | None = None,
        created_by: str,
    ) -> tuple[StudentCreditWallet, StudentCreditLedger]:
        """
        Consumes search credits exactly once.

        Caller must ensure:
        - the billable action is valid
        - entitlement / fingerprint logic has already been resolved
        - outer transaction commit/rollback is handled by caller
        """
        existing_result = await db.execute(
            select(StudentCreditLedger).where(
                StudentCreditLedger.idempotency_key == idempotency_key
            )
        )
        existing_ledger_entry = existing_result.scalar_one_or_none()
        if existing_ledger_entry is not None:
            wallet_result = await db.execute(
                select(StudentCreditWallet).where(
                    StudentCreditWallet.student_user_id == student_user_id
                )
            )
            wallet = wallet_result.scalar_one_or_none()
            if wallet is None:
                raise StudentBillingError(
                    "Search credit consumption already exists, but wallet snapshot is missing."
                )

            return wallet, existing_ledger_entry

        try:
            wallet = await self.get_or_create_wallet_for_update(
                db=db,
                student_user_id=student_user_id,
                nowait=True,
            )
        except OperationalError as exc:
            if self._is_lock_not_available_error(exc):
                raise StudentBillingError(
                    "Billing engine is currently busy processing another transaction. Please try again in a few seconds."
                ) from exc
            raise

        if wallet.available_credits < credit_cost:
            raise InsufficientCreditsError(
                "Insufficient credits for College Filter search.",
                available_credits=wallet.available_credits,
                required_credits=credit_cost,
            )

        new_balance = wallet.available_credits - credit_cost

        insert_stmt = (
            insert(StudentCreditLedger)
            .values(
                student_user_id=student_user_id,
                entry_type=CreditLedgerEntryType.SEARCH_CREDIT_CONSUMED,
                credit_delta=-credit_cost,
                balance_after=new_balance,
                reference_type=BILLING_REFERENCE_TYPE_COLLEGE_FILTER_SEARCH,
                reference_id=entitlement_id,
                idempotency_key=idempotency_key,
                metadata_json=metadata_json or {},
                created_by=created_by,
            )
            .on_conflict_do_nothing(index_elements=["idempotency_key"])
        )

        result = await db.execute(insert_stmt)

        if result.rowcount == 0:
            ledger_result = await db.execute(
                select(StudentCreditLedger).where(
                    StudentCreditLedger.idempotency_key == idempotency_key
                )
            )
            ledger_entry = ledger_result.scalar_one()

            await db.refresh(wallet)
            return wallet, ledger_entry

        wallet.available_credits = new_balance
        wallet.lifetime_credits_consumed = (
            wallet.lifetime_credits_consumed + credit_cost
        )
        wallet.version = wallet.version + 1

        await db.flush()

        ledger_result = await db.execute(
            select(StudentCreditLedger).where(
                StudentCreditLedger.idempotency_key == idempotency_key
            )
        )
        ledger_entry = ledger_result.scalar_one()

        await db.refresh(wallet)

        return wallet, ledger_entry

    @staticmethod
    def _is_lock_not_available_error(exc: OperationalError) -> bool:
        """
        Detect PostgreSQL fail-fast row-lock acquisition failure.

        We only translate real lock contention into a user-facing
        "billing engine is busy" message. Other OperationalError
        cases must bubble up unchanged.
        """
        original = getattr(exc, "orig", None)

        pgcode = getattr(original, "pgcode", None)
        if pgcode == "55P03":
            return True

        message = str(original or exc).lower()
        return (
            "could not obtain lock on row" in message
            or "lock not available" in message
        )


credit_ledger_service = CreditLedgerService()