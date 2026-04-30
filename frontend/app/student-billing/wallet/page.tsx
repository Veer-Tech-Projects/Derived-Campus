"use client";

import { useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";

import { useStudentAuth } from "@/features/student-auth/hooks/use-student-auth";
import { studentAuthRouteConfig } from "@/features/student-auth/config/student-auth-route-config";
import { StudentBillingPageShell } from "@/features/student-billing/components/layout/student-billing-page-shell";
import { StudentBillingWalletSection } from "@/features/student-billing/components/sections/student-billing-wallet-section";
import { StudentAvailableCreditsBadge } from "@/features/student-billing/components/widgets/student-available-credits-badge";
import { useStudentBillingOverview } from "@/features/student-billing/hooks/use-student-billing-overview";
import type { StudentAvailableCreditsBadgeViewModel } from "@/features/student-billing/types/student-billing-view-models";

export default function StudentBillingWalletPage() {
  const router = useRouter();
  const { status, accessToken } = useStudentAuth();

  const overviewQuery = useStudentBillingOverview({
    accessToken,
    enabled: status === "authenticated_completed" && Boolean(accessToken),
  });

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace(studentAuthRouteConfig.loginPath);
      return;
    }

    if (status === "authenticated_pending_onboarding") {
      router.replace(studentAuthRouteConfig.onboardingPath);
    }
  }, [router, status]);

  const availableCreditsBadgeViewModel =
    useMemo<StudentAvailableCreditsBadgeViewModel | null>(() => {
      if (!overviewQuery.viewModel) {
        return null;
      }

      return {
        availableCredits: overviewQuery.viewModel.wallet.available_credits,
        lowCreditState: overviewQuery.viewModel.lowCreditState,
      };
    }, [overviewQuery.viewModel]);

  if (status === "unknown" || status === "refreshing") {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (
    status === "unauthenticated" ||
    status === "authenticated_pending_onboarding"
  ) {
    return null;
  }

  return (
    <StudentBillingPageShell
      title="Wallet"
      description="Review your current credit balance and the backend-verified totals that define your billing wallet."
      backHref="/student-account?tab=billing"
      backLabel="Back to billing"
      headerSlot={
        availableCreditsBadgeViewModel ? (
          <StudentAvailableCreditsBadge
            viewModel={availableCreditsBadgeViewModel}
          />
        ) : null
      }
    >
      {overviewQuery.isLoading ? (
        <div className="rounded-[2rem] border border-border bg-card p-6 shadow-sm">
          <div className="flex items-center justify-center py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        </div>
      ) : null}

      {!overviewQuery.isLoading && overviewQuery.isError ? (
        <div className="rounded-[2rem] border border-border bg-card p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-foreground">
            Unable to load wallet
          </h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {overviewQuery.error?.message ??
              "Wallet information could not be loaded right now."}
          </p>
        </div>
      ) : null}

      {!overviewQuery.isLoading &&
      !overviewQuery.isError &&
      overviewQuery.viewModel ? (
        <StudentBillingWalletSection viewModel={overviewQuery.viewModel} />
      ) : null}

      {!overviewQuery.isLoading &&
      !overviewQuery.isError &&
      !overviewQuery.viewModel ? (
        <div className="rounded-[2rem] border border-border bg-card p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-foreground">
            Wallet is unavailable
          </h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            We could not build the wallet page from backend billing data.
          </p>
        </div>
      ) : null}
    </StudentBillingPageShell>
  );
}