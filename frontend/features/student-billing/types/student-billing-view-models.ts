import type {
  CreditLedgerEntryDTO,
  CreditPackageDTO,
  PaymentTransactionDTO,
  StudentCreditWalletDTO,
} from "./student-billing-contracts";

export type BillingPackageCode = "STARTER_10" | "PRO_30" | "ELITE_70";

export type BillingPurchaseLifecycleStatus =
  | "idle"
  | "creating_order"
  | "opening_checkout"
  | "awaiting_backend_confirmation"
  | "settled"
  | "failed"
  | "cancelled"
  | "expired"
  | "pending_manual_verification";

export type BillingPurchaseSessionSnapshot = {
  paymentOrderId: string;
  merchantOrderRef: string;
  packageCode: string;
  clientIdempotencyKey: string;
  createdAt: string;
  lastKnownStatus: BillingPurchaseLifecycleStatus | string;
};

export type BillingStatusBannerTone =
  | "neutral"
  | "info"
  | "success"
  | "warning"
  | "danger";

export type BillingStatusBannerState = {
  visible: boolean;
  tone: BillingStatusBannerTone;
  title: string;
  description?: string;
};

export type BillingLowCreditState = {
  isLowCredit: boolean;
  remainingCredits: number;
  threshold: number;
};

export type BillingPackageBenefit = {
  id: string;
  label: string;
};

export type BillingPackageCardViewModel = {
  packageId: string;
  packageCode: BillingPackageCode | string;
  displayName: string;
  description: string | null;
  creditAmount: number;
  priceMinor: number;
  currencyCode: string;
  displayOrder: number;
  badgeLabel?: string;
  helperLabel?: string;
  benefits: BillingPackageBenefit[];
};

export type BillingOverviewViewModel = {
  wallet: StudentCreditWalletDTO;
  lowCreditState: BillingLowCreditState;
  recentTransactions: PaymentTransactionDTO[];
  recentLedgerEntries: CreditLedgerEntryDTO[];
  packages: BillingPackageCardViewModel[];
};

export type StudentAvailableCreditsBadgeViewModel = {
  availableCredits: number;
  lowCreditState: BillingLowCreditState;
};

export type BillingHistoryItemKind = "transaction" | "ledger";

export type BillingHistoryItemViewModel = {
  id: string;
  kind: BillingHistoryItemKind;
  title: string;
  subtitle: string;
  meta: string;
  createdAt: string;
};

export type BillingWalletSummaryViewModel = {
  availableCredits: number;
  lifetimePurchased: number;
  lifetimeConsumed: number;
  updatedAtLabel: string;
};