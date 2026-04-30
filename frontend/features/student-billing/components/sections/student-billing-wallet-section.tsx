"use client";

import type { BillingOverviewViewModel } from "../../types/student-billing-view-models";
import { buildBillingWalletSummaryViewModel } from "../../utils/student-billing-package-view-models";
import { StudentCreditBalanceCard } from "../widgets/student-credit-balance-card";

type StudentBillingWalletSectionProps = {
  viewModel: BillingOverviewViewModel;
};

export function StudentBillingWalletSection({
  viewModel,
}: StudentBillingWalletSectionProps) {
  const walletSummary = buildBillingWalletSummaryViewModel({
    availableCredits: viewModel.wallet.available_credits,
    lifetimePurchased: viewModel.wallet.lifetime_credits_purchased,
    lifetimeConsumed: viewModel.wallet.lifetime_credits_consumed,
    updatedAt: viewModel.wallet.updated_at,
  });

  return (
    <div className="space-y-6">
      <StudentCreditBalanceCard viewModel={walletSummary} />

      <div className="rounded-[2rem] border border-border bg-card p-5 shadow-sm sm:p-6">
        <h3 className="text-lg font-semibold text-foreground">
          Wallet guidance
        </h3>
        <div className="mt-3 space-y-3 text-sm leading-6 text-muted-foreground">
          <p>
            Available credits are always shown from backend billing state, not from client-side assumptions.
          </p>
          <p>
            When a credit purchase settles, this section updates through query invalidation and backend refetch, so a manual page refresh should not be necessary.
          </p>
          <p>
            If a payment is still pending verification, the wallet remains unchanged until settlement is confirmed by the backend.
          </p>
        </div>
      </div>
    </div>
  );
}