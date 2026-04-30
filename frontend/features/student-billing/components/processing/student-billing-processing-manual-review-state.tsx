"use client";

type StudentBillingProcessingManualReviewStateProps = {
  onRetry: () => void;
  onGoBack: () => void;
};

export function StudentBillingProcessingManualReviewState({
  onRetry,
  onGoBack,
}: StudentBillingProcessingManualReviewStateProps) {
  return (
    <div className="space-y-6">
      <div className="rounded-[1.5rem] border border-amber-300/70 bg-amber-50 p-6 text-amber-900 shadow-sm dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100">
        <h2 className="text-lg font-semibold">Still verifying your payment</h2>
        <p className="mt-2 text-sm leading-6 opacity-90">
          Verification is taking longer than expected. Please do not make a
          duplicate payment blindly. You can re-check the status or return to
          billing safely.
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center justify-center rounded-2xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm transition-opacity hover:opacity-90"
        >
          Re-check status
        </button>

        <button
          type="button"
          onClick={onGoBack}
          className="inline-flex items-center justify-center rounded-2xl border border-border bg-card px-4 py-2.5 text-sm font-semibold text-foreground shadow-sm"
        >
          Back to account
        </button>
      </div>
    </div>
  );
}