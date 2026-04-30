"use client";

import { useState } from "react";
import type { BillingOverviewViewModel } from "../../types/student-billing-view-models";
import { StudentBillingLedgerList } from "./student-billing-ledger-list";
import { StudentBillingTransactionsList } from "./student-billing-transactions-list";

type HistoryMode = "payments" | "credits";

type StudentBillingHistorySectionProps = {
  viewModel: BillingOverviewViewModel;
};

export function StudentBillingHistorySection({
  viewModel,
}: StudentBillingHistorySectionProps) {
  const [mode, setMode] = useState<HistoryMode>("payments");

  return (
    <div className="space-y-6">
      <div className="rounded-[2rem] border border-border bg-card p-2 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setMode("payments")}
            className={[
              "inline-flex rounded-[1rem] px-4 py-2.5 text-sm font-semibold transition-all",
              mode === "payments"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:bg-secondary hover:text-foreground",
            ].join(" ")}
          >
            Payments
          </button>
          <button
            type="button"
            onClick={() => setMode("credits")}
            className={[
              "inline-flex rounded-[1rem] px-4 py-2.5 text-sm font-semibold transition-all",
              mode === "credits"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:bg-secondary hover:text-foreground",
            ].join(" ")}
          >
            Credit activity
          </button>
        </div>
      </div>

      {mode === "payments" ? (
        <StudentBillingTransactionsList items={viewModel.recentTransactions} />
      ) : (
        <StudentBillingLedgerList items={viewModel.recentLedgerEntries} />
      )}
    </div>
  );
}