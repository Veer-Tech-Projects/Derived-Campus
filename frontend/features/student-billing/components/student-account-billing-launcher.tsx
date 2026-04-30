"use client";

import {
  ArrowRight,
  CreditCard,
  History,
  LayoutDashboard,
  Wallet,
} from "lucide-react";



type StudentAccountBillingLauncherProps = {

  availableCredits: number | null;
  isLoading: boolean;
  errorMessage: string | null;
  onOpenOverview: () => void;
  onOpenSubscriptions: () => void;
  onOpenWallet: () => void;
  onOpenHistory: () => void;
};

type LauncherCardProps = {
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  onClick: () => void;
};

function LauncherCard({
  title,
  description,
  icon: Icon,
  onClick,
}: LauncherCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="group w-full rounded-[2rem] border border-border bg-card p-5 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md sm:p-6"
    >
      <div className="flex h-full flex-col gap-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <Icon className="h-6 w-6" />
          </div>

          <div className="flex h-10 w-10 items-center justify-center rounded-full border border-border text-muted-foreground transition-colors group-hover:border-primary/30 group-hover:text-primary">
            <ArrowRight className="h-4 w-4" />
          </div>
        </div>

        <div>
          <h3 className="text-lg font-semibold text-foreground">{title}</h3>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {description}
          </p>
        </div>
      </div>
    </button>
  );
}

export function StudentAccountBillingLauncher({

  availableCredits,
  isLoading,
  errorMessage,
  onOpenOverview,
  onOpenSubscriptions,
  onOpenWallet,
  onOpenHistory,
}: StudentAccountBillingLauncherProps) {
  return (
    <div className="space-y-6">
      <div className="rounded-[2rem] border border-border bg-card p-5 shadow-sm sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-2xl">
            <div className="inline-flex rounded-full border border-border bg-secondary px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">
              Billing
            </div>

            <h2 className="mt-4 text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
              Open a billing section
            </h2>

            <p className="mt-3 text-sm leading-6 text-muted-foreground sm:text-base">
              Choose a billing area to review wallet health, compare
              subscriptions, inspect history, or manage your backend-verified
              credit activity.
            </p>
          </div>


        </div>
      </div>

      <div className="rounded-[2rem] border border-border bg-card p-5 shadow-sm sm:p-6">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <Wallet className="h-5 w-5" />
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Available credits
            </p>
            <p className="mt-1 text-xl font-semibold text-foreground">
              {typeof availableCredits === "number" ? availableCredits : "—"}
            </p>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="rounded-[2rem] border border-border bg-card p-6 shadow-sm">
          <div className="flex items-center justify-center py-10">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        </div>
      ) : null}

      {!isLoading && errorMessage ? (
        <div className="rounded-[2rem] border border-border bg-card p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-foreground">
            Billing summary is temporarily unavailable
          </h3>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {errorMessage}
          </p>
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <LauncherCard
          title="Overview"
          description="See your billing summary, low-credit signals, and recent verified activity."
          icon={LayoutDashboard}
          onClick={onOpenOverview}
        />

        <LauncherCard
          title="Subscriptions"
          description="Compare available credit packs and start a secure purchase flow."
          icon={CreditCard}
          onClick={onOpenSubscriptions}
        />

        <LauncherCard
          title="Wallet"
          description="Review your available credits and long-term billing totals."
          icon={Wallet}
          onClick={onOpenWallet}
        />

        <LauncherCard
          title="History"
          description="Track payment records and credit ledger activity in one place."
          icon={History}
          onClick={onOpenHistory}
        />
      </div>
    </div>
  );
}