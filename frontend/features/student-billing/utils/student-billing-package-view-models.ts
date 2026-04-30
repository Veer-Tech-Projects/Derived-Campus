import {
  STUDENT_BILLING_PACKAGE_BENEFITS,
  STUDENT_BILLING_PACKAGE_CODES,
} from "../constants/student-billing-ui";
import type { CreditPackageDTO } from "../types/student-billing-contracts";
import type {
  BillingLowCreditState,
  BillingPackageCardViewModel,
  BillingPackageCode,
  BillingWalletSummaryViewModel,
} from "../types/student-billing-view-models";
import { STUDENT_BILLING_LOW_CREDIT_THRESHOLD } from "../constants/student-billing-ui";
import { formatRelativeSyncLabel } from "./student-billing-formatters";

function asKnownPackageCode(value: string): BillingPackageCode | null {
  const knownCodes = new Set<string>([
    STUDENT_BILLING_PACKAGE_CODES.starter,
    STUDENT_BILLING_PACKAGE_CODES.pro,
    STUDENT_BILLING_PACKAGE_CODES.elite,
  ]);

  return knownCodes.has(value) ? (value as BillingPackageCode) : null;
}

function getBadgeLabel(packageCode: string): string | undefined {
  switch (packageCode) {
    case STUDENT_BILLING_PACKAGE_CODES.starter:
      return "Starter";
    case STUDENT_BILLING_PACKAGE_CODES.pro:
      return "Popular";
    case STUDENT_BILLING_PACKAGE_CODES.elite:
      return "Power";
    default:
      return undefined;
  }
}

function getHelperLabel(packageCode: string): string | undefined {
  switch (packageCode) {
    case STUDENT_BILLING_PACKAGE_CODES.starter:
      return "Great for first-time guided usage";
    case STUDENT_BILLING_PACKAGE_CODES.pro:
      return "Balanced for active counselling exploration";
    case STUDENT_BILLING_PACKAGE_CODES.elite:
      return "Best for heavier repeated usage";
    default:
      return undefined;
  }
}

export function buildBillingPackageCardViewModel(
  value: CreditPackageDTO,
): BillingPackageCardViewModel {
  const knownPackageCode = asKnownPackageCode(value.package_code);
  const benefits =
    knownPackageCode !== null
      ? STUDENT_BILLING_PACKAGE_BENEFITS[knownPackageCode]
      : [
          {
            id: `${value.package_code}-default-benefit`,
            label: "Backed by secure, backend-verified credit purchase flow",
          },
        ];

  return {
    packageId: value.id,
    packageCode: value.package_code,
    displayName: value.display_name,
    description: value.description,
    creditAmount: value.credit_amount,
    priceMinor: value.price_minor,
    currencyCode: value.currency_code,
    displayOrder: value.display_order,
    badgeLabel: getBadgeLabel(value.package_code),
    helperLabel: getHelperLabel(value.package_code),
    benefits,
  };
}

export function buildBillingPackageCardViewModels(
  values: CreditPackageDTO[],
): BillingPackageCardViewModel[] {
  return [...values]
    .sort((left, right) => left.display_order - right.display_order)
    .map(buildBillingPackageCardViewModel);
}

export function buildBillingLowCreditState(
  availableCredits: number,
): BillingLowCreditState {
  return {
    isLowCredit: availableCredits <= STUDENT_BILLING_LOW_CREDIT_THRESHOLD,
    remainingCredits: availableCredits,
    threshold: STUDENT_BILLING_LOW_CREDIT_THRESHOLD,
  };
}

export function buildBillingWalletSummaryViewModel(input: {
  availableCredits: number;
  lifetimePurchased: number;
  lifetimeConsumed: number;
  updatedAt: string;
}): BillingWalletSummaryViewModel {
  return {
    availableCredits: input.availableCredits,
    lifetimePurchased: input.lifetimePurchased,
    lifetimeConsumed: input.lifetimeConsumed,
    updatedAtLabel: formatRelativeSyncLabel(input.updatedAt),
  };
}