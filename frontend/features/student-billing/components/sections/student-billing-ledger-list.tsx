"use client";

import type { CreditLedgerEntryDTO } from "../../types/student-billing-contracts";
import { formatDateTimeLabel } from "../../utils/student-billing-formatters";
import { StudentBillingEmptyState } from "../widgets/student-billing-empty-state";

type StudentBillingLedgerListProps = {
  items: CreditLedgerEntryDTO[];
};

export function StudentBillingLedgerList({
  items,
}: StudentBillingLedgerListProps) {
  if (items.length === 0) {
    return (
      <StudentBillingEmptyState
        title="No credit activity yet"
        description="Your billing ledger will appear here after backend-verified credit purchases or future usage events."
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
                {item.entry_type}
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                Credit delta: {item.credit_delta > 0 ? `+${item.credit_delta}` : item.credit_delta}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Balance after: {item.balance_after}
              </p>
            </div>

            <div className="flex flex-col gap-2 sm:items-end">
              <span className="inline-flex w-fit rounded-full bg-secondary px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-foreground">
                {item.reference_type}
              </span>
              <p className="text-xs text-muted-foreground">
                {formatDateTimeLabel(item.created_at)}
              </p>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}