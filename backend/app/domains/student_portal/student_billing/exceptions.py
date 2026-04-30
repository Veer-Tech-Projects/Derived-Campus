from __future__ import annotations


class StudentBillingError(Exception):
    """Base billing domain exception."""


class CreditPackageNotFoundError(StudentBillingError):
    """Raised when a requested credit package does not exist."""


class InactiveCreditPackageError(StudentBillingError):
    """Raised when a requested credit package exists but is not active."""


class PaymentOrderNotFoundError(StudentBillingError):
    """Raised when a payment order cannot be resolved."""


class PaymentOrderOwnershipError(StudentBillingError):
    """Raised when a student tries to access an order they do not own."""


class PaymentOrderAlreadySettledError(StudentBillingError):
    """Raised when settlement is attempted for an already-settled order."""


class PaymentOrderAmountMismatchError(StudentBillingError):
    """Raised when provider-reported amount does not match internal order amount."""


class PaymentOrderCurrencyMismatchError(StudentBillingError):
    """Raised when provider-reported currency does not match internal order currency."""


class DuplicateLedgerGrantError(StudentBillingError):
    """Raised when a duplicate purchase credit grant is attempted."""


class InvalidWebhookSignatureError(StudentBillingError):
    """Raised when webhook signature verification fails."""


class WebhookDedupConflictError(StudentBillingError):
    """Raised when a verified webhook event duplicates an already-processed event."""

class InsufficientCreditsError(StudentBillingError):
    """Raised when a student does not have enough credits for a billable action."""

    def __init__(
        self,
        message: str = "Insufficient credits.",
        *,
        available_credits: int = 0,
        required_credits: int = 1,
    ) -> None:
        super().__init__(message)
        self.available_credits = available_credits
        self.required_credits = required_credits