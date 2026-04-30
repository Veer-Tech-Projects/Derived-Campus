from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Any

import httpx

from app.domains.student_portal.student_billing.config.student_billing_config import (
    student_billing_settings,
)
from app.domains.student_portal.student_billing.constants import (
    RAZORPAY_EVENT_ORDER_PAID,
)
from app.domains.student_portal.student_billing.exceptions import (
    InvalidWebhookSignatureError,
    StudentBillingError,
)


class RazorpayGatewayService:
    """
    Async gateway adapter for Razorpay.

    Design rules:
    - no DB access in this service
    - no student ownership logic here
    - no ledger mutation here
    - only external gateway communication + payload normalization
    """

    def __init__(self) -> None:
        self._settings = student_billing_settings

    @property
    def _auth_header(self) -> str:
        token = (
            f"{self._settings.RAZORPAY_KEY_ID}:{self._settings.RAZORPAY_KEY_SECRET}"
        ).encode("utf-8")
        encoded = base64.b64encode(token).decode("utf-8")
        return f"Basic {encoded}"

    async def _request_json(
        self,
        *,
        method: str,
        path: str,
        json_payload: dict[str, Any] | None = None,
        query_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        timeout = httpx.Timeout(15.0, connect=10.0)

        async with httpx.AsyncClient(
            base_url=self._settings.razorpay_api_base_url_normalized,
            timeout=timeout,
            headers={
                "Authorization": self._auth_header,
                "Content-Type": "application/json",
            },
        ) as client:
            try:
                response = await client.request(
                    method=method,
                    url=path,
                    json=json_payload,
                    params=query_params,
                )
            except httpx.HTTPError as exc:
                raise StudentBillingError(
                    f"Razorpay request failed for {method.upper()} {path}."
                ) from exc

        if response.status_code >= 400:
            raise StudentBillingError(
                f"Razorpay request failed for {method.upper()} {path} with status {response.status_code}."
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise StudentBillingError(
                f"Razorpay response for {method.upper()} {path} was not valid JSON."
            ) from exc

        if not isinstance(data, dict):
            raise StudentBillingError(
                f"Razorpay response for {method.upper()} {path} was not a JSON object."
            )

        return data

    async def create_order(
        self,
        *,
        amount_minor: int,
        currency_code: str,
        receipt: str,
        notes: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "amount": amount_minor,
            "currency": currency_code,
            "receipt": receipt,
        }

        if notes:
            payload["notes"] = notes

        data = await self._request_json(
            method="POST",
            path="/orders",
            json_payload=payload,
        )

        gateway_order_id = data.get("id")
        response_amount = data.get("amount")
        response_currency = data.get("currency")

        if not gateway_order_id:
            raise StudentBillingError(
                "Razorpay order creation response did not include an order id."
            )

        if response_amount != amount_minor:
            raise StudentBillingError(
                "Razorpay order amount does not match the requested amount."
            )

        if str(response_currency).upper() != currency_code.upper():
            raise StudentBillingError(
                "Razorpay order currency does not match the requested currency."
            )

        return data

    async def fetch_order(self, *, gateway_order_id: str) -> dict[str, Any]:
        data = await self._request_json(
            method="GET",
            path=f"/orders/{gateway_order_id}",
        )

        returned_id = str(data.get("id") or "").strip()
        if returned_id != gateway_order_id:
            raise StudentBillingError(
                "Razorpay fetch order response returned an unexpected order id."
            )

        return data

    async def fetch_payments_for_order(
        self,
        *,
        gateway_order_id: str,
    ) -> list[dict[str, Any]]:
        data = await self._request_json(
            method="GET",
            path=f"/orders/{gateway_order_id}/payments",
        )

        raw_items = data.get("items", [])
        if not isinstance(raw_items, list):
            raise StudentBillingError(
                "Razorpay order payments response did not include a valid items list."
            )

        payments: list[dict[str, Any]] = []
        for item in raw_items:
            if isinstance(item, dict):
                payments.append(item)

        return payments

    async def build_order_reconciliation_snapshot(
        self,
        *,
        gateway_order_id: str,
    ) -> dict[str, Any]:
        order = await self.fetch_order(gateway_order_id=gateway_order_id)
        payments = await self.fetch_payments_for_order(gateway_order_id=gateway_order_id)

        return {
            "order": order,
            "payments": payments,
            "paid_payment": self.select_preferred_paid_payment(payments),
        }

    @staticmethod
    def select_preferred_paid_payment(
        payments: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """
        Reconciliation selection policy:
        1. Only captured payments are eligible for settlement
        2. Authorized-only payments are NOT final for credit grant
        3. Ignore failed/refunded/created/authorized entries for settlement
        """
        for payment in payments:
            status = str(payment.get("status") or "").strip().lower()
            if status == "captured":
                payment_id = str(payment.get("id") or "").strip()
                if payment_id:
                    return payment

        return None

    def verify_webhook_signature(
        self,
        *,
        raw_body: bytes,
        signature_header: str | None,
    ) -> None:
        """
        Verifies Razorpay webhook signature in memory.

        This MUST happen before any billing persistence.
        """
        if not signature_header:
            raise InvalidWebhookSignatureError(
                "Missing Razorpay webhook signature header."
            )

        expected_signature = hmac.new(
            key=self._settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
            msg=raw_body,
            digestmod=hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, signature_header):
            raise InvalidWebhookSignatureError("Invalid Razorpay webhook signature.")

    @staticmethod
    def extract_event_type(payload: dict[str, Any]) -> str | None:
        value = payload.get("event")
        return str(value).strip() if value is not None else None

    @staticmethod
    def extract_gateway_order_id(payload: dict[str, Any]) -> str | None:
        order_entity = (
            payload.get("payload", {})
            .get("order", {})
            .get("entity", {})
        )
        value = order_entity.get("id")
        return str(value).strip() if value is not None else None

    @staticmethod
    def extract_gateway_payment_id(payload: dict[str, Any]) -> str | None:
        payment_entity = (
            payload.get("payload", {})
            .get("payment", {})
            .get("entity", {})
        )
        value = payment_entity.get("id")
        return str(value).strip() if value is not None else None

    @staticmethod
    def extract_amount_minor(payload: dict[str, Any]) -> int | None:
        payment_entity = (
            payload.get("payload", {})
            .get("payment", {})
            .get("entity", {})
        )

        value = payment_entity.get("amount")
        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def extract_currency_code(payload: dict[str, Any]) -> str | None:
        payment_entity = (
            payload.get("payload", {})
            .get("payment", {})
            .get("entity", {})
        )
        value = payment_entity.get("currency")
        return str(value).strip().upper() if value is not None else None

    @staticmethod
    def extract_gateway_event_id(payload: dict[str, Any]) -> str | None:
        value = payload.get("id")
        return str(value).strip() if value is not None else None

    def build_webhook_dedup_key(self, payload: dict[str, Any]) -> str:
        event_type = self.extract_event_type(payload) or "UNKNOWN_EVENT"
        gateway_event_id = self.extract_gateway_event_id(payload)
        gateway_payment_id = self.extract_gateway_payment_id(payload)
        gateway_order_id = self.extract_gateway_order_id(payload)

        if gateway_event_id:
            return f"RAZORPAY:{gateway_event_id}"

        if gateway_payment_id:
            return f"RAZORPAY:{event_type}:{gateway_payment_id}"

        if gateway_order_id:
            return f"RAZORPAY:{event_type}:{gateway_order_id}"

        raise StudentBillingError(
            "Unable to build webhook dedup key from Razorpay payload."
        )

    @staticmethod
    def is_order_paid_event(payload: dict[str, Any]) -> bool:
        return (RazorpayGatewayService.extract_event_type(payload) or "") == (
            RAZORPAY_EVENT_ORDER_PAID
        )


razorpay_gateway_service = RazorpayGatewayService()