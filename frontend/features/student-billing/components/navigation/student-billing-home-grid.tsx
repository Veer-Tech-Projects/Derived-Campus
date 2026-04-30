"use client";

import {
  CreditCard,
  History,
  LayoutDashboard,
  Wallet,
} from "lucide-react";

import { StudentBillingEntryCard } from "./student-billing-entry-card";

export function StudentBillingHomeGrid() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StudentBillingEntryCard
        href="/student-billing/overview"
        title="Overview"
        description="See your billing summary, low-credit signals, and recent verified activity."
        icon={LayoutDashboard}
      />

      <StudentBillingEntryCard
        href="/student-billing/plans"
        title="Subscriptions"
        description="Compare credit packs and securely start a new purchase flow."
        icon={CreditCard}
      />

      <StudentBillingEntryCard
        href="/student-billing/wallet"
        title="Wallet"
        description="Review your available credits and long-term purchase and usage totals."
        icon={Wallet}
      />

      <StudentBillingEntryCard
        href="/student-billing/history"
        title="History"
        description="Track payment records and credit ledger activity in one place."
        icon={History}
      />
    </div>
  );
}