"use client";

import type { BillingStatusBannerState } from "../../types/student-billing-view-models";

type StudentBillingStatusBannerProps = {
  state: BillingStatusBannerState;
};

function toneClasses(tone: BillingStatusBannerState["tone"]): string {
  switch (tone) {
    case "success":
      return "border-emerald-300/70 bg-emerald-50 text-emerald-900 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-100";
    case "warning":
      return "border-amber-300/70 bg-amber-50 text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100";
    case "danger":
      return "border-rose-300/70 bg-rose-50 text-rose-900 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-100";
    case "info":
      return "border-primary/25 bg-primary/10 text-foreground";
    default:
      return "border-border bg-secondary text-foreground";
  }
}

export function StudentBillingStatusBanner({
  state,
}: StudentBillingStatusBannerProps) {
  if (!state.visible) {
    return null;
  }

  return (
    <div
      className={`rounded-3xl border p-4 shadow-sm ${toneClasses(state.tone)}`}
      role="status"
      aria-live="polite"
    >
      <div className="flex flex-col gap-1">
        <p className="text-sm font-semibold">{state.title}</p>
        {state.description ? (
          <p className="text-sm leading-6 opacity-90">{state.description}</p>
        ) : null}
      </div>
    </div>
  );
}