from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreditPackageDTO(BaseModel):
    id: UUID
    package_code: str = Field(..., min_length=1, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=128)
    description: str | None = None
    credit_amount: int = Field(..., gt=0)
    price_minor: int = Field(..., gt=0)
    currency_code: str = Field(..., min_length=3, max_length=3)
    active: bool
    display_order: int = Field(..., ge=0)

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class CreditPackageListResponse(BaseModel):
    items: list[CreditPackageDTO]

    model_config = ConfigDict(extra="forbid")


class StudentCreditWalletDTO(BaseModel):
    available_credits: int = Field(..., ge=0)
    lifetime_credits_purchased: int = Field(..., ge=0)
    lifetime_credits_consumed: int = Field(..., ge=0)
    updated_at: datetime

    model_config = ConfigDict(extra="forbid")


class PaymentTransactionDTO(BaseModel):
    id: UUID
    payment_order_id: UUID
    gateway_payment_id: str = Field(..., min_length=1, max_length=128)
    gateway_event_type: str = Field(..., min_length=1, max_length=64)
    amount_minor: int = Field(..., gt=0)
    currency_code: str = Field(..., min_length=3, max_length=3)
    status: str = Field(..., min_length=1, max_length=64)
    processed_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class PaymentTransactionListResponse(BaseModel):
    items: list[PaymentTransactionDTO]

    model_config = ConfigDict(extra="forbid")


class CreditLedgerEntryDTO(BaseModel):
    id: UUID
    entry_type: str = Field(..., min_length=1, max_length=64)
    credit_delta: int
    balance_after: int = Field(..., ge=0)
    reference_type: str = Field(..., min_length=1, max_length=64)
    reference_id: UUID
    metadata_json: dict
    created_by: str = Field(..., min_length=1, max_length=64)
    created_at: datetime

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class CreditLedgerListResponse(BaseModel):
    items: list[CreditLedgerEntryDTO]

    model_config = ConfigDict(extra="forbid")


class StudentBillingOverviewResponse(BaseModel):
    wallet: StudentCreditWalletDTO
    packages: list[CreditPackageDTO]
    recent_transactions: list[PaymentTransactionDTO] = Field(default_factory=list)
    recent_ledger_entries: list[CreditLedgerEntryDTO] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class StudentBillingCreateOrderRequest(BaseModel):
    package_code: str = Field(..., min_length=1, max_length=64)
    client_idempotency_key: str = Field(..., min_length=1, max_length=128)

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class StudentBillingCreateOrderResponse(BaseModel):
    payment_order_id: UUID
    merchant_order_ref: str = Field(..., min_length=1, max_length=64)

    gateway_provider: str = Field(..., min_length=1, max_length=64)
    gateway_order_id: str = Field(..., min_length=1, max_length=128)

    amount_minor: int = Field(..., gt=0)
    currency_code: str = Field(..., min_length=3, max_length=3)

    status: str = Field(..., min_length=1, max_length=64)
    expires_at: datetime | None = None

    package: CreditPackageDTO

    checkout_public_key: str = Field(..., min_length=1)
    checkout_prefill_name: str | None = Field(default=None, max_length=200)
    checkout_prefill_email: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class StudentBillingOrderStatusResponse(BaseModel):
    payment_order_id: UUID
    merchant_order_ref: str = Field(..., min_length=1, max_length=64)

    package_code: str = Field(..., min_length=1, max_length=64)
    credit_amount: int = Field(..., gt=0)

    amount_minor: int = Field(..., gt=0)
    currency_code: str = Field(..., min_length=3, max_length=3)

    status: str = Field(..., min_length=1, max_length=64)
    settled: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class RazorpayWebhookAckResponse(BaseModel):
    success: bool
    message: str = Field(..., min_length=1, max_length=255)

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )