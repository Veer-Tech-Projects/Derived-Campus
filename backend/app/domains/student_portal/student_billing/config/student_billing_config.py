from __future__ import annotations

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class StudentBillingSettings(BaseSettings):
    """
    Student billing runtime settings.

    Design rules:
    - billing config is isolated from student auth config
    - secrets and environment-dependent values come only from env
    - package pricing does NOT belong here; DB credit_packages remains SOT
    - webhook verification uses the raw shared secret from env
    """

    RAZORPAY_KEY_ID: str
    RAZORPAY_KEY_SECRET: str
    RAZORPAY_WEBHOOK_SECRET: str

    RAZORPAY_API_BASE_URL: str = "https://api.razorpay.com/v1"
    BILLING_DEFAULT_CURRENCY: str = "INR"

    BILLING_MERCHANT_ORDER_PREFIX: str = "DC"
    BILLING_PAYMENT_ORDER_EXPIRY_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @computed_field
    @property
    def razorpay_api_base_url_normalized(self) -> str:
        return self.RAZORPAY_API_BASE_URL.rstrip("/")

    @computed_field
    @property
    def billing_default_currency_normalized(self) -> str:
        return self.BILLING_DEFAULT_CURRENCY.strip().upper()

    @computed_field
    @property
    def billing_merchant_order_prefix_normalized(self) -> str:
        return self.BILLING_MERCHANT_ORDER_PREFIX.strip().upper()


student_billing_settings = StudentBillingSettings()