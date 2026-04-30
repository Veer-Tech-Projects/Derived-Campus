"use client";

import type { BillingPackageCardViewModel } from "../../types/student-billing-view-models";
import { formatCreditsLabel, formatCurrencyMinor } from "../../utils/student-billing-formatters";

type StudentBillingPackageCardProps = {
  packageViewModel: BillingPackageCardViewModel;
  isHighlighted?: boolean;
  isBusy?: boolean;
  isActivePurchase?: boolean;
  onBuyNow?: (packageCode: string) => void;
};

export function StudentBillingPackageCard({
  packageViewModel,
  isHighlighted = false,
  isBusy = false,
  isActivePurchase = false,
  onBuyNow,
}: StudentBillingPackageCardProps) {
  const {
    packageCode,
    displayName,
    description,
    creditAmount,
    priceMinor,
    currencyCode,
    badgeLabel,
    helperLabel,
    benefits,
  } = packageViewModel;

  return (
    <article
      className={[
        "relative flex h-full min-h-[25.5rem] flex-col rounded-[2rem] border bg-card p-5 shadow-sm transition-transform duration-300 sm:min-h-[26rem]",
        isHighlighted
          ? "border-primary/35 shadow-md ring-1 ring-primary/15"
          : "border-border hover:-translate-y-0.5",
      ].join(" ")}
    >
      <div className="flex min-h-8 items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {badgeLabel ? (
            <span className="inline-flex rounded-full bg-primary/12 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">
              {badgeLabel}
            </span>
          ) : null}
          {isActivePurchase ? (
            <span className="inline-flex rounded-full bg-secondary px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-foreground">
              Active
            </span>
          ) : null}
        </div>
      </div>

      <div className="mt-4 min-h-[4.75rem]">
        <h3 className="text-xl font-semibold tracking-tight text-foreground">
          {displayName}
        </h3>
        <p className="mt-1 text-sm leading-6 text-muted-foreground">
          {description ?? helperLabel ?? "Backend-verified credit package"}
        </p>
      </div>

      <div className="mt-5 min-h-[4.5rem] space-y-2">
        <p className="text-3xl font-semibold tracking-tight text-foreground">
          {formatCurrencyMinor(priceMinor, currencyCode)}
        </p>
        <p className="text-sm font-medium text-primary">
          {formatCreditsLabel(creditAmount)}
        </p>
      </div>

      <ul className="mt-5 flex min-h-[9.5rem] flex-1 flex-col gap-3">
        {benefits.map((benefit) => (
          <li
            key={benefit.id}
            className="flex items-start gap-3 text-sm leading-6 text-foreground"
          >
            <span className="mt-1 inline-block h-2 w-2 rounded-full bg-primary" />
            <span>{benefit.label}</span>
          </li>
        ))}
      </ul>

      <div className="mt-6">
        <button
          type="button"
          onClick={() => onBuyNow?.(packageCode)}
          disabled={isBusy}
          className={[
            "inline-flex w-full items-center justify-center rounded-2xl px-4 py-3 text-sm font-semibold transition-all",
            isBusy
              ? "cursor-not-allowed bg-secondary text-muted-foreground"
              : "bg-primary text-primary-foreground shadow-sm hover:opacity-90",
          ].join(" ")}
        >
          {isBusy ? "Processing…" : `Buy ${displayName}`}
        </button>
      </div>
    </article>
  );
}