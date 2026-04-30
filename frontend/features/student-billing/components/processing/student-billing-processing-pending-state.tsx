"use client";

type StudentBillingProcessingPendingStateProps = {
  creditAmount?: number;
  amountLabel?: string;
  packageCode?: string;
};

export function StudentBillingProcessingPendingState({
  creditAmount,
  amountLabel,
  packageCode,
}: StudentBillingProcessingPendingStateProps) {
  return (
    <div className="space-y-6">
      <div className="rounded-[1.5rem] border border-amber-300/70 bg-amber-50 p-6 text-amber-900 shadow-sm dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100">
        <div className="flex flex-col items-center text-center">
          <div className="mb-5 h-12 w-12 animate-pulse rounded-full border-4 border-current/25 border-t-current" />
          <h2 className="text-lg font-semibold">
            Awaiting backend confirmation
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 opacity-90">
            Your payment interaction may already be complete. Credits will be
            added only after backend verification confirms settlement.
          </p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-border bg-card p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Credits
          </p>
          <p className="mt-2 text-lg font-semibold text-foreground">
            {typeof creditAmount === "number" ? creditAmount : "—"}
          </p>
        </div>

        <div className="rounded-2xl border border-border bg-card p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Amount
          </p>
          <p className="mt-2 text-lg font-semibold text-foreground">
            {amountLabel ?? "—"}
          </p>
        </div>

        <div className="rounded-2xl border border-border bg-card p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Package
          </p>
          <p className="mt-2 text-lg font-semibold text-foreground">
            {packageCode ?? "—"}
          </p>
        </div>
      </div>

      <div className="rounded-[1.5rem] border border-border bg-card p-5">
        <p className="text-sm leading-6 text-muted-foreground">
          If you returned manually from a UPI app, refreshed the page, or
          experienced network delay, this verification page will continue
          checking your order safely against backend truth.
        </p>
      </div>
    </div>
  );
}