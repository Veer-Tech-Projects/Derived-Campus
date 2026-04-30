"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { useStudentAuth } from "@/features/student-auth/hooks/use-student-auth";
import { studentAuthRouteConfig } from "@/features/student-auth/config/student-auth-route-config";
import { StudentBillingPageShell } from "@/features/student-billing/components/layout/student-billing-page-shell";
import { StudentAvailableCreditsBadge } from "@/features/student-billing/components/widgets/student-available-credits-badge";
import { StudentBillingTransactionsList } from "@/features/student-billing/components/sections/student-billing-transactions-list";
import { StudentBillingLedgerList } from "@/features/student-billing/components/sections/student-billing-ledger-list";
import { StudentBillingEmptyState } from "@/features/student-billing/components/widgets/student-billing-empty-state";
import { useStudentBillingOverview } from "@/features/student-billing/hooks/use-student-billing-overview";
import type { StudentAvailableCreditsBadgeViewModel } from "@/features/student-billing/types/student-billing-view-models";

type HistoryMode = "payments" | "credits";


export default function StudentBillingHistoryPage() {
  const router = useRouter();
  const { status, accessToken } = useStudentAuth();

  const [historyMode, setHistoryMode] = useState<HistoryMode>("payments");

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

  const payments = overviewQuery.viewModel?.recentTransactions ?? [];
  const creditActivity = overviewQuery.viewModel?.recentLedgerEntries ?? [];


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
      title="Billing history"
      description="Review payment records and credit ledger activity from your backend-synchronized billing history."
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
            Unable to load billing history
          </h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {overviewQuery.error?.message ??
              "Billing history could not be loaded right now."}
          </p>
        </div>
      ) : null}

      {!overviewQuery.isLoading &&
      !overviewQuery.isError &&
      overviewQuery.viewModel ? (
        <div className="space-y-6">
          <div className="rounded-[2rem] border border-border bg-card p-2 shadow-sm">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setHistoryMode("payments")}
                className={[
                  "inline-flex rounded-[1rem] px-4 py-2.5 text-sm font-semibold transition-all",
                  historyMode === "payments"
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                ].join(" ")}
              >
                Payments
              </button>

              <button
                type="button"
                onClick={() => setHistoryMode("credits")}
                className={[
                  "inline-flex rounded-[1rem] px-4 py-2.5 text-sm font-semibold transition-all",
                  historyMode === "credits"
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                ].join(" ")}
              >
                Credit activity
              </button>
            </div>
          </div>

          {historyMode === "payments" ? (
            <>
              {payments.length === 0 ? (
                <StudentBillingEmptyState
                  title="No payment history yet"
                  description="Your completed or pending billing transactions will appear here once you start purchasing credits."
                />
              ) : (
                <StudentBillingTransactionsList items={payments} />
              )}
            </>
          ) : (
            <>
              {creditActivity.length === 0 ? (
                <StudentBillingEmptyState
                  title="No credit activity yet"
                  description="Your billing ledger will appear here after backend-verified credit purchases or future usage events."
                />
              ) : (
                <StudentBillingLedgerList items={creditActivity} />
              )}
            </>
          )}
        </div>
      ) : null}

      {!overviewQuery.isLoading &&
      !overviewQuery.isError &&
      !overviewQuery.viewModel ? (
        <div className="rounded-[2rem] border border-border bg-card p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-foreground">
            Billing history is unavailable
          </h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            We could not build the history page from backend billing data.
          </p>
        </div>
      ) : null}
    </StudentBillingPageShell>
  );
}