from __future__ import annotations

"""
Student billing domain constants.

Important:
- DB remains source of truth for package pricing and credit_amount
- these constants are only stable symbolic identifiers / internal references
- do not hardcode commercial amounts here
"""

# --- Supported gateway providers ---
BILLING_GATEWAY_PROVIDER_RAZORPAY = "RAZORPAY"

# --- Razorpay event names we explicitly care about in Phase 1 ---
RAZORPAY_EVENT_ORDER_PAID = "order.paid"

# --- Internal ledger / reference typing ---
BILLING_REFERENCE_TYPE_PAYMENT_ORDER = "PAYMENT_ORDER"

# --- Internal created_by actors for immutable ledger / audit-friendly traces ---
BILLING_CREATED_BY_WEBHOOK = "SYSTEM_BILLING_WEBHOOK"
BILLING_CREATED_BY_RECONCILIATION = "SYSTEM_BILLING_RECONCILIATION"

# --- Stable package codes (commercial metadata still comes from DB rows) ---
CREDIT_PACKAGE_CODE_STARTER_10 = "STARTER_10"
CREDIT_PACKAGE_CODE_PRO_30 = "PRO_30"
CREDIT_PACKAGE_CODE_ELITE_70 = "ELITE_70"


# --- Reconciliation / Celery operational constants ---
BILLING_RECONCILIATION_QUEUE = "billing_queue"
BILLING_RECONCILIATION_SWEEP_TASK = (
    "app.domains.student_portal.student_billing.tasks.student_billing_reconciliation_tasks.run_billing_reconciliation_sweep"
)
BILLING_RECONCILIATION_SWEEP_LIMIT = 100
BILLING_RECONCILIATION_STALE_ORDER_MINUTES = 30
BILLING_RECONCILIATION_BEAT_MINUTES = 10


# --- College Filter search credit consumption constants ---
COLLEGE_FILTER_SEARCH_CREDIT_COST = 1
COLLEGE_FILTER_SEARCH_ENTITLEMENT_HOURS = 2

BILLING_REFERENCE_TYPE_COLLEGE_FILTER_SEARCH = "COLLEGE_FILTER_SEARCH"
BILLING_CREATED_BY_COLLEGE_FILTER_SEARCH = "SYSTEM_COLLEGE_FILTER_SEARCH"