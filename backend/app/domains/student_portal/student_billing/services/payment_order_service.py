from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BillingGatewayProvider,
    CreditPackage,
    PaymentOrder,
    PaymentOrderStatus,
    StudentExternalIdentity,
    StudentUser,
)
from app.domains.student_portal.student_billing.config.student_billing_config import (
    student_billing_settings,
)
from app.domains.student_portal.student_billing.constants import (
    BILLING_GATEWAY_PROVIDER_RAZORPAY,
)
from app.domains.student_portal.student_billing.exceptions import (
    CreditPackageNotFoundError,
    InactiveCreditPackageError,
    PaymentOrderNotFoundError,
    PaymentOrderOwnershipError,
    StudentBillingError,
)
from app.domains.student_portal.student_billing.schemas.student_billing_schemas import (
    CreditPackageDTO,
    StudentBillingCreateOrderRequest,
    StudentBillingCreateOrderResponse,
    StudentBillingOrderStatusResponse,
)
from app.domains.student_portal.student_billing.services.razorpay_gateway_service import (
    razorpay_gateway_service,
)


class PaymentOrderService:
    """
    Student-facing internal payment order orchestration.

    Design rules:
    - package pricing and credits come only from DB credit_packages
    - order creation is student-scoped idempotent
    - gateway order is created only after internal order exists
    """

    async def create_or_reuse_payment_order(
        self,
        *,
        db: AsyncSession,
        student: StudentUser,
        payload: StudentBillingCreateOrderRequest,
    ) -> StudentBillingCreateOrderResponse:
        existing = await self._find_existing_order_by_idempotency_key(
            db=db,
            student_user_id=student.id,
            client_idempotency_key=payload.client_idempotency_key,
        )
        if existing is not None:
            package = await self._get_credit_package_by_id(
                db=db,
                package_id=existing.package_id,
            )
            return await self._build_create_order_response(
                db=db,
                student=student,
                order=existing,
                package=package,
            )

        package = await self._resolve_active_package_by_code(
            db=db,
            package_code=payload.package_code,
        )

        merchant_order_ref = self._build_merchant_order_ref()

        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=student_billing_settings.BILLING_PAYMENT_ORDER_EXPIRY_MINUTES
        )

        order = PaymentOrder(
            student_user_id=student.id,
            package_id=package.id,
            merchant_order_ref=merchant_order_ref,
            gateway_provider=BillingGatewayProvider.RAZORPAY,
            client_idempotency_key=payload.client_idempotency_key,
            amount_minor=package.price_minor,
            currency_code=package.currency_code,
            status=PaymentOrderStatus.CREATED,
            expires_at=expires_at,
        )

        db.add(order)

        try:
            await db.flush()
            await db.commit()
            await db.refresh(order)
        except IntegrityError:
            await db.rollback()

            existing_after_conflict = await self._find_existing_order_by_idempotency_key(
                db=db,
                student_user_id=student.id,
                client_idempotency_key=payload.client_idempotency_key,
            )
            if existing_after_conflict is None:
                raise StudentBillingError(
                    "Payment order creation collided but no existing order could be recovered."
                )

            package_after_conflict = await self._get_credit_package_by_id(
                db=db,
                package_id=existing_after_conflict.package_id,
            )
            return await self._build_create_order_response(
                db=db,
                student=student,
                order=existing_after_conflict,
                package=package_after_conflict,
            )

        try:
            gateway_order = await razorpay_gateway_service.create_order(
                amount_minor=package.price_minor,
                currency_code=package.currency_code,
                receipt=merchant_order_ref,
                notes={
                    "payment_order_id": str(order.id),
                    "student_user_id": str(student.id),
                    "package_code": package.package_code,
                },
            )
        except Exception:
            order.status = PaymentOrderStatus.FAILED
            await db.commit()
            raise

        order.gateway_order_id = str(gateway_order["id"])
        order.gateway_receipt = str(gateway_order.get("receipt") or merchant_order_ref)
        order.status = PaymentOrderStatus.GATEWAY_ORDER_CREATED

        await db.commit()
        await db.refresh(order)

        return await self._build_create_order_response(
            db=db,
            student=student,
            order=order,
            package=package,
        )

    async def get_owned_order_or_404(
        self,
        *,
        db: AsyncSession,
        student: StudentUser,
        payment_order_id: UUID,
    ) -> PaymentOrder:
        result = await db.execute(
            select(PaymentOrder).where(PaymentOrder.id == payment_order_id)
        )
        order = result.scalar_one_or_none()

        if order is None:
            raise PaymentOrderNotFoundError("Payment order was not found.")

        if order.student_user_id != student.id:
            raise PaymentOrderOwnershipError(
                "Student does not own the requested payment order."
            )

        return order

    async def get_order_status_response(
        self,
        *,
        db: AsyncSession,
        student: StudentUser,
        payment_order_id: UUID,
    ) -> StudentBillingOrderStatusResponse:
        order = await self.get_owned_order_or_404(
            db=db,
            student=student,
            payment_order_id=payment_order_id,
        )
        package = await self._get_credit_package_by_id(
            db=db,
            package_id=order.package_id,
        )

        status_value = (
            order.status.value if hasattr(order.status, "value") else str(order.status)
        )

        return StudentBillingOrderStatusResponse(
            payment_order_id=order.id,
            merchant_order_ref=order.merchant_order_ref,
            package_code=package.package_code,
            credit_amount=package.credit_amount,
            amount_minor=order.amount_minor,
            currency_code=order.currency_code,
            status=status_value,
            settled=(status_value == PaymentOrderStatus.SETTLED.value),
            created_at=order.created_at,
            updated_at=order.updated_at,
        )

    async def _resolve_active_package_by_code(
        self,
        *,
        db: AsyncSession,
        package_code: str,
    ) -> CreditPackage:
        result = await db.execute(
            select(CreditPackage).where(CreditPackage.package_code == package_code)
        )
        package = result.scalar_one_or_none()

        if package is None:
            raise CreditPackageNotFoundError("Requested credit package was not found.")

        if not package.active:
            raise InactiveCreditPackageError(
                "Requested credit package is currently inactive."
            )

        return package

    async def _get_credit_package_by_id(
        self,
        *,
        db: AsyncSession,
        package_id: UUID,
    ) -> CreditPackage:
        result = await db.execute(
            select(CreditPackage).where(CreditPackage.id == package_id)
        )
        package = result.scalar_one_or_none()

        if package is None:
            raise CreditPackageNotFoundError("Credit package was not found.")

        return package

    async def _find_existing_order_by_idempotency_key(
        self,
        *,
        db: AsyncSession,
        student_user_id: UUID,
        client_idempotency_key: str,
    ) -> PaymentOrder | None:
        result = await db.execute(
            select(PaymentOrder).where(
                PaymentOrder.student_user_id == student_user_id,
                PaymentOrder.client_idempotency_key == client_idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def _build_create_order_response(
        self,
        *,
        db: AsyncSession,
        student: StudentUser,
        order: PaymentOrder,
        package: CreditPackage,
    ) -> StudentBillingCreateOrderResponse:
        prefill_name = self._build_checkout_prefill_name(student)
        prefill_email = await self._resolve_provider_email(
            db=db,
            student_user_id=student.id,
        )

        status_value = (
            order.status.value if hasattr(order.status, "value") else str(order.status)
        )

        return StudentBillingCreateOrderResponse(
            payment_order_id=order.id,
            merchant_order_ref=order.merchant_order_ref,
            gateway_provider=BILLING_GATEWAY_PROVIDER_RAZORPAY,
            gateway_order_id=order.gateway_order_id or "",
            amount_minor=order.amount_minor,
            currency_code=order.currency_code,
            status=status_value,
            expires_at=order.expires_at,
            package=CreditPackageDTO(
                id=package.id,
                package_code=package.package_code,
                display_name=package.display_name,
                description=package.description,
                credit_amount=package.credit_amount,
                price_minor=package.price_minor,
                currency_code=package.currency_code,
                active=package.active,
                display_order=package.display_order,
            ),
            checkout_public_key=student_billing_settings.RAZORPAY_KEY_ID,
            checkout_prefill_name=prefill_name,
            checkout_prefill_email=prefill_email,
        )

    @staticmethod
    def _build_merchant_order_ref() -> str:
        prefix = student_billing_settings.billing_merchant_order_prefix_normalized
        return f"{prefix}-{uuid4().hex[:20].upper()}"

    @staticmethod
    def _build_checkout_prefill_name(student: StudentUser) -> str | None:
        display_name = (student.display_name or "").strip()
        if display_name:
            return display_name

        full_name = (
            f"{(student.first_name or '').strip()} {(student.last_name or '').strip()}"
        ).strip()
        return full_name or None

    async def _resolve_provider_email(
        self,
        *,
        db: AsyncSession,
        student_user_id: UUID,
    ) -> str | None:
        result = await db.execute(
            select(StudentExternalIdentity.provider_email)
            .where(StudentExternalIdentity.student_user_id == student_user_id)
            .order_by(StudentExternalIdentity.created_at.asc())
        )
        emails = [row[0] for row in result.all() if row[0]]
        return emails[0] if emails else None


payment_order_service = PaymentOrderService()