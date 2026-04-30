"use client";

import type { PaymentTransactionDTO } from "../../types/student-billing-contracts";
import { formatCurrencyMinor, formatDateTimeLabel } from "../../utils/student-billing-formatters";
import { StudentBillingEmptyState } from "../widgets/student-billing-empty-state";

type StudentBillingTransactionsListProps = {
  items: PaymentTransactionDTO[];
};

export function StudentBillingTransactionsList({
  items,
}: StudentBillingTransactionsListProps) {
  if (items.length === 0) {
    return (
      <StudentBillingEmptyState
        title="No payment history yet"
        description="Your completed or pending billing transactions will appear here once you start purchasing credits."
      />
    );
  }

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <article
          key={item.id}
          className="rounded-[1.5rem] border border-border bg-card p-4 shadow-sm"
        >
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-foreground">
                {formatCurrencyMinor(item.amount_minor, item.currency_code)}
              </p>
              <p className="mt-1 break-all text-xs text-muted-foreground">
                Payment ID: {item.gateway_payment_id}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Event: {item.gateway_event_type}
              </p>
            </div>

            <div className="flex flex-col gap-2 sm:items-end">
              <span className="inline-flex w-fit rounded-full bg-secondary px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-foreground">
                {item.status}
              </span>
              <p className="text-xs text-muted-foreground">
                {formatDateTimeLabel(item.processed_at ?? item.created_at)}
              </p>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}