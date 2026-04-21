"use client";

import { BadgeCheck, LogIn, ShieldCheck } from "lucide-react";
import type { StudentAccountSummaryViewModel } from "../types/student-account-view-models";

type StudentProfileSummaryCardProps = {
  summary: StudentAccountSummaryViewModel;
};

function resolveFallbackInitial(name: string): string {
  return name.trim().slice(0, 1).toUpperCase() || "S";
}

function MetricCell({
  icon,
  label,
  value,
  divider = true,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  divider?: boolean;
}) {
  return (
    <div className="relative flex flex-1 flex-col items-center justify-center px-2 py-4 text-center">
      <div className="mb-1.5 flex h-6 w-6 items-center justify-center text-primary-foreground/80 sm:h-7 sm:w-7">
        {icon}
      </div>

      <p className="text-[10px] font-bold uppercase tracking-wider text-primary-foreground/70">
        {label}
      </p>

      <p className="mt-1 text-xs font-bold text-primary-foreground sm:text-sm">
        {value}
      </p>

      {divider ? (
        <div className="absolute right-0 top-1/2 hidden h-10 w-px -translate-y-1/2 bg-primary-foreground/20 sm:block" />
      ) : null}
    </div>
  );
}

export function StudentProfileSummaryCard({
  summary,
}: StudentProfileSummaryCardProps) {
  return (
    <div className="relative rounded-[2rem] bg-card px-5 pb-6 pt-16 shadow-[0_8px_30px_rgba(0,0,0,0.06)] dark:shadow-[0_8px_30px_rgba(0,0,0,0.4)] sm:px-8 sm:pb-8 sm:pt-20">
      <div className="absolute left-1/2 top-0 z-10 -translate-x-1/2 -translate-y-1/2">
        <div className="flex h-[104px] w-[104px] items-center justify-center overflow-hidden rounded-full border-[6px] border-card bg-background shadow-sm sm:h-[120px] sm:w-[120px]">
          {summary.profileImageUrl ? (
            <img
              src={summary.profileImageUrl}
              alt="Student profile"
              className="h-full w-full object-cover"
              loading="lazy"
              referrerPolicy="no-referrer"
            />
          ) : (
            <div className="text-3xl font-semibold text-muted-foreground">
              {resolveFallbackInitial(summary.fullName)}
            </div>
          )}
        </div>
      </div>

      <div className="mt-2 text-center">
        <h2 className="text-[1.5rem] font-bold tracking-tight text-foreground sm:text-[1.85rem]">
          {summary.fullName}
        </h2>
      </div>

      <div className="mx-auto mt-6 max-w-[440px] overflow-hidden rounded-[1.5rem] bg-primary shadow-md">
        <div className="flex flex-col items-stretch sm:flex-row sm:items-center sm:justify-between">
          <MetricCell
            icon={<ShieldCheck className="h-4 w-4" />}
            label="Account"
            value={summary.accountStatusLabel}
          />

          <div className="mx-6 h-px bg-primary-foreground/20 sm:hidden" />

          <MetricCell
            icon={<BadgeCheck className="h-4 w-4" />}
            label="Onboarding"
            value={summary.onboardingStatusLabel}
          />

          <div className="mx-6 h-px bg-primary-foreground/20 sm:hidden" />

          <MetricCell
            icon={<LogIn className="h-4 w-4" />}
            label="Sign in"
            value={summary.providerLabel}
            divider={false}
          />
        </div>
      </div>
    </div>
  );
}