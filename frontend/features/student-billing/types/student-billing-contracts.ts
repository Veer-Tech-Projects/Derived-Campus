export type CreditPackageDTO = {
  id: string;
  package_code: string;
  display_name: string;
  description: string | null;
  credit_amount: number;
  price_minor: number;
  currency_code: string;
  active: boolean;
  display_order: number;
};

export type CreditPackageListResponse = {
  items: CreditPackageDTO[];
};

export type StudentCreditWalletDTO = {
  available_credits: number;
  lifetime_credits_purchased: number;
  lifetime_credits_consumed: number;
  updated_at: string;
};

export type PaymentTransactionDTO = {
  id: string;
  payment_order_id: string;
  gateway_payment_id: string;
  gateway_event_type: string;
  amount_minor: number;
  currency_code: string;
  status: string;
  processed_at: string | null;
  created_at: string;
};

export type PaymentTransactionListResponse = {
  items: PaymentTransactionDTO[];
};

export type CreditLedgerEntryDTO = {
  id: string;
  entry_type: string;
  credit_delta: number;
  balance_after: number;
  reference_type: string;
  reference_id: string;
  metadata_json: Record<string, unknown>;
  created_by: string;
  created_at: string;
};

export type CreditLedgerListResponse = {
  items: CreditLedgerEntryDTO[];
};

export type StudentBillingOverviewResponse = {
  wallet: StudentCreditWalletDTO;
  packages: CreditPackageDTO[];
  recent_transactions: PaymentTransactionDTO[];
  recent_ledger_entries: CreditLedgerEntryDTO[];
};

export type StudentBillingCreateOrderRequest = {
  package_code: string;
  client_idempotency_key: string;
};

export type StudentBillingCreateOrderResponse = {
  payment_order_id: string;
  merchant_order_ref: string;
  gateway_provider: string;
  gateway_order_id: string;
  amount_minor: number;
  currency_code: string;
  status: string;
  expires_at: string | null;
  package: CreditPackageDTO;
  checkout_public_key: string;
  checkout_prefill_name: string | null;
  checkout_prefill_email: string | null;
};

export type StudentBillingOrderStatusResponse = {
  payment_order_id: string;
  merchant_order_ref: string;
  package_code: string;
  credit_amount: number;
  amount_minor: number;
  currency_code: string;
  status: string;
  settled: boolean;
  created_at: string;
  updated_at: string;
};

export type RazorpayWebhookAckResponse = {
  success: boolean;
  message: string;
};