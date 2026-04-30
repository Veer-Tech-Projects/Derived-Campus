from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CreditPackage,
    PaymentTransaction,
    StudentCreditLedger,
    StudentCreditWallet,
    StudentUser,
)
from app.domains.student_portal.student_billing.schemas.student_billing_schemas import (
    CreditLedgerEntryDTO,
    CreditPackageDTO,
    PaymentTransactionDTO,
    StudentBillingOverviewResponse,
    StudentCreditWalletDTO,
)
from app.domains.student_portal.student_billing.services.payment_order_service import (
    payment_order_service,
)


class StudentBillingService:
    """
    Read-side student billing orchestration.

    Design rules:
    - read only
    - no ledger mutation
    - no gateway calls
    """

    async def list_active_packages(
        self,
        *,
        db: AsyncSession,
    ) -> list[CreditPackageDTO]:
        result = await db.execute(
            select(CreditPackage)
            .where(CreditPackage.active.is_(True))
            .order_by(CreditPackage.display_order.asc(), CreditPackage.created_at.asc())
        )
        packages = result.scalars().all()

        return [
            CreditPackageDTO(
                id=package.id,
                package_code=package.package_code,
                display_name=package.display_name,
                description=package.description,
                credit_amount=package.credit_amount,
                price_minor=package.price_minor,
                currency_code=package.currency_code,
                active=package.active,
                display_order=package.display_order,
            )
            for package in packages
        ]

    async def get_wallet_snapshot(
        self,
        *,
        db: AsyncSession,
        student: StudentUser,
    ) -> StudentCreditWalletDTO:
        result = await db.execute(
            select(StudentCreditWallet).where(
                StudentCreditWallet.student_user_id == student.id
            )
        )
        wallet = result.scalar_one_or_none()

        if wallet is None:
            return StudentCreditWalletDTO(
                available_credits=0,
                lifetime_credits_purchased=0,
                lifetime_credits_consumed=0,
                updated_at=datetime.now(timezone.utc),
            )

        return StudentCreditWalletDTO(
            available_credits=wallet.available_credits,
            lifetime_credits_purchased=wallet.lifetime_credits_purchased,
            lifetime_credits_consumed=wallet.lifetime_credits_consumed,
            updated_at=wallet.updated_at,
        )

    async def list_transactions(
        self,
        *,
        db: AsyncSession,
        student: StudentUser,
        limit: int = 20,
    ) -> list[PaymentTransactionDTO]:
        result = await db.execute(
            select(PaymentTransaction)
            .join(PaymentTransaction.payment_order)
            .where(PaymentTransaction.payment_order.has(student_user_id=student.id))
            .order_by(PaymentTransaction.created_at.desc())
            .limit(limit)
        )
        transactions = result.scalars().all()

        return [
            PaymentTransactionDTO(
                id=tx.id,
                payment_order_id=tx.payment_order_id,
                gateway_payment_id=tx.gateway_payment_id,
                gateway_event_type=tx.gateway_event_type,
                amount_minor=tx.amount_minor,
                currency_code=tx.currency_code,
                status=tx.status.value if hasattr(tx.status, "value") else str(tx.status),
                processed_at=tx.processed_at,
                created_at=tx.created_at,
            )
            for tx in transactions
        ]

    async def list_ledger_entries(
        self,
        *,
        db: AsyncSession,
        student: StudentUser,
        limit: int = 20,
    ) -> list[CreditLedgerEntryDTO]:
        result = await db.execute(
            select(StudentCreditLedger)
            .where(StudentCreditLedger.student_user_id == student.id)
            .order_by(StudentCreditLedger.created_at.desc())
            .limit(limit)
        )
        entries = result.scalars().all()

        return [
            CreditLedgerEntryDTO(
                id=entry.id,
                entry_type=entry.entry_type.value if hasattr(entry.entry_type, "value") else str(entry.entry_type),
                credit_delta=entry.credit_delta,
                balance_after=entry.balance_after,
                reference_type=entry.reference_type,
                reference_id=entry.reference_id,
                metadata_json=entry.metadata_json,
                created_by=entry.created_by,
                created_at=entry.created_at,
            )
            for entry in entries
        ]

    async def get_billing_overview(
        self,
        *,
        db: AsyncSession,
        student: StudentUser,
    ) -> StudentBillingOverviewResponse:
        wallet = await self.get_wallet_snapshot(db=db, student=student)
        packages = await self.list_active_packages(db=db)
        recent_transactions = await self.list_transactions(db=db, student=student, limit=10)
        recent_ledger_entries = await self.list_ledger_entries(db=db, student=student, limit=10)

        return StudentBillingOverviewResponse(
            wallet=wallet,
            packages=packages,
            recent_transactions=recent_transactions,
            recent_ledger_entries=recent_ledger_entries,
        )

    async def get_order_status(
        self,
        *,
        db: AsyncSession,
        student: StudentUser,
        payment_order_id: UUID,
    ):
        return await payment_order_service.get_order_status_response(
            db=db,
            student=student,
            payment_order_id=payment_order_id,
        )


student_billing_service = StudentBillingService()