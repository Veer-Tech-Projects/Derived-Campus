"""add_student_billing_domain

Revision ID: 6db4ece46e79
Revises: 33bc5cdf8e50
Create Date: 2026-04-21 17:01:34.348880+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "6db4ece46e79"
down_revision: Union[str, None] = "33bc5cdf8e50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# --- PostgreSQL ENUM TYPES (create once, reuse everywhere) ---

billing_gateway_provider_enum = postgresql.ENUM(
    "RAZORPAY",
    name="billing_gateway_provider_enum",
    create_type=False,
)

payment_webhook_processing_status_enum = postgresql.ENUM(
    "PENDING",
    "PROCESSED",
    "FAILED",
    name="payment_webhook_processing_status_enum",
    create_type=False,
)

payment_order_status_enum = postgresql.ENUM(
    "CREATED",
    "GATEWAY_ORDER_CREATED",
    "CHECKOUT_INITIATED",
    "SETTLED",
    "FAILED",
    "CANCELLED",
    "EXPIRED",
    name="payment_order_status_enum",
    create_type=False,
)

credit_ledger_entry_type_enum = postgresql.ENUM(
    "PURCHASE_CREDIT_GRANTED",
    "USAGE_DEBIT",
    "ADMIN_ADJUSTMENT_CREDIT",
    "ADMIN_ADJUSTMENT_DEBIT",
    "REFUND_REVERSAL_DEBIT",
    name="credit_ledger_entry_type_enum",
    create_type=False,
)

payment_transaction_status_enum = postgresql.ENUM(
    "RECEIVED",
    "PROCESSED",
    "FAILED_PROCESSING",
    name="payment_transaction_status_enum",
    create_type=False,
)


def upgrade() -> None:
    # --- Create shared enum types first ---
    bind = op.get_bind()

    billing_gateway_provider_enum.create(bind, checkfirst=True)
    payment_webhook_processing_status_enum.create(bind, checkfirst=True)
    payment_order_status_enum.create(bind, checkfirst=True)
    credit_ledger_entry_type_enum.create(bind, checkfirst=True)
    payment_transaction_status_enum.create(bind, checkfirst=True)

    # --- Tables ---
    op.create_table(
        "credit_packages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("package_code", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("credit_amount", sa.Integer(), nullable=False),
        sa.Column("price_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("display_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("char_length(currency_code) = 3", name="ck_credit_package_currency_code_len"),
        sa.CheckConstraint("credit_amount > 0", name="ck_credit_package_credit_amount_positive"),
        sa.CheckConstraint("price_minor > 0", name="ck_credit_package_price_minor_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("package_code", name="uq_credit_package_code"),
    )
    op.create_index(
        "idx_credit_package_active_display",
        "credit_packages",
        ["active", "display_order"],
        unique=False,
    )

    op.create_table(
        "payment_webhook_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("gateway_provider", billing_gateway_provider_enum, nullable=False),
        sa.Column("gateway_event_id", sa.String(length=128), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("signature_verified", sa.Boolean(), nullable=False),
        sa.Column(
            "payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("dedup_key", sa.String(length=128), nullable=False),
        sa.Column(
            "processing_status",
            payment_webhook_processing_status_enum,
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column("processing_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "processing_attempts >= 0",
            name="ck_payment_webhook_processing_attempts_non_negative",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedup_key", name="uq_payment_webhook_dedup_key"),
        sa.UniqueConstraint(
            "gateway_provider",
            "gateway_event_id",
            name="uq_payment_webhook_provider_event_id",
        ),
    )
    op.create_index(
        "idx_payment_webhook_status_created",
        "payment_webhook_events",
        ["processing_status", "created_at"],
        unique=False,
    )

    op.create_table(
        "payment_orders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("student_user_id", sa.UUID(), nullable=False),
        sa.Column("package_id", sa.UUID(), nullable=False),
        sa.Column("merchant_order_ref", sa.String(length=64), nullable=False),
        sa.Column("gateway_provider", billing_gateway_provider_enum, nullable=False),
        sa.Column("gateway_order_id", sa.String(length=128), nullable=True),
        sa.Column("client_idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column(
            "status",
            payment_order_status_enum,
            server_default=sa.text("'CREATED'"),
            nullable=False,
        ),
        sa.Column("gateway_receipt", sa.String(length=128), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount_minor > 0", name="ck_payment_order_amount_minor_positive"),
        sa.CheckConstraint("char_length(currency_code) = 3", name="ck_payment_order_currency_code_len"),
        sa.ForeignKeyConstraint(["package_id"], ["credit_packages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_user_id"], ["student_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gateway_order_id", name="uq_payment_order_gateway_order_id"),
        sa.UniqueConstraint("merchant_order_ref", name="uq_payment_order_merchant_ref"),
        sa.UniqueConstraint(
            "student_user_id",
            "client_idempotency_key",
            name="uq_payment_order_client_idempotency",
        ),
    )
    op.create_index(
        "idx_payment_order_status_created",
        "payment_orders",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_payment_order_student_created",
        "payment_orders",
        ["student_user_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "student_credit_ledger",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("student_user_id", sa.UUID(), nullable=False),
        sa.Column("entry_type", credit_ledger_entry_type_enum, nullable=False),
        sa.Column("credit_delta", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("reference_type", sa.String(length=64), nullable=False),
        sa.Column("reference_id", sa.UUID(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("balance_after >= 0", name="ck_credit_ledger_balance_after_non_negative"),
        sa.ForeignKeyConstraint(["student_user_id"], ["student_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_credit_ledger_idempotency_key"),
    )
    op.create_index(
        "idx_credit_ledger_reference",
        "student_credit_ledger",
        ["reference_type", "reference_id"],
        unique=False,
    )
    op.create_index(
        "idx_credit_ledger_student_created",
        "student_credit_ledger",
        ["student_user_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "student_credit_wallets",
        sa.Column("student_user_id", sa.UUID(), nullable=False),
        sa.Column("available_credits", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("lifetime_credits_purchased", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("lifetime_credits_consumed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("version", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("available_credits >= 0", name="ck_credit_wallet_available_non_negative"),
        sa.CheckConstraint(
            "lifetime_credits_consumed >= 0",
            name="ck_credit_wallet_lifetime_consumed_non_negative",
        ),
        sa.CheckConstraint(
            "lifetime_credits_purchased >= 0",
            name="ck_credit_wallet_lifetime_purchased_non_negative",
        ),
        sa.CheckConstraint("version >= 0", name="ck_credit_wallet_version_non_negative"),
        sa.ForeignKeyConstraint(["student_user_id"], ["student_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("student_user_id"),
    )

    op.create_table(
        "payment_transactions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("payment_order_id", sa.UUID(), nullable=False),
        sa.Column("gateway_payment_id", sa.String(length=128), nullable=False),
        sa.Column("gateway_signature", sa.Text(), nullable=True),
        sa.Column("gateway_event_type", sa.String(length=64), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column(
            "status",
            payment_transaction_status_enum,
            server_default=sa.text("'RECEIVED'"),
            nullable=False,
        ),
        sa.Column(
            "raw_gateway_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount_minor > 0", name="ck_payment_tx_amount_minor_positive"),
        sa.CheckConstraint("char_length(currency_code) = 3", name="ck_payment_tx_currency_code_len"),
        sa.ForeignKeyConstraint(["payment_order_id"], ["payment_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gateway_payment_id", name="uq_payment_tx_gateway_payment_id"),
    )
    op.create_index(
        "idx_payment_tx_event_created",
        "payment_transactions",
        ["gateway_event_type", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_payment_tx_gateway_payment_id",
        "payment_transactions",
        ["gateway_payment_id"],
        unique=False,
    )
    op.create_index(
        "idx_payment_tx_order_created",
        "payment_transactions",
        ["payment_order_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("idx_payment_tx_order_created", table_name="payment_transactions")
    op.drop_index("idx_payment_tx_gateway_payment_id", table_name="payment_transactions")
    op.drop_index("idx_payment_tx_event_created", table_name="payment_transactions")
    op.drop_table("payment_transactions")

    op.drop_table("student_credit_wallets")

    op.drop_index("idx_credit_ledger_student_created", table_name="student_credit_ledger")
    op.drop_index("idx_credit_ledger_reference", table_name="student_credit_ledger")
    op.drop_table("student_credit_ledger")

    op.drop_index("idx_payment_order_student_created", table_name="payment_orders")
    op.drop_index("idx_payment_order_status_created", table_name="payment_orders")
    op.drop_table("payment_orders")

    op.drop_index("idx_payment_webhook_status_created", table_name="payment_webhook_events")
    op.drop_table("payment_webhook_events")

    op.drop_index("idx_credit_package_active_display", table_name="credit_packages")
    op.drop_table("credit_packages")

    # Drop enum types after all dependent tables are gone
    payment_transaction_status_enum.drop(bind, checkfirst=True)
    credit_ledger_entry_type_enum.drop(bind, checkfirst=True)
    payment_order_status_enum.drop(bind, checkfirst=True)
    payment_webhook_processing_status_enum.drop(bind, checkfirst=True)
    billing_gateway_provider_enum.drop(bind, checkfirst=True)