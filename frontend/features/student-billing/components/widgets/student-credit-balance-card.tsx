"use client";

import type { BillingWalletSummaryViewModel } from "../../types/student-billing-view-models";
import { StudentAvailableCreditsBadge } from "./student-available-credits-badge";
import { buildBillingLowCreditState } from "../../utils/student-billing-package-view-models";

type StudentCreditBalanceCardProps = {
  viewModel: BillingWalletSummaryViewModel;
};

export function StudentCreditBalanceCard({
  viewModel,
}: StudentCreditBalanceCardProps) {
  return (
    <section className="rounded-[2rem] border border-border bg-card p-5 shadow-sm sm:p-6">
      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-muted-foreground">
              Wallet
            </p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
              {viewModel.availableCredits} credits
            </h2>
            <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">
              Your billing wallet reflects backend-verified credit purchases and
              remains the trusted balance for future feature usage.
            </p>
          </div>

          <StudentAvailableCreditsBadge
            viewModel={{
              availableCredits: viewModel.availableCredits,
              lowCreditState: buildBillingLowCreditState(
                viewModel.availableCredits,
              ),
            }}
          />
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-2xl border border-border bg-secondary/60 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Available
            </p>
            <p className="mt-2 text-xl font-semibold text-foreground">
              {viewModel.availableCredits}
            </p>
          </div>

          <div className="rounded-2xl border border-border bg-secondary/60 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Lifetime purchased
            </p>
            <p className="mt-2 text-xl font-semibold text-foreground">
              {viewModel.lifetimePurchased}
            </p>
          </div>

          <div className="rounded-2xl border border-border bg-secondary/60 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Lifetime consumed
            </p>
            <p className="mt-2 text-xl font-semibold text-foreground">
              {viewModel.lifetimeConsumed}
            </p>
          </div>
        </div>

        <p className="text-xs text-muted-foreground">
          {viewModel.updatedAtLabel}
        </p>
      </div>
    </section>
  );
}