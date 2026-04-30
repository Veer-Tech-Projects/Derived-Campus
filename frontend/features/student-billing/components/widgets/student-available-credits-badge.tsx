"use client";

import type { StudentAvailableCreditsBadgeViewModel } from "../../types/student-billing-view-models";

type StudentAvailableCreditsBadgeProps = {
  viewModel: StudentAvailableCreditsBadgeViewModel;
  compact?: boolean;
};

export function StudentAvailableCreditsBadge({
  viewModel,
  compact = false,
}: StudentAvailableCreditsBadgeProps) {
  const lowCreditTone = viewModel.lowCreditState.isLowCredit;

  return (
    <div
      className={[
        "inline-flex items-center gap-2 rounded-full border px-3 py-2 text-sm font-semibold shadow-sm",
        lowCreditTone
          ? "border-amber-300/70 bg-amber-50 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200"
          : "border-border bg-secondary text-foreground",
        compact ? "px-2.5 py-1.5 text-xs" : "",
      ].join(" ")}
      aria-label={`${viewModel.availableCredits} credits available`}
    >
      <span
        className={[
          "h-2.5 w-2.5 rounded-full",
          lowCreditTone ? "bg-amber-500" : "bg-primary",
        ].join(" ")}
      />
      <span>{viewModel.availableCredits} credits available</span>
    </div>
  );
}