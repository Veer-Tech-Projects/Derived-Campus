"use client";

import { useMemo } from "react";

import type {
  BillingOverviewViewModel,
  BillingStatusBannerState,
} from "../../types/student-billing-view-models";
import { buildBillingWalletSummaryViewModel } from "../../utils/student-billing-package-view-models";
import { StudentBillingStatusBanner } from "../widgets/student-billing-status-banner";
import { StudentCreditBalanceCard } from "../widgets/student-credit-balance-card";
import { StudentBillingTransactionsList } from "./student-billing-transactions-list";
import { StudentBillingLedgerList } from "./student-billing-ledger-list";

const OVERVIEW_PREVIEW_LIMIT = 5;

type StudentBillingOverviewSectionProps = {
  viewModel: BillingOverviewViewModel;
  bannerState: BillingStatusBannerState;
  onJumpToSubscriptions: () => void;
};

export function StudentBillingOverviewSection({
  viewModel,
  bannerState,
  onJumpToSubscriptions,
}: StudentBillingOverviewSectionProps) {
  const walletSummary = buildBillingWalletSummaryViewModel({
    availableCredits: viewModel.wallet.available_credits,
    lifetimePurchased: viewModel.wallet.lifetime_credits_purchased,
    lifetimeConsumed: viewModel.wallet.lifetime_credits_consumed,
    updatedAt: viewModel.wallet.updated_at,
  });

  const previewTransactions = useMemo(
    () => viewModel.recentTransactions.slice(0, OVERVIEW_PREVIEW_LIMIT),
    [viewModel.recentTransactions],
  );

  const previewLedgerEntries = useMemo(
    () => viewModel.recentLedgerEntries.slice(0, OVERVIEW_PREVIEW_LIMIT),
    [viewModel.recentLedgerEntries],
  );

  return (
    <div className="space-y-6">
      <StudentBillingStatusBanner state={bannerState} />

      {viewModel.lowCreditState.isLowCredit ? (
        <div className="rounded-[1.5rem] border border-amber-300/70 bg-amber-50 p-4 text-amber-900 shadow-sm dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-semibold">
                Low credit balance detected
              </p>
              <p className="mt-1 text-sm leading-6 opacity-90">
                You have {viewModel.lowCreditState.remainingCredits} credits remaining. A proactive top-up can help avoid interruption later.
              </p>
            </div>
            <button
              type="button"
              onClick={onJumpToSubscriptions}
              className="inline-flex w-fit items-center justify-center rounded-2xl bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm hover:opacity-90"
            >
              View plans
            </button>
          </div>
        </div>
      ) : null}

      <StudentCreditBalanceCard viewModel={walletSummary} />

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-foreground">
            Recent payments
          </h3>
          <p className="text-xs text-muted-foreground">
            Backend-confirmed transaction snapshot
          </p>
        </div>
        <StudentBillingTransactionsList items={previewTransactions} />
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-foreground">
            Recent credit activity
          </h3>
          <p className="text-xs text-muted-foreground">
            Immutable billing ledger preview
          </p>
        </div>
        <StudentBillingLedgerList items={previewLedgerEntries} />
      </section>
    </div>
  );
}