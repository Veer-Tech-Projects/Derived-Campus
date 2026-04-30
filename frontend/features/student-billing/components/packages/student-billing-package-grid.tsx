"use client";

import type { BillingPackageCardViewModel } from "../../types/student-billing-view-models";
import { StudentBillingPackageCard } from "./student-billing-package-card";

type StudentBillingPackageGridProps = {
  packages: BillingPackageCardViewModel[];
  activePackageCode?: string | null;
  isBusy?: boolean;
  onBuyNow?: (packageCode: string) => void;
};

export function StudentBillingPackageGrid({
  packages,
  activePackageCode = null,
  isBusy = false,
  onBuyNow,
}: StudentBillingPackageGridProps) {
  return (
    <div className="hidden gap-5 lg:grid lg:grid-cols-3">
      {packages.map((item, index) => (
        <StudentBillingPackageCard
          key={item.packageId}
          packageViewModel={item}
          isHighlighted={index === 1}
          isBusy={isBusy && activePackageCode === item.packageCode}
          isActivePurchase={activePackageCode === item.packageCode}
          onBuyNow={onBuyNow}
        />
      ))}
    </div>
  );
}