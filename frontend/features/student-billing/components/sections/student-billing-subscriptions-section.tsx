"use client";

import type { BillingOverviewViewModel } from "../../types/student-billing-view-models";
import { StudentBillingPackageCarousel } from "../packages/student-billing-package-carousel";
import { StudentBillingPackageGrid } from "../packages/student-billing-package-grid";
import { StudentBillingStatusBanner } from "../widgets/student-billing-status-banner";
import type { BillingStatusBannerState } from "../../types/student-billing-view-models";

type StudentBillingSubscriptionsSectionProps = {
  viewModel: BillingOverviewViewModel;
  activePackageCode?: string | null;
  isBusy?: boolean;
  bannerState: BillingStatusBannerState;
  onBuyNow: (packageCode: string) => void;
};

export function StudentBillingSubscriptionsSection({
  viewModel,
  activePackageCode = null,
  isBusy = false,
  bannerState,
  onBuyNow,
}: StudentBillingSubscriptionsSectionProps) {
  return (
    <div className="space-y-6">
      <StudentBillingStatusBanner state={bannerState} />

      <div className="rounded-[2rem] border border-border bg-card p-5 shadow-sm sm:p-6">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-muted-foreground">
            Subscriptions
          </p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">
            Choose a plan that matches your exploration pace
          </h2>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            Plans are rendered from backend package data, while settlement and wallet updates continue to follow backend-confirmed billing truth.
          </p>
        </div>
      </div>

      <StudentBillingPackageGrid
        packages={viewModel.packages}
        activePackageCode={activePackageCode}
        isBusy={isBusy}
        onBuyNow={onBuyNow}
      />

      <StudentBillingPackageCarousel
        packages={viewModel.packages}
        activePackageCode={activePackageCode}
        isBusy={isBusy}
        onBuyNow={onBuyNow}
      />
    </div>
  );
}