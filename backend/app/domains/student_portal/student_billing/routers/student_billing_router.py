from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import StudentUser
from app.domains.student_auth.dependencies.student_auth_dependency import get_current_student
from app.domains.student_portal.student_billing.exceptions import (
    CreditPackageNotFoundError,
    InactiveCreditPackageError,
    PaymentOrderNotFoundError,
    PaymentOrderOwnershipError,
    StudentBillingError,
)
from app.domains.student_portal.student_billing.schemas.student_billing_schemas import (
    CreditLedgerListResponse,
    CreditPackageListResponse,
    PaymentTransactionListResponse,
    StudentBillingCreateOrderRequest,
    StudentBillingCreateOrderResponse,
    StudentBillingOrderStatusResponse,
    StudentBillingOverviewResponse,
)
from app.domains.student_portal.student_billing.services.payment_order_service import (
    payment_order_service,
)
from app.domains.student_portal.student_billing.services.student_billing_service import (
    student_billing_service,
)

router = APIRouter(
    prefix="/student-billing",
    tags=["Student Billing"],
)


@router.get(
    "/overview",
    response_model=StudentBillingOverviewResponse,
    status_code=status.HTTP_200_OK,
)
async def get_student_billing_overview(
    current_student: StudentUser = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
) -> StudentBillingOverviewResponse:
    return await student_billing_service.get_billing_overview(
        db=db,
        student=current_student,
    )


@router.get(
    "/packages",
    response_model=CreditPackageListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_student_billing_packages(
    db: AsyncSession = Depends(get_db),
    _: StudentUser = Depends(get_current_student),
) -> CreditPackageListResponse:
    items = await student_billing_service.list_active_packages(db=db)
    return CreditPackageListResponse(items=items)


@router.post(
    "/orders",
    response_model=StudentBillingCreateOrderResponse,
    status_code=status.HTTP_200_OK,
)
async def create_student_billing_order(
    payload: StudentBillingCreateOrderRequest,
    current_student: StudentUser = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
) -> StudentBillingCreateOrderResponse:
    try:
        return await payment_order_service.create_or_reuse_payment_order(
            db=db,
            student=current_student,
            payload=payload,
        )
    except CreditPackageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InactiveCreditPackageError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except StudentBillingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/orders/{payment_order_id}",
    response_model=StudentBillingOrderStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_student_billing_order_status(
    payment_order_id: UUID,
    current_student: StudentUser = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
) -> StudentBillingOrderStatusResponse:
    try:
        return await student_billing_service.get_order_status(
            db=db,
            student=current_student,
            payment_order_id=payment_order_id,
        )
    except PaymentOrderNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except PaymentOrderOwnershipError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.get(
    "/transactions",
    response_model=PaymentTransactionListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_student_billing_transactions(
    limit: int = Query(default=20, ge=1, le=100),
    current_student: StudentUser = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
) -> PaymentTransactionListResponse:
    items = await student_billing_service.list_transactions(
        db=db,
        student=current_student,
        limit=limit,
    )
    return PaymentTransactionListResponse(items=items)


@router.get(
    "/ledger",
    response_model=CreditLedgerListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_student_billing_ledger_entries(
    limit: int = Query(default=20, ge=1, le=100),
    current_student: StudentUser = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
) -> CreditLedgerListResponse:
    items = await student_billing_service.list_ledger_entries(
        db=db,
        student=current_student,
        limit=limit,
    )
    return CreditLedgerListResponse(items=items)