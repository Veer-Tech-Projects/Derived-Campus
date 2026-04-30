"use client";

type StudentBillingProcessingSuccessStateProps = {
  creditAmount?: number;
  amountLabel?: string;
  countdownSeconds: number;
  onGoNow: () => void;
};

export function StudentBillingProcessingSuccessState({
  creditAmount,
  amountLabel,
  countdownSeconds,
  onGoNow,
}: StudentBillingProcessingSuccessStateProps) {
  return (
    <div className="space-y-6">
      <div className="rounded-[1.5rem] border border-emerald-300/70 bg-emerald-50 p-6 text-emerald-900 shadow-sm dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-100">
        <div className="flex flex-col items-center text-center">
          <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/15 text-2xl font-bold">
            ✓
          </div>
          <h2 className="text-xl font-semibold">Credits added successfully</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 opacity-90">
            Your payment has been verified by the backend and your wallet is now
            updated.
          </p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-2xl border border-border bg-card p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Credits granted
          </p>
          <p className="mt-2 text-2xl font-semibold text-foreground">
            {typeof creditAmount === "number" ? creditAmount : "—"}
          </p>
        </div>

        <div className="rounded-2xl border border-border bg-card p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Charged amount
          </p>
          <p className="mt-2 text-2xl font-semibold text-foreground">
            {amountLabel ?? "—"}
          </p>
        </div>
      </div>

      <div className="rounded-[1.5rem] border border-border bg-card p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-foreground">
              Redirecting back in {countdownSeconds} second
              {countdownSeconds === 1 ? "" : "s"}.
            </p>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              You can continue immediately or wait for the automatic redirect.
            </p>
          </div>

          <button
            type="button"
            onClick={onGoNow}
            className="inline-flex items-center justify-center rounded-2xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm transition-opacity hover:opacity-90"
          >
            Go now
          </button>
        </div>
      </div>
    </div>
  );
}