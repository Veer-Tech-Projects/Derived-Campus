import type {
  BillingPackageBenefit,
  BillingPackageCode,
} from "../types/student-billing-view-models";

export const STUDENT_BILLING_QUERY_KEYS = {
  overview: ["student-billing-overview"] as const,
  packages: ["student-billing-packages"] as const,
  transactions: (limit: number) =>
    ["student-billing-transactions", { limit }] as const,
  ledger: (limit: number) => ["student-billing-ledger", { limit }] as const,
  orderStatus: (paymentOrderId: string) =>
    ["student-billing-order-status", paymentOrderId] as const,
} as const;

export const STUDENT_BILLING_STORAGE_KEYS = {
  purchaseSession: "derived-campus.student-billing.purchase-session.v1",
} as const;

export const STUDENT_BILLING_POLLING = {
  initialIntervalMs: 1000,
  backoffMultiplier: 1.8,
  maxIntervalMs: 5000,
  hardTimeoutMs: 3 * 60 * 1000,
} as const;

export const STUDENT_BILLING_LOW_CREDIT_THRESHOLD = 5;

export const STUDENT_BILLING_HISTORY_LIMITS = {
  overviewPreview: 5,
  tabDefault: 20,
  tabMax: 100,
} as const;

export const STUDENT_BILLING_PACKAGE_CODES = {
  starter: "STARTER_10",
  pro: "PRO_30",
  elite: "ELITE_70",
} as const satisfies Record<string, BillingPackageCode>;

export const STUDENT_BILLING_FINAL_FAILURE_STATUSES = new Set([
  "FAILED",
  "CANCELLED",
  "EXPIRED",
]);

export const STUDENT_BILLING_ACTIVE_ORDER_STATUSES = new Set([
  "CREATED",
  "GATEWAY_ORDER_CREATED",
  "CHECKOUT_INITIATED",
]);

export const STUDENT_BILLING_SETTLED_STATUS = "SETTLED";


export const STUDENT_BILLING_PACKAGE_BENEFITS: Record<
  BillingPackageCode,
  BillingPackageBenefit[]
> = {
  STARTER_10: [
    {
      id: "starter-guided",
      label: "Built for getting started with guided college exploration",
    },
    {
      id: "starter-searches",
      label: "Supports repeated College Filter usage with low-friction top-ups",
    },
    {
      id: "starter-clarity",
      label: "Good fit for first-time cutoff and projection discovery",
    },
  ],
  PRO_30: [
    {
      id: "pro-research",
      label: "Designed for deeper comparison across more college options",
    },
    {
      id: "pro-sync",
      label: "Better for repeated shortlist refinement and projection checks",
    },
    {
      id: "pro-confidence",
      label: "Balanced plan for active counselling decision-making",
    },
  ],
  ELITE_70: [
    {
      id: "elite-volume",
      label: "Best for broader multi-path college exploration at higher volume",
    },
    {
      id: "elite-iteration",
      label: "Supports heavier iterative filtering and shortlist revision",
    },
    {
      id: "elite-power",
      label: "Made for students who want sustained billing headroom",
    },
  ],
};